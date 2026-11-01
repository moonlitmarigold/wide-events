from datetime import datetime, UTC

from ..blocks.timer import _Timer
from ..context.ids import uuid4_hex
from ..results import BaseResult, ExceptionResult, Status
from ._logging import LoggingCollector, logging_hookimpl


class ExceptionCollector(LoggingCollector):

    name = "ExceptionCollector"

    @logging_hookimpl
    def on_exception(self, name, func, args, kwargs, exception):
        self.context.set(exception=ExceptionResult.from_exception(exception).dump())


class TimingCollector(LoggingCollector):

    name = "TimingCollector"

    @logging_hookimpl
    def on_create(self, name, func, args, kwargs):
        self.state["timer"] = _Timer(lambda duration: self.set(duration_ms=duration)).start_timer()

    @logging_hookimpl
    def on_finish(self, name, func, args, kwargs, result):
        self.state["timer"].stop_timer()

    @logging_hookimpl
    def on_exception(self, name, func, args, kwargs, exception):
        self.state["timer"].stop_timer()


class TimestampCollector(LoggingCollector):

    name = "TimestampCollector"

    @logging_hookimpl
    def on_create(self, name, func, args, kwargs):
        self.set(started_at=datetime.now(UTC))

    @logging_hookimpl
    def on_finish(self, name, func, args, kwargs, result):
        self.set(finished_at=datetime.now(UTC))

    @logging_hookimpl
    def on_exception(self, name, func, args, kwargs, exception):
        self.set(finished_at=datetime.now(UTC))


class OutcomeCollector(LoggingCollector):

    name = "OutcomeCollector"

    @logging_hookimpl
    def on_finish(self, name, func, args, kwargs, result):
        self.set(outcome=Status.success)

    @logging_hookimpl
    def on_exception(self, name, func, args, kwargs, exception):
        self.set(outcome=Status.failed)


class IdentityCollector(LoggingCollector):

    name = "IdentityCollector"

    @logging_hookimpl
    def on_create(self, name, func, args, kwargs):
        self.set(event_id=uuid4_hex(), function=func.__qualname__, module=func.__module__)


class ResultCollector(LoggingCollector):

    name = "ResultCollector"

    @logging_hookimpl
    def on_finish(self, name, func, args, kwargs, result):
        if isinstance(result, BaseResult):
            self.set(result=result.dump())
        elif result is not None:
            # only the type: a raw return value can be huge, unserializable or sensitive
            self.set(result_type=type(result).__qualname__)
