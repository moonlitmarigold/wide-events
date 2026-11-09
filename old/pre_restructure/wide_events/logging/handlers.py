import logging
from pathlib import Path


class FileHandler(logging.FileHandler):
    """A `logging.FileHandler` that creates the folder of its log file."""

    def _open(self):
        # here and not in __init__: with `delay=True` the folder only appears once the first record is written
        Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
        return super()._open()
