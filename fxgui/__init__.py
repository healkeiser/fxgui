"""FxGui - A modern Qt-based GUI framework for DCC applications.

Customized Qt widgets and utilities for consistent user interfaces in
Digital Content Creation (DCC) applications and standalone tools.

Modules:
    fxconfig: Configuration and settings management.
    fxcore: Core functionality and custom Qt classes.
    fxicons: Icon management and utilities.
    fxstyle: Styling, themes, and color management.
    fxutils: General utility functions.
    fxwidgets: Custom Qt widgets.
    fxconstants: Package constants and paths.

Examples:
    Basic usage with FXMainWindow:

    >>> from fxgui import fxwidgets
    >>> app = fxwidgets.FXApplication()
    >>> window = fxwidgets.FXMainWindow(title="My App")
    >>> window.show()
    >>> app.exec()
"""

# Third-party
import qtpy

if not qtpy.QT6:
    raise ImportError(
        f"fxgui needs Qt 6 (PySide6 6.5 or newer, or PyQt6); qtpy found "
        f"{qtpy.API_NAME}."
    )
if qtpy.PYSIDE6 and tuple(
    int(part) for part in qtpy.PYSIDE_VERSION.split(".")[:2]
) < (6, 5):
    raise ImportError(
        f"fxgui needs PySide6 6.5 or newer; found {qtpy.PYSIDE_VERSION}."
    )

# Internal
from fxgui import (
    fxconfig,
    fxconstants,
    fxcore,
    fxicons,
    fxstyle,
    fxutils,
    fxwidgets,
)

__all__ = [
    "fxconfig",
    "fxconstants",
    "fxcore",
    "fxicons",
    "fxstyle",
    "fxutils",
    "fxwidgets",
]


def __getattr__(name: str) -> str:
    """Read `__version__` on first ask: importlib.metadata costs 30 ms."""
    if name != "__version__":
        raise AttributeError(f"module 'fxgui' has no attribute {name!r}")
    from importlib.metadata import PackageNotFoundError, version

    try:
        found = version("fxgui")
    except PackageNotFoundError:
        # A source tree that was never installed.
        found = "0.0.0.dev"
    globals()["__version__"] = found
    return found

__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"
