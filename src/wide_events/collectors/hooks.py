import pluggy

logging_hookspec = pluggy.HookspecMarker("wide_events")
logging_hookimpl = pluggy.HookimplMarker("wide_events")
# same project name as the logging marker, so these impls also fit `LoggingHooks` until funccall gets its own specs
func_call_hookimpl = pluggy.HookimplMarker("wide_events")

class LoggingHooks:  # was the enum
    """The pluggy hookspecs of the `log_event` phases, which `LoggingCollector` subclasses implement."""

    @logging_hookspec
    def on_create(self, name, func, args, kwargs):
        """Called by `log_event` after it opens the event, before the decorated function runs."""
    @logging_hookspec
    def on_exception(self, name, func, args, kwargs, exception):
        """The phase for when the decorated function raises; `log_event` does not call it yet."""
    @logging_hookspec
    def on_finish(self, name, func, args, kwargs, result):
        """The phase for when the decorated function returns; `log_event` does not call it yet."""
