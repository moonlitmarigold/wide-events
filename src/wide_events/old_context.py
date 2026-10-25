from contextvars import ContextVar, Token
import dataclasses
from typing import ClassVar
import uuid

_current: ContextVar[dict | None] = ContextVar("wide_events-" + uuid.uuid4().hex, default=None)
_blocks: ContextVar[dict | None] = ContextVar("wide_events.block", default=None)
_collectors: ContextVar[list | None] = ContextVar("wide_events.collectors", default=None)
_capture: ContextVar[bool | None] = ContextVar("wide_events.capture", default=None)











@dataclasses.dataclass
class ContextCollectors:

    token: Token | None = None

    @classmethod
    def init(cls):
        _cls = cls()
        _cls.token = _collectors.set([])
        return _cls

    @staticmethod
    def get():
        ctx = _collectors.get()
        if ctx is None:
            return []
        return ctx

    @staticmethod
    def set_collectors(collectors:list):
        ContextCollectors.get().extend(collectors)


    def drop(self):
        if not self.token:
            return
        _ctx = self.get()
        _collectors.reset(self.token)
        return _ctx

@dataclasses.dataclass
class ContextCapture(BaseContext):

    _contex_var = _capture

    @classmethod
    def set(cls, var:bool):
        cls._contex_var.set(var)

    @classmethod
    def get(cls):
        return cls._contex_var.get()

    @classmethod
    def init(cls):
        _cls = cls()
        ctx_var = _cls.check_or_raise_contex_var()
        _cls.token = ctx_var.set(None)
        return _cls
