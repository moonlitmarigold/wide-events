from dataclasses import dataclass
from contextvars import Token, ContextVar
from typing import ClassVar, Any, Callable
from wide_events.context.ids import uuid4_hex
from abc import ABC, abstractclassmethod
from typing import Self

class ReturnContextVars:
    """Factories for the ContextVars that contexts hold their value in."""

    @staticmethod
    def with_uuid4(base_name:str = '', _default:Any=None):
        """A new ContextVar named `base_name` plus a random hex suffix, with `_default` as its default.

        The default object is shared: every context that never set the var gets this same object back.
        """
        return ContextVar(base_name + uuid4_hex(), default=None) # TODO

class ContextNotInitError(Exception):
    """A write to a context that no `init()` has opened."""

    def __init__(self, context_var:ContextVar):
        # TODO AI: Better Error
        pass

# marks "no default passed", since None is a valid default
_NO_DEFAULT = object()

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

    @classmethod
    def is_init(cls):
        """Whether a context of this class is open, i.e. its current value is not None."""
        return cls.get() is not None


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
        """The current value, or the ContextVar's default when no context is open."""
        return cls._contex_var.get()

    @abstractclassmethod
    def set(cls, **kwargs):
        """Write to the current value; each subclass defines what its arguments mean and calls this first.

        Raises:
            ContextNotInitError: When no context of this class is open.
        """
        if cls._contex_var.get() is None:
            raise ContextNotInitError(cls._contex_var)
        ...

    def __init_subclass__(cls, default:Any=_NO_DEFAULT, **kwargs):
        """Give the subclass its own ContextVar, unless its body sets `_contex_var`.

        Args:
            default: The new ContextVar's default. If given, `context_default` returns it too, unless the class body
                sets one; it is the same object every time, so a mutable default is shared by every opened context.
        """
        super().__init_subclass__(**kwargs)
        # every subclass gets its own var unless its body sets one
        if "_contex_var" not in cls.__dict__:
            var_default = None if default is _NO_DEFAULT else default
            cls._contex_var = ReturnContextVars.with_uuid4(cls.__name__ + "-", var_default)
        # an explicit default beats an inherited context_default, but not one in the class body
        if default is not _NO_DEFAULT and "context_default" not in cls.__dict__:
            cls.context_default = lambda: default

    @classmethod
    def new(cls, name: str, default:Any=_NO_DEFAULT) -> type[Self]:
        """A subclass of this context with its own ContextVar."""
        return type(name, (cls,), {"__module__": cls.__module__}, default=default)