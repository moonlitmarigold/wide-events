from wide_events.blocks import EventBlock
from dataclasses import dataclass
from contextvars import ContextVar
from uuid import uuid4
from typing import ClassVar
from wide_events.blocks.event import ContextCollection
from wide_events.logging import LogContext, LogEvent, ContextNames, log_event


def test_new_blocks():
    l = LogContext.init()

    LogEvent.set(a="b")

    assert l.drop() == {"a":"b"}

def test_context_collector():
    con = ContextCollection([LogContext]).init()

    LogEvent.set(a="b")

    _drop = con.drop()
    print(_drop)
    assert _drop[ContextNames.log_context] == {"a":"b"}

@dataclass
class SubEvent(LogEvent):
    namespace = "sub"
    use_namespace_on_write = True

@log_event
def sample_func(once:bool=False):
    LogEvent.set(a="b")
    LogEvent.set(c="d")

    if not once:
        sample_func(True)

    SubEvent.set(a="b")

    return 1

def test_log_event():
    res = sample_func()

    assert res == 1