# Wide Events: design

This document describes where the idea behind `wide-events` comes from, how it carries over from web
requests to any kind of program, and what the package bundles on top: a simpler logging config, checks
and collectors.

---

## Origin

The idea comes from web development, from my package
[django-wide-events](https://github.com/moonlitmarigold/django-wide-events). It applies the *wide event*
(or *canonical log line*) pattern described at <https://loggingsucks.com/>.

Instead of writing a dozen scattered log lines while a request runs, the app collects everything that
happens to the request and logs it **once**, when the request finishes. The result is one structured JSON
log line per request.

### Example: one event per request

A single request to a picture download view produces one record like this:

```json
{
  "loglevel": "INFO",
  "message": "request",
  "logger": "wide_events.request",
  "timestamp": 1789650000.123,
  "request_id": "9f1c2e...",
  "started_at": "2026-09-17T10:00:00.000+00:00",
  "meta": {"method": "GET", "timezone": "UTC"},
  "user": {"id": 42, "username": "ada", "is_authenticated": true, "is_staff": false},
  "session": {"session_id": "b71d0a...", "session_status": "existing_session_id"},
  "picture": {"id": "abc", "is_owner": true, "timers": {"s3_fetch_ms": 12.4}},
  "route": "/pictures/abc/download/",
  "view_name": "pictures:download",
  "status_code": 200,
  "duration_ms": 48.31,
  "sample_rate": 10
}
```

Framework fields (`route`, `status_code`, `duration_ms`, `user`) sit next to domain data (`picture`).
If the view raises, the same record also carries an `error` block with `type`, `message` and `stack`.

### What this gives me

- **A better overview.** Each event is wide enough to be queried like an analytics table ("slow downloads
  by logged-in users, grouped by route") instead of grepped line by line.
- **Session traceability.** Because every event carries a `session_id`, I'm not limited to querying the
  logs of one request: I can query all requests of one user session and follow it from one request to
  the next.
- **Tail sampling.** The keep-or-drop decision is made after the event is complete, so it can depend on
  how the request turned out.

### Example: tail sampling

Tail sampling keeps every event that matters and only a fraction of the routine ones. `TailSampling` is a
plain `logging.Filter`:

1. It runs its rules against the finished event. Any rule that returns `True` keeps the event.
2. If no rule fires, the event is kept with a chance of 1 in `base_rate`, and `sample_rate` is written
   onto it so counts can be scaled back up later.
3. That chance is deterministic: it's a hash of `request_id`, so the same id always gives the same
   answer.

With `base_rate=20`, and the rules from django-wide-events:

| Event | Rule | Kept? |
|---|---|---|
| `POST /checkout/`, 201, 80 ms | non-GET/HEAD (`WriteRequest`) | always |
| `GET /pictures/`, 500 | 5xx (`ServerError`) | always |
| `GET /pictures/`, 200, 1450 ms | slow, >= 1000 ms (`SlowRequest`) | always |
| `GET /admin/`, 403 | security status (`SecurityStatus`) | always |
| `GET /pictures/`, 200, 35 ms | none | 1 in 20, with `"sample_rate": 20` |

Tail sampling is not part of this package for now (removed 2026-10-25); it stays in django-wide-events.

---

## Outside of web development

Outside the web there is no natural start and finish like a request. So instead of one wide event per
request, I build **one wide event per execution**: a CLI command, a workflow run, a deploy.

### Results as data

A new concept on top of that: every (major) operation returns a dataclass result, which can be dumped to
JSON and so lands in the wide event.

> **Not final.** The exact definition of a result is still open. What exists today is the set of
> classes in `wide_events.results`, taken from execflow.

Today's classes:

- `SingleCheckResult`: one named check with its `Status` and, if it raised, the exception type and
  traceback (via `ExceptionResult`)
- `MultiCheckResult`: the `StatusCount` of a group of checks, with each `SingleCheckResult`
- `ExecResult`: like `SingleCheckResult`, plus a `skipped()` constructor

Each one has a `dump()` that returns plain JSON data tagged with `result_name`:

```json
{
  "result_name": "MultiCheckResult",
  "success": 1, "failed": 1, "warning": 0, "skipped": 0, "queued": 0, "num": 2,
  "single_checks": [
    {"result_name": "SingleCheckResult", "name": "disk_mounted", "status": "success",
     "exception": null, "traceback": null},
    {"result_name": "SingleCheckResult", "name": "has_space", "status": "failed",
     "exception": "OSError", "traceback": "Traceback (most recent call last): ..."}
  ]
}
```

### Two kinds of logging output

The two outputs serve different readers:

1. **Visual:** human-readable lines in the terminal. Short warnings, info and CLI output, nothing more.
   This is `ConsoleLogHandler` (warnings and up, extra fields hidden) or `VerboseConsoleLogHandler` (info
   and up). Single lines for the console only go through `LogClass.console_logger`.
2. **Log files:** the wide events, one JSON line each. This is `FileLogHandler`. Finished events are
   written through `WideEvent.emit` (core, stdlib `logging`) or `LogClass.file_logger()` (structlog), both on
   the `wide_events.event` logger, which only reaches the file, never the console.

### Tree-like collection

Executions nest: a run calls steps, steps call sub-steps. The wide event follows that nesting and is
collected as a tree. `EventBlock`s are the main way to write into it.

`tests/test_wrappers.py` shows this. `MainRun` opens the event for the whole run. Each nested call that's
decorated with `log_event(name)` collects its own fields and merges them into its caller's event under
`name` when it returns:

```text
MainRun.run                      WideEvent.wrap: opens the event, emits it to the file
└── SubRun.run                   @log_event("test"): its fields land under "test"
    ├── ContextEvent.update({"test": "test"})
    ├── Exec(0).run              @log_event("exec"): its fields land under "test.exec"
    │   └── ExecEventBlock.add(0)    writes num=[0]
    ├── Exec(1).run  ->  num=[1]
    ├── Exec(2).run  ->  num=[2]
    └── Exec(3).run  ->  num=[3]
```

`ExecEventBlock` sets `append_list = True`, and `log_event` merges with lists appended, so the four
`num` lists add up instead of overwriting each other. The file gets exactly one record:

```json
{
  "test": {
    "test": "test",
    "exec": {"num": [0, 1, 2, 3]}
  },
  "event": "wide_event",
  "app": "wide-events-tests",
  "logger": "wide_events.event",
  "level": "info",
  "timestamp": "2026-10-24T20:52:34.503222Z"
}
```

Meanwhile the console only shows the four `INFO: test` lines from `console_logger`.

A block is a typed handle on one part of the tree:

```python
from wide_events import TimerEventBlock


class PictureBlock(TimerEventBlock):
    namespace = "picture"


block = PictureBlock(kwargs={"id": "abc"})
with block.timer("s3_fetch"):
    ...  # writes picture.timers.s3_fetch_ms
```

---

## Additional content

### Simpler logging config

A logging setup that feeds directly into stdlib `logging`, so the app's own loggers and third-party ones
end up in the same handlers. An app subclasses `LogConfig`, picks its handlers and calls `configure()`
once:

```python
from pathlib import Path

from wide_events.log import ConsoleLogHandler, FileLogHandler, LogConfig


class AppFileLog(FileLogHandler):
    path = Path("logs/app.log")


class AppLogConfig(LogConfig):
    name = "myapp"
    handlers = (ConsoleLogHandler, AppFileLog)


AppLogConfig.configure()
```

The terminal GUI (`wide_events.ui`) already exists from termlog and shares the same rich `Console` (`Terminal.console`) as
the log lines, so log output never overwrites it:

- `ProgressDisplay` / `ProgressBar`: a live view with one bar per workflow and a ✓, ✗ or - line per step
- `Menu`: an arrow-key choice between options, which pauses the progress display while it asks

### Checks

Checks use the results concept from above. An `InlineCheck` wraps a function: a truthy return is a
success, and a falsy return or a raise is a failure. It always returns a `SingleCheckResult`, never an
exception. `Checks` runs a group and returns a `MultiCheckResult`:

```python
from wide_events import Checks, InlineCheck


def disk_mounted(path):
    return path == "/mnt/data"


result = Checks((InlineCheck(["path"], disk_mounted),))(path="/mnt/data")
result.ok      # True when nothing failed or was skipped
result.dump()  # JSON data for the wide event
```

### Collectors

Collectors add data to the wide event automatically, without the code under observation calling them.
They follow the same principle as in django-wide-events.

A `Collector` subclass implements the hook phases it cares about from `CollectorHooks`:

- `on_create`: when the event is opened
- `on_exception`: when the observed code raises
- `on_finish` / `on_finish_no_response`: when it finishes, with or without a result

Only the phases a collector actually overrides are run. Inside a hook, `self.set(...)` merges fields into
the current event. A failing hook never breaks the run; in django-wide-events it's recorded as a
`HookErrorEvent` instead.

The order within a phase can be changed with `HookPosition`. For example `Duration` runs first on
`on_create` and last on `on_finish`, so its `duration_ms` covers every other hook:

```python
from wide_events.collectors import Change, CollectorHooks, Duration, HookPosition

HookPosition(Duration, (
    Change(CollectorHooks.on_create, 0),
    Change(CollectorHooks.on_finish, -1),
    Change(CollectorHooks.on_finish_no_response, -1),
))
```

Built-in collectors register themselves with `builtin_collector`. Right now these are `Duration` and
`Timestamp`.

> **Not final.** The hook signatures still take `request` and `response` from django-wide-events. The
> lifecycle for a non-web execution still needs its own definition.

#### Next step: collectors on pluggy

The planned direction is to build the collectors on [pluggy](https://pluggy.readthedocs.io/), the plugin
system behind pytest, instead of the own hook machinery. A working prototype is in
[`prototypes/pluggy_collectors.py`](prototypes/pluggy_collectors.py):

- each phase is a `@hookspec`, each collector method a `@hookimpl`
- `tryfirst=True` / `trylast=True` replace `HookPosition`
- `Duration` becomes one `wrapper=True` hook that runs around every other `on_finish`
- `Collector.__init_subclass__` wraps each hook in a try/except, because pluggy itself stops at the first
  raising hook; the error lands in the event as `hook_errors`

Run it with `uv run --no-project --with pluggy python docs/prototypes/pluggy_collectors.py`. The
trade-offs are in [DECISIONS.md](DECISIONS.md), decision 4.
