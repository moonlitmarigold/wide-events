import logging

from .context import ContextList
from .blocks import BlockAlreadyAttached, ContextBlock, EventBlock, StatefulEventBlock, ExceptionEvent, HookErrorEvent, TimerEventBlock
#from .event import WideEvent, log_event
from .checks import Checks, InlineCheck
from .results import MultiCheckResult, SingleCheckResult, Status

# a library stays silent until the app configures logging, e.g. with DEFAULT_LOGGING
logging.getLogger("wide_events").addHandler(logging.NullHandler())
