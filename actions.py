#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Scripts related to the Qt QAction."""

from PySide2.QtGui import QIcon, QKeySequence
from PySide2.QtWidgets import QAction, QWidget

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


def create_action(
    parent: "QWidget",
    name: "str",
    icon: "str",
    trigger: "function",
    enable: "bool" = True,
    visible: "bool" = True,
    shortcut: "bool" = None,
) -> "None":
    """Creates a QACtion.

    Args:
        parent (QWidget): Parent object.
        name (str): Name to display.
        icon (str): Icon path.
        trigger (function): Function to trigger when clicked.
        enable (bool, optional): Enable/disable. Defaults to `True`.
        visible (bool, optional): Show/hide. Defaults to `True`.
        shortcut (str, optional): If not `None`, key sequence (hotkeys) to use.
            Defaults to `None`.
    """

    action = QAction(name, parent or None)
    action.setIcon(QIcon(icon))
    action.triggered.connect(trigger)
    action.setEnabled(enable)
    action.setVisible(visible)
    if shortcut is not None:
        action.setShortcut(QKeySequence(shortcut))

    return action
