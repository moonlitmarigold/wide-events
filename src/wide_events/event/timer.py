from dataclasses import dataclass, field
import time
from typing import Callable

from .blocks import EventBlock
from .errors import TimerNotStarted

@dataclass
class Timer:
    """Measures one duration and passes it to `save_timer` in milliseconds, rounded to 0.01.

    Input: `Timer(lambda ms: ...).start_timer()`, later `.stop_timer()` -> `save_timer(12.34)`; or `with Timer(...):`.
    """

    save_timer:Callable
    timer_start: float | None = field(init=False, default=None)

    def start_timer(self):
        """Start measuring from now and return the timer."""
        self.timer_start = time.perf_counter()
        return self

    def stop_timer(self):
        """Pass the milliseconds since `start_timer()` to `save_timer`, reset the start and return the timer.

        Raises:
            TimerNotStarted: When the timer was not started.
        """
        if not self.timer_start:
            raise TimerNotStarted()
        self.save_timer(round((time.perf_counter() - self.timer_start) * 1000, 2))
        self.timer_start = None
        return self

    def __enter__(self):
        self.start_timer()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_timer()


@dataclass
class TimerEventBlock(EventBlock, abstract=True):
    """Base for EventBlocks that record durations under `timers`, as `<name>_ms` in milliseconds."""


    def timer(self, name:str):
        """A timer that saves its duration as `timers.<name>_ms` on this block, used as a context manager or with
        `start_timer()`/`stop_timer()`."""
        return Timer(self.save_timer(name))

    def save_timer(self, name:str):
        """A callback that writes a duration in ms as `timers.<name>_ms` on this block."""
        return lambda duration: self.set(timers={f"{name}_ms":duration})
