from dataclasses import dataclass
from typing import ClassVar
from ..context import ContextDict

@dataclass
class EventBlock:
    """A namespaced part of the current wide event: its fields go under `path`, its parents' namespaces and then its
    own. A subclass sets `namespace`, or passes `abstract=True` to be a base for other blocks. Creating an instance
    writes `kwargs`; the block itself is not kept, so it holds no state between calls.

    Attributes:
        use_namespace_on_write: Write fields under `path`; False writes them at the event's top level.
        append_list: Extend lists already in the event instead of replacing them.
        drop_none: Skip None values.
    """

    kwargs:dict | None = None

    namespace: ClassVar[str | None] = None
    parent: ClassVar[type["EventBlock"] | None] = None
    path: ClassVar[tuple[str, ...]] = ()
    drop_none:ClassVar[bool] = True
    use_namespace_on_write:ClassVar[bool] = True
    append_list:ClassVar[bool] = False

    abstract: ClassVar[bool] = True
    _context_event: ClassVar[type[ContextDict]] # Add a class Check!

    def __post_init__(self):
        if self.kwargs:
            self.set(**self.kwargs)

    def __init_subclass__(cls, abstract=False ,**kwargs):
        """Check a concrete subclass's `namespace` and `parent` and build its `path`.

        Raises:
            TypeError: If `namespace` is missing or not a str, or `parent` is not a concrete, single EventBlock.
            ValueError: If `namespace` is empty or contains a '.'.
        """
        super().__init_subclass__(**kwargs)
        cls.abstract = abstract
        if abstract:
            return

        namespace = getattr(cls, "namespace", None)
        if namespace is None:
            raise TypeError(f"{cls.__name__} must define a 'namespace' or 'abstract = True'")
        if not isinstance(namespace, str):
            raise TypeError(
                f"{cls.__name__}.namespace must be a str (got {type(namespace).__name__})."
            )
        if not namespace or "." in namespace:
            raise ValueError(
                f"{cls.__name__}.namespace must be non-empty and contain no '.' (got {namespace!r})."
            )

        cls.path = cls._build_path(namespace)

    @classmethod
    def _build_path(cls, namespace:str):
        parent = getattr(cls, "parent", None)
        if parent is None:
            return (namespace,)
        if not (isinstance(parent, type) and issubclass(parent, EventBlock)):
            raise TypeError(
                f"{cls.__name__}.parent must be an EventBlock subclass (got {parent!r})."
            )
        if parent.abstract:
            raise TypeError(
                f"{cls.__name__}.parent is {parent.__name__}, which is abstract and has "
                f"no namespace of its own to nest under."
            )
        parent._check_nestable(cls)
        return parent.path + (namespace,)

    @classmethod
    def _check_nestable(cls, child:type["EventBlock"]):
        """Raise TypeError if `child` cannot nest under this block; every stateless block can be nested into."""

    @classmethod
    def get_key(cls):
        """The block's path joined with '.', its unique key among the attached blocks."""
        # '.' is banned inside a namespace, so joining on it keeps every path unique --
        # 'picture.timing' and 's3.timing' stay distinct despite the shared leaf name.
        return ".".join(cls.get_path())

    @classmethod
    def get_path(cls):
        """The block's path; raises TypeError on a class without a namespace."""
        if not cls.path:
            raise TypeError(f"{cls.__name__} must define a 'namespace'")
        return cls.path

    @classmethod
    def set(cls, **kwargs):
        """Write `kwargs` to the current event, under the block's path unless `use_namespace_on_write` is False; return the
        block."""
        if cls.use_namespace_on_write:
            cls._context_event.merge(cls.get(), kwargs, cls.drop_none, cls.append_list)
        else:
            cls._context_event.update(kwargs, cls.drop_none, cls.append_list)
        return cls

    @classmethod
    def from_kwargs(cls, **kwargs):
        """Write `kwargs` to the current event through a new block."""
        return cls(kwargs=kwargs)

    @classmethod
    def get(cls):
        """The block's dict inside the current event, created on first access."""
        ctx = cls._context_event.get()
        for part in cls.get_path():
            ctx = ctx.setdefault(part, {})
        return ctx
