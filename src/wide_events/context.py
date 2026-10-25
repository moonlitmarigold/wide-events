from contextvars import ContextVar, Token
import dataclasses
from typing import ClassVar

_current: ContextVar[dict | None] = ContextVar("wide_events.event", default=None)
_blocks: ContextVar[dict | None] = ContextVar("wide_events.block", default=None)
_collectors: ContextVar[list | None] = ContextVar("wide_events.collectors", default=None)
_capture: ContextVar[bool | None] = ContextVar("wide_events.capture", default=None)


class BlockAlreadyAttached(Exception):
    """Raised when a block attaches at a key that a single-attach block already holds on the current event."""

    def __init__(self, key, attached, incoming):
        self.key = key
        self.attached = attached
        self.incoming = incoming
        super().__init__(
            f"{type(incoming).__name__} cannot attach at {key!r}: already claimed by "
            f"{type(attached).__name__} on this event. Use {type(incoming).__name__}"
            f".current() to reach the attached block, or set 'multiple = True' if this "
            f"block is meant to attach more than once."
        )


@dataclasses.dataclass
class BaseContext:
    """Base for a dict held in a ContextVar: `init()` opens a fresh one, `drop()` closes it and restores the outer one."""

    token: Token|None = None
    _contex_var: ClassVar[ContextVar[dict | None]] = None

    def check_or_raise_contex_var(self):
        """The subclass's ContextVar; raises ValueError if the subclass set none."""
        if self._contex_var is None:
            raise ValueError("Internal: ContextVar for Event is not set")
        return self._contex_var

    def drop(self):
        """Restore the dict that was current before `init()` and return this one's, or None if it was never opened."""
        if not self.token:
            return
        ctx_var = self.check_or_raise_contex_var()
        ctx = ctx_var.get()
        ctx_var.reset(self.token)
        return ctx

    @classmethod
    def init(cls):
        """Open a fresh empty dict in the ContextVar and return the context that can drop it."""
        _cls = cls()
        ctx_var = _cls.check_or_raise_contex_var()
        _cls.token = ctx_var.set({})
        return _cls


@dataclasses.dataclass
class ContextEvent(BaseContext):
    """The current wide event: a nested dict that code adds fields to while it runs."""

    _contex_var = _current

    @classmethod
    def set(cls, **kwargs):
        """Set `kwargs` at the top level of the current event, replacing existing values; without an open event they are
        lost."""
        ctx = cls.get()
        ctx.update(kwargs)

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

    @classmethod
    def get(cls):
        """The current event's dict, or a new empty dict when no event is open."""
        ctx = cls._contex_var.get()
        if ctx is None:
            return {}
        return ctx

@dataclasses.dataclass
class ContextBlock(BaseContext):
    """The EventBlocks attached to the current event, by key, so code can reach the block already attached."""

    _contex_var = _blocks

    @staticmethod
    def get():
        """The current blocks by key, or a new empty dict when no event is open."""
        blocks = _blocks.get()
        if blocks is None:
            return {}
        return blocks

    @staticmethod
    def attach(key:str, block, multiple:bool=False):
        """Attach `block` at `key` and return it; with `multiple` it is appended to a list there.

        Raises:
            BlockAlreadyAttached: Without `multiple`, when a block is already attached at `key`.
        """
        ctx = ContextBlock.get()
        if multiple:
            ctx.setdefault(key, []).append(block)
            return block
        attached = ctx.get(key)
        if attached is not None:
            raise BlockAlreadyAttached(key, attached, block)
        ctx[key] = block
        return block

@dataclasses.dataclass
class ContextCollectors:

    token: Token | None = None

    @classmethod
    def init(cls):
        _cls = cls()
        _cls.token = _collectors.set([])
        return _cls

    @staticmethod
    def get():
        ctx = _collectors.get()
        if ctx is None:
            return []
        return ctx

    @staticmethod
    def set_collectors(collectors:list):
        ContextCollectors.get().extend(collectors)


    def drop(self):
        if not self.token:
            return
        _ctx = self.get()
        _collectors.reset(self.token)
        return _ctx

@dataclasses.dataclass
class ContextCapture(BaseContext):

    _contex_var = _capture

    @classmethod
    def set(cls, var:bool):
        cls._contex_var.set(var)

    @classmethod
    def get(cls):
        return cls._contex_var.get()

    @classmethod
    def init(cls):
        _cls = cls()
        ctx_var = _cls.check_or_raise_contex_var()
        _cls.token = ctx_var.set(None)
        return _cls
