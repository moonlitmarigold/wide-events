import logging

# TODO: Restructure the whole project (package layout, module boundaries, what is public); the current one grew
#  piecemeal from termlog/execflow and mixes WIP (blocks, errors_2, old event) with the new collectors/logging path

from .context import ContextList
from .blocks import BlockAlreadyAttached, ContextBlock, EventBlock, StatefulEventBlock, ExceptionEvent, HookErrorEvent, TimerEventBlock
#from .event import WideEvent, log_event
from .checks import Checks, InlineCheck
from .results import MultiCheckResult, SingleCheckResult, Status

# a library stays silent until the app configures logging, e.g. with DEFAULT_LOGGING
logging.getLogger("wide_events").addHandler(logging.NullHandler())
