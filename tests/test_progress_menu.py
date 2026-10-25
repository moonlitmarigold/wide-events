import io
import sys
import threading

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from rich.console import Console
from wide_events.ui import Menu, ProgressDisplay, Terminal
from wide_events.ui.progress import ActivityColumn

DOWN = "\x1b[B"
ENTER = "\r"


def test_bars_wait_until_they_start():
    with ProgressDisplay() as display:
        render = display.add("render", total=1)
        build = display.add("build", total=2)
        build.waiting_for("render")
        task = build.rich_task()
        assert not task.started
        assert task.fields["status"] == "waiting for render"

        render.start()
        render.finished("WriteFile")
        assert render.rich_task().fields["status"] == "done"

        build.start()
        build.started("SysExec")
        assert task.started
        assert build.rich_task().fields["status"] == "SysExec"


def test_failed_step_shows_on_the_side():
    with ProgressDisplay() as display:
        bar = display.add("build", total=2)
        bar.start()
        bar.failed("SysExec")
        assert bar.rich_task().fields["status"] == "failed at SysExec"
        assert ActivityColumn().render(bar.rich_task()).plain == "✗"


def test_skipped_step_advances_the_bar():
    with ProgressDisplay() as display:
        bar = display.add("build", total=2)
        bar.start()
        bar.finished("WriteFile")
        bar.skipped("SysExec")
        assert bar.rich_task().completed == 2


def test_bars_advance_from_threads():
    with ProgressDisplay() as display:
        bars = [display.add(f"workflow-{i}", total=50) for i in range(4)]

        def work(bar):
            bar.start()
            for step in range(50):
                bar.finished(f"step-{step}")

        threads = [threading.Thread(target=work, args=(bar,)) for bar in bars]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert [task.completed for task in display.progress.tasks] == [50] * 4


def test_only_one_display_at_a_time():
    with ProgressDisplay(), pytest.raises(RuntimeError, match="already on screen"), ProgressDisplay():
        pass
    assert ProgressDisplay.active is None


@pytest.fixture
def tty_console(monkeypatch):
    """The Terminal console as a real terminal, written to a buffer."""
    console = Console(file=io.StringIO(), force_terminal=True, width=80)
    monkeypatch.setattr(Terminal, "console", console)
    return console


def test_pause_clears_the_bars_instead_of_leaving_a_frame(tty_console):
    with ProgressDisplay() as display:
        display.add("build", total=1)
        with ProgressDisplay.paused():
            pass
        assert display.progress.live.transient is False
    # the frame left on screen at the end, and none from the pause
    assert tty_console.file.getvalue().count("\x1b[?25l") == 2  # cursor hidden on each start
    assert "build" in tty_console.file.getvalue()


def test_paused_takes_the_display_off_screen():
    with ProgressDisplay() as display:
        with ProgressDisplay.paused():
            assert not display.progress.live.is_started
        assert display.progress.live.is_started


@pytest.fixture
def keys(monkeypatch):
    """Typed keys for the menu, as if stdin were a terminal."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with create_pipe_input() as pipe, create_app_session(input=pipe):
        yield pipe


def test_menu_returns_the_picked_option(keys):
    keys.send_text(DOWN + ENTER)
    assert Menu("Server?", ["vps-1", "vps-2"]).ask() == "vps-2"


def test_menu_pauses_the_display(keys):
    keys.send_text(ENTER)
    with ProgressDisplay() as display:
        assert Menu("Server?", ["vps-1"]).ask() == "vps-1"
        assert display.progress.live.is_started


def test_menu_asks_on_the_alternate_screen(keys, tty_console):
    keys.send_text(ENTER)
    assert Menu("Server?", ["vps-1"]).ask() == "vps-1"
    out = tty_console.file.getvalue()
    assert out.index("\x1b[?1049h") < out.index("Server?") < out.index("\x1b[?1049l")


def test_menu_needs_a_terminal(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(RuntimeError, match="needs an interactive terminal"):
        Menu("Server?", ["vps-1"]).ask()


def test_menu_needs_options():
    with pytest.raises(ValueError, match="has no options"):
        Menu("Server?", [])
