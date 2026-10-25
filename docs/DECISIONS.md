# Open decisions

Decisions that have to be made before the first PyPI release. Each one is **open** until it is answered here.

## 1. License — open

- django-wide-events is GPL-3.0-or-later. termlog and execflow have no license.
- All three are my own code, so the merged package can use any license.
- Note: GPL makes every project that imports the package GPL too. MIT or Apache-2.0 is the usual choice for a
  library that others should adopt freely.

## 2. Relative vs. absolute imports — open

- The copied code uses relative imports (`from ..context import ContextEvent`), like infra.
- The `python-code-style` skill prefers absolute imports (`from wide_events.context import ContextEvent`).
- Once decided, record the rule in the `python-code-style` skill and apply it to the whole package.

## 3. Optional dependencies — decided (2026-10-25)

- The core needs only the stdlib; `rich`, `structlog` and `questionary` moved to extras. One distribution,
  split into layers that only import from the layers above them:

  | Layer                  | Install                  | Contents                                                     |
  |------------------------|--------------------------|--------------------------------------------------------------|
  | core                   | `wide-events`            | `context`, `blocks`, `event`, `collectors`, `results`, `checks`, `formatters` |
  | `wide_events.terminal` | either extra             | the shared rich `Console` (`Terminal`)                       |
  | `wide_events.log`      | `wide-events[log]`       | `LogConfig`, handlers, `Debug`                               |
  | `wide_events.ui`       | `wide-events[ui]`        | `ProgressDisplay`, `ProgressBar`, `Menu`                     |

- The event lifecycle (`WideEvent.wrap`, `log_event`) moved from `log` to the core `event` module. It emits
  through stdlib `logging` with the fields on `record.event`, which `JSONFORMATTER` and `LogConfig` both render.
- `checks` no longer imports `log`: it logs a missing argument through stdlib `logging` and dropped its
  `debug()` calls, so it runs without `LogConfig.configure()`.

## 4. Collector engine: own implementation vs. pluggy — open

Found while researching whether the collector design already exists (2026-10-24).

- No general-purpose Python wide-event library with pluggable collectors exists; django-wide-events is the
  only one on PyPI. The closest design is evlog (TypeScript), whose plugins have optional lifecycle hooks
  (`onRequestStart`, `enrich`, `keep`, `drain`, `onRequestFinish`).
- The hook mechanics already exist in [pluggy](https://pluggy.readthedocs.io/) (pytest's plugin system, MIT,
  no dependencies):

  | Own implementation                         | pluggy                                          |
  |--------------------------------------------|-------------------------------------------------|
  | `CollectorHooks` enum                      | `@hookspec` per phase                           |
  | Hook table: only overridden methods run    | Only registered `@hookimpl`s run                |
  | `HookPosition` / `Change` (first, last)    | `tryfirst=True` / `trylast=True`                |
  | `Duration` moved first on create, last on finish | One `wrapper=True` hook around all others |
  | `BUILTIN_COLLECTORS` / `FACTORY_COLLECTORS`| `PluginManager.register(...)`                   |
  | Per-hook try/except → `HookErrorEvent`     | **Not provided**: one raising hook stops the rest |

- pluggy does not isolate errors, but a `Collector.__init_subclass__` can wrap each hook in the
  try/except that writes `HookErrorEvent`. The prototype in
  [`prototypes/pluggy_collectors.py`](prototypes/pluggy_collectors.py) verifies ordering, the wrapper and
  isolation together.
- Direction: pluggy looks good (2026-10-24); the prototype is kept for the implementation.
- What would go away: `collectors/hook_position.py`, `collectors/registry.py` and the hook-table building in
  the middleware. Event, blocks and emit stay as they are.
- OpenTelemetry was checked too and is not a fit for collectors: `SpanProcessor.on_end` gets a read-only span,
  and tail sampling isn't in the Python SDK. It stays a possible export target later.

## Also noted

- The PyPI name `wide-events` is still free (checked 2026-10-24).
