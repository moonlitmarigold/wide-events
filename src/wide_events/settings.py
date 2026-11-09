from enum import StrEnum


class LoggerNames(StrEnum):
    """The names of the package's loggers, for `logging.getLogger` and the `loggers` of `DEFAULT_LOGGING`."""

    EVENT_LOGGER = "wide_events.event"
    DEBUG = "debug"

# TODO: Document the logging settings: what each handler/logger is for, that the console handler is WARNING (so
#  events at INFO never show there), and how to route events elsewhere (own handler + json formatter + propagate=False)
# TODO: Class-based settings (approach B): a `Settings` class with ClassVars `collectors`, `event_block` and `logging`
#  (still a plain dictConfig dict), apps subclass it and call `AppSettings.apply()` once. `apply()` runs dictConfig,
#  sets the active settings that `return_pm`/`LogEvent` read, and is the freeze point for the cached `return_pm`.
#  Pydantic only in bigger projects, for loading from files.
# TODO: A debug setting for logging: one switch (e.g. `Settings.debug`) that adds an extra debug call/handler, so
#  events and DEBUG records also show on the console during development

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
            "class": "wide_events.log.handlers.FileHandler",
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

# TODO: DEBUG Handler/logger -> Wide-Events to the console
# TODO: Indents on console wide-events