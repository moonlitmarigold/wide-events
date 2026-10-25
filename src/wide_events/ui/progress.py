import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar, Self

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

from ..terminal import Terminal


class ActivityColumn(SpinnerColumn):
    """Spinner that only spins while its bar runs: a dot while it waits, ✓ when it's done, ✗ when it failed."""

    def __init__(self):
        super().__init__(finished_text=Text("✓", style="green"))

    def render(self, task: Task):
        if not task.started:
            return Text("·", style="dim")
        # stop_task() is only called on a failure; a finished task is handled by finished_text
        if task.stop_time is not None and not task.finished:
            return Text("✗", style="red")
        return super().render(task)


class IdleBarColumn(BarColumn):
    """Bar that stays empty until its task starts, instead of rich's pulse, which looks like activity."""

    def render(self, task: Task):
        bar = super().render(task)
        bar.pulse = False
        return bar


class ProgressDisplay:
    """Live terminal view of a run: one bar per workflow, with its state as text on the side, and a ✓ or ✗ line
    per finished step.

    Bars are added up front and wait until they start, so workflows that run concurrently show together. Its
    methods are safe to call from several threads.
    """

    columns: ClassVar[tuple] = (
        ActivityColumn(),
        TextColumn("{task.description}"),
        IdleBarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("{task.fields[status]}", style="dim"),
    )
    done_mark: ClassVar[Text] = Text("✓ ", style="green")
    failed_mark: ClassVar[Text] = Text("✗ ", style="red")
    skipped_mark: ClassVar[Text] = Text("- ", style="dim")

    # the display that is on screen, so a menu can pause it without being handed it
    active: ClassVar["ProgressDisplay | None"] = None

    def __init__(self):
        self.progress = Progress(*self.columns, console=Terminal.console)
        # reentrant: a paused display holds it while the menu's thread may also print a mark
        self.lock = threading.RLock()

    def __enter__(self) -> Self:
        if ProgressDisplay.active is not None:
            raise RuntimeError("a ProgressDisplay is already on screen; add bars to it instead")
        self.progress.start()
        ProgressDisplay.active = self
        return self

    def __exit__(self, *exc_info):
        ProgressDisplay.active = None
        self.progress.stop()

    def add(self, name: str, total: int) -> "ProgressBar":
        """Add a waiting bar for the workflow `name` with `total` steps."""
        return ProgressBar(self, name, total)

    def mark(self, mark: Text, text: str):
        """Print a finished-step line above the bars."""
        with self.lock:
            self.progress.console.print(mark + text)

    @classmethod
    @contextmanager
    def paused(cls) -> Iterator[None]:
        """Clear the active display off the screen meanwhile and draw it again after, e.g. around a menu. Marks from
        other threads wait until then."""
        display = cls.active
        if display is None:
            yield
            return
        live = display.progress.live
        with display.lock:
            # transient: stop() clears the bars; otherwise it leaves a last frame that start() would draw again below
            transient, live.transient = live.transient, True
            display.progress.stop()
            live.transient = transient
            try:
                yield
            finally:
                display.progress.start()


class ProgressBar:
    """One workflow in a ProgressDisplay. It waits, with an empty bar and no elapsed time, until start()."""

    def __init__(self, display: ProgressDisplay, name: str, total: int):
        self.display = display
        self.name = name
        self.task = display.progress.add_task(name, total=total, start=False, status="queued")

    def rich_task(self) -> Task:
        """The rich Task behind this bar."""
        return next(task for task in self.display.progress.tasks if task.id == self.task)

    def status(self, text: str):
        """Set the text on the side of the bar."""
        self.display.progress.update(self.task, status=text)

    def waiting_for(self, *names: str):
        """Show which workflows this one waits for."""
        self.status(f"waiting for {', '.join(names)}")

    def start(self):
        """Start the elapsed time and fill the bar from here on."""
        self.display.progress.start_task(self.task)
        self.status("running")

    def started(self, step: str):
        """Show `step` as the running step on the side."""
        self.status(step)

    def finished(self, step: str):
        """Print a ✓ line for `step` and advance the bar; after the last step the side shows 'done'."""
        self.display.mark(self.display.done_mark, f"{self.name}: {step}")
        self.display.progress.advance(self.task)
        if self.rich_task().finished:
            self.status("done")

    def skipped(self, step: str):
        """Print a - line for `step` and advance the bar, so skipped steps still fill it."""
        self.display.mark(self.display.skipped_mark, f"{self.name}: {step}")
        self.display.progress.advance(self.task)

    def failed(self, step: str):
        """Print a ✗ line for `step`, show where the workflow failed and stop its elapsed time."""
        self.display.mark(self.display.failed_mark, f"{self.name}: {step}")
        self.status(f"failed at {step}")
        self.display.progress.stop_task(self.task)
