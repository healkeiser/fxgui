"""Private shim: the severity levels now live in `_severity`."""

# TODO: delete once _main_window.py, _notification_banner.py, _status_bar.py
# and fxwidgets/__init__.py import the levels from _severity.
from fxgui.fxwidgets._severity import (  # noqa: F401
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    SUCCESS,
    WARNING,
)
