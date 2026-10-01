"""What each severity looks like and logs as, for every widget that shows one."""

# Built-in
import logging
from typing import NamedTuple, Optional

# Internal
from fxgui.fxwidgets._constants import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    SUCCESS,
    WARNING,
)


class _Severity(NamedTuple):
    """A severity's title, icon name, feedback color key and log level."""

    title: str
    icon: str
    feedback: str
    level: int


SEVERITIES = {
    CRITICAL: _Severity("Critical", "cancel", "error", logging.CRITICAL),
    ERROR: _Severity("Error", "error", "error", logging.ERROR),
    WARNING: _Severity("Warning", "warning", "warning", logging.WARNING),
    SUCCESS: _Severity("Success", "check_circle", "success", logging.INFO),
    INFO: _Severity("Info", "info", "info", logging.INFO),
    DEBUG: _Severity("Debug", "bug_report", "debug", logging.DEBUG),
}


def severity(level: Optional[int]) -> _Severity:
    """Return `level`'s severity; an unknown one reads as INFO."""
    return SEVERITIES.get(level, SEVERITIES[INFO])


def log(logger: Optional[logging.Logger], level: int, message: str) -> None:
    """Log `message` on `logger` at `level`'s logging level, if any logger."""
    if logger is not None:
        logger.log(severity(level).level, message)
