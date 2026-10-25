from ..base import BaseContext
from dataclasses import dataclass
from typing import ClassVar, Any
from contextvars import ContextVar

@dataclass
class SingleValue(BaseContext):
    """Base for a single value held in a ContextVar; a subclass sets `_contex_var`."""

    _contex_var: ClassVar[ContextVar[Any]]

    @classmethod
    def set(cls, var:Any):
        """Replace the current value with `var`."""
        cls._contex_var.set(var)