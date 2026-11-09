from uuid import uuid4


def uuid4_hex() -> str:
    """A random UUID4 as 32 hex characters."""
    return uuid4().hex
