"""Prototype: django-wide-events collectors on pluggy (see docs/DECISIONS.md, decision 4).

Run with `uv run --no-project --with pluggy python docs/prototypes/pluggy_collectors.py`. Verified with pluggy 1.7.0:
tryfirst/trylast replace HookPosition, a wrapper=True hook replaces moving Duration first and last, and
Collector.__init_subclass__ isolates each hook so one raising collector never stops the others.
"""
import functools, time, traceback
import pluggy

hookspec = pluggy.HookspecMarker("wide_events")
hookimpl = pluggy.HookimplMarker("wide_events")
event: dict = {}

class Phases:
    @hookspec
    def on_create(self, request): ...
    @hookspec
    def on_finish(self, request, response): ...

class Collector:
    """Every hook is isolated: an exception lands in the event instead of stopping the other collectors."""
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name in ("on_create", "on_finish"):
            func = cls.__dict__.get(name)
            if func is None or getattr(func, "_isolated", False):
                continue
            if getattr(func, "wide_events_impl", {}).get("wrapper"):
                continue  # wrappers are generators, they see exceptions themselves
            @functools.wraps(func)
            def safe(self, *args, _func=func, _name=name, **kwargs):
                try:
                    return _func(self, *args, **kwargs)
                except Exception as exc:
                    event.setdefault("hook_errors", []).append(
                        {"hook": f"{type(self).__name__}.{_name}", "error": repr(exc)})
            safe._isolated = True
            setattr(cls, name, safe)

class Duration(Collector):
    @hookimpl(wrapper=True)          # replaces HookPosition(first on create ... last on finish)
    def on_finish(self, request, response):
        start = request["start"]
        result = yield               # every other on_finish runs here
        event["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        event["order"].append("Duration(after all)")
        return result

class Start(Collector):
    @hookimpl(tryfirst=True)
    def on_create(self, request):
        request["start"] = time.perf_counter(); event["order"] = ["Start(first)"]

class Status(Collector):
    @hookimpl
    def on_finish(self, request, response):
        event["status_code"] = response; event["order"].append("Status")

class Broken(Collector):
    @hookimpl
    def on_finish(self, request, response):
        raise ValueError("boom")

class Last(Collector):
    @hookimpl(trylast=True)
    def on_finish(self, request, response):
        event["order"].append("Last(trylast)")

pm = pluggy.PluginManager("wide_events")
pm.add_hookspecs(Phases)
for c in (Start, Duration, Status, Broken, Last):   # composition root: this list decides what runs
    pm.register(c())
request = {}
pm.hook.on_create(request=request)
pm.hook.on_finish(request=request, response=200)
print(event)
print("on_finish impls:", [type(i.plugin).__name__ for i in pm.hook.on_finish.get_hookimpls()])
