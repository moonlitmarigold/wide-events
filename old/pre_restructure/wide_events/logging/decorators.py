from functools import wraps
import logging
from ..blocks import ContextCollection
from .base import LogContext, ContextNames, LoggerNames, BaseContext
from ..collectors import LoggingCollector, CollectorState
from typing import Callable

def record_event(_list_ctx:list[BaseContext], _pm:Callable, context_name:str, logger):
    """A `log_event`-style decorator that opens `_list_ctx` per call, runs the hooks of the plugin manager `_pm()`
    returns, and emits the drop's `context_name` entry on `logger` (or merges it into the outer `LogContext`).

    Input: `record_event([LogContext, CollectorState], LoggingCollector.return_pm, ContextNames.log_context,
    logger)` -> `log_event`.
    """
    def log_event(func):
        """Run `func` in a fresh `LogContext`; afterwards merge its fields into the outer `LogContext` under the
        function's name, or, without an outer one, emit them as one record on the `EVENT_LOGGER`."""
        name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            _not_init = [c.__name__ for c in _list_ctx if not c.is_init()]
            pm = _pm()

            ctx = ContextCollection(_list_ctx).init()

            pm.hook.on_create(name=name, func=func, args=args, kwargs=kwargs)
            try:
                result = func(*args, **kwargs)
                pm.hook.on_finish(name=name, func=func, args=args, kwargs=kwargs, result=result)
                return result
            except Exception as e:
                pm.hook.on_exception(name=name, func=func, args=args, kwargs=kwargs, exception=e)
                raise e
            finally:
                _drop = ctx.drop()
                context_result = _drop.get(context_name)

                if context_name in _not_init:
                    # the fields travel as `record.event`, which JSONFORMATTER spreads into the line
                    logger.info(name, extra={"event": context_result})
                else:
                    LogContext.update({name:context_result})

        return wrapper
    return log_event

#  TODO: make the log_event more arbitairy (base event) and make both record_function_call and log_event inherit from it
log_event = record_event([LogContext, CollectorState], LoggingCollector.return_pm, ContextNames.log_context, logging.getLogger(LoggerNames.EVENT_LOGGER))

def record_function_call():
    # TODO: Implement the record function call
    ...
