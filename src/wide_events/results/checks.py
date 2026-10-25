from .base import *


@dataclass(frozen=True)
class SingleCheckResult(ExceptionResult, SingleStatus):
    """The outcome of one check under its name, with the exception when it raised."""

    result_name = "SingleCheckResult"

    @classmethod
    def from_exception(cls, name:str, exc: Exception):
        """A failed result for `name` with the type and traceback of `exc`."""
        _exception = ExceptionResult.from_exception(exc)
        return cls(
            name, Status.failed,
            **_exception.dump(False)
        )

    @classmethod
    def failed(cls, name:str):
        """A failed result for `name` without an exception."""
        return cls(name, Status.failed, None, None)

    @classmethod
    def success(cls, name:str):
        """A successful result for `name` without an exception."""
        return cls(name, Status.success, None, None)

@dataclass(frozen=True)
class MultiCheckResult(StatusCount):
    """The status counts of a group of checks, with each check's result."""

    result_name = "MultiCheckResult"

    single_checks:list[SingleCheckResult]

    @classmethod
    def count(cls, _execs:list|tuple,  results:list[SingleStatus]):
        """Count `results` by status and keep them; `num` is the number of `_execs`."""
        _cls = StatusCount.count(_execs, results)
        return cls(
            **_cls.dump(False), single_checks=results
        )

    def dump(self, _super:bool=True):
        """The counts and each check's result as JSON data."""
        return {
            **super().dump(_super),
            "single_checks":[s.dump() for s in self.single_checks]
        }
