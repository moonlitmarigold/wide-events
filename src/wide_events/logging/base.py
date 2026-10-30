from ..blocks.base import EventBlock
from ..context import ContextDict, SingleValueContext, BaseContext
from enum import StrEnum, auto
from dataclasses import dataclass, field

class ContextNames(StrEnum):
    """The names of the logging contexts, which are also their keys in `ContextCollection.drop()`."""

    log_context = auto()

LogContext = ContextDict.new(ContextNames.log_context)
#ResultContext = ContextDict.new("results") Results later

@dataclass
class SampleLogEvent(EventBlock):
    """The `log_event` block, which writes its fields at the top level of the `LogContext` event."""

    namespace = "log_event"
    use_namespace_on_write = False
    _context_event = LogContext

ClassForLogEvent = SampleLogEvent
LogEvent:EventBlock = ClassForLogEvent
# TODO: Dynamic LogEvent -> fixed to SampleLogEvent at import; move the choice to the planned config library

class LoggerNames(StrEnum):

    EVENT_LOGGER = "wide_events.event"
