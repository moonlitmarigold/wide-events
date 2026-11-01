from wide_events.blocks import EventBlock
from dataclasses import dataclass
from contextvars import ContextVar
from uuid import uuid4
from typing import ClassVar
from wide_events.blocks.event import ContextCollection
from wide_events.logging import LogContext, LogEvent, ContextNames, log_event
from wide_events.collectors import *
from copy import deepcopy
from wide_events.logging import DEFAULT_LOGGING, LoggerNames
import logging
import logging.config


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
    _logging = deepcopy(DEFAULT_LOGGING)
    _logging["handlers"]["event_console"] = {
        "class": "logging.StreamHandler", "stream": "ext://sys.stdout", "formatter": "json",
    }
    _logging["loggers"][LoggerNames.EVENT_LOGGER] = {"handlers": ["event_console"], "level": "INFO", "propagate": False}
    logging.config.dictConfig(_logging)
    res = sample_func()

    print([x for x in LOGGING_COLLECTORS.values()])

    assert res == 1

class TestHook(LoggingCollector):
    name = "hook_name"

    @logging_hookimpl
    def on_create(self, name, func, args, kwargs):
        print('test')