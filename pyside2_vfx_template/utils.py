#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Load UI files generated with Qt Designer."""

# Built-in
import os

# Third-party
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile
from PySide2.QtWidgets import QWidget

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


def load_ui(parent: QWidget, ui_file: str) -> QWidget:
    """Load a UI file and return the loaded UI as a QWidget.

    Args:
        parent (QWidget): Parent object.
        ui_file (str): Path to the UI file.

    Returns:
        QWidget: The loaded UI.

    Raises:
        FileNotFoundError: If the specified UI file doesn't exist.

    Examples:
        To load a UI file located in the same directory as the Python script
        >>> from pathlib import Path
        >>> ui_path = Path(__file__).with_suffix('.ui')
        >>> loaded_ui = load_ui(self, ui_path)
    """

    if os.path.isfile(ui_file):
        ui_file = QFile(ui_file)
        loaded_ui = QUiLoader().load(ui_file, parent)
        ui_file.close()
        return loaded_ui
    else:
        raise FileNotFoundError(f"UI file not found: {ui_file}")
