from functools import wraps
import logging
from ..blocks import ContextCollection
from .base import LogContext, ContextNames, LoggerNames
from ..collectors import LoggingCollector, CollectorState

logger = logging.getLogger(LoggerNames.EVENT_LOGGER)

def log_event(func):
    """Run `func` in a fresh `LogContext`; afterwards merge its fields into the outer `LogContext` under the
    function's name, or, without an outer one, emit them as one record on the `EVENT_LOGGER`."""
    name = func.__name__
    # TODO: Get the pm inside wrapper (per call): here the first @log_event at import fills the cache, so collectors
    #  defined later never run
    pm = LoggingCollector.return_pm()
    @wraps(func)
    def wrapper(*args, **kwargs):
        _list_ctx = [LogContext, CollectorState]
        _not_init = [c.__name__ for c in _list_ctx if not c.is_init()]

        ctx = ContextCollection(_list_ctx).init()

        # TODO: No collector runs yet: return_pm registers the registry keys (strings), not instances
        #  -> pm.register(LOGGING_COLLECTORS[name], name=name), later from DEFAULT_COLLECTORS
        # TODO: Pass the call info (name, args, kwargs) instead of request={}, and rename request/response (Django names)
        pm.hook.on_create(request={})
        try:
            result = func(*args, **kwargs)
            # TODO: Run pm.hook.on_finish(request=..., response=result)
            return result
        except Exception as e:
            # TODO: Run pm.hook.on_exception(request=..., exception=e) before re-raising
            raise e
        finally:
            _drop = ctx.drop()
            context_result = _drop.get(ContextNames.log_context)

            if ContextNames.log_context in _not_init:
                # the fields travel as `record.event`, which JSONFORMATTER spreads into the line
                logger.info(name, extra={"event": context_result})
            else:
                LogContext.update({name:context_result})

    return wrapper

#  TODO: make the log_event more arbitary (base event) and make both record_function_call and log_event inherit from it

def record_function_call():
    # TODO: Implement the record function call
    ...
