from ..base import BaseContext
from dataclasses import dataclass
from typing import ClassVar
from contextvars import ContextVar

@dataclass
class ContextDict(BaseContext):
    """The current wide event: a nested dict that code adds fields to while it runs."""

    _contex_var:ClassVar[ContextVar[dict]]
    context_default = dict

    @classmethod
    def set(cls, **kwargs):
        """Set `kwargs` at the top level of the current event, replacing existing values; raises ContextNotInitError
        without an open event."""
        super().set()
        cls.update(kwargs)

    @classmethod
    def update(cls, payload:dict, drop_none:bool=True, append_lists:bool=False):
        """Merge `payload` into the current event, as `merge` does; without an open event it is lost."""
        ctx = cls.get()
        return cls.merge(ctx, payload, drop_none, append_lists)

    @classmethod
    def merge(cls, ctx:dict, payload:dict, drop_none:bool=True, append_lists:bool=False):
        """Merge `payload` into `ctx` in place and return `ctx`: dicts merge key by key, other values overwrite.

        Args:
            drop_none: Skip None values instead of writing them.
            append_lists: Extend a list already at the key instead of replacing it; a list landing anywhere else is
                written as a copy.
        """
        # payload is positional on purpose: taking it as **kwargs let a field named
        # 'ctx' raise TypeError and a field named 'drop_none' silently vanish.
        for key, value in payload.items():
            if isinstance(value, dict):
                cls.merge(ctx.setdefault(key, {}), value, drop_none, append_lists)
            else:
                if drop_none and value is None:
                    continue
                if append_lists and isinstance(value, list):
                    attached = ctx.get(key)
                    # Only list-on-list accumulates. A list landing on a scalar writes as
                    # usual -- merging there would lose the scalar silently. On nothing it
                    # writes a copy, so the caller keeps their list free of later appends.
                    if isinstance(attached, list):
                        attached.extend(value)
                        continue
                    value = list(value)
                ctx[key] = value
        return ctx