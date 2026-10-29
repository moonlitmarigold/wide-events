from datetime import datetime, timezone

from ..blocks.timer import _Timer
from .base import Collector
from .registry import builtin_collector


@builtin_collector
class Duration(Collector):

    def __init__(self):
        self.timer = None

    def on_create(self, request):
        self.timer = _Timer(lambda ms: self.set(duration_ms=ms)).start_timer()

    def on_finish(self, request, response):
        self.timer.stop_timer()

    def on_finish_no_response(self, request, response=None):
        self.timer.stop_timer()


@builtin_collector
class Timestamp(Collector):

    def on_create(self, request):
        self.set(started_at=datetime.now(timezone.utc).isoformat(timespec='milliseconds'))
