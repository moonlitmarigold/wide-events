import json
import logging
import logging.config
from copy import deepcopy

import pytest

from wide_events.logging import DEFAULT_LOGGING, LoggerNames, LogEvent, log_event


@pytest.fixture
def log_file(tmp_path):
    config = deepcopy(DEFAULT_LOGGING)
    path = tmp_path / "logs" / "app.log"
    config["handlers"]["file"]["filename"] = path
    logging.config.dictConfig(config)
    yield path
    # dictConfig is global: undo it so other tests see unconfigured logging again
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "root": {"handlers": [], "level": "WARNING"},
        "loggers": {LoggerNames.EVENT_LOGGER: {"handlers": [], "level": "NOTSET", "propagate": True}},
    })


@log_event
def inner():
    LogEvent.set(step="inner")


@log_event
def outer():
    LogEvent.set(step="outer")
    inner()


def test_nested_event_writes_one_line(log_file):
    outer()

    [line] = log_file.read_text().splitlines()
    event = json.loads(line)
    assert (event["message"], event["logger"], event["event"]) == (
        "outer", LoggerNames.EVENT_LOGGER, {"step": "outer", "inner": {"step": "inner"}}
    )


class Collect(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def test_events_skip_the_console(log_file):
    # next to the console handler on the root; caplog can't tell, it also sees non-propagating loggers
    root = Collect()
    logging.getLogger().addHandler(root)

    outer()
    logging.getLogger("wide_events_test_app").warning("disk_full")

    assert root.messages == ["disk_full"]


def test_log_folder_waits_for_the_first_event(log_file):
    assert not log_file.parent.exists()

    outer()

    assert log_file.exists()

def test_logging():
    _logging = deepcopy(DEFAULT_LOGGING)
    _logging["loggers"][LoggerNames.EVENT_LOGGER] = {"handlers": ["console"], "level": "WARNING", "propagate": True}
    logging.config.dictConfig(_logging)


    logger = logging.getLogger(LoggerNames.EVENT_LOGGER)
    logger.warning("test")