from wide_events.context.base import BaseContext, ReturnContextVars
from dataclasses import dataclass
from wide_events.context.errors import BlockAlreadyAttached

@dataclass
class ContextBlock(BaseContext):
    """The EventBlocks attached to the current event, by key, so code can reach the block already attached."""


    ### ONLY needed when event blocks are implemented
    _contex_var = ReturnContextVars.with_uuid4("")

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