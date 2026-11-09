from dataclasses import dataclass
from typing import ClassVar

from ..context import ContextDict
from .contexts import ContextBlock, LogContext

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


@dataclass
class SampleLogEvent(EventBlock):
    """The `log_event` block, which writes its fields at the top level of the `LogContext` event."""

    namespace = "log_event"
    use_namespace_on_write = False
    _context_event = LogContext

ClassForLogEvent = SampleLogEvent
LogEvent:EventBlock = ClassForLogEvent
# TODO: Dynamic LogEvent -> fixed to SampleLogEvent at import; move the choice to the planned config library
