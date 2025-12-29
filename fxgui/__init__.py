"""FxGui - A modern Qt-based GUI framework for DCC applications.

This package provides customized Qt widgets and utilities for building
consistent user interfaces across different Digital Content Creation (DCC)
applications like Houdini, Maya, and Nuke.

Modules:
    fxcore: Core functionality and custom Qt classes.
    fxdcc: DCC-specific utility functions.
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
    >>> app.exec_()
"""

# Built-in
from importlib.metadata import version, PackageNotFoundError

# Internal
from fxgui import (
    fxconstants,
    fxcore,
    fxdcc,
    fxicons,
    fxstyle,
    fxutils,
    fxwidgets,
)

__all__ = [
    "fxconstants",
    "fxcore",
    "fxdcc",
    "fxicons",
    "fxstyle",
    "fxutils",
    "fxwidgets",
]

try:
    __version__ = version("fxgui")
except PackageNotFoundError:
    # Package is not installed (running from source)
    __version__ = "0.0.0.dev"

__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"
