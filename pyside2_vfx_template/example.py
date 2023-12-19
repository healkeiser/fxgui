#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Run a VFXSPlashscreen and VFXWindow instance as an example."""

# Built-in
import os
import sys

# Third-party
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Internal
import splashscreen
import window

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


_ui_file = os.path.join(os.path.dirname(__file__), "ui", "test.ui")
_pixmap = os.path.join(os.path.dirname(__file__), "images", "splash.png")


def main():
    # Initialize the QApplication
    app = QApplication(sys.argv)

    # Initialize window for splashscreen
    win = window.VFXWindow(ui_file=_ui_file, light_theme=False)
    app.processEvents()

    # Splashscreen
    splash = splashscreen.VFXSplashScreen(image_path=_pixmap)
    app.processEvents()

    splash.show()
    app.processEvents()

    splash.finish(win)
    app.processEvents()

    # Window
    win.set_status_bar_message("Window initialized", severity_type=window.INFO)
    win.show()
    app.processEvents()

    # Buttons in `test.ui` example
    win.ui.button_error.clicked.connect(
        lambda: win.set_status_bar_message("Error", window.ERROR)
    )
    win.ui.button_success.clicked.connect(
        lambda: win.set_status_bar_message("Success", window.SUCCESS)
    )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
