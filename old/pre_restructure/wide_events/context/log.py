from enum import StrEnum, auto

from .implementations.dict import ContextDict

# lives outside the `logging` package: collectors import LogContext, and `logging.decorators` imports collectors


class ContextNames(StrEnum):
    """The names of the logging contexts, which are also their keys in `ContextCollection.drop()`."""

    log_context = auto()

LogContext = ContextDict.new(ContextNames.log_context)
#ResultContext = ContextDict.new("results") Results later
