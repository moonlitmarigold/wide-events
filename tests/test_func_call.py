import logging

import pytest

from wide_events.collectors import ArgumentsCollector
from wide_events.event import LogEvent
from wide_events.recorder import log_event, record_function_call
from wide_events.settings import LoggerNames, Settings


@pytest.fixture(autouse=True)
def no_active_settings(monkeypatch):
    monkeypatch.setattr(Settings, "_active", None)


class Collect(logging.Handler):
    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        self.events.append((record.getMessage(), record.event))


def collect_on(name):
    # straight on the logger: earlier tests leave loggers configured with propagate=False or another level
    logger = logging.getLogger(name)
    handler, level = Collect(), logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield handler.events
    logger.removeHandler(handler)
    logger.setLevel(level)


@pytest.fixture
def calls():
    yield from collect_on(LoggerNames.FUNC_CALL_LOGGER)


@pytest.fixture
def events():
    yield from collect_on(LoggerNames.EVENT_LOGGER)


@record_function_call
def charge(user, api_key, monkey=3):
    return 1


@record_function_call
def checkout(user):
    return charge(user, "s3cr3t")


@log_event
def job():
    LogEvent.set(step="job")
    charge("ann", "s3cr3t")


@pytest.mark.parametrize("param, sensitive", [
    ("api_key", True), ("apiKey", True), ("auth_tokens", True), ("passwords", True), ("Authorization", True),
    ("monkey", False), ("keyboard", False), ("author", False), ("user", False),
])
def test_redaction_matches_whole_words(param, sensitive):
    assert ArgumentsCollector().is_sensitive(param) == sensitive


def test_function_call_records_on_its_own_logger(calls):
    charge("ann", "s3cr3t")
    print(calls)
    [(name, event)] = calls
    assert (name, event["args"], {"host", "python", "pid"} <= event["environment"].keys(), "cpu_ms" in event["resources"]) == (
        "charge", {"user": "ann", "api_key": "[REDACTED]", "monkey": 3}, True, True
    )


def test_nested_call_merges_into_the_outer_call(calls):
    checkout("ann")

    [(name, event)] = calls
    assert (name, event["args"], event["charge"]["args"]["user"]) == ("checkout", {"user": "ann"}, "ann")


def test_function_call_stays_out_of_the_wide_event(calls, events):
    job()

    [(_, event)] = events
    assert ("args" in event, "charge" in event, [name for name, _ in calls]) == (False, False, ["charge"])


def test_only_listed_func_call_collectors_run(calls):
    Settings(func_call_collectors=("ArgumentsCollector",), logging=None).apply()

    charge("ann", "s3cr3t")

    [(_, event)] = calls
    assert set(event) == {"args"}


def test_unknown_func_call_collector_lists_the_registered_ones():
    with pytest.raises(ValueError, match="Unknown func_call_collectors \\['Nope'\\].*ArgumentsCollector"):
        Settings(func_call_collectors=("Nope",))


def test_debug_events_also_show_function_calls():
    loggers = Settings(debug_events=True).logging_config()["loggers"]

    assert loggers[LoggerNames.FUNC_CALL_LOGGER]["handlers"] == ["file", "debug_json"]
