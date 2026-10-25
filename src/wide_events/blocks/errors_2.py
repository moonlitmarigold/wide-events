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