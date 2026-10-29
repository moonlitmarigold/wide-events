from wide_events.blocks import TimerEventBlock
from wide_events.blocks import ContextBlock, ContextEvent
from multiprocessing import Pool
import asyncio
import threading
from time import sleep, time
from random import randint
import concurrent.futures

class TimerBlock(TimerEventBlock):
    namespace = "timer"

def do_task(num:int):
    ctx, blocks = ContextEvent.init(), ContextBlock.init() # Easier access to a event block -> not extra Event block needed

    ContextEvent.set(num=num)
    with TimerBlock().timer("sleep"): # Why ()?
        sleep(randint(0, 10)/10)
    ContextEvent.set(end=True)

    blocks.drop()
    return ctx.drop()

def test_mp():
    with Pool(processes=4) as pool:
        results = pool.map(do_task, [x for x in range(3)])
    for i, r in enumerate(results):
        assert r["num"] == i
    """
    Result:
    {'num': 0, 'timer': {'timers': {'sleep_ms': 400.12}}, 'end': True}
    {'num': 1, 'timer': {'timers': {'sleep_ms': 500.12}}, 'end': True}
    {'num': 2, 'timer': {'timers': {'sleep_ms': 0.04}}, 'end': True}
    -> Reuse one context for multiple processes
    """

def test_th():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(do_task, range(3)))
    assert [(r["num"], r["end"]) for r in results] == [(0, True), (1, True), (2, True)]


def test_th_events_stay_apart():
    barrier = threading.Barrier(3)

    def task(num:int):
        ctx, blocks = ContextEvent.init(), ContextBlock.init()
        ContextEvent.set(num=num)
        barrier.wait()  # all three events are open at once, so a leak between threads would show
        TimerBlock(kwargs={"by": num})
        barrier.wait()
        blocks.drop()
        return ctx.drop()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(task, range(3)))
    assert results == [{"num": n, "timer": {"by": n}} for n in range(3)]
    assert ContextEvent.get() == {}  # the test's own thread never saw them


async def do_async_task(num:int):
    ctx, blocks = ContextEvent.init(), ContextBlock.init()

    ContextEvent.set(num=num)
    with TimerBlock().timer("sleep"):
        await asyncio.sleep(randint(0, 10)/100)
    ContextEvent.set(end=True)

    blocks.drop()
    return ctx.drop()


def test_async():
    async def main():
        return await asyncio.gather(*(do_async_task(x) for x in range(3)))

    results = asyncio.run(main())
    assert [(r["num"], r["end"]) for r in results] == [(0, True), (1, True), (2, True)]


def test_async_events_stay_apart():
    async def task(num:int, barrier:asyncio.Barrier):
        ctx, blocks = ContextEvent.init(), ContextBlock.init()
        ContextEvent.set(num=num)
        await barrier.wait()  # every task's event is open before any of them writes its block
        TimerBlock(kwargs={"by": num})
        await barrier.wait()
        blocks.drop()
        return ctx.drop()

    async def main():
        # asyncio.Barrier binds to the running loop, so it's created inside it
        barrier = asyncio.Barrier(3)
        return await asyncio.gather(*(task(x, barrier) for x in range(3)))

    results = asyncio.run(main())
    assert results == [{"num": n, "timer": {"by": n}} for n in range(3)]


def test_async_to_thread():
    async def main():
        return await asyncio.gather(*(asyncio.to_thread(do_task, x) for x in range(3)))

    results = asyncio.run(main())
    assert [(r["num"], r["end"]) for r in results] == [(0, True), (1, True), (2, True)]


def test_to_thread_sees_the_callers_event():
    async def main():
        ctx = ContextEvent.init()
        ContextEvent.set(caller=True)
        # to_thread copies the context, and the copy holds the same dict: the thread writes into the caller's event
        await asyncio.to_thread(ContextEvent.set, worker=True)
        return ctx.drop()

    assert asyncio.run(main()) == {"caller": True, "worker": True}