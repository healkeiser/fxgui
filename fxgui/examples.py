"""Examples on how to use the `fxgui` module."""

# Built-in
import os

print(">>> ", os.getenv("QT_API"))

# Third-party
import qtawesome as qta
from qtpy.QtWidgets import *
from qtpy.QtUiTools import *
from qtpy.QtCore import *
from qtpy.QtGui import *

# Internal
from fxgui import fxwidgets, fxutils, fxdcc, fxstyle


_ui_file = os.path.join(os.path.dirname(__file__), "ui", "test.ui")
_pixmap = os.path.join(os.path.dirname(__file__), "images", "splash.png")


def show_window_houdini():
    """An example FXMainWindow instance launched from inside Houdini."""

    houdini_window = fxdcc.get_dcc_main_window()
    window = fxwidgets.FXMainWindow(parent=houdini_window, ui_file=_ui_file)
    window.show()


def show_floating_dialog_houdini():
    """An example FXFloatingDialog launched from inside Houdini."""

    import hou

    houdini_window = fxdcc.get_dcc_main_window()
    floating_dialog = fxwidgets.FXFloatingDialog(parent=houdini_window)

    # Set icon
    icon = hou.qt.Icon("MISC_python")
    pixmap = fxutils.convert_qicon_to_qpixmap(icon, QSize(10, 100))
    floating_dialog.set_dialog_icon(pixmap)

    # Add button to the `button_box`
    floating_dialog.button_box.addButton("Test", QDialogButtonBox.ActionRole)

    # Add combo box
    combo_box = QComboBox(floating_dialog)
    combo_box.addItems(["Item 1", "Item 2", "Item 3"])
    floating_dialog.main_layout.addWidget(combo_box)

    # Show under the cursor
    floating_dialog.show_under_cursor()


def show_splashscreen(time: float = 5.0):
    """Show the splashscreen.

    Args:
        time (float): The time in seconds to show the splashscreen.
    """
    _fix = QUiLoader()  # XXX: This is a PySide6 bug
    application = fxwidgets.FXApplication()
    splashscreen = fxwidgets.FXSplashScreen(
        image_path=_pixmap, show_progress_bar=True, fade_in=False
    )
    splashscreen.show()
    splashscreen.progress_bar.setValue(75)
    QTimer.singleShot(time * 1000, splashscreen.close)
    QTimer.singleShot(time * 1000, application.quit)
    application.exec_()


def show_window():
    """Show the window."""

    # Initialize the QApplication
    _fix = QUiLoader()  # XXX: This is a PySide6 bug
    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow(ui_file=_ui_file)

    # Buttons in `test.ui` example
    window.ui.button_success.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Success message", fxwidgets.SUCCESS
        )
    )
    window.ui.button_info.clicked.connect(
        lambda: window.statusBar().showMessage("Info message", fxwidgets.INFO),
    )
    window.ui.button_warning.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Warning message", fxwidgets.WARNING
        )
    )
    window.ui.button_error.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Error message", fxwidgets.ERROR
        ),
    )
    window.ui.button_critical.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Critical message", fxwidgets.CRITICAL
        )
    )

    window.show()
    application.exec_()


def show_window_alt():
    _fix = QUiLoader()  # XXX: This is a PySide6 bug
    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow()
    window.set_ui_file(_ui_file)
    button_sucess = window.ui.button_success

    # Spining icons
    animation = qta.Spin(button_sucess)
    spin_icon = qta.icon("fa5s.spinner", color="green", animation=animation)
    button_sucess.setIcon(spin_icon)

    window.show()
    application.exec_()


def main(show_delayed: bool = False):
    """Main example function.

    Args:
        show_delayed (bool): Whether to show the window after 3 seconds or not.
    """

    # Initialize the QApplication
    _fix = QUiLoader()  # XXX: This is a PySide6 bug
    application = fxwidgets.FXApplication()
    application.setStyle(fxstyle.FXProxyStyle())

    # Initialize window now for splashscreen
    window = fxwidgets.FXMainWindow(
        project="fxgui", version="0.1.0", ui_file=_ui_file
    )
    # window.set_status_line_colors(color_a="#fd6b72", color_b="#ffc577")
    application.processEvents()

    # Splashscreen
    splashscreen = fxwidgets.FXSplashScreen(
        image_path=_pixmap, fade_in=False, show_progress_bar=True
    )
    application.processEvents()

    splashscreen.show()
    application.processEvents()

    # Fake loading process
    for i in range(101):
        splashscreen.progress_bar.setValue(i)
        QTimer.singleShot(i, application.processEvents)

    if show_delayed:
        # Delay the call to splash.finish by 5 seconds
        QTimer.singleShot(3 * 1000, lambda: splashscreen.finish(window))
        application.processEvents()
    else:
        # Link the window loading to the splashcreen visibility
        splashscreen.finish(window)
        application.processEvents()

    # Window
    if show_delayed:
        # Delay the call to _window.show by 3 seconds
        QTimer.singleShot(3 * 1000 + 200, window.show)
    else:
        window.show()

    window.statusBar().showMessage("Window initialized", fxwidgets.INFO)
    window.toolbar.hide()

    application.processEvents()

    # Buttons in `test.ui` example
    window.ui.button_success.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Success message", fxwidgets.SUCCESS
        )
    )
    window.ui.button_info.clicked.connect(
        lambda: window.statusBar().showMessage("Info message", fxwidgets.INFO),
    )
    window.ui.button_warning.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Warning message", fxwidgets.WARNING
        )
    )
    window.ui.button_error.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Error message", fxwidgets.ERROR
        ),
    )
    window.ui.button_critical.clicked.connect(
        lambda: window.statusBar().showMessage(
            "Critical message", fxwidgets.CRITICAL
        )
    )

    style = window.style()
    window.ui.button_critical.setIcon(
        style.standardIcon(QStyle.SP_MediaVolumeMuted)
    )

    # Set tooltips on the buttons
    fxutils.set_formatted_tooltip(
        window.ui.button_success, "Success", "This is a success message."
    )

    # Refresh toolbar button
    def refresh():
        # Store original icon
        original_icon = window.refresh_action.icon()

        # Display statusbar message and change icon
        window.set_statusbar_message("Refreshing...", fxwidgets.INFO)
        ok_pixmap = QStyle.StandardPixmap.SP_DialogOkButton
        ok_icon = window.style().standardIcon(ok_pixmap)
        window.refresh_action.setIcon(ok_icon)

        # Restore original icon after 2 seconds
        def restore_icon():
            window.refresh_action.setIcon(original_icon)
            window.refresh_action.setEnabled(True)

        QTimer.singleShot(1 * 1000, restore_icon)

    window.refresh_action.triggered.connect(refresh)

    application.exec_()


if __name__ == "__main__":
    # main()
    # show_window()
    show_window_alt()
