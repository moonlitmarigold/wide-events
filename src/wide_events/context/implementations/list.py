from ..base import BaseContext
from dataclasses import dataclass
from typing import ClassVar
from contextvars import ContextVar

@dataclass
class ContextList(BaseContext):
    """A list held in a ContextVar, for the collectors of the current context."""

    _contex_var: ClassVar[ContextVar[list]]
    context_default = list

    @classmethod
    def set(cls, _list:list):
        """Extend the current list with `_list` in place."""
        cls._contex_var.get().extend(_list)