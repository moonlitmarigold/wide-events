from abc import ABC

import pluggy

from ..context.log import LogContext
from .base import BaseCollector

# same project name as the logging marker, so these impls also fit `LoggingHooks` until funccall gets its own specs
func_call_hookimpl = pluggy.HookimplMarker("wide_events")


class FuncCallCollector(BaseCollector, ABC):
    """Stub base for the collectors of `record_function_call`. Not wired: no registry, hookspecs or plugin
    manager yet, so no subclass runs."""

    # TODO: FUNCCALL_COLLECTORS registry (AutoRegister), FuncCallHooks hookspecs and return_pm, once
    #  record_function_call exists; context may become its own FuncCallContext
    hook_names = ("on_create", "on_exception", "on_finish")
    context = LogContext
