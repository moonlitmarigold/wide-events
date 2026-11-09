from .base import EventBlock
from dataclasses import dataclass, field
import time
from typing import Callable

class TimerNotStarted(Exception):
    """Raised when a timer is stopped before it was started."""

    def __init__(self):
        super().__init__("The Timer has not been started so it cant record a time.")

@dataclass
class _Timer:

    save_timer:Callable
    timer_start: float | None = field(init=False, default=None)

    def start_timer(self):
        self.timer_start = time.perf_counter()
        return self

    def stop_timer(self):
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
        return _Timer(self.save_timer(name))

    def save_timer(self, name:str):
        """A callback that writes a duration in ms as `timers.<name>_ms` on this block."""
        return lambda duration: self.set(timers={f"{name}_ms":duration})
