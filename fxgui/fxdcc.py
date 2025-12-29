"""DCC (Digital Content Creation) utility functions for `fxgui`.

This module provides utility functions for integrating fxgui with various
DCC applications including Houdini, Maya, and Nuke. It handles the
detection of the current DCC environment and provides access to their
main windows and stylesheets.

Constants:
    STANDALONE: Constant indicating standalone Python mode.
    HOUDINI: Constant indicating Houdini environment.
    MAYA: Constant indicating Maya environment.
    NUKE: Constant indicating Nuke environment.

Functions:
    get_dcc_main_window: Auto-detect and return the current DCC main window.
    get_houdini_main_window: Get the Houdini main window.
    get_houdini_stylesheet: Get the Houdini stylesheet.
    get_maya_main_window: Get the Maya main window.
    get_nuke_main_window: Get the Nuke main window.

Examples:
    Getting the DCC main window automatically:

    >>> from fxgui import fxdcc
    >>> main_window = fxdcc.get_dcc_main_window()
    >>> if main_window is not None:
    ...     my_dialog = MyDialog(parent=main_window)
    ...     my_dialog.show()

    Explicitly getting a specific DCC window:

    >>> houdini_window = fxdcc.get_houdini_main_window()
    >>> maya_window = fxdcc.get_maya_main_window()
"""

# Built-in
import importlib
from typing import Optional, Any

# Third-party
from qtpy import QtWidgets

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


# Constants
STANDALONE = 0
HOUDINI = 1
MAYA = 2
NUKE = 3


def get_dcc_main_window() -> Optional[Any]:
    """Import the current DCC main window.

    Returns:
        Optional[Any]: The return value of the first successful function call,
            or `None` if no calls are successful.

    Notes:
        This function is DCC agnostic and will return the main window based on
            the success of the DCC module import.
    """

    dccs = [
        ("maya.OpenMayaUI", get_maya_main_window),
        ("nuke", get_nuke_main_window),
        ("hou", get_houdini_main_window),
    ]

    for module_name, function in dccs:
        try:
            importlib.import_module(module_name)
            return function()
        except ImportError:
            continue

    return None


def get_houdini_main_window() -> QtWidgets.QWidget:
    """Get the Houdini main window.

    Returns:
        qtpy.QtWidgets.QWidget: `QWidget` Houdini main window.
    """

    import hou

    return hou.qt.mainWindow()  # type:ignore


def get_houdini_stylesheet() -> str:
    """Get the Houdini stylesheet.

    Returns:
        str: The Houdini stylesheet.
    """

    import hou

    return hou.qt.styleSheet()  # type:ignore


def get_maya_main_window() -> QtWidgets.QWidget:
    """Get the Maya main window.

    Returns:
        qtpy.QtWidgets.QWidget: `TmainWindow` Maya main window.
    """

    import maya.OpenMayaUI as omui

    try:
        from shiboken6 import wrapInstance
    except ImportError:
        from shiboken2 import wrapInstance

    window = omui.MQtUtil.mainWindow()
    if window is not None:
        return wrapInstance(int(window), QtWidgets.QWidget)
    return None


def get_nuke_main_window() -> QtWidgets.QMainWindow:
    """Get the Nuke main window.

    Returns:
        qtpy.QtWidgets.QMainWindow: `DockMainWindow` Nuke main window.
    """

    import nuke

    for widget in QtWidgets.QApplication.topLevelWidgets():
        if (
            widget.inherits("QMainWindow")
            and widget.metaObject().className() == "Foundry::UI::DockMainWindow"
        ):
            return widget
