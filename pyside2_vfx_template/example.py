#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a VFXSPlashscreen and VFXWindow instance as an example."""

# Built-in
import os
import sys
from importlib import reload

# Third-party
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Internal
try:
    from pyside2_vfx_template import splashscreen, window, application
except ModuleNotFoundError:
    import splashscreen, window, application

# Reload
reload(splashscreen)
reload(window)
reload(application)

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

###### CODE ####################################################################

_ui_file = os.path.join(os.path.dirname(__file__), "ui", "test.ui")
_pixmap = os.path.join(os.path.dirname(__file__), "images", "splash.png")


def main(show_delayed: bool = False):
    """Main example function.

    Args:
        show_delayed (bool): Whether to show the window after 3 seconds or not.
    """

    # Initialize the QApplication
    _application = application.VFXApplication()

    # Initialize window for splashscreen
    _window = window.VFXWindow(ui_file=_ui_file)
    _application.processEvents()

    # Splashscreen
    _splashscreen = splashscreen.VFXSplashScreen(image_path=_pixmap, fade_in=False, show_progress_bar=True)
    _application.processEvents()

    _splashscreen.show()
    _application.processEvents()

    # Loading process
    for i in range(101):
        _splashscreen.progress_bar.setValue(i)
        QTimer.singleShot(i, _application.processEvents)

    if show_delayed:
        # Delay the call to splash.finish by 5 seconds
        QTimer.singleShot(3 * 1000, lambda: _splashscreen.finish(_window))
        _application.processEvents()
    else:
        # Link the window loading to the splashcreen visibility
        _splashscreen.finish(_window)
        _application.processEvents()

    # Window
    if show_delayed:
        # Delay the call to _window.show by 3 seconds
        QTimer.singleShot(3 * 1000 + 200, _window.show)
    else:
        _window.show()

    _window.set_statusbar_message("Window initialized", window.INFO)
    _application.processEvents()

    # Buttons in `test.ui` example
    _window.ui.button_success.clicked.connect(lambda: _window.set_statusbar_message("Success", window.SUCCESS))
    _window.ui.button_info.clicked.connect(lambda: _window.set_statusbar_message("Info", window.INFO))
    _window.ui.button_warning.clicked.connect(lambda: _window.set_statusbar_message("Success", window.WARNING))
    _window.ui.button_error.clicked.connect(lambda: _window.set_statusbar_message("Error", window.ERROR))
    _window.ui.button_critical.clicked.connect(lambda: _window.set_statusbar_message("Success", window.CRITICAL))

    # Refresh toolbar button
    def refresh():
        # Store original icon
        original_icon = _window.refresh_action.icon()

        # Display statusbar message and change icon
        _window.set_statusbar_message("Refreshing...", window.INFO)
        ok_pixmap = QStyle.StandardPixmap.SP_DialogOkButton
        ok_icon = _window.style().standardIcon(ok_pixmap)
        _window.refresh_action.setIcon(ok_icon)

        # Restore original icon after 2 seconds
        def restore_icon():
            _window.refresh_action.setIcon(original_icon)
            _window.refresh_action.setEnabled(True)

        QTimer.singleShot(2000, restore_icon)

    _window.refresh_action.triggered.connect(refresh)

    sys.exit(_application.exec_())


def show_splashscreen(time: float = 3.0):
    """Show the splashscreen.

    Args:
        time (float): The time in seconds to show the splashscreen.
    """

    _application = application.VFXApplication()
    _splashscreen = splashscreen.VFXSplashScreen(image_path=_pixmap, fade_in=False)
    _splashscreen.show()
    QTimer.singleShot(time * 1000, _splashscreen.close)
    QTimer.singleShot(time * 1000, _application.quit)
    _application.exec_()


def show_window():
    """Show the window."""

    _application = application.VFXApplication()
    _window = window.VFXWindow(ui_file=_ui_file)
    _window.show()
    sys.exit(_application.exec_())


if __name__ == "__main__":
    # show_splashscreen()
    # show_window()
    main(False)
