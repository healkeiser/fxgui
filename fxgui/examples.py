"""Examples on how to use the `ui.qt` module."""

# Built-in
import os
import sys

# Third-party
from qtpy.QtWidgets import *
from qtpy.QtUiTools import *
from qtpy.QtCore import *
from qtpy.QtGui import *

# Internal
import widgets, utils


###### CODE ####################################################################


_ui_file = os.path.join(os.path.dirname(__file__), "ui", "test.ui")
_pixmap = os.path.join(os.path.dirname(__file__), "images", "splash.png")


def show_window_houdini():
    """An example VFXWindow instance."""

    # Create instance
    _window = widgets.VFXWindow()

    # Show
    _window.show()


def show_floating_dialog_houdini():
    """An example VFXFloatingDialog instance."""

    # Create instance
    _floating_dialog = widgets.VFXFloatingDialog()

    # Set icon
    icon = None
    pixmap = utils.convert_qicon_to_qpixmap(icon, QSize(10, 100))
    _floating_dialog.set_dialog_icon(pixmap)

    # Add button to the `button_box`
    _floating_dialog.button_box.addButton("Test", QDialogButtonBox.ActionRole)

    # Add combo box
    combo_box = QComboBox(_floating_dialog)
    combo_box.addItems(["Item 1", "Item 2", "Item 3"])
    _floating_dialog.main_layout.addWidget(combo_box)

    # Show under the cursor
    _floating_dialog.show_under_cursor()


def show_splashscreen(time: float = 5.0):
    """Show the splashscreen.

    Args:
        time (float): The time in seconds to show the splashscreen.
    """

    _application = widgets.VFXApplication()
    _splashscreen = widgets.VFXSplashScreen(image_path=_pixmap, show_progress_bar=True, fade_in=False)
    _splashscreen.show()
    _splashscreen.progress_bar.setValue(75)
    QTimer.singleShot(time * 1000, _splashscreen.close)
    QTimer.singleShot(time * 1000, _application.quit)
    _application.exec_()


def show_window():
    """Show the window."""

    _application = widgets.VFXApplication()
    _window = widgets.VFXWindow(ui_file=_ui_file)
    _window.show()
    sys.exit(_application.exec_())


def main(show_delayed: bool = False):
    """Main example function.

    Args:
        show_delayed (bool): Whether to show the window after 3 seconds or not.
    """

    # Initialize the QApplication
    _application = widgets.VFXApplication()

    # Initialize window for splashscreen
    _window = widgets.VFXWindow(ui_file=_ui_file)
    _application.processEvents()

    # Splashscreen
    _splashscreen = widgets.VFXSplashScreen(image_path=_pixmap, fade_in=False, show_progress_bar=True)
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

    _window.set_statusbar_message("Window initialized", widgets.INFO)
    _window.hide_toolbar()
    _application.processEvents()

    # Buttons in `test.ui` example
    _window.ui.button_success.clicked.connect(lambda: _window.set_statusbar_message("Success message", widgets.SUCCESS))
    _window.ui.button_info.clicked.connect(lambda: _window.set_statusbar_message("Info message", widgets.INFO))
    _window.ui.button_warning.clicked.connect(lambda: _window.set_statusbar_message("Success message", widgets.WARNING))
    _window.ui.button_error.clicked.connect(lambda: _window.set_statusbar_message("Error message", widgets.ERROR))
    _window.ui.button_critical.clicked.connect(
        lambda: _window.set_statusbar_message("Critical message", widgets.CRITICAL)
    )

    # Refresh toolbar button
    def refresh():
        # Store original icon
        original_icon = _window.refresh_action.icon()

        # Display statusbar message and change icon
        _window.set_statusbar_message("Refreshing...", widgets.INFO)
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


if __name__ == "__main__":
    main()
