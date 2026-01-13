"""Custom main window widget."""

# Built-in
import os
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
from webbrowser import open_new_tab

# Third-party
from qtpy.QtCore import QPoint, QRect, QSize, Qt
from qtpy.QtGui import QAction, QCloseEvent, QIcon
from qtpy.QtWidgets import (
    QActionGroup,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from qtpy import QT_VERSION

QT_VERSION_MAJOR = int(QT_VERSION.split(".")[0])
if QT_VERSION_MAJOR >= 6:
    from qtpy.QtGui import QScreen
else:
    from qtpy.QtWidgets import QDesktopWidget

from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._tooltip import FXTooltipManager
from fxgui.fxwidgets._constants import (
    CRITICAL,
    ERROR,
    WARNING,
    SUCCESS,
    INFO,
    DEBUG,
)
from fxgui.fxwidgets._status_bar import FXStatusBar


class FXMainWindow(fxstyle.FXThemeAware, QMainWindow):
    """Customized QMainWindow class.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (str, optional): Path to the window icon image. Defaults to `None`.
        title (str, optional): Title of the window. Defaults to `None`.
        size (Tuple[int, int], optional): Window size as width and height.
            Defaults to `None`.
        documentation (str, optional): URL to the tool's documentation.
            Defaults to `None`.
        version (str, optional): Version label for the window.
            Defaults to `None`.
        company (str, optional): Company name for the window.
            Defaults to `Company`.
        ui_file (str, optional): Path to the UI file for loading.
            Defaults to `None`.
        set_stylesheet (bool, optional): Whether to set the default stylesheet.
            Defaults to `True`.
    """

    # Class-level severity constants for convenience
    CRITICAL: int = CRITICAL
    ERROR: int = ERROR
    WARNING: int = WARNING
    SUCCESS: int = SUCCESS
    INFO: int = INFO
    DEBUG: int = DEBUG

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        size: Optional[Tuple[int, int]] = None,
        documentation: Optional[str] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        ui_file: Optional[str] = None,
        set_stylesheet: bool = True,
    ):
        super().__init__(parent)

        # Private attributes
        self._default_icon_path: str = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "images",
            "fxgui_logo_background_dark.svg",
        )
        self._set_stylesheet: bool = set_stylesheet

        # Public attributes
        self.window_icon: Optional[str] = icon
        self.window_title: Optional[str] = title
        self.window_size: Optional[Tuple[int, int]] = size
        self.documentation: Optional[str] = documentation
        self.project: str = project or "Project"
        self.version: str = version or "0.0.0"
        self.company: str = company or "\u00a9 Company"
        self.ui_file: Optional[str] = ui_file
        self.ui: Optional[QWidget] = None

        # Theme action storage
        self.theme_actions: Dict[str, QAction] = {}
        self.theme_action_group: Optional[QActionGroup] = None

        # Banner icon storage for theme-aware updates
        self._banner_icon_name: Optional[str] = None
        self._banner_icon_size: int = 20

        # Initialize UI components
        self._create_actions()
        self._create_banner()
        self._load_ui()
        self.setWindowTitle(self.window_title)
        self._set_window_icon()
        self._set_window_size()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._check_documentation()
        self._add_shadows()

        # Styling - load_stylesheet() automatically uses the saved theme
        if self._set_stylesheet:
            self.setStyleSheet(fxstyle.load_stylesheet())

        # Install the global FXTooltip manager for rich tooltips
        # This replaces standard Qt tooltips with FXTooltip for all widgets
        FXTooltipManager.install()

    # Private methods
    def _load_ui(self) -> None:
        """Load the UI from the specified UI file.

        Sets the loaded UI as the central widget of the main window.

        Warning:
            This method is intended for internal use only.
        """
        if self.ui_file is not None:
            self.ui = fxutils.load_ui(self, self.ui_file)
            self.setCentralWidget(self.ui)

    def _set_window_icon(self) -> None:
        """Sets the window icon from the specified icon path.

        Warning:
            This method is intended for internal use only.
        """
        icon_path = (
            self.window_icon
            if self.window_icon and os.path.isfile(self.window_icon)
            else self._default_icon_path
        )
        self.setWindowIcon(QIcon(icon_path))

    def _set_window_size(self) -> None:
        """Set the window size from the specified size.

        Warning:
            This method is intended for internal use only.
        """
        default_size = QSize(500, 600)
        if self.window_size and len(self.window_size) >= 2:
            self.resize(QSize(*self.window_size))
        else:
            self.resize(default_size)

    def _create_actions(self) -> None:
        """Create the actions for the window.

        Warning:
            This method is intended for internal use only.
        """
        # Main menu
        self.about_action = fxutils.create_action(
            self,
            "About",
            trigger=self._show_about_dialog,
            enable=True,
            visible=True,
            icon_name="help",
        )

        self.check_updates_action = fxutils.create_action(
            self,
            "Check for Updates...",
            trigger=None,
            enable=False,
            visible=True,
            icon_name="update",
        )

        self.hide_action = fxutils.create_action(
            self,
            "Hide",
            trigger=self.hide,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+h",
            icon_name="visibility_off",
        )

        self.hide_others_action = fxutils.create_action(
            self,
            "Hide Others",
            trigger=None,
            enable=False,
            visible=True,
            icon_name="disabled_visible",
        )

        self.close_action = fxutils.create_action(
            self,
            "Close",
            trigger=self.close,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+q",
            icon_name="close",
        )

        # Edit menu
        self.settings_action = fxutils.create_action(
            self,
            "Settings",
            trigger=None,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+s",
            icon_name="settings",
        )

        # Window menu
        self.window_on_top_action = fxutils.create_action(
            self,
            "Always On Top",
            trigger=self._toggle_window_on_top,
            enable=True,
            visible=True,
            shortcut="Ctrl+Shift+t",
            icon_name="hdr_strong",
        )

        self.minimize_window_action = fxutils.create_action(
            self,
            "Minimize",
            trigger=self.showMinimized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+m",
            icon_name="minimize",
        )

        self.maximize_window_action = fxutils.create_action(
            self,
            "Maximize",
            trigger=self.showMaximized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+f",
            icon_name="maximize",
        )

        self.toggle_theme_action = fxutils.create_action(
            self,
            "Toggle Theme",
            trigger=self._toggle_theme,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+t",
            icon_name="brightness_4",
        )

        # Theme selection actions (populated dynamically from available themes)
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        for theme_name in fxstyle.get_available_themes():
            action = fxutils.create_action(
                self,
                theme_name.title().replace("_", " "),
                None,
                lambda checked, t=theme_name: self._set_theme(t),
                enable=True,
                visible=True,
                checkable=True,
            )
            # Check the current theme
            if theme_name == fxstyle.get_theme():
                action.setChecked(True)
            self.theme_action_group.addAction(action)
            self.theme_actions[theme_name] = action

        # Help menu
        self.open_documentation_action = fxutils.create_action(
            self,
            "Documentation",
            trigger=lambda: open_new_tab(self.documentation),
            enable=True,
            visible=True,
            icon_name="menu_book",
        )

        # Toolbar
        self.home_action = fxutils.create_action(
            self,
            "Home",
            trigger=None,
            enable=False,
            visible=True,
            icon_name="home",
        )

        self.previous_action = fxutils.create_action(
            self,
            "Previous",
            trigger=None,
            enable=False,
            visible=True,
            icon_name="arrow_back",
        )

        self.next_action = fxutils.create_action(
            self,
            "Next",
            trigger=None,
            enable=False,
            visible=True,
            icon_name="arrow_forward",
        )

        self.refresh_action = fxutils.create_action(
            self,
            "Refresh",
            trigger=None,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+r",
            icon_name="refresh",
        )

    def _create_menu_bar(
        self,
        native_menu_bar: bool = False,
    ) -> None:
        """Creates the menu bar for the window.

        Args:
            native_menu_bar (bool): Whether to use the native menu bar.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(native_menu_bar)  # Mostly for macOS

        # Main menu
        self.main_menu = self.menu_bar.addMenu("File")
        self.about_menu = self.main_menu.addAction(self.about_action)
        self.main_menu.addSeparator()
        self.check_updates_menu = self.main_menu.addAction(
            self.check_updates_action
        )
        self.main_menu.addSeparator()
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
        self.minimize_menu = self.window_menu.addAction(
            self.minimize_window_action
        )
        self.maximize_menu = self.window_menu.addAction(
            self.maximize_window_action
        )
        self.window_menu.addSeparator()
        self.on_top_menu = self.window_menu.addAction(self.window_on_top_action)
        self.window_menu.addSeparator()
        # Theme submenu with radio-style selection
        self.theme_menu = self.window_menu.addMenu("Theme")
        fxicons.set_icon(self.theme_menu, "brightness_4")
        for theme_name, action in self.theme_actions.items():
            self.theme_menu.addAction(action)

        # Help menu
        self.help_menu = self.menu_bar.addMenu("Help")
        self.open_documentation_menu = self.help_menu.addAction(
            self.open_documentation_action
        )

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

        return QLabel(attribute if attribute else default)

    def _create_banner(self) -> None:
        """Creates a banner with the window title for the window.

        Note:
            This method is intended for internal use only.
        """

        # Create banner container widget
        self.banner = QWidget(self)
        self.banner.setFixedHeight(50)
        self.banner.setStyleSheet(
            f"background: transparent; "
            f"border-bottom: 1px solid {self.theme.border};"
        )

        # Create layout for banner
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(10, 0, 10, 0)
        banner_layout.setSpacing(8)

        # Create icon label (hidden by default)
        self.banner_icon = QLabel(self.banner)
        self.banner_icon.setFixedSize(24, 24)
        self.banner_icon.setStyleSheet("border: none;")
        self.banner_icon.hide()

        # Create text label
        self.banner_label = QLabel("Banner", self.banner)
        self.banner_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.banner_label.setStyleSheet(
            f"color: {self.theme.text}; font-size: 16px; border: none;"
        )

        banner_layout.addWidget(self.banner_icon)
        banner_layout.addWidget(self.banner_label)
        banner_layout.addStretch()

        central_widget = self.centralWidget()
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.banner)

        if central_widget is not None:
            layout.addWidget(central_widget)
        else:
            central_widget = QWidget()
            layout.addWidget(central_widget)

        self.setCentralWidget(widget)

    def _create_status_bar(self) -> None:
        """Creates the status bar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.status_bar = FXStatusBar(
            parent=self,
            project=self.project,
            version=self.version,
            company=self.company,
        )
        self.setStatusBar(self.status_bar)

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

        project_label = self._generate_label(self.project, "Project")
        project_label.setAlignment(Qt.AlignCenter)
        version_label = self._generate_label(self.version, "0.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        company_label = self._generate_label(self.company, "\u00a9 Company")
        company_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(project_label)
        layout.addWidget(version_label)
        layout.addWidget(company_label)
        layout.addStretch()

        self.about_dialog.setFixedSize(200, 150)
        self.about_dialog.setLayout(layout)
        self.about_dialog.exec_()

    def _toggle_window_on_top(self) -> None:
        """Sets the window on top of all other windows or not.

        Warning:
            This method is intended for internal use only.
        """

        flags = self.windowFlags()
        stays_on_top = bool(flags & Qt.WindowStaysOnTopHint)
        flags ^= Qt.WindowStaysOnTopHint

        if stays_on_top:
            self.window_on_top_action.setText("Always on Top")
            fxicons.set_icon(self.window_on_top_action, "hdr_strong")
        else:
            self.window_on_top_action.setText("Regular Position")
            fxicons.set_icon(self.window_on_top_action, "hdr_weak")

        self.setWindowFlags(flags)
        self.show()

    def _move_window(self) -> None:
        """Moves the window to the selected area of the screen.

        Warning:
            This method is intended for internal use only.
        """

        frame_geo = self.frameGeometry()

        if QT_VERSION_MAJOR >= 6:
            screen: QScreen = QApplication.primaryScreen()
            desktop_geometry = screen.availableGeometry()
        else:
            desktop_geometry: QRect = QDesktopWidget().availableGeometry()

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

    def _is_valid_url(self, url: str) -> bool:
        """Checks if the specified URL is valid.

        Args:
            url (str): The URL to check.

        Warning:
            This method is intended for internal use only.
        """

        if not url:
            return False
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except (ValueError, AttributeError):
            return False

    def _check_documentation(self):
        """Checks if the documentation URL is valid and enables/disables the
        action accordingly.

        Warning:
            This method is intended for internal use only.
        """

        self.open_documentation_action.setEnabled(
            self._is_valid_url(self.documentation)
        )

    def _add_shadows(
        self,
        menu_bar: bool = False,
        toolbar: bool = False,
        status_bar: bool = False,
    ) -> None:
        """Adds shadows to the window elements.

        Args:
            menu_bar (bool, optional): Whether to add shadows to the menu bar.
                Defaults to `False`.
            toolbar (bool, optional): Whether to add shadows to the toolbar.
                Defaults to `False`.
            status_bar (bool, optional): Whether to add shadows to the status bar.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        if menu_bar:
            fxutils.add_shadows(self, self.menu_bar)
        if toolbar:
            fxutils.add_shadows(self, self.toolbar)
        if status_bar:
            fxutils.add_shadows(self, self.statusBar())

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes for the window.

        This method is called automatically by the FXThemeAware mixin
        when the theme changes. Override this method to customize
        theme-specific styling.

        Warning:
            This method is intended for internal use only.
        """
        # Update banner container for the new theme (match _create_banner style)
        if hasattr(self, "banner") and self.banner is not None:
            self.banner.setStyleSheet(
                f"background: transparent; "
                f"border-bottom: 1px solid {self.theme.border};"
            )

        # Update banner label text color
        if hasattr(self, "banner_label") and self.banner_label is not None:
            self.banner_label.setStyleSheet(
                f"color: {self.theme.text}; font-size: 16px; border: none;"
            )

        # Update banner icon with new theme colors
        if self._banner_icon_name is not None:
            self._update_banner_icon()

        # Force menu bar to repaint with new icons
        if hasattr(self, "menu_bar") and self.menu_bar is not None:
            self.menu_bar.update()
            self.menu_bar.repaint()

        # Update the checked state of theme actions
        current_theme = fxstyle.get_theme()
        if current_theme in self.theme_actions:
            self.theme_actions[current_theme].setChecked(True)

    def _set_theme(self, theme: str) -> None:
        """Internal method to apply a specific theme to the window.

        Args:
            theme: The theme name to apply.

        Warning:
            This method is intended for internal use only.
            Use `set_theme()` for external theme selection.
        """
        # Use centralized theme application
        # This automatically syncs icon colors and refreshes all registered icons
        # and triggers the FXThemeAware mixin to call _apply_theme_styles
        fxstyle.apply_theme(self, theme=theme)

    def _toggle_theme(self) -> None:
        """Toggles the theme of the window between available themes.

        Warning:
            This method is intended for internal use only.
            Use `toggle_theme()` for external theme cycling.
        """
        # Get available themes and find the next one
        themes = fxstyle.get_available_themes()
        current = fxstyle.get_theme()
        if current in themes:
            current_idx = themes.index(current)
            next_idx = (current_idx + 1) % len(themes)
            next_theme = themes[next_idx]
        else:
            next_theme = themes[0] if themes else "dark"

        self._set_theme(next_theme)

    def _refresh_dialog_button_icons(self) -> None:
        """Refresh and register all QDialogButtonBox button icons.

        This method finds all QDialogButtonBox widgets in the window and
        registers their buttons with fxicons for automatic theme updates.

        Warning:
            This method is intended for internal use only.
        """
        # Map of standard button roles to their icon names
        button_icon_map: Dict[QDialogButtonBox.StandardButton, str] = {
            QDialogButtonBox.Ok: "check",
            QDialogButtonBox.Cancel: "cancel",
            QDialogButtonBox.Close: "close",
            QDialogButtonBox.Save: "save",
            QDialogButtonBox.SaveAll: "save_all",
            QDialogButtonBox.Open: "open_in_new",
            QDialogButtonBox.Yes: "check",
            QDialogButtonBox.YesToAll: "done_all",
            QDialogButtonBox.No: "cancel",
            QDialogButtonBox.NoToAll: "do_not_disturb",
            QDialogButtonBox.Abort: "cancel",
            QDialogButtonBox.Retry: "restart_alt",
            QDialogButtonBox.Ignore: "notifications_off",
            QDialogButtonBox.Discard: "delete",
            QDialogButtonBox.Help: "help",
            QDialogButtonBox.Apply: "check",
            QDialogButtonBox.Reset: "cleaning_services",
            QDialogButtonBox.RestoreDefaults: "settings_backup_restore",
        }

        # Find all QDialogButtonBox widgets and register their buttons
        for button_box in self.findChildren(QDialogButtonBox):
            for role, icon_name in button_icon_map.items():
                button = button_box.button(role)
                if button is not None:
                    fxicons.set_icon(button, icon_name)

    # Public methods
    def set_theme(self, theme: str) -> str:
        """Set the theme of the window.

        This method can be called from external code to apply a specific theme,
        including when running inside a DCC like Houdini, Maya, or Nuke
        where you don't have direct access to QApplication.

        Args:
            theme: The theme name to apply (e.g., "dark", "light", or custom).

        Returns:
            str: The theme that was applied.

        Examples:
            >>> window = FXMainWindow()
            >>> window.show()
            >>> window.set_theme("light")
            >>> window.set_theme("dark")
        """
        self._set_theme(theme)
        return fxstyle.get_theme()

    def toggle_theme(self) -> str:
        """Toggle the theme of the window to the next available theme.

        This method can be called from external code to cycle through themes,
        including when running inside a DCC like Houdini, Maya, or Nuke
        where you don't have direct access to QApplication.

        Returns:
            str: The new theme that was applied.

        Examples:
            >>> window = FXMainWindow()
            >>> window.show()
            >>> new_theme = window.toggle_theme()
            >>> print(f"Switched to {new_theme} theme")
        """
        self._toggle_theme()
        return fxstyle.get_theme()

    def get_available_themes(self) -> List[str]:
        """Get a list of all available theme names.

        Returns:
            List[str]: List of theme names (e.g., ["dark", "light"]).

        Examples:
            >>> window = FXMainWindow()
            >>> themes = window.get_available_themes()
            >>> print(themes)  # ['dark', 'light']
        """
        return fxstyle.get_available_themes()

    def center_on_screen(self) -> None:
        """Center the window on the primary screen.

        This method centers the window on the available screen geometry,
        accounting for taskbars and other system UI elements.

        Examples:
            >>> window = FXMainWindow()
            >>> window.resize(800, 600)
            >>> window.center_on_screen()
            >>> window.show()
        """
        frame_geo = self.frameGeometry()

        if QT_VERSION_MAJOR >= 6:
            screen: QScreen = QApplication.primaryScreen()
            desktop_geometry = screen.availableGeometry()
        else:
            desktop_geometry: QRect = QDesktopWidget().availableGeometry()

        center_point = desktop_geometry.center()
        frame_geo.moveCenter(center_point)
        self.move(frame_geo.topLeft())

    # Overrides
    def statusBar(self) -> FXStatusBar:
        """Returns the FXStatusBar instance associated with this window.

        Returns:
            FXStatusBar: The FXStatusBar instance associated with this window.

        Note:
            Overrides the base class method.
        """

        return self.status_bar

    def setCentralWidget(self, widget: QWidget) -> None:
        """Override the QMainWindow's setCentralWidget method.

        Ensures that the status line is always at the bottom of the window
        and the banner is always at the top.

        Args:
            widget: The widget to set as the central widget.

        Note:
            Overrides the base class method.
        """

        # Create a new QWidget to hold the banner, widget, and the status line
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add the banner first (top)
        if hasattr(self, "banner") and self.banner is not None:
            layout.addWidget(self.banner)

        # Add the widget to the new layout
        layout.addWidget(widget)

        # Add the status line last (bottom)
        if hasattr(self, "status_line") and self.status_line is not None:
            layout.addWidget(self.status_line)

        # Call the parent's setCentralWidget method with the new central widget
        super().setCentralWidget(central_widget)

    def setWindowTitle(self, title: str) -> None:
        """Override the setWindowTitle method.

        Args:
            title: The new window title.
        """
        title = f"{title if title else 'Window'}"
        super().setWindowTitle(title)

    # Banner methods
    def set_banner_text(self, text: str) -> None:
        """Sets the text of the banner.

        Args:
            text: The text to set in the banner.
        """
        self.banner_label.setText(text)

    def set_banner_icon(
        self, icon: Optional[Union[QIcon, str]], size: int = 20
    ) -> None:
        """Sets the icon of the banner.

        Args:
            icon: The icon to set in the banner. Can be a QIcon or an icon
                name string for theme-aware icons.
            size: The size of the icon. Defaults to 20.

        Note:
            Using an icon name string (e.g., "widgets") is recommended for
            theme-aware icons that automatically update when the theme changes.
        """
        self._banner_icon_size = size
        self.banner_icon.setFixedSize(size, size)

        if isinstance(icon, str):
            # Store icon name for theme-aware updates
            self._banner_icon_name = icon
            self._update_banner_icon()
        else:
            # Direct QIcon - not theme-aware
            self._banner_icon_name = None
            self.banner_icon.setPixmap(icon.pixmap(size, size))

        self.banner_icon.show()

    def _update_banner_icon(self) -> None:
        """Update the banner icon with current theme colors.

        Warning:
            This method is intended for internal use only.
        """
        if self._banner_icon_name is None:
            return

        icon = fxicons.get_icon(self._banner_icon_name)
        size = self._banner_icon_size
        self.banner_icon.setPixmap(icon.pixmap(size, size))

    def hide_banner(self) -> None:
        """Hides the banner."""
        self.banner.hide()

    def show_banner(self) -> None:
        """Shows the banner."""
        self.banner.show()

    # Status line methods
    def set_status_line_colors(self, color_a: str, color_b: str) -> None:
        """Set the colors of the status line.

        Args:
            color_a: The first color of the gradient.
            color_b: The second color of the gradient.
        """
        self.status_bar.set_status_line_colors(color_a, color_b)

    def hide_status_line(self) -> None:
        """Hides the status line."""
        self.status_bar.hide_status_line()

    def show_status_line(self) -> None:
        """Shows the status line."""
        self.status_bar.show_status_line()

    # UI file methods
    def set_ui_file(self, ui_file: str) -> None:
        """Sets the UI file and loads the UI.

        Args:
            ui_file: Path to the UI file to load.
        """
        self.ui_file = ui_file
        self._load_ui()

    # Status bar label methods
    def set_project_label(self, project: str) -> None:
        """Sets the project label in the status bar.

        Args:
            project: The project name.
        """
        self.statusBar().project_label.setText(project)

    def set_company_label(self, company: str) -> None:
        """Sets the company label in the status bar.

        Args:
            company: The company name.
        """
        self.statusBar().company_label.setText(company)

    def set_version_label(self, version: str) -> None:
        """Sets the version label in the status bar.

        Args:
            version: The version string.
        """
        self.statusBar().version_label.setText(version)

    # Events
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle the window close event.

        Args:
            event (QCloseEvent): The close event.
        """
        self.setParent(None)
        super().closeEvent(event)


def example() -> None:
    import sys
    from fxgui.fxwidgets import FXApplication

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXMainWindow Demo")

    window.resize(550, 500)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
