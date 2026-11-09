import pluggy

logging_hookspec = pluggy.HookspecMarker("wide_events")
logging_hookimpl = pluggy.HookimplMarker("wide_events")
# same project name as the logging marker: function-call collectors implement `LoggingHooks` too
func_call_hookimpl = pluggy.HookimplMarker("wide_events")

class LoggingHooks:  # was the enum
    """The pluggy hookspecs of the `log_event` and `record_function_call` phases, which `LoggingCollector` and
    `FuncCallCollector` subclasses implement."""

    @logging_hookspec
    def on_create(self, name, func, args, kwargs):
        """Called after the event is opened, before the decorated function runs."""
    @logging_hookspec
    def on_exception(self, name, func, args, kwargs, exception):
        """Called when the decorated function raises, before the exception is re-raised."""
    @logging_hookspec
    def on_finish(self, name, func, args, kwargs, result):
        """Called when the decorated function returns."""
