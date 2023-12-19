#!/usr/bin/env python
# -*- coding= utf-8 -*-

"""Utility functions for retrieving main windows of DCC applications.

Note:
    To avoid potential ModuleImportErrors, each DCC module (e.g., `hou`, `nuke`)
    is imported within its own function. This approach ensures that attempting
    to  use a function like `get_houdini_main_window` only triggers the import
    of `hou`, even if the main program lacks access to other modules like
    `nuke` or `OpenMayaUI`.
"""

# Built-in
import shiboken2

# Third-party
from PySide2 import QtWidgets

# Metadatas
__author__ = "John Russel"
__email__ = "johndavidrussell@gmail.com"


###### CODE ####################################################################


def get_houdini_main_window() -> QtWidgets.QWidget:
    """Get the Houdini main window.

    Returns:
        PySide2.QtWidgets.QWidget: 'QWidget' Houdini main window.
    """

    import hou  # type:ignore

    return hou.qt.mainWindow()


def get_maya_main_window() -> QtWidgets.QWidget:
    """Get the Maya main window.

    Returns:
        PySide2.QtWidgets.QWidget: 'TmainWindow' Maya main window.
    """

    import maya.OpenMayaUI as apiUI  # type:ignore

    window = apiUI.MQtUtil.mainWindow()
    if window is not None:
        return shiboken2.wrapInstance(long(window), QtWidgets.QWidget)


def get_nuke_main_window() -> QtWidgets.QMainWindow:
    """Get the Nuke main window.

    Returns:
        PySide2.QtWidgets.QMainWindow: 'DockMainWindow' Nuke main window.
    """

    import nuke  # type:ignore

    for widget in QtWidgets.QApplication.topLevelWidgets():
        if (
            widget.inherits("QMainWindow")
            and widget.metaObject().className() == "Foundry::UI::DockMainWindow"
        ):
            return widget
