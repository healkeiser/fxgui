"""This module defines the `VFXWindow` class which provides a custom window
tailored for VFX-oriented DCC applications.

The `VFXWindow` class uses PySide2 for the UI and includes various utilities
and actions for a VFX workflow.

This module also defines several constants for different types of notifications.

Classes:
    VFXWindow: A class for creating a customized window.
"""

# pylint:disable=wildcard-import

# Built-in
import os
import logging
from typing import Optional
from datetime import datetime
from webbrowser import open_new_tab
from urllib.parse import urlparse

# Third-party
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Internal
try:
    from pyside2_vfx_template import style, shadows, actions, utils, icons
except ModuleNotFoundError:
    import style, shadows, actions, utils, icons

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


# Constants
CRITICAL = 0
ERROR = 1
WARNING = 2
SUCCESS = 3
INFO = 4

# TODO: Add the status bar color notification system (Fix)
# TODO: Replace the colors by reading the JSONC file in the status bar stylesheet


class VFXWindow(QMainWindow):
    """Customized QMainWindow class.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `None`.
        icon (str, optional): Path to the window icon image. Defaults to `None`.
        title (str, optional): Title of the window. Defaults to `None`.
        size (Tuple[int, int], optional): Window size as width and height.
            Defaults to `None`.
        flags (Qt.WindowFlags, optional): Window flags. Defaults to `None`.
        documentation (str, optional): URL to the tool's documentation.
            Defaults to `None`.
        version (str, optional): Version label for the window.
            Defaults to `None`.
        company (str, optional): Company name for the window.
            Defaults to `None`.
        theme (str, optional): Theme to be applied to the splash screen.
            Defaults to `dark`.
        accent_color (str, optional): Accent color to be applied to the splash
            screen. Defaults to `#039492`.
        ui_file (str, optional): Path to the UI file for loading.
            Defaults to `None`.

    Attributes:
        window_icon (QIcon): The icon of the window.
        window_title (str): The title of the window.
        window_size (QSize): The size of the window.
        window_flags (Qt.WindowFlags): The window flags.
        documentation (str): The documentation string.
        project (str): The project name.
        version (str): The version string.
        company (str): The company name.
        theme (str): The theme name.
        accent_color (str): The accent color.
        ui_file (str): The UI file path.

        CRITICAL (int): Constant for critical log level.
        ERROR (int): Constant for error log level.
        WARNING (int): Constant for warning log level.
        SUCCESS (int): Constant for success log level.
        INFO (int): Constant for info log level.

        about_action (QAction): Action for the "About" menu item.
        hide_action (QAction): Action for the "Hide" menu item.
        hide_others_action (QAction): Action for the "Hide Others" menu item.
        close_action (QAction): Action for the "Close" menu item.
        check_updates_action (QAction): Action for the "Check for Updates..."
            menu item.
        settings_action (QAction): Action for the "Settings" menu item.
        switch_theme_action (QAction): Action for the "Switch Theme" menu item.
        window_on_top_action (QAction): Action for the "Always On Top" menu
            item.
        minimize_window_action (QAction): Action for the "Minimize" menu item.
        maximize_window_action (QAction): Action for the "Maximize" menu item.
        open_documentation_action (QAction): Action for the "Documentation"
            menu item.
        previous_action (QAction): Action for the "Previous" toolbar item.
        next_action (QAction): Action for the "Next" toolbar item.
        refresh_action (QAction): Action for the "Refresh" toolbar item.
        home_action (QAction): Action for the "Home" toolbar item.

        menu_bar (QMenuBar): The menu bar of the window.
        icon_menu (QMenu): The icon menu of the menu bar.
        main_menu (QMenu): The main menu of the menu bar.
        about_menu (QAction): The "About" menu item in the main menu.
        check_updates_menu (QAction): The "Check for Updates..." menu item in
            the main menu.
        close_menu (QAction): The "Close" menu item in the main menu.
        hide_main_menu (QAction): The "Hide" menu item in the main menu.
        hide_others_menu (QAction): The "Hide Others" menu item in the main
            menu.
        edit_menu (QMenu): The edit menu of the menu bar.
        settings_menu (QAction): The "Settings" menu item in the edit menu.
        window_menu (QMenu): The window menu of the menu bar.
        switch_theme_menu (QAction): The "Switch Theme" menu item in the window
            menu.
        minimize_menu (QAction): The "Minimize" menu item in the window menu.
        maximize_menu (QAction): The "Maximize" menu item in the window menu.
        on_top_menu (QAction): The "Always On Top" menu item in the window menu.
        help_menu (QMenu): The help menu of the menu bar.
        open_documentation_menu (QAction): The "Documentation" menu item in the
            help menu.

        toolbar (QToolBar): The toolbar of the window.
        previous_toolbar (QAction): The "Previous" toolbar item.
        next_toolbar (QAction): The "Next" toolbar item.
        refresh_toolbar (QAction): The "Refresh" toolbar item.
        home_toolbar (QAction): The "Home" toolbar item.
        about_dialog (QDialog): The "About" dialog.

        status_bar (QStatusBar): The status bar of the window.
        project_label (QLabel): The project label in the status bar.
        version_label (QLabel): The version label in the status bar.
        company_label (QLabel): The company label in the status bar.

    Examples:
        Outside a DCC
        >>> app = QApplication(sys.argv)
        >>> _window = VFXWindow(
        ...     icon="path/to/icon.png",
        ...     title="My Custom Window",
        ...     size=(800, 600),
        ...     documentation="https://my_tool_docs.com",
        ...     project="Awesome Project",
        ...     version="v1.0.0",
        ...     ui_file="path/to/ui_file.ui",
        ...     theme="dark",
        ... )
        >>> _window.show()
        >>> _window.set_statusbar_message("Window initialized", window.INFO)
        >>> sys.exit(app.exec_())

        Inside a DCC (Houdini)
        >>> houdini_window = dcc.get_houdini_main_window()
        >>> houdini_style = dcc.get_houdini_stylesheet()
        >>> _window = window.VFXWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...    theme="dark",
        ...   )
        >>> _window.show()
        >>> _window.set_statusbar_message("Window initialized", window.INFO)

        Hide toolbar and menu bar
        >>> houdini_window = dcc.get_houdini_main_window()
        >>> houdini_style = dcc.get_houdini_stylesheet()
        >>> _window = window.VFXWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...    theme="dark",
        ...   )
        >>> _window.show()
        >>> _window.hide_toolbar()
        >>> _window.hide_menu_bar()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        size: Optional[int] = None,
        flags: Optional[Qt.WindowFlags] = None,
        documentation: Optional[str] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        theme: str = "dark",
        accent_color: str = "#039492",
        ui_file: Optional[str] = None,
    ):
        """Constructor.

        Args:
            parent (QtWidget, optional): Parent widget. Defaults to `None`.
        """

        super().__init__(parent)

        # Attributes
        self._default_icon = os.path.join(os.path.dirname(__file__), "icons", "favicon.png")
        self.window_icon: QIcon = icon
        self.window_title: str = title
        self.window_size: QSize = size
        self.window_flags: Qt.WindowFlags = flags
        self.documentation: str = documentation
        self.project: str = project
        self.version: str = version
        self.company: str = company
        self.theme: str = theme
        self.accent_color: str = accent_color
        self.ui_file: str = ui_file

        self.CRITICAL: int = CRITICAL
        self.ERROR: int = ERROR
        self.WARNING: int = WARNING
        self.SUCCESS: int = SUCCESS
        self.INFO: int = INFO

        self._status_icon_connected = False

        # Methods
        self._create_actions()
        self._load_ui()
        self._set_window_icon()
        self._set_window_title()
        self._set_window_size()
        self._set_window_flags()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._check_documentation()
        # self._add_shadows()

    # - Private methods

    def _load_ui(self) -> None:
        """Loads the UI from the specified UI file and sets it as the central
        widget of the main window.

        Warning:
            This method is intended for internal use only.
        """

        if self.ui_file is not None:
            self.ui = utils.load_ui(self, self.ui_file)

            # Add the loaded UI to the main window
            self.setCentralWidget(self.ui)

    def _set_window_icon(self) -> None:
        """Sets the window icon from the specified icon path.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_icon is not None and os.path.isfile(self.window_icon):
            self.setWindowIcon(QIcon(self.window_icon))
        else:
            self.setWindowIcon(QIcon(self._default_icon))

    def _set_window_title(self) -> None:
        """Sets the window title from the specified title.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_title is not None and len(self.window_title) >= 1:
            self.setWindowTitle(f"VFX | {self.window_title} *")
        else:
            self.setWindowTitle(f"VFX | Window *")

    def _set_window_size(self) -> None:
        """Sets the window size from the specified size.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_size is not None and len(self.window_size) >= 1:
            self.resize(QSize(*self.window_size))
        else:
            self.resize(QSize(500, 600))

    def _set_window_flags(self) -> None:
        """Sets the window flags from the specified flags.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_flags is not None:
            self.setWindowFlags(self.windowFlags() | self.window_flags)

    def _create_actions(self) -> None:
        """Creates the actions for the window.

        Warning:
            This method is intended for internal use only.
        """

        # Main menu
        self.about_action = actions.create_action(
            self,
            "About",
            icons.get_icon("support"),
            self._show_about_dialog,
            enable=True,
            visible=True,
        )

        self.hide_action = actions.create_action(
            self,
            "Hide",
            icons.get_icon("hide_source"),
            self.hide,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+h",
        )

        self.hide_others_action = actions.create_action(
            self,
            "Hide Others",
            icons.get_icon("hide_source"),
            None,
            enable=False,
            visible=True,
        )

        self.close_action = actions.create_action(
            self,
            "Close",
            icons.get_icon("close"),
            self.close,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+q",
        )

        self.check_updates_action = actions.create_action(
            self,
            "Check for Updates...",
            icons.get_icon("update"),
            None,
            enable=False,
            visible=True,
        )

        # Edit menu
        self.settings_action = actions.create_action(
            self,
            "Settings",
            icons.get_icon("settings"),
            None,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+s",
        )

        # Window menu
        self.window_on_top_action = actions.create_action(
            self,
            "Always On Top",
            icons.get_icon("hdr_strong"),
            self._window_on_top,
            enable=True,
            visible=True,
            shortcut="Ctrl+Shift+t",
        )

        self.minimize_window_action = actions.create_action(
            self,
            "Minimize",
            icons.get_icon("minimize"),
            self.showMinimized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+m",
        )

        self.maximize_window_action = actions.create_action(
            self,
            "Maximize",
            icons.get_icon("maximize"),
            self.showMaximized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+f",
        )

        # Help menu
        self.open_documentation_action = actions.create_action(
            self,
            "Documentation",
            icons.get_icon("contact_support"),
            lambda: open_new_tab(self.documentation),
            enable=True,
            visible=True,
        )

        # Toolbar
        self.home_action = actions.create_action(
            self,
            "Home",
            icons.get_icon("home"),
            None,
            enable=False,
            visible=True,
        )

        self.previous_action = actions.create_action(
            self,
            "Previous",
            icons.get_icon("arrow_back"),
            None,
            enable=False,
            visible=True,
        )

        self.next_action = actions.create_action(
            self,
            "Next",
            icons.get_icon("arrow_forward"),
            None,
            enable=False,
            visible=True,
        )

        self.refresh_action = actions.create_action(
            self,
            "Refresh",
            icons.get_icon("refresh"),
            None,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+r",
        )

    def _on_theme_changed(self, theme):
        self.theme = theme

    def _create_menu_bar(
        self,
        native_menu_bar: bool = False,
    ) -> None:
        """Creates the menu bar for the window.

        Args:
            native_menu_bar (bool, optional): Whether to use the native menu
                bar. Defaults to `False`.
            enable_logo_menu_bar (bool, optional): Whether to enable the logo
                menu bar. Defaults to `True`.

        Warning:
            This method is intended for internal use only.
        """

        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(native_menu_bar)  # Mostly for macOS

        # Main menu
        self.main_menu = self.menu_bar.addMenu("&File")
        self.about_menu = self.main_menu.addAction(self.about_action)
        self.main_menu.addSeparator()
        self.check_updates_menu = self.main_menu.addAction(self.check_updates_action)
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)
        self.hide_main_menu = self.main_menu.addAction(self.hide_action)
        self.hide_others_menu = self.main_menu.addAction(self.hide_others_action)
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)

        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("&Edit")
        self.settings_menu = self.edit_menu.addAction(self.settings_action)

        # Window menu
        self.window_menu = self.menu_bar.addMenu("&Window")
        self.minimize_menu = self.window_menu.addAction(self.minimize_window_action)
        self.maximize_menu = self.window_menu.addAction(self.maximize_window_action)
        self.window_menu.addSeparator()
        self.on_top_menu = self.window_menu.addAction(self.window_on_top_action)
        self.window_menu.addSeparator()

        # Help menu
        self.help_menu = self.menu_bar.addMenu("&Help")
        self.open_documentation_menu = self.help_menu.addAction(self.open_documentation_action)

    def _create_toolbars(self) -> None:
        """Creates the toolbar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setIconSize(QSize(17, 17))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.home_toolbar = self.toolbar.addAction(self.home_action)
        self.previous_toolbar = self.toolbar.addAction(self.previous_action)
        self.next_toolbar = self.toolbar.addAction(self.next_action)
        self.refresh_toolbar = self.toolbar.addAction(self.refresh_action)

        self.toolbar.setMovable(True)

    def _generate_label(self, attribute: str, default: str) -> QLabel:
        """Generates a label for the status bar.

        Args:
            attribute (str): The attribute to be displayed.
            default (str): The default value to be displayed if the attribute
                is not set.

        Warning:
            This method is intended for internal use only.
        """

        if attribute is not None and len(attribute) >= 1:
            return QLabel(attribute)
        else:
            return QLabel(default)

    def _create_status_bar(self) -> None:
        """Creates the status bar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.status_bar = self.statusBar()

        self.project_label = self._generate_label(self.project, "N/A")
        self.version_label = self._generate_label(self.version, "v0.0.0")
        self.company_label = self._generate_label(self.company, "\u00A9 Company Ltd.")

        separator_str = "|"
        separator_left = QLabel(separator_str)
        separator_right = QLabel(separator_str)

        widgets = [
            self.project_label,
            # separator_left,
            self.version_label,
            # separator_right,
            self.company_label,
        ]

        for widget in widgets:
            self.status_bar.addPermanentWidget(widget)
        self.status_bar.setEnabled(True)
        self.status_bar.setVisible(True)

    def _show_about_dialog(self) -> None:
        """Shows the "About" dialog.

        Warning:
            This method is intended for internal use only.
        """

        # ! Repetition from `_create_status_bar` is necessary to create new
        # ! objects
        # If the dialog already exists and is open, close it
        if hasattr(self, "about_dialog") and self.about_dialog is not None:
            self.about_dialog.close()

        # Create a new dialog with self (window) as the parent
        self.about_dialog = QDialog(self)
        self.about_dialog.setWindowTitle("About")

        project_label = self._generate_label(self.project, "N/A")
        project_label.setAlignment(Qt.AlignCenter)
        version_label = self._generate_label(self.version, "v0.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        company_label = self._generate_label(self.company, "\u00A9 Company Ltd.")
        company_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(project_label)
        layout.addWidget(version_label)
        layout.addWidget(company_label)

        self.about_dialog.setFixedSize(200, 150)
        self.about_dialog.setLayout(layout)
        self.about_dialog.exec_()

    def _switch_theme(self):
        """Switches the theme of the window.

        Warning:
            This method is intended for internal use only.
        """

        combo_box = QComboBox()
        # combo_box.addItems(qdarktheme.get_themes())
        # combo_box.currentTextChanged.connect(qdarktheme.setup_theme)
        combo_box.show()

    def _window_on_top(self) -> None:
        """Sets the window on top of all other windows or not.

        Warning:
            This method is intended for internal use only.
        """

        flags = self.windowFlags()
        action_values = {
            True: (
                "Always on Top",
                icons.get_icon("hdr_strong"),
                self.windowTitle().replace(" **", " *"),
            ),
            False: (
                "Regular Position",
                icons.get_icon("hdr_weak"),
                self.windowTitle().replace(" *", " **"),
            ),
        }
        stays_on_top = bool(flags & Qt.WindowStaysOnTopHint)
        text, icon, window_title = action_values[stays_on_top]
        flags ^= Qt.WindowStaysOnTopHint
        self.window_on_top_action.setText(text)
        if icon is not None:
            self.window_on_top_action.setIcon(icon)
        self.setWindowFlags(flags)
        self.setWindowTitle(window_title)
        self.show()

    def _move_window(self) -> None:
        """Moves the window to the selected area of the screen.

        Warning:
            This method is intended for internal use only.
        """

        frame_geo = self.frameGeometry()
        desktop_geometry = QDesktopWidget().availableGeometry()
        center_point = desktop_geometry.center()
        left_top_point = QPoint(desktop_geometry.left(), desktop_geometry.top())
        right_top_point = QPoint(desktop_geometry.right(), desktop_geometry.top())
        left_bottom_point = QPoint(desktop_geometry.left(), desktop_geometry.bottom())
        right_bottom_point = QPoint(desktop_geometry.right(), desktop_geometry.bottom())
        moving_position = {
            1: center_point,
            2: left_top_point,
            3: right_top_point,
            4: left_bottom_point,
            5: right_bottom_point,
        }.get(3, center_point)
        moving_position.setX(moving_position.x() + 0)
        moving_position.setY(moving_position.y() + 0)
        frame_geo.moveCenter(moving_position)
        self.move(frame_geo.topLeft())

    def _is_valid_url(self, url: str) -> bool:
        """Checks if the specified URL is valid.

        Args:
            url (str): The URL to check.

        Warning:
            This method is intended for internal use only.
        """

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _check_documentation(self):
        """Checks if the documentation URL is valid and enables/disables the
        action accordingly.

        Warning:
            This method is intended for internal use only.
        """

        pass
        if self._is_valid_url(self.documentation):
            self.open_documentation_action.setEnabled(True)
        else:
            self.open_documentation_action.setEnabled(False)

    def _add_shadows(self) -> None:
        """Adds shadows to the window elements.

        Warning:
            This method is intended for internal use only.
        """

        shadows.add_shadows(self, self.menu_bar)
        # shadows.add_shadows(self, self.toolbar)
        shadows.add_shadows(self, self.status_bar)

    def _get_current_time(self, display_seconds: bool = False, display_date: bool = False) -> str:
        """Returns the current time as a string.

        Args:
            display_seconds (bool, optional): Whether to display the seconds.
                Defaults to `False`.
            display_date (bool, optional): Whether to display the date.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        format_string = "%H:%M:%S" if display_seconds else "%H:%M"
        if display_date:
            format_string = "%Y-%m-%d " + format_string
        return datetime.now().strftime(format_string)

    # - Public methods

    def hide_toolbar(self) -> None:
        """Hide the toolbar."""

        self.toolbar.hide()

    def show_toolbar(self) -> None:
        """Show the toolbar."""

        self.toolbar.show()

    def hide_menu_bar(self) -> None:
        """Hide the menu bar."""

        self.menu_bar.hide()

    def show_menu_bar(self) -> None:
        """Show the menu bar."""

        self.menu_bar.show()

    def hide_statusbar(self) -> None:
        """Hide the status bar."""

        self.status_bar.hide()

    def show_statusbar(self) -> None:
        """Show the status bar."""

        self.status_bar.show()

    def set_statusbar_message(
        self,
        message: str,
        severity_type: int = 4,
        duration: float = 2.5,
        time: bool = True,
        logger: logging.Logger = None,
    ) -> None:
        """Display a message in the status bar with a specified severity.

        Args:
            message (str): The message to be displayed.
            severity_type (int, optional): The severity level of the message.
                Should be one of `CRITICAL`, `ERROR`, `WARNING`, `SUCCESS`,
                or `INFO`. Defaults to `INFO`.
            duration (float, optional): The duration in seconds for which
                the message should be displayed. Defaults to` 2.5`.
            time (bool, optional): Whether to display the current time before
                the message. Defaults to `True`.
            logger (Logger, optional): A logger object to log the message.
                Defaults to `None`.

        Examples:
            To display a critical error message with a red background
            >>> self.set_statusbar_message(
            ...     "Critical error occurred!",
            ...     severity_type=self.CRITICAL,
            ...     duration=5,
            ...     logger=my_logger,
            ... )

        Note:
            You can either use the window instance to retrieve the verbosity
            constants, or the window module.
        """

        # Create dictionnary for verbosity colors
        colors_dict = style.load_colors_from_jsonc()
        severity_mapping = {
            0: (
                "Critical",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxCritical),
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            1: (
                "Error",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxCritical),
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            2: (
                "Warning",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning),
                colors_dict["feedback"]["warning"]["background"],
                colors_dict["feedback"]["warning"]["dark"],
            ),
            3: (
                "Success",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxQuestion),
                colors_dict["feedback"]["success"]["background"],
                colors_dict["feedback"]["success"]["dark"],
            ),
            4: (
                "Info",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxInformation),
                colors_dict["feedback"]["info"]["background"],
                colors_dict["feedback"]["info"]["dark"],
            ),
        }

        (
            severity_prefix,
            severity_icon,
            status_bar_color,
            status_bar_border_color,
        ) = severity_mapping[severity_type]

        # Message
        message_prefix = f"{severity_prefix}: {self._get_current_time()} - " if time else f"{severity_prefix}: "
        notification_message = f"{message_prefix} {message}"
        self.status_bar.showMessage(notification_message, duration * 1000)

        # Link `Logger` object
        if logger is not None:
            # Modify log level according to severity_type
            if severity_type == 0:
                logger.critical(message)
            if severity_type == 1:
                logger.warning(message)
            elif severity_type == 2:
                logger.error(message)
            elif severity_type == 3 or severity_type == 4:
                logger.info(message)

    # - Events

    def closeEvent(self, event) -> None:
        self.setParent(None)
