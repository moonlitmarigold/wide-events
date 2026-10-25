import logging
from typing import Any, ClassVar

import structlog

from .handlers import DebugLogHandler


class Debug:
    """Print replacement for tests: console only, always on, tagged with the calling file and line."""

    logger_name: ClassVar[str] = "wide_events.debug"
    logger: ClassVar[structlog.stdlib.BoundLogger | None] = None

    callsite: ClassVar[structlog.processors.CallsiteParameterAdder] = structlog.processors.CallsiteParameterAdder(
        {structlog.processors.CallsiteParameter.FILENAME, structlog.processors.CallsiteParameter.LINENO},
        additional_ignores=[__name__],
    )

    @classmethod
    def configure(cls, shared_processors: tuple):
        """Set up the debug logger with the app's shared processors plus the call site."""
        stdlib_logger = logging.getLogger(cls.logger_name)
        for old in stdlib_logger.handlers:
            old.close()
        # no FileLogHandler and no propagation: debug output never reaches the log file
        stdlib_logger.handlers = [DebugLogHandler.build()]
        stdlib_logger.setLevel(logging.DEBUG)
        stdlib_logger.propagate = False

        cls.logger = structlog.wrap_logger(
            stdlib_logger,
            processors=[*shared_processors, cls.callsite, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
            wrapper_class=structlog.stdlib.BoundLogger,
        )

    @classmethod
    def log(cls, event: str = "debug", **fields: Any):
        """Print `fields` to the console, e.g. `debug(path=path)`. Exported as `debug`."""
        if cls.logger is None:
            raise RuntimeError("debug() was called before LogConfig.configure()")
        cls.logger.debug(event, **fields)


debug = Debug.log
