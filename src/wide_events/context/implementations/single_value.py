from ..base import BaseContext
from dataclasses import dataclass
from typing import ClassVar, Any
from contextvars import ContextVar

@dataclass
class SingleValue(BaseContext):

    _contex_var: ClassVar[ContextVar[Any]]

    @classmethod
    def set(cls, var:Any):
        cls._contex_var.set(var)