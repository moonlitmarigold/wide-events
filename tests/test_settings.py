import logging

import pytest

from wide_events.event import LogEvent
from wide_events.recorder import log_event
from wide_events.results import Status
from wide_events.settings import DEFAULT_COLLECTORS, LoggerNames, Settings


@pytest.fixture(autouse=True)
def no_active_settings(monkeypatch):
    monkeypatch.setattr(Settings, "_active", None)


@pytest.fixture
def dict_configs(monkeypatch):
    calls = []
    monkeypatch.setattr("wide_events.settings.dictConfig", calls.append)
    return calls


class Collect(logging.Handler):
    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        self.events.append(record.event)


@pytest.fixture
def events():
    # straight on the event logger: earlier tests leave it configured with propagate=False or level WARNING
    logger = logging.getLogger(LoggerNames.EVENT_LOGGER)
    handler, level = Collect(), logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield handler.events
    logger.removeHandler(handler)
    logger.setLevel(level)


@log_event
def job():
    LogEvent.set(step="job")


def test_unknown_collector_lists_the_registered_ones():
    with pytest.raises(ValueError, match="Unknown collectors \\['Nope'\\].*TimingCollector"):
        Settings(collectors=("Nope",))


def test_event_block_must_be_an_event_block():
    with pytest.raises(TypeError, match="EventBlock subclass"):
        Settings(event_block=dict)


def test_apply_configures_logging_and_activates(dict_configs):
    config = {"version": 1}
    settings = Settings(logging=config).apply()

    assert (dict_configs, Settings.active()) == ([config], settings)


def test_apply_without_logging_leaves_logging_alone(dict_configs):
    Settings(logging=None).apply()

    assert dict_configs == []


def test_active_defaults_without_configuring_logging(dict_configs):
    assert (Settings.active().collectors, dict_configs) == (DEFAULT_COLLECTORS, [])


def test_plugin_manager_is_built_once_per_settings():
    settings = Settings()

    assert settings.plugin_manager is settings.plugin_manager


def test_only_listed_collectors_run(events):
    Settings(collectors=("OutcomeCollector",), logging=None).apply()

    job()

    assert events == [{"step": "job", "outcome": Status.success}]


def test_default_collectors_run(events):
    job()

    [event] = events
    assert {"event_id", "duration_ms", "started_at", "finished_at", "outcome"} <= event.keys()
