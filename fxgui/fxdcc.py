"""Utility functions related to DCC packages."""

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

    import maya.OpenMayaUI

    window = apiUI.MQtUtil.mainWindow()  # type:ignore
    if window is not None:
        return shiboken2.wrapInstance(int(window), QtWidgets.QWidget)


def get_nuke_main_window() -> QtWidgets.QMainWindow:
    """Get the Nuke main window.

    Returns:
        qtpy.QtWidgets.QMainWindow: `DockMainWindow` Nuke main window.
    """

    import nuke

    for widget in QtWidgets.QApplication.topLevelWidgets():
        if (
            widget.inherits("QMainWindow")
            and widget.metaObject().className()
            == "Foundry::UI::DockMainWindow"
        ):
            return widget
