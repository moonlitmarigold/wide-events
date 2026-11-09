from dataclasses import dataclass
from enum import StrEnum, auto

from ..context import BaseContext, ContextDict, ReturnContextVars
from .errors import BlockAlreadyAttached


class ContextNames(StrEnum):
    """The names of the logging contexts, which are also their keys in `ContextCollection.drop()`."""

    log_context = auto()
    func_call_context = auto()


LogContext = ContextDict.new(ContextNames.log_context)
#ResultContext = ContextDict.new("results") Results later

CollectorState = ContextDict.new("collector_state")

# the same pair for `record_function_call`, so its fields and collector state never mix with the `log_event` ones
FuncCallContext = ContextDict.new(ContextNames.func_call_context)
FuncCallState = ContextDict.new("func_call_state")


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
