import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from .results.checks import MultiCheckResult, SingleCheckResult

logger = logging.getLogger(__name__)


@dataclass()
class InlineCheck:
    """A check that calls `func` with the keyword arguments it is run with.

    It fails when one of `args` is missing, `func` returns something falsy or `func` raises; a failure becomes a
    warning when `warning` is set. `on_error`, a callable or a message to log, runs only when `func` raises.
    """

    args:list[str]
    func:Callable
    on_error:Callable|None = None

    def __call__(self, **kwargs):
        """Run the check with `kwargs` and return its result."""
        error = self.on_error if self.on_error else lambda:None
        # Check if args in kwargs
        for arg in self.args:
            if arg not in kwargs:
                logger.warning("Inline Check: Given Argument %r is not in kwargs (%s)", arg, kwargs)
                return SingleCheckResult.failed(self.exec_name)
        # Run the Check function // predefine some
        # Return Check Result
        try:
            res = self.func(**kwargs)
            return SingleCheckResult.success(self.exec_name) if res else SingleCheckResult.failed(self.exec_name)
        except Exception as exe:
            error()
            return SingleCheckResult.from_exception(self.exec_name, exe)

    @cached_property
    def exec_name(self) -> str:
        """The check's name: the `__qualname__` of `func` if it has one, else its repr."""
        return getattr(self.func, "__qualname__", repr(self.func))

    def dump(self) -> dict[str, Any]:
        """The check as JSON data; `func` and `on_error` are dumped as their names only, so it can't be loaded back."""
        return {
            "exec": self._callable_path(type(self)),
            "exec_name": self.exec_name,
            "args": list(self.args),
            "func": self._callable_path(self.func),
            "on_error": self._callable_path(self.on_error) if self.on_error else None,
        }

    @staticmethod
    def _callable_path(func: Callable) -> str:
        qualname = getattr(func, "__qualname__", None)
        if qualname is None:
            return repr(func)
        return f"{func.__module__}.{qualname}"


@dataclass(frozen=True)
class Checks:
    """Runs a group of checks."""
    checks:tuple[InlineCheck, ...]

    def __call__(self, **kwargs):
        """Run every check with `kwargs` and count the results by status."""
        results = [c(**kwargs) for c in self.checks]
        return MultiCheckResult.count(self.checks, results)
