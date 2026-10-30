from .base import LoggerNames

# Passed to `logging.config.dictConfig`, as Django's LOGGING setting. Use it as is, or `deepcopy` it and change
# what differs, e.g. `config["handlers"]["file"]["filename"]`. The console handler needs the `log` extra (rich).
DEFAULT_LOGGING = {
    "version": 1,
    # otherwise loggers created at import time, e.g. wide_events.checks, are silenced
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": ["levelname", "name", "message"],
            "rename_fields": {"levelname": "loglevel", "name": "logger"},
            "timestamp": True,
        },
    },
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            # the progress display shows normal flow; the console only gets problems
            "level": "WARNING",
            # shared with the progress display, otherwise log lines overwrite the live progress bar
            "console": "ext://wide_events.terminal.Terminal.console",
            "rich_tracebacks": True,
        },
        "file": {
            "class": "wide_events.logging.handlers.FileHandler",
            "filename": "logs/wide_events.log",
            "delay": True,
            "formatter": "json",
        },
    },
    "loggers": {
        # wide events go to the file only; everything else reaches the console through the root
        LoggerNames.EVENT_LOGGER: {"handlers": ["file"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
