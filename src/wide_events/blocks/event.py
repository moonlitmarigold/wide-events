from wide_events.context.base import ContextDict, ReturnContextVars

class ContextEvent(ContextDict):

    _contex_var = ReturnContextVars.with_uuid4("wide-events-", {})
    context_default = {}