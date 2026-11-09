import logging

import pytest

from wide_events.event import LogEvent
from wide_events.recorder import log_event
from wide_events.settings import LoggerNames, Settings
from wide_events.terminal import debug, debug_exec


@log_event
def job():
    LogEvent.set(step="job")


def event_handlers(settings):
    return settings.logging_config()["loggers"][LoggerNames.EVENT_LOGGER]["handlers"]


def test_debug_events_adds_the_json_console():
    assert (event_handlers(Settings()), event_handlers(Settings(debug_events=True))) == (
        ["file"], ["file", "debug_json"]
    )


def test_debug_events_show_indented_on_the_console(tmp_path, capsys):
    config = Settings().logging
    config["handlers"]["file"]["filename"] = tmp_path / "events.log"
    Settings(logging=config, debug_events=True).apply()

    job()

    err = capsys.readouterr().err
    # 4 for the record's keys, 8 inside its "event"
    assert ('\n    "event": {' in err, '\n        "step": "job"' in err) == (True, True)


@pytest.fixture(autouse=True)
def no_active_settings(monkeypatch):
    monkeypatch.setattr(Settings, "_active", None)


def test_debug_shows_on_the_console(capsys):
    Settings(debug=True).apply()

    logging.getLogger(LoggerNames.DEBUG).debug("a")
    debug("b")
    debug_exec(lambda: "c")

    # the debug handler writes to Terminal.console, which is on stderr
    err = capsys.readouterr().err
    print(err)
    assert ("a" in err, "b" in err, "c" in err) == (True, True, True)


def test_debug_off_skips_the_call(capsys):
    Settings().apply()

    debug("b")
    debug_exec(lambda: pytest.fail("ran with debug off"))

    assert "b" not in capsys.readouterr().err


def test_apply_keeps_the_callers_config():
    config = Settings().logging
    loggers = dict(config["loggers"])

    Settings(debug=True, logging=config).apply()

    assert config["loggers"] == loggers
