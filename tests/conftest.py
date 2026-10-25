import pytest
from wide_events.log import LogConfig


# console only and warnings up; the config is global, so every test starts from it
class QuietLogConfig(LogConfig):
    name = "wide-events-tests"


@pytest.fixture(autouse=True)
def quiet_logging():
    QuietLogConfig.configure()
