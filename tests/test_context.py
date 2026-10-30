import pytest
from wide_events import context
from wide_events.context.implementations.list import ContextList
from wide_events.context.base import ContextNotInitError
from wide_events.blocks import ContextBlock


def test_dict():
    class TestContext(context.ContextDict):
        _contex_var = context.ReturnContextVars.with_uuid4()

    t = TestContext.init()

    TestContext.set(a="b")
    TestContext.set(name={"1":1})
    TestContext.set(name = {"2": 2})

    event = t.drop()

    assert "a" in event
    assert "name" in event

    name = event["name"]
    assert "1" in name
    assert "2" in name

def test_list():
    class TestList(context.ContextList):
        _contex_var = context.ReturnContextVars.with_uuid4()

    t = TestList.init()

    t.set(['a'])
    t.set('b')

    event = t.drop()

    assert 'a' in event
    assert 'b' in event

def test_single_value():
    class BoolValue(context.SingleValueContext):
        _contex_var = context.ReturnContextVars.with_uuid4()
        context_default = lambda:False

    b = BoolValue.init()

    BoolValue.set(True)

    assert b.drop()

def test_inline_context():
    BoolValue:context.SingleValueContext = context.SingleValueContext.new("bool_value", False)

    b = BoolValue.init()

    BoolValue.set(True)

    assert b.drop()

def test_subclass_default():
    class BoolValue(context.SingleValueContext, default=False): pass

    assert BoolValue.get() is False
    b = BoolValue.init()
    assert BoolValue.get() is False
    BoolValue.set(True)
    assert b.drop()


def test_inline_list_gets_fresh_list():
    TestList = context.ContextList.new("TestList")
    Other = context.ContextList.new("Other")

    assert TestList._contex_var is not Other._contex_var
    t = TestList.init()
    TestList.set(["a"])
    assert t.drop() == ["a"]
    assert TestList.init().drop() == []


@pytest.mark.parametrize("make_context, args, kwargs", [
    (lambda: context.ContextDict.new("Dict"), (), {"a": "b"}),
    (lambda: context.ContextList.new("List"), (["a"],), {}),
    (lambda: context.SingleValueContext.new("Single"), (True,), {}),
    (lambda: ContextBlock, ("key", object()), {}),
])
def test_set_without_init_raises(make_context, args, kwargs):
    with pytest.raises(ContextNotInitError):
        make_context().set(*args, **kwargs)
