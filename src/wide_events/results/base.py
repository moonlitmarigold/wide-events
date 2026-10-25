from enum import StrEnum, auto
from dataclasses import dataclass
from collections import Counter
import traceback
from typing import ClassVar


class Status(StrEnum):
    """How a check ended; a failed check marked `warning` ends as warning."""

    success = auto()
    failed = auto()
    warning = auto()
    skipped = auto()
    queued = auto()

@dataclass(frozen=True)
class BaseResult:
    """Base for results that dump to JSON data; `result_name` tags each dump with the result's kind."""

    result_name:ClassVar[str]

    def dump(self, _super:bool=True):
        """The result as JSON data; `_super=False` leaves out `result_name`, so the fields fit back into the constructor."""
        if not _super:
            return {}
        return {"result_name":self.result_name}

@dataclass(frozen=True)
class SingleStatus(BaseResult):
    """The status of one named check or exec."""

    result_name = "SingleStatus"
    
    name:str
    status:Status
    
    def dump(self, _super:bool=True):
        """The name and status as JSON data."""
        return {**super().dump(_super), "name":self.name, "status":str(self.status)}
    
@dataclass(frozen=True)
class StatusCount(BaseResult):
    """How many results succeeded, failed, warned or were skipped, out of `num` planned."""

    result_name = "StatusCount"
    
    success:int
    failed:int
    warning:int
    skipped:int
    queued:int
    num:int
    
    @classmethod
    def count(cls, _execs:list|tuple, results:list[SingleStatus]):
        """Count `results` by status, with `num` set to the number of `_execs`."""
        counts = Counter(r.status for r in results)
        return StatusCount(
            counts[Status.success],
            counts[Status.failed],
            counts[Status.warning],
            counts[Status.skipped],
            counts[Status.queued],
            len(_execs)
        )
    
    def dump(self, _super:bool=True):
        """The counts as JSON data."""
        return {
            **super().dump(_super),
            "success":self.success,
            "failed":self.failed,
            "warning":self.warning,
            "skipped":self.skipped,
            "queued":self.queued,
            "num":self.num
        }

    @property
    def ok(self):
        """True when no result failed."""
        return self.failed == 0 and self.skipped == 0
    
@dataclass(frozen=True)
class ExceptionResult(BaseResult):
    """The type and formatted traceback of a raised exception, or None for both."""
    
    exception: str | None
    traceback: str | None

    @classmethod
    def from_exception(cls, exc: Exception):
        """A failed result with the type and traceback of `exc`."""
        snapshot = traceback.TracebackException.from_exception(exc)
        return cls(snapshot.exc_type_str, "".join(snapshot.format()))

    def dump(self, _super:bool=True):
        """The exception type and traceback as JSON data."""
        return {**super().dump(_super), "exception":self.exception, "traceback":self.traceback}
