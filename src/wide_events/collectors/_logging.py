from .base import *
import pluggy

logging_hookspec = pluggy.HookspecMarker("wide_events")
logging_hookimpl = pluggy.HookimplMarker("wide_events")

class LoggingHooks:  # was the enum
    @logging_hookspec
    def on_create(self, request): ...
    @logging_hookspec
    def on_exception(self, request, exception): ...
    @logging_hookspec
    def on_finish(self, request, response): ...

LOGGING_COLLECTORS = ClassRegistry["LoggingCollector"](attr_name="name", unique=True)

class LoggingCollector(AutoRegister(LOGGING_COLLECTORS), BaseCollector, ABC):

    hook_names = ("on_create", "on_exception", "on_finish")

    @classmethod
    @cache
    def return_pm(cls):
        pm = pluggy.PluginManager("wide_events")
        pm.add_hookspecs(LoggingHooks)
        for collector in LOGGING_COLLECTORS: # TODO: Replace with settings DEFAULT COLLECTOR
            pm.register(collector)
        return pm

