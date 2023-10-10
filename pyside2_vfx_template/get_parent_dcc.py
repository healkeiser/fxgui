#!/usr/bin/env python
# -*- coding= utf-8 -*-

"""Utility functions for retrieving main windows of DCC applications."""

# Built-in
import shiboken2

# Third-party
from PySide2 import QtWidgets

import hou
import maya.OpenMayaUI as apiUI
import nuke

# Metadatas
__author__ = "John Russel"
__email__ = "johndavidrussell@gmail.com"


###### CODE ####################################################################


def get_houdini_main_window():
    """Get the Houdini main window.

    Returns:
        PySide2.QtWidgets.QWidget: 'QWidget' Houdini main window.
    """

    return hou.qt.mainWindow()


def get_maya_main_window():
    """Get the Maya main window.

    Returns:
        PySide2.QtWidgets.QWidget: 'TmainWindow' Maya main window.
    """

    ptr = apiUI.MQtUtil.mainWindow()
    if ptr is not None:
        return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)


def get_nuke_main_window():
    """Get the Nuke main window.

    Returns:
        PySide2.QtWidgets.QMainWindow: 'DockMainWindow' Nuke main window.
    """

    for w in QtWidgets.QApplication.topLevelWidgets():
        if (
            w.inherits("QMainWindow")
            and w.metaObject().className() == "Foundry::UI::DockMainWindow"
        ):
            return w
