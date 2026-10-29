from functools import wraps
import json
from ..blocks import ContextCollection
from .base import LogContext, ContextNames

def sample_log(text, event:dict):
    """Print `text` and `event`, as JSON, on one line."""
    print(f"{text} : {json.dumps(event)}")

log = sample_log

def log_event(func):
    """Run `func` in a fresh `LogContext`; afterwards `log` its fields if a `LogContext` was already open, otherwise
    merge them into `LogContext` under the function's name."""
    name = func.__name__
    @wraps(func)
    def wrapper(*args, **kwargs):
        _list_ctx = [LogContext]
        _not_init = [c for c in _list_ctx if c.is_init()]
        ctx = ContextCollection(_list_ctx).init()

        # Run Collectors
        result = func(*args, **kwargs)

        _drop = ctx.drop()
        context_result = _drop.get(ContextNames.log_context)

        if LogContext in _not_init:
            log(name, context_result)
        else:
            LogContext.update({name:context_result})

        return result
    return wrapper

