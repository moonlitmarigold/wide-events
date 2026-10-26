from wide_events.context import ContextDict, SingleValueContext
from dataclasses import dataclass
from .base import EventBlock

LogContext = ContextDict.new("wide-events")
#ResultContext = ContextDict.new("results") Results later

@dataclass
class SampleLogEvent(EventBlock):
    """The `log_event` block, which writes its fields at the top level of the `LogContext` event."""

    namespace = "log_event"
    use_namespace_on_write = False
    _context_event = LogContext

ClassForLogEvent = SingleValueContext.new("class-event-log", SampleLogEvent)
LogEvent:EventBlock = ClassForLogEvent.get()
# TODO: Dynamic LogEvent -> fixed to SampleLogEvent at import; move the choice to the planned config library