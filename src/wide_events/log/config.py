import logging
from typing import ClassVar

import structlog

from .debug import Debug
from .handlers import CONSOLE_LOGGER, EVENT_LOGGER, ConsoleLogHandler, LogHandler


class LogConfig:
    """Logging setup for an app, on the root logger: the app's loggers, its libraries' and third-party ones all end
    in the same handlers. An app subclasses it and sets `name`, which every record carries as `app`."""

    name: ClassVar[str | None] = None
    level: ClassVar[int] = logging.INFO
    handlers: ClassVar[tuple[type[LogHandler], ...]] = (ConsoleLogHandler,)
    # logger name -> level, to turn down noisy third-party loggers, e.g. {"pyinfra": logging.WARNING}
    quiet: ClassVar[dict[str, int]] = {}

    processors: ClassVar[tuple] = (
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    )

    # what the last configure() put on the root logger; set on LogConfig itself, so every subclass replaces it
    installed: ClassVar[list[logging.Handler]] = []

    @classmethod
    def configure(cls):
        """Put the handlers on the root logger and configure structlog and Debug. Safe to call again: the handlers
        of the last call are closed, and handlers wide_events did not add (e.g. pytest's) stay."""
        if cls.name is None:
            raise TypeError(f"{cls.__qualname__} has no app name: set `name`, e.g. 'myapp'")
        root = logging.getLogger()
        for old in LogConfig.installed:
            root.removeHandler(old)
            old.close()
        # third-party records get the same fields (logger, level, app, ...) as structlog's, and the core's wide events
        # their fields; add_wide_event goes first so the shared fields win, as they do for structlog's own records
        foreign_pre_chain = (cls.add_wide_event, cls.add_app_name, *cls.processors)
        LogConfig.installed = [handler.build(foreign_pre_chain) for handler in cls.handlers]
        for handler in LogConfig.installed:
            root.addHandler(handler)
        root.setLevel(cls.level)
        for name, level in cls.quiet.items():
            logging.getLogger(name).setLevel(level)

        structlog.configure(
            processors=[cls.add_app_name, *cls.processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        # without the app name: debug output never reaches the log file
        Debug.configure(cls.processors)

    @classmethod
    def add_app_name(cls, logger, method_name: str, event_dict: dict) -> dict:
        """Processor that adds `name` to every record as `app`."""
        event_dict["app"] = cls.name
        return event_dict

    @staticmethod
    def add_wide_event(logger, method_name: str, event_dict: dict) -> dict:
        """Processor for stdlib records that spreads the fields of a wide event from `WideEvent.emit` (`record.event`)
        into the record."""
        record = event_dict["_record"]
        if record.name != EVENT_LOGGER:
            return event_dict
        return {**record.event, **event_dict}

    @classmethod
    def get_logger(cls, name:str):
        """The structlog logger called `name`."""
        return structlog.get_logger(name)

class LogClass:
    """Mixin that gives instances a structlog `logger`, named by `logger_name` or else by the class's module."""

    # plain class attributes, so classmethods reach them via `cls` too
    logger = structlog.get_logger(__name__)
    # for single lines that only reach the console; the log file gets the wide event instead
    console_logger = structlog.get_logger(CONSOLE_LOGGER)

    @staticmethod
    def file_logger():
        """Write a finished wide event as one record that only reaches the log file, never the console."""
        return structlog.get_logger(EVENT_LOGGER)


def divider(name: str = ""):
    """Print '===== name =====' across the console as an INFO line, `name` centered; never in the log file."""
    structlog.get_logger(CONSOLE_LOGGER).info(name, divider=True)
