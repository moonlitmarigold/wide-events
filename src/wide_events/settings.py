from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cached_property
from logging.config import dictConfig
from typing import ClassVar

import pluggy

from .collectors import FUNCCALL_COLLECTORS, FuncCallCollector, LOGGING_COLLECTORS, LoggingCollector
from .event import EventBlock, SampleLogEvent


class LoggerNames(StrEnum):
    """The names of the package's loggers, for `logging.getLogger` and the `loggers` of `DEFAULT_LOGGING`."""

    EVENT_LOGGER = "wide_events.event"
    FUNC_CALL_LOGGER = "wide_events.func_call"
    DEBUG = "wide_events.debug"

# TODO: Document the logging settings: what each handler/logger is for, that the console handler is WARNING (so
#  events at INFO never show there), and how to route events elsewhere (own handler + json formatter + propagate=False)

# Passed to `logging.config.dictConfig`, as Django's LOGGING setting. Use it as is, or `deepcopy` it and change
# what differs, e.g. `config["handlers"]["file"]["filename"]`. The console handler needs the `log` extra (rich).
DEFAULT_LOGGING = {
    "version": 1,
    # otherwise loggers created at import time, e.g. wide_events.checks, are silenced
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": ["levelname", "name", "message"],
            "rename_fields": {"levelname": "loglevel", "name": "logger"},
            "timestamp": True,
        },
        # for reading events on a console; not for the file, which needs one event per line
        "json_indent": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": ["levelname", "name", "message"],
            "rename_fields": {"levelname": "loglevel", "name": "logger"},
            "timestamp": True,
            "json_indent": 4,
        },
    },
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            # the progress display shows normal flow; the console only gets problems
            "level": "WARNING",
            # shared with the progress display, otherwise log lines overwrite the live progress bar
            "console": "ext://wide_events.terminal.Terminal.console",
            "rich_tracebacks": True,
        },
        # only used when `Settings(debug=True)` routes the debug logger here
        "debug":{
            "class": "rich.logging.RichHandler",
            "level": "DEBUG",
            # shared with the progress display, otherwise log lines overwrite the live progress bar
            "console": "ext://wide_events.terminal.Terminal.console",
            "rich_tracebacks": True,
        },
        # only used when `Settings(debug_events=True)` adds it to the event logger
        "debug_json": {
            "class": "rich.logging.RichHandler",
            "formatter": "json_indent",
            # shared with the progress display, otherwise log lines overwrite the live progress bar
            "console": "ext://wide_events.terminal.Terminal.console",
            # the event JSON carries level, logger and timestamp itself; rich's columns would only squeeze it
            "show_time": False,
            "show_level": False,
            "show_path": False,
        },
        "file": {
            "class": "wide_events.log.handlers.FileHandler",
            "filename": "logs/wide_events.log",
            "delay": True,
            "formatter": "json",
        },
    },
    "loggers": {
        # wide events go to the file only; everything else reaches the console through the root
        LoggerNames.EVENT_LOGGER: {"handlers": ["file"], "level": "INFO", "propagate": False},
        LoggerNames.FUNC_CALL_LOGGER: {"handlers": ["file"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# The composition root of `log_event`: only the collectors named here run. pluggy calls the hooks in reverse order
# of registration, so the last one listed runs first.
DEFAULT_COLLECTORS = (
    "ExceptionCollector",
    "TimingCollector",
    "TimestampCollector",
    "OutcomeCollector",
    "IdentityCollector",
    "ResultCollector",
)

# The same for `record_function_call`.
DEFAULT_FUNC_CALL_COLLECTORS = (
    "EnvironmentCollector",
    "ArgumentsCollector",
    "ResourceCollector",
)


@dataclass(frozen=True)
class Settings:
    """The package's settings; an app builds one, or a subclass with other defaults, and calls `apply()` once.

    Input: `Settings(collectors=(*DEFAULT_COLLECTORS, "MyCollector"), logging=my_logging).apply()`

    Attributes:
        collectors: Keys of `LOGGING_COLLECTORS` that `log_event` runs, e.g. `"TimingCollector"`.
        func_call_collectors: Keys of `FUNCCALL_COLLECTORS` that `record_function_call` runs.
        event_block: The block behind `LogEvent`. Not read yet: `LogEvent` is still bound at import.
        logging: Passed to `dictConfig` by `apply()`; None leaves logging to the app.
        debug: `apply()` adds the debug logger at DEBUG on the `debug` handler, so `terminal.debug()` shows.
        debug_logger_name: The logger `terminal.debug()` writes to.
        debug_events: `apply()` adds the `debug_json` handler to the event and function-call loggers, so each wide
            event also shows on the console as indented JSON.
    """

    collectors: tuple[str, ...] = DEFAULT_COLLECTORS
    func_call_collectors: tuple[str, ...] = DEFAULT_FUNC_CALL_COLLECTORS
    event_block: type[EventBlock] = SampleLogEvent
    logging: dict | None = field(default_factory=lambda: deepcopy(DEFAULT_LOGGING))
    debug:bool = False
    debug_logger_name:str = LoggerNames.DEBUG
    debug_events:bool = False

    _active: ClassVar["Settings | None"] = None

    def __post_init__(self):
        for field_name, registry in (("collectors", LOGGING_COLLECTORS),
                                     ("func_call_collectors", FUNCCALL_COLLECTORS)):
            unknown = [name for name in getattr(self, field_name) if name not in registry]
            if unknown:
                raise ValueError(
                    f"Unknown {field_name} {unknown}. Registered: {list(registry.keys())}. "
                    f"A collector registers when its module is imported, so import it before building the settings."
                )
        if not (isinstance(self.event_block, type) and issubclass(self.event_block, EventBlock)):
            raise TypeError(f"event_block must be an EventBlock subclass (got {self.event_block!r}).")

    def apply(self) -> "Settings":
        """Run `dictConfig(self.logging)` unless it is None, and make these the settings `log_event` reads."""

        if self.logging is not None:
            dictConfig(self.logging_config())
        # on the base class, so `AppSettings().apply()` is seen by `Settings.active()` too
        Settings._active = self
        return self

    def logging_config(self) -> dict:
        """`logging` with the debug switches applied, as a new dict: `self.logging` may be the caller's own config.

        `debug` -> `loggers[debug_logger_name] = {"handlers": ["debug"], "level": "DEBUG", ...}`
        `debug_events` -> `loggers["wide_events.event" | "wide_events.func_call"]["handlers"] += ["debug_json"]`
        """
        loggers = dict(self.logging.get("loggers", {}))
        if self.debug:
            loggers[self.debug_logger_name] = {"handlers": ["debug"], "level": "DEBUG", "propagate": False}
        else:
            # also when off: dictConfig keeps a logger it isn't given as it was, so an earlier
            # `apply()` with debug=True would stay on. A debug logger in `logging` itself wins.
            loggers.setdefault(self.debug_logger_name, {"handlers": [], "level": "NOTSET", "propagate": True})
        if self.debug_events:
            for name in (LoggerNames.EVENT_LOGGER, LoggerNames.FUNC_CALL_LOGGER):
                event_logger = loggers.get(name, {})
                loggers[name] = {**event_logger, "handlers": [*event_logger.get("handlers", []), "debug_json"]}
        return {**self.logging, "loggers": loggers}

    @classmethod
    def active(cls) -> "Settings":
        """The settings of the last `apply()`, else the defaults, with logging left unconfigured."""
        if Settings._active is None:
            # no dictConfig here: a library must not configure logging just because it was imported
            Settings._active = Settings()
        return Settings._active

    @cached_property
    def plugin_manager(self) -> pluggy.PluginManager:
        """The `PluginManager` of `collectors`, built on first access and kept for this instance."""
        return LoggingCollector.build_pm(self.collectors)

    @cached_property
    def func_call_plugin_manager(self) -> pluggy.PluginManager:
        """The `PluginManager` of `func_call_collectors`, built on first access and kept for this instance."""
        return FuncCallCollector.build_funccall_pm(self.func_call_collectors)