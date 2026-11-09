import pytest

from wide_events.collectors import ArgumentsCollector


@pytest.mark.parametrize("param, sensitive", [
    ("api_key", True), ("apiKey", True), ("auth_tokens", True), ("passwords", True), ("Authorization", True),
    ("monkey", False), ("keyboard", False), ("author", False), ("user", False),
])
def test_redaction_matches_whole_words(param, sensitive):
    assert ArgumentsCollector().is_sensitive(param) == sensitive
