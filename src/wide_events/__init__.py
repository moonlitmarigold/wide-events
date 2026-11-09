import logging

from .context import ContextList
from .event import (BlockAlreadyAttached, ContextBlock, EventBlock, StatefulEventBlock, ExceptionEvent,
                    HookErrorEvent, LogContext, LogEvent, TimerEventBlock)
from .checks import Checks, InlineCheck
from .results import MultiCheckResult, SingleCheckResult, Status
from .settings import DEFAULT_COLLECTORS, DEFAULT_LOGGING, LoggerNames, Settings
from .recorder import log_event

__all__ = [
    "BlockAlreadyAttached", "Checks", "ContextBlock", "ContextList", "DEFAULT_COLLECTORS", "DEFAULT_LOGGING",
    "EventBlock", "ExceptionEvent", "HookErrorEvent", "InlineCheck", "LogContext", "LogEvent", "LoggerNames",
    "MultiCheckResult", "SingleCheckResult", "Settings", "StatefulEventBlock", "Status", "TimerEventBlock",
    "log_event",
]

# a library stays silent until the app configures logging, e.g. with Settings().apply()
logging.getLogger("wide_events").addHandler(logging.NullHandler())
