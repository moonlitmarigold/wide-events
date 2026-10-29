import logging
from pathlib import Path
from typing import ClassVar

import structlog
from rich.text import Text

from ..event import EVENT_LOGGER
from ..terminal import Terminal

# single lines for the console only; finished wide events (EVENT_LOGGER) go to the log file only
CONSOLE_LOGGER = "wide_events.console"


class RichConsoleHandler(logging.Handler):
    """Writes already-rendered log lines through the shared rich Console."""

    def emit(self, record: logging.LogRecord):
        try:
            # structlog records carry their fields as a dict in record.msg, plain stdlib records a str
            if isinstance(record.msg, dict) and record.msg.get("divider"):
                # a rule, not a log line: no level prefix
                Terminal.console.rule(record.msg["event"], characters="=")
                return
            # ConsoleRenderer outputs ANSI, so parse it as ANSI instead of rich markup;
            # soft_wrap stops rich from re-wrapping key=value pairs
            Terminal.console.print(Text.from_ansi(self.format(record)), soft_wrap=True)
        except Exception:
            self.handleError(record)


class RichJsonHandler(logging.Handler):
    """Pretty-prints already-rendered JSON log lines through the shared rich Console."""

    def emit(self, record: logging.LogRecord):
        try:
            Terminal.console.print_json(self.format(record))
        except Exception:
            self.handleError(record)


class LevelPrefix:
    """Console column that renders the level as 'WARNING:', colored like structlog's default levels."""

    def __init__(self, colors: bool):
        self.styles = structlog.dev.ConsoleRenderer.get_default_level_styles(colors)
        self.reset = structlog.dev.RESET_ALL if colors else ""

    def __call__(self, key: str, value: object) -> str:
        return f"{self.styles.get(str(value), '')}{str(value).upper()}:{self.reset}"


class Plain:
    """Console column that renders only the value, without 'key='."""

    def __call__(self, key: str, value: object) -> str:
        return str(value)


class KeyValue:
    """Console column that renders 'key=value', for keys without their own column."""

    def __call__(self, key: str, value: object) -> str:
        return f"{key}={value!r}"


class Hidden:
    """Console column that drops its key; the full fields still land in the JSON log file."""

    def __call__(self, key: str, value: object) -> str:
        return ""


class DropLoggers(logging.Filter):
    """Drops the records of the loggers called `names`, e.g. the wide events on the console."""

    def __init__(self, *names: str):
        super().__init__()
        self.names = names

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name not in self.names


class LogHandler:
    """Base for log handlers: a subclass picks the stdlib handler, its level, its filters and its renderers."""

    level: ClassVar[int] = logging.NOTSET
    filters: ClassVar[tuple[logging.Filter, ...]] = ()
    # renderers run per handler; the shared processors run once in LogConfig
    processors: ClassVar[tuple] = ()

    @classmethod
    def handler(cls) -> logging.Handler:
        """Create the stdlib handler. Subclasses must override it."""
        raise NotImplementedError()

    @classmethod
    def build(cls, foreign_pre_chain: tuple = ()) -> logging.Handler:
        """Create the stdlib handler with this class's level and a formatter running its processors.

        Args:
            foreign_pre_chain: Processors for records from plain stdlib loggers (third-party libraries), which skip
                structlog's processors, e.g. LogConfig's shared ones.
        """
        handler = cls.handler()
        handler.setLevel(cls.level)
        for log_filter in cls.filters:
            handler.addFilter(log_filter)
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *cls.processors],
                foreign_pre_chain=list(foreign_pre_chain),
            )
        )
        return handler


class ConsoleLogHandler(LogHandler):
    """Terminal output for warnings and errors, as 'WARNING: <event>' with the other fields hidden."""

    # the progress display shows normal flow; the console only gets problems
    level = logging.WARNING

    @staticmethod
    def renderer(fields) -> structlog.dev.ConsoleRenderer:
        """Build the console renderer.

        Args:
            fields: Column formatter for every key other than level and event, e.g. Hidden() or KeyValue().
        """
        return structlog.dev.ConsoleRenderer(
            # "WARNING: <event>", then `fields` renders every other key (the "" column).
            # with columns, colors are set per column (LevelPrefix), not via colors=
            columns=[
                structlog.dev.Column("level", LevelPrefix(Terminal.console.is_terminal)),
                structlog.dev.Column("event", Plain()),
                structlog.dev.Column("", fields),
            ],
            # locals can hold secrets (tokens, env), keep them out of the terminal
            exception_formatter=structlog.dev.RichTracebackFormatter(show_locals=False),
        )

    processors = (renderer(Hidden()),)
    # a wide event is one long record for the file; the console gets the single lines
    filters = (DropLoggers(EVENT_LOGGER),)

    @classmethod
    def handler(cls) -> logging.Handler:
        return RichConsoleHandler()


class VerboseConsoleLogHandler(ConsoleLogHandler):
    """Console handler that also shows INFO events."""

    level = logging.INFO


class DebugLogHandler(ConsoleLogHandler):
    """Console handler for debug(): every level, with the key=value pairs shown."""

    # debug() must always print, whatever the console level is
    level = logging.DEBUG
    # debug() is for inspecting values, so it keeps the key=value pairs
    processors = (ConsoleLogHandler.renderer(KeyValue()),)


class FileLogHandler(LogHandler):
    """Writes every event as one JSON line to the log file, creating its folder if needed."""

    # no default: the log file belongs to the app, so a subclass sets it
    path: ClassVar[Path | None] = None
    # console lines are already summed up in the wide events
    filters = (DropLoggers(CONSOLE_LOGGER),)
    processors = (
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    )

    @classmethod
    def handler(cls) -> logging.Handler:
        if cls.path is None:
            raise TypeError(f"{cls.__qualname__} has no log file: subclass FileLogHandler and set `path`")
        cls.path.parent.mkdir(parents=True, exist_ok=True)
        return logging.FileHandler(cls.path)


class FileMirrorLogHandler(FileLogHandler):
    """Debug handler that prints what FileLogHandler writes to the console, pretty-printed; no file needed."""

    # same filters and JSON renderer as the file, so the console shows exactly what lands in it

    @classmethod
    def handler(cls) -> logging.Handler:
        return RichJsonHandler()
