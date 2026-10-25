import json

from wide_events.event import WideEvent, log_event
from wide_events.log import *
from pathlib import Path
from wide_events.blocks import EventBlock
from wide_events.context import ContextEvent

class MainRun(LogClass):

    def __init__(self):
        self.run = WideEvent.wrap(self.run)

    def run(self):
        SubRun().run()

class SubRun(LogClass):

    @log_event("test")
    def run(self):
        ContextEvent.update({"test":"test"})
        [Exec(x).run() for x in range(4)]

class ExecEventBlock(EventBlock, abstract=False):

    namespace = "exec_res"
    use_namespace_on_write = False
    append_list = True

    @classmethod
    def add(cls, n):
        return cls().set(num=[n])

class Exec(LogClass):

    def __init__(self, num):
        self.num = num

    @log_event("exec")
    def run(self):
        ExecEventBlock.add(self.num)
        self.console_logger.info("test")
        return self.num




def test_wrappers(tmp_path:Path):
    class TmpFileLog(FileLogHandler):
        path = tmp_path / "logs" / "app.log"

    class BaseLogging(LogConfig):
        name = "wide-events-tests"
        handlers = (VerboseConsoleLogHandler, TmpFileLog)

    BaseLogging.configure()
    MainRun().run()

    [line] = TmpFileLog.path.read_text().splitlines()
    event = json.loads(line)
    assert (event["test"], event["event"], event["logger"], event["app"]) == (
        {"test": "test", "exec": {"num": [0, 1, 2, 3]}}, "wide_event", "wide_events.event", "wide-events-tests"
    )

