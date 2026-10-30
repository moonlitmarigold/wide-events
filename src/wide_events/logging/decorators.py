from functools import wraps
import logging
from ..blocks import ContextCollection
from .base import LogContext, ContextNames, LoggerNames

logger = logging.getLogger(LoggerNames.EVENT_LOGGER)

def log_event(func):
    """Run `func` in a fresh `LogContext`; afterwards merge its fields into the outer `LogContext` under the
    function's name, or, without an outer one, emit them as one record on the `EVENT_LOGGER`."""
    name = func.__name__
    @wraps(func)
    def wrapper(*args, **kwargs):
        _list_ctx = [LogContext]
        _not_init = [c.__name__ for c in _list_ctx if not c.is_init()]

        ctx = ContextCollection(_list_ctx).init()

        # TODO: Run Collectors
        # TODO: Wrap in a try/expect
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:

            raise e
        finally:
            _drop = ctx.drop()
            context_result = _drop.get(ContextNames.log_context)

            if ContextNames.log_context in _not_init:
                # the fields travel as `record.event`, which JSONFORMATTER spreads into the line
                logger.info(name, extra={"event": context_result})
            else:
                LogContext.update({name:context_result})

        return result
    return wrapper
