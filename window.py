#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""_summary_"""

# Built-in
import os
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
import splashscreen

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


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
        version (str, optional): Version label for the window. Defaults to `None`.
        ui_file (str, optional): Path to the UI file for loading.
            Defaults to `None`.
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
        self.light_theme = not light_theme  # ! Invert value because of the
        # !`self._switch_theme()` function call during construction

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

        # TODO: temporary
        self.ui.pushButton_2.clicked.connect(
            lambda: self.set_status_bar_message("Error", 1)
        )
        self.ui.pushButton.clicked.connect(
            lambda: self.set_status_bar_message("Success", 3)
        )

    def _load_ui(self):
        if self.ui_file != None and os.path.isfile(self.ui_file):
            loader = QUiLoader()
            self.ui_file = QFile(self.ui_file)
            self.ui_file.open(QFile.ReadOnly)
            self.ui = loader.load(self.ui_file, self)
            self.ui_file.close()

            # Add the loaded UI to the main window
            self.setCentralWidget(self.ui)

    def _set_window_icon(self):
        if self.window_icon != None and os.path.isfile(self.window_icon):
            self.setWindowIcon(QIcon(self.window_icon))
        else:
            self.setWindowIcon(QIcon(self._default_icon))

    def _set_window_title(self):
        if self.window_title != None and len(self.window_title) >= 1:
            self.setWindowTitle(f"VFX | {self.window_title} *")
        else:
            self.setWindowTitle(f"VFX | Window *")

    def _set_window_size(self):
        if self.window_size != None and len(self.window_size) >= 1:
            self.resize(QSize(*self.window_size))
        else:
            self.resize(QSize(500, 600))

    def _create_actions(self):
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
            enable=True,
            visible=True,
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
        native_menu_bar=False,
        enable_logo_menu_bar=True,
    ):
        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(native_menu_bar)

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

    def _create_toolbars(self):
        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setIconSize(QSize(17, 17))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.previous_toolbar = self.toolbar.addAction(self.previous_action)
        self.next_toolbar = self.toolbar.addAction(self.next_action)
        self.refresh_toolbar = self.toolbar.addAction(self.refresh_action)
        self.home_toolbar = self.toolbar.addAction(self.home_action)

        self.toolbar.setMovable(True)

    def _create_status_bar(self):
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

    def _window_on_top(self):
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

    def _move_window(self):
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

    def _switch_theme(self):
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

    def _is_valid_url(self, url):
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

    def _add_shadows(self):
        shadows.add_shadows(self, self.menu_bar)
        # shadows.add_shadows(self, self.toolbar)
        shadows.add_shadows(self, self.status_bar)

    def _get_current_time(self, display_seconds=False, display_date=False):
        format_string = "%H:%M:%S" if display_seconds else "%H:%M"
        if display_date:
            format_string = "%Y-%m-%d " + format_string
        return datetime.now().strftime(format_string)

    def _status_changed(self, args):
        # If there are no arguments (meaning the message is being removed),
        # then change the status bar background back to black.

        if not args:
            if self.light_theme:
                # TODO: Call `style.replace_colors()`` instead of manually typing
                # TODO: the color values
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

    # ' Placeholders

    def set_status_bar_message(
        self, message, severity_type=4, duration=2.5, time=True, logger=None
    ):
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
            log_message = message

            # Modify log level according to severity_type
            if severity_type == 0:
                logger.critical(log_message)
            if severity_type == 1:
                logger.warning(log_message)
            elif severity_type == 2:
                logger.error(log_message)
            elif severity_type == 3 or severity_type == 4:
                logger.info(log_message)

    def refresh(self):
        pass

    # ' Events

    def closeEvent(self, event):
        self.setParent(None)
