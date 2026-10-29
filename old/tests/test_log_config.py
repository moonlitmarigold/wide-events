import json
import logging
from pathlib import Path

import pytest
import structlog
from wide_events.log import FileLogHandler, LogConfig, LogClass, ConsoleLogHandler, VerboseConsoleLogHandler, Debug, DebugLogHandler, FileMirrorLogHandler, Terminal, divider
from wide_events.log.handlers import CONSOLE_LOGGER, EVENT_LOGGER


def test_file_log_writes_json_lines(tmp_path:Path):
    class TmpFileLog(FileLogHandler):
        path = tmp_path / "logs" / "app.log"

    class AppLogConfig(LogConfig):
        name = "wide_events_test_app"
        handlers = (TmpFileLog,)

    AppLogConfig.configure()
    structlog.get_logger("wide_events_test_app.module").info("thing_done", count=2)

    [line] = TmpFileLog.path.read_text().splitlines()
    event = json.loads(line)
    assert (event["event"], event["count"], event["logger"], event["app"]) == (
        "thing_done", 2, "wide_events_test_app.module", "wide_events_test_app"
    )


def test_third_party_records_get_the_shared_fields(tmp_path:Path):
    class TmpFileLog(FileLogHandler):
        path = tmp_path / "logs" / "app.log"

    class AppLogConfig(LogConfig):
        name = "wide_events_test_app"
        handlers = (TmpFileLog,)
        quiet = {"wide_events_test_noisy": logging.WARNING}

    AppLogConfig.configure()
    logging.getLogger("wide_events_test_lib").info("plain_stdlib")
    logging.getLogger("wide_events_test_noisy").info("turned_down")

    [line] = TmpFileLog.path.read_text().splitlines()
    event = json.loads(line)
    assert (event["event"], event["level"], event["logger"], event["app"]) == (
        "plain_stdlib", "info", "wide_events_test_lib", "wide_events_test_app"
    )


def test_configure_needs_a_name():
    with pytest.raises(TypeError, match="has no app name"):
        LogConfig.configure()


def test_file_log_needs_a_path():
    with pytest.raises(TypeError, match="has no log file"):
        FileLogHandler.build()

def test_console_logging(tmp_path:Path):
    class TmpFileLog(FileLogHandler):
        path = tmp_path / "logs" / "app.log"

    class AppLogConfig(LogConfig):
        name = "wide_events_test_app"
        handlers = (
            ConsoleLogHandler,
            #DebugLogHandler
        )


    AppLogConfig.configure()
    AppLogConfig.get_logger("wide_events_test_app").warning("test1")
    LogConfig.get_logger("wide_events_test_app").warning("test2")
    Debug.log("test")


def test_console_lines_and_wide_events_go_to_one_output_each(tmp_path:Path):
    class TmpFileLog(FileLogHandler):
        path = tmp_path / "logs" / "app.log"

    class AppLogConfig(LogConfig):
        name = "wide_events_test_app"
        handlers = (TmpFileLog,)

    AppLogConfig.configure()
    LogClass().console_logger.info("console_only")
    LogClass.file_logger().info("wide_event", a="b")

    [line] = TmpFileLog.path.read_text().splitlines()
    event = json.loads(line)
    assert (event["event"], event["a"]) == ("wide_event", "b")


def test_console_drops_wide_events():
    console = ConsoleLogHandler.build()
    event = logging.LogRecord(EVENT_LOGGER, logging.ERROR, __file__, 1, "wide_event", None, None)
    line = logging.LogRecord(CONSOLE_LOGGER, logging.ERROR, __file__, 1, "line", None, None)
    assert (console.filter(event), bool(console.filter(line))) == (False, True)


def test_divider_is_a_console_info_rule(tmp_path:Path):
    class TmpFileLog(FileLogHandler):
        path = tmp_path / "logs" / "app.log"

    class VerboseConfig(LogConfig):
        name = "wide_events_test_app"
        handlers = (VerboseConsoleLogHandler, TmpFileLog)

    class DefaultConfig(LogConfig):
        name = "wide_events_test_app"

    VerboseConfig.configure()
    with Terminal.console.capture() as verbose:
        divider("Init")
    DefaultConfig.configure()
    with Terminal.console.capture() as default:
        divider("Init")

    assert "== Init ==" in verbose.get() and "INFO" not in verbose.get()
    assert default.get() == ""
    assert TmpFileLog.path.read_text() == ""


def test_file_mirror_prints_what_the_file_gets(tmp_path:Path):
    class TmpFileLog(FileLogHandler):
        path = tmp_path / "logs" / "app.log"

    class AppLogConfig(LogConfig):
        name = "wide_events_test_app"
        handlers = (TmpFileLog, FileMirrorLogHandler)

    AppLogConfig.configure()
    with Terminal.console.capture() as mirror:
        LogClass().console_logger.info("console_only")
        LogClass.file_logger().info("wide_event", a="b")

    [line] = TmpFileLog.path.read_text().splitlines()
    assert json.loads(mirror.get()) == json.loads(line)
