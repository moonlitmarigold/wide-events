import logging
from functools import wraps
from typing import ClassVar

from .blocks import ContextBlock, ContextEvent

# the logger every finished wide event is written to; log handlers route it to the log file only
EVENT_LOGGER = "wide_events.event"


class WideEvent:
    """The lifecycle of a wide event: open it, collect nested calls into it, and emit it once finished."""

    # stdlib on purpose: the core needs no logging extra, and any handler (JSONFORMATTER, wide_events.log) can render it
    logger: ClassVar[logging.Logger] = logging.getLogger(EVENT_LOGGER)

    @classmethod
    def emit(cls, event: dict):
        """Write a finished wide event as one `wide_event` record; its fields travel as `record.event`."""
        cls.logger.info("wide_event", extra={"event": event})

    @classmethod
    def wrap(cls, func):
        """Wrap `func` so it fills a fresh wide event while it runs, which is then emitted as one `wide_event` record.
        If `func` raises, nothing is emitted and the outer event is not restored."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            event, block = ContextEvent.init(), ContextBlock.init()
            result = func(*args, **kwargs)
            cls.emit(event.drop())
            block.drop()
            return result
        return wrapper

    @staticmethod
    def collect(name:str=None):
        """Decorator that collects a call's fields in its own event and merges them into the caller's event when it
        returns, under `name` if given, with lists appended. If the call raises, nothing is merged and the outer event is
        not restored."""
        def outer_wrapper(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                event, block = ContextEvent.init(), ContextBlock.init()
                result = func(*args, **kwargs) # Improve the func logic with try/except

                event = event.drop()
                block.drop()

                if name:
                    event = {name:event}

                ContextEvent.update(event, append_lists=True)

                return result

            return wrapper
        return outer_wrapper


log_event = WideEvent.collect
