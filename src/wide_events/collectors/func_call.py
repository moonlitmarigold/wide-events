import inspect
import os
import platform
import resource
import socket
import threading
import time
from functools import cache
from typing import ClassVar

from ._func_call import FuncCallCollector, func_call_hookimpl


class EnvironmentCollector(FuncCallCollector):
    """Writes `environment: {host, python, pid}` on create."""

    name = "EnvironmentCollector"

    @func_call_hookimpl
    def on_create(self, name, func, args, kwargs):
        # pid is read per call: it changes in a forked worker, the rest does not
        # TODO: service, version and env, once the config library exists
        self.set(environment={**self.static_environment(), "pid": os.getpid()})

    @staticmethod
    @cache
    def static_environment():
        """`{host, python}`, computed on the first call and cached for the process."""
        return {"host": socket.gethostname(), "python": platform.python_version()}


class ArgumentsCollector(FuncCallCollector):
    """Writes the call's bound arguments, defaults included, as `args: {param: summarize(param, value)}`, without
    `self` and `cls`.

    Input: `f(user="ann", api_key="s3cr3t", obj=object())` -> `args: {user: "ann", api_key: "[REDACTED]", n: 3,
    obj: "object"}`.
    """

    name = "ArgumentsCollector"

    redact: ClassVar[tuple[str, ...]] = ("password", "secret", "token", "key", "auth")
    scalar_types: ClassVar[tuple[type, ...]] = (str, int, float, bool)
    skip_params: ClassVar[frozenset[str]] = frozenset({"self", "cls"})

    @func_call_hookimpl
    def on_create(self, name, func, args, kwargs):
        bound = inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
        self.set(args={
            param: self.summarize(param, value)
            for param, value in bound.arguments.items()
            if param not in self.skip_params
        })

    def summarize(self, param:str, value):
        """The value to record for `param`: `"[REDACTED]"` for a sensitive name, the value itself for a scalar,
        otherwise only its type name."""
        if any(word in param.lower() for word in self.redact):
            return "[REDACTED]"
        if value is None or isinstance(value, self.scalar_types):
            return value
        return type(value).__qualname__


class ResourceCollector(FuncCallCollector):
    """Writes `resources: {cpu_ms, max_rss, thread}` on finish or exception, with `cpu_ms` the thread's CPU time
    since `on_create`."""

    name = "ResourceCollector"

    @func_call_hookimpl
    def on_create(self, name, func, args, kwargs):
        # thread_time, not process_time: other threads' CPU would be counted against this call
        self.state["cpu_start"] = time.thread_time()

    @func_call_hookimpl
    def on_finish(self, name, func, args, kwargs, result):
        self.save_usage()

    @func_call_hookimpl
    def on_exception(self, name, func, args, kwargs, exception):
        self.save_usage()

    def save_usage(self):
        """Write `resources` from the CPU start in `state["cpu_start"]` and the current `getrusage`."""
        self.set(resources={
            "cpu_ms": round((time.thread_time() - self.state["cpu_start"]) * 1000, 2),
            # the process's peak so far, not this call's; KB on Linux, bytes on macOS
            "max_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "thread": threading.current_thread().name,
        })
