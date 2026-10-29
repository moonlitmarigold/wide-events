from wide_events.context import ContextDict, SingleValueContext, BaseContext
from dataclasses import dataclass, field


from types import TracebackType



@dataclass
class ContextCollection:

    contexts: list[type[BaseContext]]
    _opened: list[BaseContext] = field(init=False, default_factory=list)

    _result:dict = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.init()

    @property
    def result(self):
        if not self.result:
            raise AttributeError() # Fix error
        return self.result

    def init(self):
        self._opened = [c.init() for c in self.contexts]
        return self

    def drop(self):
        return {
            type(c).__name__:c.drop() for c in self._opened
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None):
        self.result = self.drop()