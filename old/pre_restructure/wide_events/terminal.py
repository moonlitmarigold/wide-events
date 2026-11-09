from typing import ClassVar

from rich.console import Console


class Terminal:
    """The single rich Console. The progress display and console logs must share it,
    otherwise log lines overwrite the live progress bar."""

    # stderr keeps stdout free for the CLI's own output (e.g. `infra render > file`)
    console: ClassVar[Console] = Console(stderr=True)
