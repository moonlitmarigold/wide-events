import sys
import threading
from collections.abc import Sequence
from typing import ClassVar

import questionary
from prompt_toolkit.output import create_output

from .progress import ProgressDisplay
from ..terminal import Terminal


class Menu:
    """An arrow-key choice between `options`, asked on a blank screen like most CLI tools do; the terminal comes
    back as it was once a pick is made. One menu asks at a time, and the live progress display is paused meanwhile."""

    lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, question: str, options: Sequence[str]):
        if not options:
            raise ValueError(f"menu {question!r} has no options")
        self.question = question
        self.options = list(options)

    def ask(self) -> str:
        """Show the menu and return the picked option. Ctrl-C raises KeyboardInterrupt.

        Raises:
            RuntimeError: stdin isn't an interactive terminal, so nobody can pick.
        """
        if not sys.stdin.isatty():
            raise RuntimeError(f"menu {self.question!r} needs an interactive terminal, stdin isn't one")
        # screen(): the terminal's alternate screen, a no-op when the console isn't a terminal
        with self.lock, ProgressDisplay.paused(), Terminal.console.screen():
            # drawn on the Terminal console's stream (stderr), so stdout stays free for results
            question = questionary.select(
                self.question, choices=self.options, output=create_output(stdout=Terminal.console.file),
            )
            # unsafe_ask: ask() would swallow Ctrl-C and return None
            return question.unsafe_ask()
