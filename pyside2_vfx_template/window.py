#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VFXWindow module."""

# Built-in
import os
import logging
from typing import Union
from datetime import datetime
from webbrowser import open_new_tab
from urllib.parse import urlparse

# Third-party
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Internal
import style
import shadows
import actions
import utils

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
        documentation (str, optional): URL to the tool's documentation.
            Defaults to `None`.
        version (str, optional): Version label for the window.
            Defaults to `None`.
        ui_file (str, optional): Path to the UI file for loading.
            Defaults to `None`.

    Example:
        >>> app = QApplication(sys.argv)
        >>> window = VFXWindow(
        ...     icon="path_to_icon.png",
        ...     title="My Custom Window",
        ...     size=(800, 600),
        ...     documentation="https://my_tool_docs.com",
        ...     project="Awesome Project",
        ...     version="v1.0.0",
        ...     ui_file="path_to_ui_file.ui",
        ...     light_theme=False,
        ... )
        >>> window.set_status_bar_message("Window initialized", window.INFO)
        >>> window.show()
        >>> sys.exit(app.exec_())
    """

    def __init__(
        self,
        parent=None,
        icon=None,
        title=None,
        size=None,
        documentation=None,
        project=None,
        version=None,
        ui_file=None,
        light_theme=False,
    ):
        super().__init__(parent)

        # Stylesheet
        # ! Invert value because of the
        # !`self._switch_theme()` function call during construction
        self.light_theme = not light_theme

        # Attributes
        self._default_icon = os.path.join(
            os.path.dirname(__file__), "icons", "favicon.png"
        )
        self.window_icon = icon
        self.window_title = title
        self.window_size = size
        self.documentation = documentation
        self.project = project
        self.version = version
        self.ui_file = ui_file

        # Functions
        self._load_ui()
        self._set_window_icon()
        self._set_window_title()
        self._set_window_size()
        self._create_actions()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._switch_theme()
        self._check_documentation()
        self._add_shadows()

    # - Hidden methods

    def _load_ui(self) -> None:
        if self.ui_file != None:
            self.ui = utils.load_ui(self, self.ui_file)

            # Add the loaded UI to the main window
            self.setCentralWidget(self.ui)

    def _set_window_icon(self) -> None:
        if self.window_icon != None and os.path.isfile(self.window_icon):
            self.setWindowIcon(QIcon(self.window_icon))
        else:
            self.setWindowIcon(QIcon(self._default_icon))

    def _set_window_title(self) -> None:
        if self.window_title != None and len(self.window_title) >= 1:
            self.setWindowTitle(f"VFX | {self.window_title} *")
        else:
            self.setWindowTitle(f"VFX | Window *")

    def _set_window_size(self) -> None:
        if self.window_size != None and len(self.window_size) >= 1:
            self.resize(QSize(*self.window_size))
        else:
            self.resize(QSize(500, 600))

    def _create_actions(self) -> None:
        # Main menu
        self.about_action = actions.create_action(
            self,
            "About",
            None,
            None,
            enable=True,
            visible=True,
        )

        self.hide_action = actions.create_action(
            self,
            "Hide",
            None,
            self.hide,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+h",
        )

        self.hide_others_action = actions.create_action(
            self,
            "Hide Others",
            None,
            None,
            enable=False,
            visible=True,
        )

        self.close_action = actions.create_action(
            self,
            "Close",
            None,
            self.close,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+q",
        )

        self.check_updates_action = actions.create_action(
            self,
            "Check for Updates...",
            None,
            None,
            enable=False,
            visible=True,
        )

        # Edit menu
        self.settings_action = actions.create_action(
            self,
            "Settings",
            None,
            None,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+s",
        )

        # Window menu
        self.switch_theme_action = actions.create_action(
            self,
            "Switch Theme",
            None,
            self._switch_theme,
            enable=False,  # TODO: Show when all is fixed
            visible=False,  # TODO: Enable when all is fixed
        )

        self.window_on_top_action = actions.create_action(
            self,
            "Always On Top",
            None,
            self._window_on_top,
            enable=True,
            visible=True,
            shortcut="Ctrl+Shift+t",
        )

        self.minimize_window_action = actions.create_action(
            self,
            "Minimize",
            None,
            self.showMinimized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+m",
        )

        self.maximize_window_action = actions.create_action(
            self,
            "Maximize",
            None,
            self.showMaximized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+f",
        )

        # Help menu
        self.open_documentation_action = actions.create_action(
            self,
            "Documentation",
            None,
            lambda: open_new_tab(self.documentation),
            enable=True,
            visible=True,
        )

        # Toolbar
        self.previous_action = actions.create_action(
            self,
            "Previous",
            None,
            None,
            enable=False,
            visible=False,
        )

        self.next_action = actions.create_action(
            self,
            "Next",
            None,
            None,
            enable=False,
            visible=False,
        )

        self.refresh_action = actions.create_action(
            self,
            "Refresh",
            None,
            self.refresh,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+r",
        )

        self.home_action = actions.create_action(
            self,
            "Home",
            None,
            None,
            enable=False,
            visible=False,
        )

    def _create_menu_bar(
        self,
        native_menu_bar: bool = False,
        enable_logo_menu_bar: bool = True,
    ) -> None:
        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(native_menu_bar)  # Mostly for macOS

        # Icon menu
        if enable_logo_menu_bar:
            self.icon_menu = self.menu_bar.addMenu("")
            pixmap_path = os.path.join(
                os.path.dirname(__file__), "icons", "favicon.png"
            )
            pixmap = QPixmap(pixmap_path)
            new_size = QSize(10, 10)
            scaled_pixmap = pixmap.scaled(
                new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            icon = QIcon(scaled_pixmap)
            self.icon_menu.setIcon(icon)

        # Main menu
        self.main_menu = self.menu_bar.addMenu("File")
        self.about_menu = self.main_menu.addAction(self.about_action)
        self.main_menu.addSeparator()
        self.check_updates_menu = self.main_menu.addAction(
            self.check_updates_action
        )
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)
        self.hide_main_menu = self.main_menu.addAction(self.hide_action)
        self.hide_others_menu = self.main_menu.addAction(
            self.hide_others_action
        )
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)

        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("Edit")
        self.settings_menu = self.edit_menu.addAction(self.settings_action)

        # Window menu
        self.window_menu = self.menu_bar.addMenu("Window")
        self.switch_theme_menu = self.window_menu.addAction(
            self.switch_theme_action
        )
        self.window_menu.addSeparator()
        self.minimize_menu = self.window_menu.addAction(
            self.minimize_window_action
        )
        self.maximize_menu = self.window_menu.addAction(
            self.maximize_window_action
        )
        self.window_menu.addSeparator()
        self.on_top_menu = self.window_menu.addAction(self.window_on_top_action)

        # Help menu
        self.help_menu = self.menu_bar.addMenu("Help")
        self.open_documentation_menu = self.help_menu.addAction(
            self.open_documentation_action
        )

    def _create_toolbars(self) -> None:
        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setIconSize(QSize(17, 17))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.previous_toolbar = self.toolbar.addAction(self.previous_action)
        self.next_toolbar = self.toolbar.addAction(self.next_action)
        self.refresh_toolbar = self.toolbar.addAction(self.refresh_action)
        self.home_toolbar = self.toolbar.addAction(self.home_action)

        self.toolbar.setMovable(True)

    def _create_status_bar(self) -> None:
        self.status_bar = self.statusBar()

        if self.project != None and len(self.project) >= 1:
            project_label = QLabel(self.project)
        else:
            project_label = QLabel("N/A")

        if self.version != None and len(self.version) >= 1:
            version_label = QLabel(self.version)
        else:
            version_label = QLabel("v0.0.0")

        separator_0 = QLabel("|")
        separator_1 = QLabel("|")
        company_label = QLabel("\u00A9 Company Ltd.")
        widgets = [
            project_label,
            separator_0,
            version_label,
            separator_1,
            company_label,
        ]
        for widget in widgets:
            self.status_bar.addPermanentWidget(widget)
        self.status_bar.setEnabled(True)
        self.status_bar.setVisible(True)

        # Connection to handle color change during feedback
        self.status_bar.messageChanged.connect(self._status_changed)

    def _window_on_top(self) -> None:
        flags = self.windowFlags()
        action_values = {
            True: (
                "Always on Top",
                None,
                self.windowTitle().replace(" **", " *"),
            ),
            False: (
                "Regular Position",
                None,
                self.windowTitle().replace(" *", " **"),
            ),
        }
        stays_on_top = bool(flags & Qt.WindowStaysOnTopHint)
        text, icon, window_title = action_values[stays_on_top]
        flags ^= Qt.WindowStaysOnTopHint
        self.window_on_top_action.setText(text)
        if icon != None:
            self.window_on_top_action.setIcon(icon)
        self.setWindowFlags(flags)
        self.setWindowTitle(window_title)
        self.show()

    def _move_window(self) -> None:
        frame_geo = self.frameGeometry()
        desktop_geometry = QDesktopWidget().availableGeometry()
        center_point = desktop_geometry.center()
        left_top_point = QPoint(desktop_geometry.left(), desktop_geometry.top())
        right_top_point = QPoint(
            desktop_geometry.right(), desktop_geometry.top()
        )
        left_bottom_point = QPoint(
            desktop_geometry.left(), desktop_geometry.bottom()
        )
        right_bottom_point = QPoint(
            desktop_geometry.right(), desktop_geometry.bottom()
        )
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

    def _switch_theme(self) -> None:
        if self.light_theme == False:
            self.setStyleSheet(style.load_stylesheet(light_theme=True))
            self.switch_theme_action.setText("Dark Theme")
            # self.switch_theme_action.setIcon("Dark")
            self.light_theme = True
        else:
            self.setStyleSheet(style.load_stylesheet(light_theme=False))
            self.switch_theme_action.setText("Light Theme")
            # self.switch_theme_action.setIcon("Light")
            self.light_theme = False
        # Force the status bar to get the right colors
        # self._status_changed(args=None)

    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _check_documentation(self):
        pass
        if self._is_valid_url(self.documentation):
            self.open_documentation_action.setEnabled(True)
        else:
            self.open_documentation_action.setEnabled(False)

    def _add_shadows(self) -> None:
        shadows.add_shadows(self, self.menu_bar)
        # shadows.add_shadows(self, self.toolbar)
        shadows.add_shadows(self, self.status_bar)

    def _get_current_time(
        self, display_seconds: bool = False, display_date: bool = False
    ) -> str:
        format_string = "%H:%M:%S" if display_seconds else "%H:%M"
        if display_date:
            format_string = "%Y-%m-%d " + format_string
        return datetime.now().strftime(format_string)

    def _status_changed(self, args: str) -> None:
        # If there are no arguments (meaning the message is being removed),
        # then change the status bar background back to black.

        if not args:
            if self.light_theme:
                # TODO: Call `style.replace_colors()` instead of manually typing the color values
                stylesheet = """
                    QStatusBar {
                        color: @white;
                        background-color: #e5e5e5;
                        border-top: 1px solid #c7c7c7;
                    }

                    QStatusBar::item {
                        color: @white;
                        border: 0px solid transparent;
                    }
                """
            else:
                stylesheet = """
                    QStatusBar {
                        color: @white;
                        background-color: @tableBackground;
                        border-top: 1px solid @menuBackground;
                    }

                    QStatusBar::item {
                        color: @white;
                        border: 0px solid transparent;
                    }
                """
                stylesheet = style.replace_colors(stylesheet)

            self.status_bar.setStyleSheet(stylesheet)

    # - Public methods

    def set_status_bar_message(
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

        Example:
            ... # To display a critical error message with a red background
            >>> self.set_status_bar_message(
            ...     "Critical error occurred!",
            ...     severity_type=self.CRITICAL,
            ...     duration=5,
            ...     logger=my_logger,
            ... )
        """

        colors_dict = style.load_colors_from_jsonc()
        severity_colors = {
            0: (
                "Critical",
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            1: (
                "Error",
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            2: (
                "Warning",
                colors_dict["feedback"]["warning"]["background"],
                colors_dict["feedback"]["warning"]["dark"],
            ),
            3: (
                "Success",
                colors_dict["feedback"]["success"]["background"],
                colors_dict["feedback"]["success"]["dark"],
            ),
            4: (
                "Info",
                colors_dict["feedback"]["info"]["background"],
                colors_dict["feedback"]["info"]["dark"],
            ),
        }

        (
            severity_prefix,
            status_bar_color,
            status_bar_border_color,
        ) = severity_colors[severity_type]

        message_prefix = (
            f"{severity_prefix}: {self._get_current_time()} - "
            if time
            else f"{severity_prefix}: "
        )
        notification_message = f"{message_prefix} {message}"

        self.status_bar.showMessage(notification_message, duration * 1000)

        self.status_bar.setStyleSheet(
            """QStatusBar {
        color: white;
        background: """
            + status_bar_color
            + """;
        border-top: 1px solid"""
            + status_bar_border_color
            + """;
        }
        """
        )

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

    # - Placeholders

    def refresh(self) -> None:
        pass

    # - Events

    def closeEvent(self, event) -> None:
        self.setParent(None)
