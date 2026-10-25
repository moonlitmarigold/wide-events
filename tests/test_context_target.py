from wide_events.blocks import ContextEvent
from dataclasses import dataclass
from contextvars import ContextVar
from uuid import uuid4
from typing import ClassVar

def test_new_context():
    @dataclass
    class Context2(ContextEvent):
        _contex_var:ClassVar[ContextVar[dict]] = ContextVar("wide_events-" + uuid4().hex, default={})

    c1, c2 = Context2.init(), ContextEvent.init()


    ContextEvent.set(a=True)
    Context2.set(a=False)
    
    assert c1.drop() != c2.drop()