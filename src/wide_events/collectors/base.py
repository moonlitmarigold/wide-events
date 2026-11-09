from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, ClassVar, Iterable

import pluggy
from class_registry import ClassRegistry
from class_registry.base import AutoRegister

from ..context import BaseContext
from ..event import CollectorState, FuncCallContext, FuncCallState, LogContext
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
        """The collector's registry key, also its key in `state_context`."""

    @property
    @abstractmethod
    def hook_names(self) -> tuple[str, ...]:
        """The hook methods that `__init_subclass__` wraps with `save_run`."""

    @property
    @abstractmethod
    def context(self) -> BaseContext:
        """The context the collector writes to, e.g. `LogContext`."""

    @property
    @abstractmethod
    def state_context(self) -> BaseContext:
        """The context that holds the collectors' per-call state, e.g. `CollectorState`."""

    def __init_subclass__(cls, **kwargs) -> None:
        for hook_name in getattr(cls, "hook_names", ()):
            func = cls.__dict__.get(hook_name)
            if func:
                setattr(cls, hook_name, cls.save_run(func, hook_name))

    def __setattr__(self, key, value):
        raise TypeError(f"{type(self).__name__} is stateless")

    def set(self, **kwargs):
        """Merge `kwargs` into the current event of `context`."""
        self.context.update(kwargs)

    @staticmethod
    def save_run(func, hook_name):
        """Wrap the hook `func` so an exception it raises is appended to `hook_errors` in the current event of
        `context` and the hook returns None, instead of stopping the other collectors."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                # TODO: Hook Error Event, similar to results -> Universal from exc
                self.context.update({"hook_errors": [CollectorError.from_exception(exc).dump()]}, append_lists=True)
        return wrapper

    @property
    def state(self):
        """This collector's state for the current call, stored in the open `state_context` under `name` and
        created with `state_type()` on first access."""
        return self.state_context.get().setdefault(self.name, self.state_type())

    @staticmethod
    def new_pm(registry:ClassRegistry, names:Iterable[str]) -> pluggy.PluginManager:
        """A new `PluginManager` with `LoggingHooks` and one instance of each named collector of `registry`."""
        pm = pluggy.PluginManager("wide_events")
        pm.add_hookspecs(LoggingHooks)
        for name in names:
            pm.register(registry.get_class(name)())
        return pm


LOGGING_COLLECTORS = ClassRegistry["LoggingCollector"](attr_name="name", unique=True)

class LoggingCollector(AutoRegister(LOGGING_COLLECTORS), BaseCollector, ABC):
    """A collector for `log_event`; each concrete subclass registers itself in `LOGGING_COLLECTORS` under its
    `name`."""

    hook_names = ("on_create", "on_exception", "on_finish")
    context = LogContext
    state_context = CollectorState

    @staticmethod
    def build_pm(names:Iterable[str]) -> pluggy.PluginManager:
        """A new `PluginManager` of the named `LOGGING_COLLECTORS`.

        Input: `LoggingCollector.build_pm(("TimingCollector", "OutcomeCollector"))`; `Settings` caches the result.
        """
        return BaseCollector.new_pm(LOGGING_COLLECTORS, names)


FUNCCALL_COLLECTORS = ClassRegistry["FuncCallCollector"](attr_name="name", unique=True)

class FuncCallCollector(AutoRegister(FUNCCALL_COLLECTORS), BaseCollector, ABC):
    """A collector for `record_function_call`; each concrete subclass registers itself in `FUNCCALL_COLLECTORS`
    under its `name`. Same hooks as `LoggingCollector`, its own contexts."""

    hook_names = ("on_create", "on_exception", "on_finish")
    context = FuncCallContext
    state_context = FuncCallState

    @staticmethod
    def build_funccall_pm(names:Iterable[str]) -> pluggy.PluginManager:
        """A new `PluginManager` of the named `FUNCCALL_COLLECTORS`.

        Input: `FuncCallCollector.build_funccall_pm(("ArgumentsCollector",))`; `Settings` caches the result.
        """
        return BaseCollector.new_pm(FUNCCALL_COLLECTORS, names)
