from wide_events.context import ContextDict, SingleValueContext, BaseContext
from dataclasses import dataclass, field


from types import TracebackType



@dataclass
class ContextCollection:
    """Contexts opened and dropped together; creating the collection opens them."""

    contexts: list[type[BaseContext]]
    _opened: list[BaseContext] = field(init=False, default_factory=list)

    @property
    def result(self):
        if not self.result:
            raise AttributeError() # Fix error
        return self.result

    def init(self):
        """Open a fresh value in each of `contexts` and return the collection."""
        self._opened = [c.init() for c in self.contexts]
        return self

    def drop(self):
        """Drop the contexts opened by the last `init()` and return their values by context class name."""
        return {
            type(c).__name__:c.drop() for c in self._opened
        }