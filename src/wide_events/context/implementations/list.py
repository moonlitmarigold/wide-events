from ..base import BaseContext
from dataclasses import dataclass
from typing import ClassVar
from contextvars import ContextVar

@dataclass
class ContextCollectors(BaseContext):

    _contex_var: ClassVar[ContextVar[list]]
    context_default = []

    @classmethod
    def set(cls, _list:list):
        cls._contex_var.get().extend(_list)