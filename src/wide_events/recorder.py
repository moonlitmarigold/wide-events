from functools import wraps
import logging
from typing import Callable

from .context import BaseContext, ContextCollection
from .event import CollectorState, ContextNames, LogContext
from .settings import LoggerNames, Settings

def record_event(_list_ctx:list[BaseContext], _pm:Callable, context_name:str, logger):
    """A `log_event`-style decorator that opens `_list_ctx` per call, runs the hooks of the plugin manager `_pm()`
    returns, and emits the drop's `context_name` entry on `logger` (or merges it into the outer `LogContext`).

    Input: `record_event([LogContext, CollectorState], lambda: Settings.active().plugin_manager,
    ContextNames.log_context, logger)` -> `log_event`.
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
                    # the fields travel as `record.event`, which the `json` formatter of DEFAULT_LOGGING puts into the line
                    logger.info(name, extra={"event": context_result})
                else:
                    LogContext.update({name:context_result})

        return wrapper
    return log_event

#  TODO: make the log_event more arbitairy (base event) and make both record_function_call and log_event inherit from it
# a lambda, so each call reads the settings active then, not the ones at import
log_event = record_event([LogContext, CollectorState], lambda: Settings.active().plugin_manager,
                         ContextNames.log_context, logging.getLogger(LoggerNames.EVENT_LOGGER))

def record_function_call():
    # TODO: Implement the record function call
    ...
# TODO: Combination of FuncCall and LogEvent, that appends the funccall to the Main Event
