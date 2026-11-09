from .checks import SingleCheckResult, MultiCheckResult
from .base import Status
from dataclasses import dataclass

@dataclass(frozen=True)
class ExecResult(SingleCheckResult):
    """The outcome of one exec under its name, with the exception when it raised."""

    result_name = "ExecResult"

    @classmethod
    def skipped(cls, name:str):
        return cls(
            name, Status.skipped,
            None, None
        )

@dataclass(frozen=True)
class MultiExecResult(MultiCheckResult):
    """The status counts of a group of execs, with each exec's result."""

    result_name = "MultiExecResult"
