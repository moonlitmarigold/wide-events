from class_registry import ClassRegistry
from abc import abstractmethod, ABC
from ..context.log import LogContext
from class_registry.base import AutoRegister
from functools import cache, wraps
from typing import ClassVar, Callable, Any
from ..context import ContextDict

CollectorState = ContextDict.new("collector_state")

class BaseCollector(ABC):

    state_type:ClassVar[Callable[[], Any]] = dict

    # abstract only so the registry skips the base; subclasses set `name = "..."`
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def hook_names(self) -> tuple[str, ...]: ...

    def __init_subclass__(cls, **kwargs) -> None:
        for hook_name in getattr(cls, "hook_names", ()):
            func = cls.__dict__.get(hook_name)
            if func:
                setattr(cls, hook_name, cls.save_run(func, hook_name))

    def __setattr__(self, key, value):
        raise TypeError(f"{type(self).__name__} is stateless")

    @staticmethod
    def set(**kwargs):
        LogContext.update(kwargs)

    @staticmethod
    def save_run(func, hook_name):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                # TODO: Hook Error Event, similar to results -> Universal from exc
                LogContext.update({"hook_errors": [{
                    "hook": f"{type(self).__name__}.{hook_name}",
                    "error": repr(exc)}]})
        return wrapper

    @property
    def state(self):
        return CollectorState.get().setdefault(self.name, self.state_type())




