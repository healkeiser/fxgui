"""Examples on how to use the `fxgui` module."""

# Built-in
from pathlib import Path
from typing import Dict, Tuple

# Third-party
import qtawesome as qta
from qtpy.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QComboBox,
    QWidget,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QHeaderView,
    QTableWidgetItem,
    QStyle,
    QWidgetAction,
)
from qtpy.QtUiTools import QUiLoader
from qtpy.QtCore import Qt, QTimer, QSize, QPoint
from qtpy.QtGui import QColor, QIcon

# Internal
from fxgui import fxwidgets, fxutils, fxdcc, fxstyle


# Constants
SPLASH_DELAY_MS = 3000
RESTORE_ICON_DELAY_MS = 1000

_ui_file = Path(__file__).parent / "ui" / "test.ui"
_pixmap = Path(__file__).parent / "images" / "splash.png"


def show_login_dialog():
    class FXLoginDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.setModal(True)
            self.setWindowTitle("Login")
            self.resize(500, 100)
            main_layout = QVBoxLayout()
            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignRight)

            # Login
            self.login_line_edit = QLineEdit()
            self.login_line_edit.setPlaceholderText("Mail...")
            form_layout.addRow("Login", self.login_line_edit)

            # Password
            self.password_line_edit = fxwidgets.FXPasswordLineEdit()
            self.password_line_edit.line_edit.setPlaceholderText("Password...")
            form_layout.addRow("Password", self.password_line_edit)

            # Remember Me
            self.remember_me_checkbox = QCheckBox("Remember Me")
            form_layout.addRow("", self.remember_me_checkbox)

            # Add form layout to main layout
            main_layout.addLayout(form_layout)

            # Buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.Cancel | QDialogButtonBox.Ok
            )
            button_box.button(QDialogButtonBox.Cancel).setText("Cancel")
            button_box.button(QDialogButtonBox.Ok).setText("Login")

            # Close on cancel
            button_box.rejected.connect(self.reject)

            main_layout.addWidget(button_box)
            self.setLayout(main_layout)

    application = fxwidgets.FXApplication()
    dialog = FXLoginDialog()
    dialog.exec_()


def show_window_houdini():
    """An example FXMainWindow instance launched from inside Houdini."""

    houdini_window = fxdcc.get_houdini_main_window()
    window = fxwidgets.FXMainWindow(
        parent=houdini_window, ui_file=str(_ui_file)
    )
    window.show()


def show_floating_dialog_houdini():
    """An example FXFloatingDialog launched from inside Houdini."""

    houdini_window = fxdcc.get_dcc_main_window()
    floating_dialog = fxwidgets.FXFloatingDialog(houdini_window)

    # Set icon
    # icon = hou.qt.Icon("MISC_python")
    pixmap = fxutils.convert_qicon_to_qpixmap(None, QSize(10, 100))
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

    application = fxwidgets.FXApplication()
    splashscreen = fxwidgets.FXSplashScreen(
        image_path=str(_pixmap), show_progress_bar=True, fade_in=False
    )
    splashscreen.show()
    splashscreen.progress_bar.setValue(75)
    QTimer.singleShot(time * 1000, splashscreen.close)
    QTimer.singleShot(time * 1000, application.quit)
    application.exec_()


def show_window():
    """Show the window."""

    # Initialize the QApplication
    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow(ui_file=str(_ui_file))

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

    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow()
    window.set_ui_file(str(_ui_file))
    button_sucess = window.ui.button_success

    # Spining icons
    animation = qta.Spin(button_sucess)
    spin_icon = qta.icon("fa5s.spinner", color="green", animation=animation)
    button_sucess.setIcon(spin_icon)

    window.show()
    application.exec_()


def subclass_window():

    application = fxwidgets.FXApplication()

    class MyWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.add_layout()
            self.add_buttons()

        def add_layout(self):
            """Adds a vertical layout to the main layout of the widget."""

            self.main_layout = QVBoxLayout()
            self.setLayout(self.main_layout)

        def add_buttons(self):
            """Adds buttons to the main layout of the widget."""

            pulse_button = QPushButton("Pulse Button")
            pulse_animation = qta.Pulse(pulse_button)
            pulse_icon = qta.icon(
                "fa.spinner", color="#b4b4b4", animation=pulse_animation
            )
            pulse_button.setIcon(pulse_icon)

            spin_button = QPushButton("Spin Button")
            spin_animation = qta.Spin(spin_button)
            spin_icon = qta.icon(
                "fa5s.spinner", color="#b4b4b4", animation=spin_animation
            )
            spin_button.setIcon(spin_icon)

            self.main_layout.addWidget(pulse_button)
            self.main_layout.addWidget(spin_button)
            self.main_layout.addStretch()

    class MyWindow(fxwidgets.FXMainWindow):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.toolbar.hide()
            self.setCentralWidget(MyWidget(parent=self))
            self.adjustSize()

    window = MyWindow()
    window.setWindowTitle("My Window")
    window.show()
    application.exec_()


# ' Main
def get_colors() -> Dict[str, Tuple[QColor, QColor, QColor, QIcon, bool]]:
    """Get the colors for the `FXColorLabelDelegate` class.

    Returns:
        A dictionary mapping item texts to `(background_color,
        border_color, text_icon_color, icon, color_icon)`.
    """

    icon_path = Path(__file__).parent / "icons" / "dcc"

    # Background, border, text/icon, icon
    colors = {
        "blender": (
            QColor("#5a2c13"),
            QColor("#a65123"),
            QColor("#b4b4b4"),
            QIcon(str(icon_path / "blender.svg")),
            False,
        ),
        "maya": (
            QColor("#203e4c"),
            QColor("#407c98"),
            QColor("#b4b4b4"),
            QIcon(str(icon_path / "maya.svg")),
            False,
        ),
        "exr": (
            QColor("#541431"),
            QColor("#891720"),
            QColor("#b4b4b4"),
            QIcon(str(icon_path / "open_exr.svg")),
            False,
        ),
        "usd": (
            QColor("#203e4c"),
            QColor("#407c98"),
            QColor("#b4b4b4"),
            QIcon(str(icon_path / "usd.svg")),
            False,
        ),
        "houdini": (
            QColor("#5a2c13"),
            QColor("#a65123"),
            QColor("#b4b4b4"),
            QIcon(str(icon_path / "houdini.svg")),
            False,
        ),
        "nuke": (
            QColor("#181a1b"),
            QColor("#5c6367"),
            QColor("#b4b4b4"),
            QIcon(str(icon_path / "nuke.svg")),
            False,
        ),
    }
    return colors


def show_splash_screen() -> fxwidgets.FXSplashScreen:
    """Show the splash screen.

    Returns:
        The splash screen instance.
    """

    splashscreen = fxwidgets.FXSplashScreen(
        image_path=str(_pixmap), fade_in=False, show_progress_bar=True
    )
    splashscreen.show()
    return splashscreen


def simulate_loading(
    splashscreen: fxwidgets.FXSplashScreen,
    application: fxwidgets.FXApplication,
) -> None:
    """Simulate a loading process on the splash screen.

    Args:
        splashscreen: The splash screen instance.
        application: The application instance.
    """

    for i in range(101):
        splashscreen.progress_bar.setValue(i)
        QTimer.singleShot(i, application.processEvents)


def finish_splash_screen(
    splashscreen: fxwidgets.FXSplashScreen,
    window: fxwidgets.FXMainWindow,
    show_delayed: bool,
) -> None:
    """Finish the splash screen and show the main window.

    Args:
        splashscreen: The splash screen instance.
        window: The main window instance.
        show_delayed: Whether to show the window after a delay.
    """

    if show_delayed:
        QTimer.singleShot(SPLASH_DELAY_MS, lambda: splashscreen.finish(window))
        QTimer.singleShot(SPLASH_DELAY_MS + 200, window.show)
    else:
        splashscreen.finish(window)
        window.show()


def configure_window(window: fxwidgets.FXMainWindow):
    """Configure the main window.

    Args:
        window: The main window instance.
    """

    window.statusBar().showMessage("Window initialized", fxwidgets.INFO)
    window.toolbar.hide()

    setup_status_buttons(window)
    set_button_icons(window)
    set_tooltips(window)
    setup_tree_widget(window)
    setup_list_widget(window)
    setup_table_widget(window)
    setup_refresh_action(window)


def setup_status_buttons(window: fxwidgets.FXMainWindow):
    """Connect status buttons to display messages.

    Args:
       window: The main window instance.
    """

    status_buttons = {
        window.ui.button_debug: ("Debug message", fxwidgets.DEBUG),
        window.ui.button_success: ("Success message", fxwidgets.SUCCESS),
        window.ui.button_info: ("Info message", fxwidgets.INFO),
        window.ui.button_warning: ("Warning message", fxwidgets.WARNING),
        window.ui.button_error: ("Error message", fxwidgets.ERROR),
        window.ui.button_critical: ("Critical message", fxwidgets.CRITICAL),
    }
    for button, (message, level) in status_buttons.items():
        button.clicked.connect(
            lambda msg=message, lvl=level: window.statusBar().showMessage(
                msg, lvl
            )
        )


def set_button_icons(window: fxwidgets.FXMainWindow) -> None:
    """Set icons for the status buttons.

    Args:
        window: The main window instance.
    """

    style = window.style()
    colors = fxstyle.load_colors_from_jsonc()
    button_icons = {
        window.ui.button_debug: qta.icon(
            "mdi.bug", color=colors["feedback"]["debug"]["light"]
        ),
        window.ui.button_success: qta.icon(
            "mdi.check-circle", color=colors["feedback"]["success"]["light"]
        ),
        window.ui.button_info: style.standardIcon(
            QStyle.SP_MessageBoxInformation
        ),
        window.ui.button_warning: style.standardIcon(
            QStyle.SP_MessageBoxWarning
        ),
        window.ui.button_error: qta.icon(
            "mdi.alert", color=colors["feedback"]["error"]["light"]
        ),
        window.ui.button_critical: style.standardIcon(
            QStyle.SP_MessageBoxCritical
        ),
    }
    for button, icon in button_icons.items():
        button.setIcon(icon)


def set_tooltips(window: fxwidgets.FXMainWindow) -> None:
    """Set tooltips for the buttons.

    Args:
        window: The main window instance.
    """

    fxutils.set_formatted_tooltip(
        window.ui.button_success, "Success", "This is a success message."
    )


def show_context_menu(tree: QTreeWidget, position: QPoint) -> None:
    """Show the context menu when right-clicking on an item.

    Args:
        tree: The tree widget to show the context menu in.
        position: The position of the right-click.
    """

    # Retrieve the item at the clicked position
    # item = tree.itemAt(position)
    # if not item:
    #     return

    # Retrieve all the items selected
    selected_items = tree.selectedItems()
    if not selected_items:
        return

    # Create the context menu
    menu = QMenu()

    # Title
    title = f"Items ({len(selected_items)})"
    label = QLabel(title)
    label.setMargin(2)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet("background-color: #2b2b2b; color: white;")
    label_action = QWidgetAction(menu)
    label_action.setDefaultWidget(label)
    menu.addAction(label_action)

    # Actions
    ac_show_in_explorer = menu.addAction("Show in Explorer")
    ac_show_in_explorer.setIcon(qta.icon("mdi.folder-open"))

    copy_submenu = menu.addMenu("Copy Path to Clipboard")
    copy_submenu.setIcon(qta.icon("mdi.content-copy"))

    ac_copy_default = copy_submenu.addAction("Default")
    ac_copy_default.setIcon(qta.icon("mdi.content-copy"))

    ac_copy_houdini = copy_submenu.addAction("Houdini")
    ac_copy_houdini.setIcon(
        QIcon(str(Path(__file__).parent / "icons" / "dcc" / "houdini.svg"))
    )

    # Show the context menu
    menu.exec_(tree.viewport().mapToGlobal(position))


def setup_tree_widget(window: fxwidgets.FXMainWindow) -> None:
    """Setup the tree widget with a custom delegate and a context menu.

    Args:
        window: The main window instance.
    """

    # Delegate
    color_delegate = fxwidgets.FXColorLabelDelegate(
        get_colors(), window.ui.treeWidget
    )
    window.ui.treeWidget.setItemDelegateForColumn(0, color_delegate)

    # Skip delegate drawing for items with "new"
    def set_skip_delegate_role_new(item: QTreeWidgetItem):
        if "new" in item.text(0).lower():
            item.setData(
                0, fxwidgets.FXColorLabelDelegate.SKIP_DELEGATE_ROLE, True
            )
        for i in range(item.childCount()):
            set_skip_delegate_role_new(item.child(i))

    # Skip delegate drawing for all child items
    def set_skip_delegate_role_child(item: QTreeWidgetItem):
        if item.parent() is not None:
            item.setData(
                0, fxwidgets.FXColorLabelDelegate.SKIP_DELEGATE_ROLE, True
            )
        for i in range(item.childCount()):
            set_skip_delegate_role_child(item.child(i))

    root = window.ui.treeWidget.invisibleRootItem()
    for i in range(root.childCount()):
        set_skip_delegate_role_child(root.child(i))

    # Context menu
    window.ui.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
    window.ui.treeWidget.customContextMenuRequested.connect(
        lambda pos: show_context_menu(window.ui.treeWidget, pos)
    )

    # Add child items with numbers
    items = [
        "something1",
        "something9",
        "something17",
        "something25",
        "something025",
    ]
    for item in items:
        child = fxwidgets.FXSortedTreeWidgetItem([item])
        root.addChild(child)


def setup_list_widget(window: fxwidgets.FXMainWindow) -> None:
    """Setup the list widget with a custom delegate.

    Args:
        window: The main window instance.
    """

    color_delegate = fxwidgets.FXColorLabelDelegate(
        get_colors(), window.ui.listWidget
    )
    window.ui.listWidget.setItemDelegate(color_delegate)


def setup_table_widget(window: fxwidgets.FXMainWindow) -> None:
    """Setup the table widget with a custom delegate.

    Args:
        window: The main window instance.
    """

    # Add columns
    window.ui.tableWidget.setColumnCount(2)
    window.ui.tableWidget.setHorizontalHeaderLabels(["Key", "Value"])

    # Make columns stretch to fill available space
    header = window.ui.tableWidget.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Stretch)

    # Add items
    items = [
        ("Blender", "2.93"),
        ("Maya", "2022"),
        ("Houdini", "19.0"),
        ("Nuke", "13.0"),
    ]
    for i, (key, value) in enumerate(items):
        window.ui.tableWidget.insertRow(i)
        window.ui.tableWidget.setItem(i, 0, QTableWidgetItem(key))
        window.ui.tableWidget.setItem(i, 1, QTableWidgetItem(value))

    # Skip the delegate for the second column
    for i in range(window.ui.tableWidget.rowCount()):
        item = window.ui.tableWidget.item(i, 1)
        item.setData(fxwidgets.FXColorLabelDelegate.SKIP_DELEGATE_ROLE, True)

    color_delegate = fxwidgets.FXColorLabelDelegate(
        get_colors(), window.ui.tableWidget, 4, 0, 0
    )
    window.ui.tableWidget.setItemDelegate(color_delegate)


def setup_refresh_action(window: fxwidgets.FXMainWindow) -> None:
    """Setup the refresh action in the toolbar."""

    def refresh():
        original_icon = window.refresh_action.icon()
        window.set_statusbar_message("Refreshing...", fxwidgets.INFO)
        ok_icon = window.style().standardIcon(QStyle.SP_DialogOkButton)
        window.refresh_action.setIcon(ok_icon)

        # Restore original icon after delay
        QTimer.singleShot(
            RESTORE_ICON_DELAY_MS,
            lambda: window.refresh_action.setIcon(original_icon),
        )

    window.refresh_action.triggered.connect(refresh)


def main(show_delayed: bool = False):
    """Main example function.

    Args:
        show_delayed: Whether to show the window after a delay.
    """

    # Initialize the application
    _ = QUiLoader()  # PySide6 bug workaround
    application = fxwidgets.FXApplication()
    application.setStyle(fxstyle.FXProxyStyle())

    # Initialize main window
    window = fxwidgets.FXMainWindow(
        project="fxgui", version="0.1.0", ui_file=str(_ui_file)
    )

    # Show splash screen
    splashscreen = show_splash_screen()

    # Simulate loading process
    simulate_loading(splashscreen, application)

    # Finish splash screen and show window
    finish_splash_screen(splashscreen, window, show_delayed)

    # Configure window
    configure_window(window)

    # Start application event loop
    application.exec_()


if __name__ == "__main__":
    main()
