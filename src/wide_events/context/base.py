from dataclasses import dataclass
from contextvars import Token, ContextVar
from typing import ClassVar, Any, Callable
from wide_events.context.ids import uuid4_hex
from abc import ABC, abstractclassmethod

class ReturnContextVars:
    """Factories for the ContextVars that contexts hold their value in."""

    @staticmethod
    def with_uuid4(base_name:str = '', _default:Any=None):
        """A new ContextVar named `base_name` plus a random hex suffix, with `_default` as its default.

        The default object is shared: every context that never set the var gets this same object back.
        """
        return ContextVar(base_name + uuid4_hex(), default=_default)

@dataclass
class BaseContext(ABC):
    """Base for a dict held in a ContextVar: `init()` opens a fresh one, `drop()` closes it and restores the outer one."""

    token: Token

    _contex_var: ClassVar[ContextVar[Any]]
    # a factory, not a value: init() calls it, so every opened context gets its own object
    context_default: ClassVar[Callable[[], Any]]

    @classmethod
    def check_or_raise_contex_var(cls):
        """The subclass's ContextVar; raises ValueError if the subclass set none."""
        if not hasattr(cls, "_contex_var"):
            raise ValueError("Internal: ContextVar for Event is not set")
        return cls._contex_var

    def drop(self):
        """Restore the dict that was current before `init()` and return this one's, or None if it was never opened."""
        ctx_var = self.check_or_raise_contex_var()
        ctx = ctx_var.get()
        ctx_var.reset(self.token)
        return ctx

    @classmethod
    def init(cls):
        """Open a fresh value from `context_default()` in the ContextVar and return the context that can drop it."""
        ctx_var = cls.check_or_raise_contex_var()
        token = ctx_var.set(cls.context_default())
        return cls(token)

    @classmethod
    def get(cls):
        return cls._contex_var.get()

    @abstractclassmethod
    def set(cls, **kwargs):
        """Write to the current value; each subclass defines what its arguments mean."""
        ...