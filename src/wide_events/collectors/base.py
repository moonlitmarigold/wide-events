from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, ClassVar, Iterable

import pluggy
from class_registry import ClassRegistry
from class_registry.base import AutoRegister

from ..context import BaseContext
from ..event import CollectorState, LogContext
from ..results import ExceptionResult
from .hooks import LoggingHooks

class CollectorError(ExceptionResult):
    """An exception raised inside a collector hook, as `ExceptionResult` tagged `result_name: "CollectorError"`."""

    result_name = "CollectorError"

class BaseCollector(ABC):
    """Base for collectors, which add fields to the current event from pluggy hooks without the observed code
    calling them.

    Instances are stateless: setting any attribute raises TypeError. Per-call state goes in `state`. Each hook
    listed in `hook_names` is wrapped by `save_run` when the subclass is created.

    Attributes:
        state_type: Builds a fresh `state` for each call.
    """

    state_type:ClassVar[Callable[[], Any]] = dict

    # abstract only so the registry skips the base; subclasses set `name = "..."`
    @property
    @abstractmethod
    def name(self) -> str:
        """The collector's registry key, also its key in `CollectorState`."""

    @property
    @abstractmethod
    def hook_names(self) -> tuple[str, ...]:
        """The hook methods that `__init_subclass__` wraps with `save_run`."""

    @property
    @abstractmethod
    def context(self) -> BaseContext:
        """The context the collector writes to, e.g. `LogContext`."""

    def __init_subclass__(cls, **kwargs) -> None:
        for hook_name in getattr(cls, "hook_names", ()):
            func = cls.__dict__.get(hook_name)
            if func:
                setattr(cls, hook_name, cls.save_run(func, hook_name))

    def __setattr__(self, key, value):
        raise TypeError(f"{type(self).__name__} is stateless")

    @staticmethod
    def set(**kwargs):
        """Merge `kwargs` into the current `LogContext` event."""
        LogContext.update(kwargs)

    @staticmethod
    def save_run(func, hook_name):
        """Wrap the hook `func` so an exception it raises is appended to `hook_errors` in the current `LogContext`
        and the hook returns None, instead of stopping the other collectors."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                # TODO: Hook Error Event, similar to results -> Universal from exc
                LogContext.update({"hook_errors": [CollectorError.from_exception(exc).dump()]}, append_lists=True)
        return wrapper

    @property
    def state(self):
        """This collector's state for the current call, stored in the open `CollectorState` under `name` and
        created with `state_type()` on first access."""
        return CollectorState.get().setdefault(self.name, self.state_type())


LOGGING_COLLECTORS = ClassRegistry["LoggingCollector"](attr_name="name", unique=True)

class LoggingCollector(AutoRegister(LOGGING_COLLECTORS), BaseCollector, ABC):
    """A collector for `log_event`; each concrete subclass registers itself in `LOGGING_COLLECTORS` under its
    `name`."""

    hook_names = ("on_create", "on_exception", "on_finish")
    context = LogContext

    @staticmethod
    def build_pm(names:Iterable[str]) -> pluggy.PluginManager:
        """A new `PluginManager` with `LoggingHooks` and one instance of each named collector registered.

        Input: `LoggingCollector.build_pm(("TimingCollector", "OutcomeCollector"))`; `Settings` caches the result.
        """
        pm = pluggy.PluginManager("wide_events")
        pm.add_hookspecs(LoggingHooks)
        for name in names:
            pm.register(LOGGING_COLLECTORS.get_class(name)())
        return pm


class FuncCallCollector(BaseCollector, ABC):
    """Stub base for the collectors of `record_function_call`. Not wired: no registry, hookspecs or plugin
    manager yet, so no subclass runs."""

    # TODO: FUNCCALL_COLLECTORS registry (AutoRegister), FuncCallHooks hookspecs and return_pm, once
    #  record_function_call exists; context may become its own FuncCallContext
    hook_names = ("on_create", "on_exception", "on_finish")
    context = LogContext
