from wide_events.context.base import BaseContext, ReturnContextVars
from dataclasses import dataclass
from typing import ClassVar
from wide_events.blocks.base import EventBlock
from wide_events.blocks.errors_2 import BlockAlreadyAttached

@dataclass
class ContextBlock(BaseContext):
    """The EventBlocks attached to the current event, by key, so code can reach the block already attached."""


    ### ONLY needed when event blocks are implemented
    _contex_var = ReturnContextVars.with_uuid4("")
    context_default = dict

    @classmethod
    def get(cls, ):
        """The current blocks by key, or a new empty dict when no event is open."""
        blocks = cls._contex_var.get()
        if blocks is None:
            return {}
        return blocks

    @classmethod
    def set(cls, key:str, block, multiple:bool=False):
        """Attach `block` at `key` and return it; with `multiple` it is appended to a list there.

        Raises:
            BlockAlreadyAttached: Without `multiple`, when a block is already attached at `key`.
            ContextNotInitError: When no ContextBlock is open.
        """
        super().set()
        ctx = ContextBlock.get()
        if multiple:
            ctx.setdefault(key, []).append(block)
            return block
        attached = ctx.get(key)
        if attached is not None:
            raise BlockAlreadyAttached(key, attached, block)
        ctx[key] = block
        return block


@dataclass
class StatefulEventBlock(EventBlock, abstract=True):
    """An EventBlock that attaches itself to the current event, so later code can reach it with `current()` and
    `from_kwargs` writes to the block already attached instead of creating a new one.

    Attributes:
        multiple: Allow more than one instance per event; otherwise a second one raises BlockAlreadyAttached.
    """

    multiple: ClassVar[bool] = False

    def __post_init__(self):
        self._attach()
        super().__post_init__()

    @classmethod
    def _check_nestable(cls, child:type[EventBlock]):
        if cls.multiple:
            raise TypeError(
                f"{child.__name__} cannot nest under {cls.__name__}: it has "
                f"'multiple = True', so it renders as a list and has no single dict to "
                f"nest into."
            )

    def _attach(self):
        ContextBlock.set(self.get_key(), self, self.multiple)

    @classmethod
    def from_kwargs(cls, **kwargs):
        """Write `kwargs` to the block already attached to the current event, or attach a new one; a `multiple` block
        always gets a new one."""
        if not cls.multiple:
            attached = cls.current()
            if attached is not None:
                return attached.set(**kwargs)
        return cls(kwargs=kwargs)

    @classmethod
    def current(cls):
        """The block of this class on the current event (the latest one if `multiple`), or None."""
        _block = ContextBlock.get().get(cls.get_key())
        if _block is None:
            return None
        if cls.multiple:
            return _block[-1]
        else:
            return _block
