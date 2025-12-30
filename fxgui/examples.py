"""Example implementations demonstrating `fxgui` module usage.

This module contains various example functions showcasing how to use
the fxgui framework for creating Qt-based applications, including:

- Basic window creation and subclassing
- Splash screens with progress bars
- Login dialogs with password input
- Custom delegates for tree/list/table widgets
- Collapsible widgets with animation
- Input validators (camelCase, lowercase, etc.)
- Output log widget with search functionality
- Singleton pattern for windows
- System tray integration
- DCC-specific implementations for Houdini

Functions:
    main: Main example function showing complete application setup.
    show_window: Simple window example with UI file.
    show_splash_screen: Display a customizable splash screen.
    show_login_dialog: Modal login dialog example.
    show_collapsible_widget: Expandable/collapsible content example.
    show_validators: Input validation examples.
    show_output_log: Log output widget example.
    show_singleton_window: Singleton window pattern example.
    show_elided_label: Text elision example.
    show_window_houdini: Example for Houdini integration.
    show_floating_dialog_houdini: Floating dialog in Houdini.

Usage:
    Run this module directly to see the full example:

    >>> python -m fxgui.examples

    Or import specific examples:

    >>> from fxgui.examples import show_window
    >>> show_window()
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
import logging
from pathlib import Path
from typing import Dict, Tuple

# Third-party
from qtpy.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
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
    QSpinBox,
)
from qtpy.QtCore import Qt, QTimer, QPoint
from qtpy.QtGui import QColor, QIcon

# Internal
from fxgui import fxwidgets, fxutils, fxdcc, fxstyle
from fxgui.fxicons import get_icon


# Constants
SPLASH_DELAY_MS = 3000
RESTORE_ICON_DELAY_MS = 1000

_ui_file = Path(__file__).parent / "ui" / "test.ui"
_pixmap = Path(__file__).parent / "images" / "splash.png"


###### Login Dialog Example


def show_login_dialog():
    """Show a login dialog with password input.

    Demonstrates:
        - FXPasswordLineEdit for secure password input
        - FXApplication for styling
        - Modal dialog creation
    """

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


###### Collapsible Widget Example


def show_collapsible_widget():
    """Show a collapsible widget with animated expand/collapse.

    Demonstrates:
        - FXCollapsibleWidget for expandable sections
        - Animation effects
        - Nested content layouts
    """

    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow(title="Collapsible Widget Example")
    window.toolbar.hide()

    # Create central widget with layout
    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)

    # First collapsible section - Settings
    settings_section = fxwidgets.FXCollapsibleWidget(
        title="Settings",
        animation_duration=200,
        max_content_height=200,
    )
    settings_layout = QFormLayout()
    settings_layout.addRow("Name:", QLineEdit())
    settings_layout.addRow("Value:", QSpinBox())
    settings_layout.addRow("Enabled:", QCheckBox())
    settings_section.setContentLayout(settings_layout)

    # Second collapsible section - Advanced
    advanced_section = fxwidgets.FXCollapsibleWidget(
        title="Advanced Options",
        animation_duration=300,
        max_content_height=150,
    )
    advanced_layout = QVBoxLayout()
    advanced_layout.addWidget(QLabel("Option 1: Enable debugging"))
    advanced_layout.addWidget(QCheckBox("Debug mode"))
    advanced_layout.addWidget(QLabel("Option 2: Verbose logging"))
    advanced_layout.addWidget(QCheckBox("Verbose"))
    advanced_section.setContentLayout(advanced_layout)

    # Third collapsible section - Info
    info_section = fxwidgets.FXCollapsibleWidget(
        title="Information",
        animation_duration=150,
    )
    info_layout = QVBoxLayout()
    info_layout.addWidget(
        QLabel("This is an example of the FXCollapsibleWidget.")
    )
    info_layout.addWidget(
        QLabel("Click the header to expand or collapse the content.")
    )
    info_section.setContentLayout(info_layout)

    main_layout.addWidget(settings_section)
    main_layout.addWidget(advanced_section)
    main_layout.addWidget(info_section)
    main_layout.addStretch()

    window.setCentralWidget(central_widget)
    window.resize(400, 500)
    window.show()
    application.exec_()


###### Validators Example


def show_validators():
    """Show input validators for different text formats.

    Demonstrates:
        - FXCamelCaseValidator for camelCase input
        - FXLowerCaseValidator for lowercase input
        - FXLettersUnderscoreValidator for identifiers
        - FXCapitalizedLetterValidator for names
    """

    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow(title="Input Validators Example")
    window.toolbar.hide()

    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)

    # Create form layout for validators
    form_layout = QFormLayout()

    # CamelCase validator
    camel_case_edit = QLineEdit()
    camel_case_edit.setValidator(fxwidgets.FXCamelCaseValidator())
    camel_case_edit.setPlaceholderText("e.g., myVariableName")
    form_layout.addRow("CamelCase:", camel_case_edit)

    # Lowercase validator
    lowercase_edit = QLineEdit()
    lowercase_edit.setValidator(fxwidgets.FXLowerCaseValidator())
    lowercase_edit.setPlaceholderText("e.g., lowercase")
    form_layout.addRow("Lowercase:", lowercase_edit)

    # Lowercase with numbers
    lowercase_num_edit = QLineEdit()
    lowercase_num_edit.setValidator(
        fxwidgets.FXLowerCaseValidator(allow_numbers=True)
    )
    lowercase_num_edit.setPlaceholderText("e.g., version2")
    form_layout.addRow("Lowercase + Numbers:", lowercase_num_edit)

    # Lowercase with underscores
    lowercase_underscore_edit = QLineEdit()
    lowercase_underscore_edit.setValidator(
        fxwidgets.FXLowerCaseValidator(allow_underscores=True)
    )
    lowercase_underscore_edit.setPlaceholderText("e.g., my_variable")
    form_layout.addRow("Lowercase + Underscores:", lowercase_underscore_edit)

    # Letters and underscores
    letters_underscore_edit = QLineEdit()
    letters_underscore_edit.setValidator(
        fxwidgets.FXLettersUnderscoreValidator()
    )
    letters_underscore_edit.setPlaceholderText("e.g., My_Variable")
    form_layout.addRow("Letters + Underscores:", letters_underscore_edit)

    # Letters, underscores, and numbers
    letters_underscore_num_edit = QLineEdit()
    letters_underscore_num_edit.setValidator(
        fxwidgets.FXLettersUnderscoreValidator(allow_numbers=True)
    )
    letters_underscore_num_edit.setPlaceholderText("e.g., My_Variable_2")
    form_layout.addRow(
        "Letters + Underscores + Numbers:", letters_underscore_num_edit
    )

    # Capitalized validator
    capitalized_edit = QLineEdit()
    capitalized_edit.setValidator(fxwidgets.FXCapitalizedLetterValidator())
    capitalized_edit.setPlaceholderText("e.g., MyName")
    form_layout.addRow("Capitalized:", capitalized_edit)

    main_layout.addLayout(form_layout)
    main_layout.addStretch()

    window.setCentralWidget(central_widget)
    window.resize(500, 400)
    window.show()
    application.exec_()


###### Output Log Widget Example


def show_output_log():
    """Show the output log widget with logging capture.

    Demonstrates:
        - FXOutputLogWidget for displaying logs
        - Log capture from Python's logging module
        - Search functionality with Ctrl+F
        - ANSI color code support
        - FXIconButton for theme-aware button icons
    """

    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow(title="Output Log Example")
    window.toolbar.hide()

    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)

    # Create log widget with capture enabled
    log_widget = fxwidgets.FXOutputLogWidget(capture_output=True)

    # Create some buttons to generate log messages
    # Using FXIconButton so icons refresh when theme changes
    button_layout = QHBoxLayout()

    debug_btn = fxwidgets.FXIconButton("Debug", icon_name="bug_report")
    debug_btn.clicked.connect(
        lambda: logging.getLogger("example").debug("This is a debug message")
    )

    info_btn = fxwidgets.FXIconButton("Info", icon_name="info")
    info_btn.clicked.connect(
        lambda: logging.getLogger("example").info("This is an info message")
    )

    warning_btn = fxwidgets.FXIconButton("Warning", icon_name="warning")
    warning_btn.clicked.connect(
        lambda: logging.getLogger("example").warning(
            "This is a warning message"
        )
    )

    error_btn = fxwidgets.FXIconButton("Error", icon_name="error")
    error_btn.clicked.connect(
        lambda: logging.getLogger("example").error("This is an error message")
    )

    button_layout.addWidget(debug_btn)
    button_layout.addWidget(info_btn)
    button_layout.addWidget(warning_btn)
    button_layout.addWidget(error_btn)

    # Setup the example logger
    logger = logging.getLogger("example")
    logger.setLevel(logging.DEBUG)

    # Add instructions
    instructions = QLabel(
        "Click buttons to generate log messages. Press Ctrl+F to search."
    )

    main_layout.addWidget(instructions)
    main_layout.addLayout(button_layout)
    main_layout.addWidget(log_widget)

    window.setCentralWidget(central_widget)
    window.resize(700, 500)
    window.show()
    application.exec_()


###### Singleton Window Example


def show_singleton_window():
    """Show a singleton window that can only have one instance.

    Demonstrates:
        - FXSingleton metaclass for single-instance windows
        - Automatic window focusing when trying to create a second instance
    """

    class MySingletonWindow(
        fxwidgets.FXMainWindow, metaclass=fxwidgets.FXSingleton
    ):
        """A window that can only have one instance."""

        def __init__(self, parent=None):
            super().__init__(parent, title="Singleton Window")
            self.toolbar.hide()

            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            layout.addWidget(
                QLabel(
                    "This window uses the FXSingleton metaclass.\n\n"
                    "Try creating another instance - it will return\n"
                    "this same window and bring it to focus."
                )
            )
            layout.addStretch()
            self.setCentralWidget(central_widget)

    application = fxwidgets.FXApplication()

    # Create first instance
    window1 = MySingletonWindow()
    window1.show()

    # Try to create second instance - should return the same window
    window2 = MySingletonWindow()

    # Verify they are the same
    assert window1 is window2, "Singleton pattern failed!"

    application.exec_()

    # Reset the singleton for future runs
    MySingletonWindow.reset_instance()


###### Elided Label Example


def show_elided_label():
    """Show the elided label that truncates text with ellipsis.

    Demonstrates:
        - FXElidedLabel for automatic text elision
        - Responsive text truncation on resize
    """

    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow(title="Elided Label Example")
    window.toolbar.hide()

    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)

    # Regular label for comparison
    main_layout.addWidget(QLabel("Regular QLabel:"))
    regular_label = QLabel(
        "This is a very long text that will overflow and not be truncated "
        "when the window is resized smaller."
    )
    main_layout.addWidget(regular_label)

    main_layout.addSpacing(20)

    # Elided label
    main_layout.addWidget(QLabel("FXElidedLabel:"))
    elided_label = fxwidgets.FXElidedLabel(
        "This is a very long text that will be automatically truncated "
        "with an ellipsis (...) when the window is resized smaller."
    )
    main_layout.addWidget(elided_label)

    main_layout.addSpacing(20)

    # Instructions
    main_layout.addWidget(
        QLabel("Resize the window to see the difference in behavior.")
    )
    main_layout.addStretch()

    window.setCentralWidget(central_widget)
    window.resize(400, 200)
    window.show()
    application.exec_()


# DCC Integration Examples


def show_window_houdini():
    """An example FXMainWindow instance launched from inside Houdini.

    Demonstrates:
        - DCC parent window detection
        - Proper window parenting for DCC integration
    """

    houdini_window = fxdcc.get_houdini_main_window()
    window = fxwidgets.FXMainWindow(
        parent=houdini_window, ui_file=str(_ui_file)
    )
    window.show()


def show_floating_dialog_houdini():
    """An example FXFloatingDialog launched from inside Houdini.

    Demonstrates:
        - FXFloatingDialog popup at cursor position
        - Adding custom widgets to the dialog
    """

    houdini_window = fxdcc.get_dcc_main_window()
    floating_dialog = fxwidgets.FXFloatingDialog(houdini_window)

    # Add button to the `button_box`
    floating_dialog.button_box.addButton("Test", QDialogButtonBox.ActionRole)

    # Add combo box
    combo_box = QComboBox(floating_dialog)
    combo_box.addItems(["Item 1", "Item 2", "Item 3"])
    floating_dialog.main_layout.addWidget(combo_box)

    # Show under the cursor
    floating_dialog.show_under_cursor()


###### Basic Window Example


def show_window():
    """Show a basic window with status bar messages.

    Demonstrates:
        - FXApplication and FXMainWindow basics
        - Status bar with different severity levels
        - Icon usage from fxicons
    """

    application = fxwidgets.FXApplication()
    window = fxwidgets.FXMainWindow(ui_file=str(_ui_file))

    # Set icons on the QDialogButtonBox buttons
    button_box = window.ui.buttonBox
    ok_button = button_box.button(QDialogButtonBox.Ok)
    cancel_button = button_box.button(QDialogButtonBox.Cancel)
    ok_button.setIcon(get_icon("check"))
    cancel_button.setIcon(get_icon("cancel"))

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


def subclass_window():
    """Show a subclassed FXMainWindow with custom widgets.

    Demonstrates:
        - Subclassing FXMainWindow
        - Creating custom central widgets
    """

    application = fxwidgets.FXApplication()

    class MyWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.main_layout = QVBoxLayout()
            self.setLayout(self.main_layout)

            # Add some example content
            self.main_layout.addWidget(QLabel("Custom Widget Content"))

            button = QPushButton("Click Me")
            button.setIcon(get_icon("touch_app"))
            self.main_layout.addWidget(button)

            self.main_layout.addStretch()

    class MyWindow(fxwidgets.FXMainWindow):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.toolbar.hide()
            self.setCentralWidget(MyWidget(parent=self))
            self.adjustSize()

    window = MyWindow()
    window.setWindowTitle("Subclassed Window")
    window.show()
    application.exec_()


###### Color Delegate Helper


def get_colors() -> Dict[str, Tuple[QColor, QColor, QColor, QIcon, bool]]:
    """Get the colors for the `FXColorLabelDelegate` class.

    Returns:
        A dictionary mapping item texts to `(background_color,
        border_color, text_icon_color, icon, color_icon)`.
    """

    # Background, border, text/icon, icon, color_icon
    colors = {
        "blender": (
            QColor("#5a2c13"),
            QColor("#a65123"),
            QColor("#ffffff"),
            get_icon("blender", library="dcc"),
            False,
        ),
        "maya": (
            QColor("#203e4c"),
            QColor("#407c98"),
            QColor("#ffffff"),
            get_icon("maya", library="dcc"),
            False,
        ),
        "exr": (
            QColor("#541431"),
            QColor("#891720"),
            QColor("#ffffff"),
            get_icon("open_exr", library="dcc"),
            False,
        ),
        "usd": (
            QColor("#203e4c"),
            QColor("#407c98"),
            QColor("#ffffff"),
            get_icon("usd", library="dcc"),
            False,
        ),
        "houdini": (
            QColor("#5a2c13"),
            QColor("#a65123"),
            QColor("#ffffff"),
            get_icon("houdini", library="dcc"),
            False,
        ),
        "nuke": (
            QColor("#181a1b"),
            QColor("#5c6367"),
            QColor("#ffffff"),
            get_icon("nuke", library="dcc"),
            False,
        ),
    }
    return colors


###### Splash Screen Functions


def show_splash_screen(
    opacity: float = 0.75,
    project: str = "fxgui",
    version: str = "0.1.0",
    company: str = "\u00a9 Valentin Beaumont",
) -> fxwidgets.FXSplashScreen:
    """Show the splash screen.

    Args:
        opacity: The overlay opacity (0.0 to 1.0). Defaults to 0.75.
        project: The project name. Defaults to "fxgui".
        version: The version string. Defaults to "0.1.0".
        company: The company name. Defaults to copyright Valentin Beaumont.

    Returns:
        The splash screen instance.
    """

    splashscreen = fxwidgets.FXSplashScreen(
        image_path=str(_pixmap),
        fade_in=False,
        show_progress_bar=True,
        project=project,
        version=version,
        company=company,
        border_width=2,
        border_color="#4a4949",
        corner_radius=15,
    )
    splashscreen.set_overlay_opacity(opacity)
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
        application.processEvents()


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


###### Main Window Configuration


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
        window.ui.button_debug: get_icon(
            "bug_report", color=colors["feedback"]["debug"]["light"]
        ),
        window.ui.button_success: get_icon(
            "check_circle", color=colors["feedback"]["success"]["light"]
        ),
        window.ui.button_info: style.standardIcon(
            QStyle.SP_MessageBoxInformation
        ),
        window.ui.button_warning: style.standardIcon(
            QStyle.SP_MessageBoxWarning
        ),
        window.ui.button_error: get_icon(
            "error", color=colors["feedback"]["error"]["light"]
        ),
        window.ui.button_critical: style.standardIcon(
            QStyle.SP_MessageBoxCritical
        ),
    }
    for button, icon in button_icons.items():
        button.setIcon(icon)

    # Set icons on QDialogButtonBox buttons
    button_box = window.ui.buttonBox
    ok_button = button_box.button(QDialogButtonBox.Ok)
    cancel_button = button_box.button(QDialogButtonBox.Cancel)
    if ok_button:
        ok_button.setIcon(get_icon("check"))
    if cancel_button:
        cancel_button.setIcon(get_icon("cancel"))


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

    # Retrieve all the items selected
    selected_items = tree.selectedItems()
    if not selected_items:
        return

    # Create the context menu
    menu = QMenu()

    # Title (use theme colors)
    theme_colors = fxstyle.get_theme_colors()
    title = f"Items ({len(selected_items)})"
    label = QLabel(title)
    label.setMargin(2)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        f"background-color: {theme_colors['background_alt']}; "
        f"color: {theme_colors['text']};"
    )
    label_action = QWidgetAction(menu)
    label_action.setDefaultWidget(label)
    menu.addAction(label_action)

    # Actions
    ac_show_in_explorer = menu.addAction("Show in Explorer")
    ac_show_in_explorer.setIcon(get_icon("folder_open"))

    copy_submenu = menu.addMenu("Copy Path to Clipboard")
    copy_submenu.setIcon(get_icon("content_copy"))

    ac_copy_default = copy_submenu.addAction("Default")
    ac_copy_default.setIcon(get_icon("content_copy"))

    ac_copy_houdini = copy_submenu.addAction("Houdini")
    ac_copy_houdini.setIcon(get_icon("houdini", library="dcc"))

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
        window.statusBar().showMessage("Refreshing...", fxwidgets.INFO)
        ok_icon = window.style().standardIcon(QStyle.SP_DialogOkButton)
        window.refresh_action.setIcon(ok_icon)

        # Restore original icon after delay
        QTimer.singleShot(
            RESTORE_ICON_DELAY_MS,
            lambda: window.refresh_action.setIcon(original_icon),
        )

    window.refresh_action.triggered.connect(refresh)


###### Main Function


def main(show_delayed: bool = True):
    """Main example function.

    Args:
        show_delayed: Whether to show the window after a delay.
    """

    # Initialize the application
    from qtpy.QtUiTools import QUiLoader

    _ = QUiLoader()  # PySide6 bug workaround
    application = fxwidgets.FXApplication()

    # Note: FXApplication already sets the style to Fusion with FXProxyStyle
    # Don't override it here or QSS borders won't work on Windows

    # Initialize main window
    window = fxwidgets.FXMainWindow(
        project="fxgui",
        version="0.1.0",
        company="\u00a9 Valentin Beaumont",
        ui_file=str(_ui_file),
    )
    window.set_banner_text("Example")

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
