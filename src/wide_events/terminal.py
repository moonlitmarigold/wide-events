import logging
from typing import Any, Callable, ClassVar

from rich.console import Console

from .settings import Settings


class Terminal:
    """The single rich Console. The progress display and console logs must share it,
    otherwise log lines overwrite the live progress bar."""

    # stderr keeps stdout free for the CLI's own output (e.g. `infra render > file`)
    console: ClassVar[Console] = Console(stderr=True)


# Whether debug output shows is decided by the logging config (`Settings(debug=True).apply()` sets the debug logger
# to DEBUG), not cached here: a cache taken before `apply()` would keep debug off for the rest of the run.
def _debug_logger() -> logging.Logger:
    return logging.getLogger(Settings.active().debug_logger_name)


def debug(data:Any):
    """Log `data` on the debug logger at DEBUG."""
    _debug_logger().debug(data)


def debug_exec(call:Callable[[], Any]):
    """Log `call()` on the debug logger at DEBUG; `call` only runs when debug output is on."""
    logger = _debug_logger()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(call())
