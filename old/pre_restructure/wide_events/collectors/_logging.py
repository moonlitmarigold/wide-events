from .base import *
import pluggy
from ..context.log import LogContext

logging_hookspec = pluggy.HookspecMarker("wide_events")
logging_hookimpl = pluggy.HookimplMarker("wide_events")

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

LOGGING_COLLECTORS = ClassRegistry["LoggingCollector"](attr_name="name", unique=True)

class LoggingCollector(AutoRegister(LOGGING_COLLECTORS), BaseCollector, ABC):
    """A collector for `log_event`; each concrete subclass registers itself in `LOGGING_COLLECTORS` under its
    `name`."""

    hook_names = ("on_create", "on_exception", "on_finish")
    context = LogContext

    @staticmethod
    @cache
    def return_pm():
        """The `PluginManager` with `LoggingHooks` and every key of `LOGGING_COLLECTORS` registered, built on the
        first call and cached per class."""
        pm = pluggy.PluginManager("wide_events")
        pm.add_hookspecs(LoggingHooks)
        for collector in LOGGING_COLLECTORS.values(): # TODO: Replace with settings DEFAULT COLLECTOR
            pm.register(collector())
        return pm

