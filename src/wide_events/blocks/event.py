from wide_events.context import ContextDict, ReturnContextVars

class ContextEvent(ContextDict):
    """The current wide event: a ContextDict with its own ContextVar."""

    _contex_var = ReturnContextVars.with_uuid4("wide-events-", {})
    context_default = {}