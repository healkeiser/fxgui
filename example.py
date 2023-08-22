#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""_summary_"""

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


__ui_file = os.path.join(os.path.dirname(__file__), "ui", "test.ui")
__pixmap = os.path.join(os.path.dirname(__file__), "images", "splash.png")


def main():
    app = QApplication(sys.argv)

    win = window.VFXWindow(ui_file=__ui_file, light_theme=False)
    app.processEvents()

    splash = splashscreen.VFXSplashScreen(image_path=__pixmap)
    app.processEvents()

    splash.show()
    app.processEvents()

    splash.finish(win)
    app.processEvents()

    win.show()
    app.processEvents()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
