"""Custom main window widget."""

# Built-in
import os
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
from webbrowser import open_new_tab

# Third-party
from qtpy.QtCore import QEvent, QObject, QSize, Qt
from qtpy.QtGui import QAction, QIcon
from qtpy.QtWidgets import (
    QActionGroup,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

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

# fxgui's menus, found on whichever menu bar the window has by these names.
_MENU_NAMES = {
    "main_menu": "fxMainMenu",
    "edit_menu": "fxEditMenu",
    "window_menu": "fxWindowMenu",
    "theme_menu": "fxThemeMenu",
    "help_menu": "fxHelpMenu",
}


class FXMainWindow(QMainWindow):
    """Customized QMainWindow class.

    The window's icon and name sit at the menu bar's right end, in
    `title_corner`; `set_banner_text` and `set_banner_icon` change them.
    `setCentralWidget` and `centralWidget` are Qt's own.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (str or QIcon, optional): The window's icon: a path to an
            image, or a `QIcon`. With neither, an icon already set on the
            running `QApplication` is left in place and fxgui's own logo is
            used only if there is none. Defaults to `None`.
        title (str, optional): Title of the window, and the name in the
            menu bar corner. Defaults to `None`.
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
        rich_tooltips (bool, optional): Whether to install the global
            FXTooltipManager, which replaces Qt tooltips application-wide
            with FXTooltip. `None` (default) and `False` both leave Qt's
            own tooltips, styled by the `QToolTip` rule and formatted by
            `fxwidgets.apply_tip`. Defaults to `None`.
        toolbar (bool, optional): Whether to build the window's toolbar.
            `False` leaves `self.toolbar` as `None`; a hidden toolbar would
            come back through the menu bar's right-click "Toolbars" entry.
            Defaults to `True`.
        fit_to_contents (bool, optional): Whether to grow to the
            layout's own `sizeHint` on first show, grow-only and
            bounded by the screen. Defaults to `False`.
        framed (bool, optional): Whether to draw the window as a frame
            around its panes. The menu bar, toolbars, status bar and the
            window behind the central widget paint the theme's ``frame``
            color with no lines between them, even for bars set later.
            Mark bands of your own with `fxstyle.mark_as_frame`.
            Defaults to `False`.

    Attributes:
        title_corner (QWidget): The widget at the menu bar's right end
            holding `banner_icon` and `banner_label`.
        main_menu, edit_menu, window_menu, theme_menu, help_menu (QMenu):
            fxgui's menus on the current menu bar, or `None` with none.
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
        icon: Optional[Union[str, QIcon]] = None,
        title: Optional[str] = None,
        size: Optional[Tuple[int, int]] = None,
        documentation: Optional[str] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        ui_file: Optional[str] = None,
        set_stylesheet: bool = True,
        rich_tooltips: Optional[bool] = None,
        toolbar: bool = True,
        fit_to_contents: bool = False,
        framed: bool = False,
    ):
        super().__init__(parent)
        self._framed: bool = framed

        # Private attributes
        self._default_icon_path: str = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "images",
            "fxgui_logo_background_dark.svg",
        )
        self._set_stylesheet: bool = set_stylesheet

        self._fit_to_contents: bool = fit_to_contents
        self._fitted: bool = False

        # Public attributes
        self.window_icon: Optional[Union[str, QIcon]] = icon
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
        self._banner_icon_size: int = 16

        # Initialize UI components
        self._create_actions()
        self._create_title_corner()
        self._load_ui()
        self.setWindowTitle(self.window_title)
        self._set_window_icon()
        self._set_window_size()
        self._adopt_menu_bar(self.menuBar())
        if toolbar:
            self._create_toolbars()
        else:
            self.toolbar = None
        self.setStatusBar(
            FXStatusBar(
                parent=self,
                project=self.project,
                version=self.version,
                company=self.company,
            )
        )
        self._check_documentation()
        if framed:
            fxstyle.mark_as_frame(self)

        # A themed root, standalone or inside a DCC host.
        if self._set_stylesheet:
            fxstyle.register_themed_root(self)
        fxstyle.theme_changed.connect(self._theme_switched)

        # Opt-in: the manager filters every tooltip in the application,
        # a DCC host's included.
        if rich_tooltips:
            FXTooltipManager.install()

    # Private methods
    def _load_ui(self) -> None:
        """Load the UI file, if any, as the central widget.

        Warning:
            This method is intended for internal use only.
        """
        if self.ui_file is not None:
            self.ui = fxutils.load_ui(self, self.ui_file)
            self.setCentralWidget(self.ui)

    def _set_window_icon(self) -> None:
        """Set the window icon: a `QIcon`, a path, the app's, or fxgui's logo.

        Warning:
            This method is intended for internal use only.
        """
        if isinstance(self.window_icon, QIcon):
            self.setWindowIcon(self.window_icon)
            return
        if self.window_icon and os.path.isfile(self.window_icon):
            self.setWindowIcon(QIcon(self.window_icon))
            return
        # The application's own mark wins over fxgui's logo.
        application = QApplication.instance()
        if application is not None and not application.windowIcon().isNull():
            return
        self.setWindowIcon(QIcon(self._default_icon_path))

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

    def showEvent(self, event) -> None:
        """Grow once to the layout's own size, if this window asked to.

        Grow-only, so a larger requested size stays, and once, so a window
        dragged smaller is not pushed back out. Bounded by the screen the
        window is on, read from its `QWindow`, which every Qt 5 and 6 has;
        `QWidget.screen()` needs Qt 5.14.
        """
        super().showEvent(event)
        if not self._fit_to_contents or self._fitted:
            return
        self._fitted = True
        handle = self.windowHandle()
        screen = handle.screen() if handle else QApplication.primaryScreen()
        wanted = self.sizeHint().boundedTo(screen.availableGeometry().size())
        self.resize(self.size().expandedTo(wanted))

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
            trigger=self.toggle_theme,
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
                lambda checked, t=theme_name: self.set_theme(t),
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


    def _create_menus(self, bar: QMenuBar) -> None:
        """Build fxgui's File, Edit, Window and Help menus on `bar`.

        Warning:
            This method is intended for internal use only.
        """
        bar.setNativeMenuBar(False)  # Mostly for macOS

        def menu(label: str, name: str, parent: QWidget) -> QMenu:
            built = QMenu(label, parent)
            built.setObjectName(name)
            return built

        main_menu = menu("File", _MENU_NAMES["main_menu"], bar)
        main_menu.addAction(self.about_action)
        main_menu.addSeparator()
        main_menu.addAction(self.check_updates_action)
        main_menu.addSeparator()
        main_menu.addAction(self.hide_action)
        main_menu.addAction(self.hide_others_action)
        main_menu.addSeparator()
        main_menu.addAction(self.close_action)
        bar.addMenu(main_menu)

        edit_menu = menu("Edit", _MENU_NAMES["edit_menu"], bar)
        edit_menu.addAction(self.settings_action)
        bar.addMenu(edit_menu)

        window_menu = menu("Window", _MENU_NAMES["window_menu"], bar)
        window_menu.addAction(self.minimize_window_action)
        window_menu.addAction(self.maximize_window_action)
        window_menu.addSeparator()
        window_menu.addAction(self.window_on_top_action)
        window_menu.addSeparator()
        theme_menu = menu("Theme", _MENU_NAMES["theme_menu"], window_menu)
        fxicons.set_icon(theme_menu, "brightness_4")
        for action in self.theme_actions.values():
            theme_menu.addAction(action)
        window_menu.addMenu(theme_menu)
        bar.addMenu(window_menu)

        help_menu = menu("Help", _MENU_NAMES["help_menu"], bar)
        help_menu.addAction(self.open_documentation_action)
        bar.addMenu(help_menu)

    def _create_toolbars(self) -> None:
        """Creates the toolbar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setIconSize(QSize(17, 17))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.addAction(self.home_action)
        self.toolbar.addAction(self.previous_action)
        self.toolbar.addAction(self.next_action)
        self.toolbar.addAction(self.refresh_action)
        self.toolbar.setMovable(True)

    def _create_title_corner(self) -> None:
        """Build the icon and name that sit at the menu bar's right end.

        Warning:
            This method is intended for internal use only.
        """
        self.title_corner = QWidget(self)
        self.title_corner.setObjectName("fxMenuBarCorner")
        layout = QHBoxLayout(self.title_corner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.banner_icon = QLabel(self.title_corner)
        self.banner_icon.setFixedSize(16, 16)
        self.banner_icon.hide()
        # Takes the menu bar's own font and color from the theme sheet.
        self.banner_label = QLabel(self.window_title or "", self.title_corner)
        self.banner_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.banner_icon)
        layout.addWidget(self.banner_label)
        self._corner_hidden = False

    def _current_menu_bar(self) -> Optional[QMenuBar]:
        """Return the menu bar the window holds, without creating one.

        Warning:
            This method is intended for internal use only.
        """
        bar = self.layout().menuBar() if self.layout() else None
        return bar if isinstance(bar, QMenuBar) else None

    def _adopt_menu_bar(self, bar: QMenuBar) -> None:
        """Give `bar` fxgui's menus, the title corner, and the frame.

        Warning:
            This method is intended for internal use only.
        """
        self._create_menus(bar)
        bar.setCornerWidget(self.title_corner, Qt.TopRightCorner)
        self.title_corner.setVisible(not self._corner_hidden)
        # QMenuBar pins a corner widget to its top at its own height; as
        # tall as the bar, the name centres on the menu titles.
        bar.installEventFilter(self)
        self._fit_title_corner()
        if self._framed:
            fxstyle.mark_as_frame(bar)

    def _menu(self, key: str) -> Optional[QMenu]:
        """Return fxgui's menu `key` on the current menu bar, or `None`.

        Warning:
            This method is intended for internal use only.
        """
        bar = self._current_menu_bar()
        return bar.findChild(QMenu, _MENU_NAMES[key]) if bar else None

    @property
    def main_menu(self) -> Optional[QMenu]:
        """The File menu on the current menu bar."""
        return self._menu("main_menu")

    @property
    def edit_menu(self) -> Optional[QMenu]:
        """The Edit menu on the current menu bar."""
        return self._menu("edit_menu")

    @property
    def window_menu(self) -> Optional[QMenu]:
        """The Window menu on the current menu bar."""
        return self._menu("window_menu")

    @property
    def theme_menu(self) -> Optional[QMenu]:
        """The Window menu's Theme submenu."""
        return self._menu("theme_menu")

    @property
    def help_menu(self) -> Optional[QMenu]:
        """The Help menu on the current menu bar."""
        return self._menu("help_menu")

    @property
    def menu_bar(self) -> QMenuBar:
        """The window's menu bar, as `menuBar()` returns it."""
        return self.menuBar()

    @property
    def status_bar(self) -> QStatusBar:
        """The window's status bar, as `statusBar()` returns it."""
        return self.statusBar()

    def use_corner_title(self) -> None:
        """Do nothing: every window shows its name in the menu bar corner."""

    def add_corner_widget(self, widget: QWidget) -> None:
        """Add `widget` to the menu bar corner, left of the icon and name."""
        layout = self.title_corner.layout()
        layout.insertWidget(layout.indexOf(self.banner_icon), widget)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Fit the menu bar corner to the bar as the bar resizes."""
        if (
            event.type() == QEvent.Resize
            and watched is self._current_menu_bar()
        ):
            self._fit_title_corner()
        return super().eventFilter(watched, event)

    def _fit_title_corner(self) -> None:
        """Size the corner as tall as the bar, inset like the first menu.

        Warning:
            This method is intended for internal use only.
        """
        bar = self._current_menu_bar()
        if bar is None:
            return
        self.title_corner.setFixedHeight(bar.height())
        # The name ends as far from the right edge as the first menu's
        # title starts from the left one.
        actions = [action for action in bar.actions() if action.isVisible()]
        if not actions:
            return
        item = bar.actionGeometry(actions[0])
        title = actions[0].text().replace("&", "")
        inset = item.left() + (
            item.width() - bar.fontMetrics().horizontalAdvance(title)) // 2
        self.title_corner.layout().setContentsMargins(0, 0, max(inset, 0), 0)

    def _show_about_dialog(self) -> None:
        """Shows the "About" dialog.

        Warning:
            This method is intended for internal use only.
        """

        # If the dialog already exists and is open, close it
        if getattr(self, "about_dialog", None) is not None:
            self.about_dialog.close()

        self.about_dialog = QDialog(self)
        self.about_dialog.setWindowTitle("About")

        layout = QVBoxLayout()
        layout.addStretch()
        for text in (self.project, self.version, self.company):
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
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

    def _is_valid_url(self, url: str) -> bool:
        """Checks if the specified URL is valid.

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
        """Enable the documentation action only for a valid URL.

        Warning:
            This method is intended for internal use only.
        """

        self.open_documentation_action.setEnabled(
            self._is_valid_url(self.documentation)
        )

    def _theme_switched(self, _theme_name: str) -> None:
        """Call `_on_theme_changed` without the theme name."""
        self._on_theme_changed()

    def _on_theme_changed(self, _theme_name: Optional[str] = None) -> None:
        """Re-render theme-colored pixmaps; override to extend.

        Warning:
            This method is intended for internal use only.
        """
        self._update_banner_icon()
        # A theme may change the menu font, and with it the first title.
        self._fit_title_corner()
        bar = self._current_menu_bar()
        if bar is not None:
            bar.update()
        current_theme = fxstyle.get_theme()
        if current_theme in self.theme_actions:
            self.theme_actions[current_theme].setChecked(True)

    # Public methods
    def set_theme(self, theme: str) -> str:
        """Set the theme of every fxgui window, standalone or in a DCC.

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
        return fxstyle.apply_theme(theme)

    def toggle_theme(self) -> str:
        """Switch every fxgui window to the next available theme.

        Returns:
            str: The new theme that was applied.

        Examples:
            >>> window = FXMainWindow()
            >>> window.show()
            >>> new_theme = window.toggle_theme()
            >>> print(f"Switched to {new_theme} theme")
        """
        themes = fxstyle.get_available_themes()
        current = fxstyle.get_theme()
        index = themes.index(current) + 1 if current in themes else 0
        return fxstyle.apply_theme(themes[index % len(themes)])

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
        """Center the window on the primary screen's available area.

        Examples:
            >>> window = FXMainWindow()
            >>> window.resize(800, 600)
            >>> window.center_on_screen()
            >>> window.show()
        """
        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(
            QApplication.primaryScreen().availableGeometry().center()
        )
        self.move(frame_geo.topLeft())

    # Overrides
    def setStatusBar(self, status_bar: Optional[QStatusBar]) -> None:
        """Set the status bar; a framed window paints it in the frame.

        Note:
            Overrides the base class method.
        """
        super().setStatusBar(status_bar)
        if self._framed and status_bar is not None:
            fxstyle.mark_as_frame(status_bar)

    def setMenuBar(self, menu_bar: Optional[QMenuBar]) -> None:
        """Set the menu bar; it gets fxgui's menus, the corner and the frame.

        `None` removes the bar and fxgui's menus with it; the corner waits
        for the next bar.

        Note:
            Overrides the base class method.
        """
        old = self._current_menu_bar()
        if menu_bar is old:
            return
        if old is not None:
            # Qt deletes the old bar, and a corner left on it goes too.
            self._corner_hidden = self.title_corner.isHidden()
            old.setCornerWidget(None, Qt.TopRightCorner)
            self.title_corner.setParent(self)
            self.title_corner.hide()
        super().setMenuBar(menu_bar)
        if menu_bar is not None:
            self._adopt_menu_bar(menu_bar)

    def setWindowTitle(self, title: str) -> None:
        """Set the window title; `None` or empty reads "Window"."""
        super().setWindowTitle(title if title else "Window")

    # Banner methods
    def set_banner_text(self, text: str) -> None:
        """Set the name in the menu bar corner."""
        self.banner_label.setText(text)

    def set_banner_icon(
        self, icon: Optional[Union[QIcon, str]], size: Optional[int] = None
    ) -> None:
        """Set the icon in the menu bar corner.

        Args:
            icon: A QIcon, or an icon name, which follows theme switches.
            size: The size of the icon. Defaults to 16.
        """
        if size is not None:
            self._banner_icon_size = size
        size = self._banner_icon_size
        self.banner_icon.setFixedSize(size, size)

        if isinstance(icon, str):
            self._banner_icon_name = icon
            self._update_banner_icon()
        else:
            self._banner_icon_name = None
            self.banner_icon.setPixmap(icon.pixmap(size, size))

        self.banner_icon.show()

    def _update_banner_icon(self) -> None:
        """Re-render a named banner icon in the current theme's colors.

        Warning:
            This method is intended for internal use only.
        """
        if self._banner_icon_name is None:
            return

        icon = fxicons.get_icon(self._banner_icon_name)
        size = self._banner_icon_size
        self.banner_icon.setPixmap(icon.pixmap(size, size))

    # Status bar methods
    def _fx_status_bar(self) -> FXStatusBar:
        """Return the status bar, refusing one that is not an FXStatusBar.

        Raises:
            TypeError: The window's status bar is not an FXStatusBar.

        Warning:
            This method is intended for internal use only.
        """
        bar = self.statusBar()
        if not isinstance(bar, FXStatusBar):
            raise TypeError(
                f"the status bar is a {type(bar).__name__}, not an "
                "FXStatusBar; set one with setStatusBar()"
            )
        return bar

    def set_status_line_colors(self, color_a: str, color_b: str) -> None:
        """Paint the status line as a gradient from `color_a` to `color_b`.

        Raises:
            TypeError: The window's status bar is not an FXStatusBar.
        """
        self._fx_status_bar().set_status_line_colors(color_a, color_b)

    def hide_status_line(self) -> None:
        """Hide the status line; a plain QStatusBar has none to hide."""
        bar = self.statusBar()
        if isinstance(bar, FXStatusBar):
            bar.hide_status_line()

    def show_status_line(self) -> None:
        """Show the status line.

        Raises:
            TypeError: The window's status bar is not an FXStatusBar.
        """
        self._fx_status_bar().show_status_line()

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
        """Set the project label in the status bar.

        Raises:
            TypeError: The window's status bar is not an FXStatusBar.
        """
        self._fx_status_bar().project_label.setText(project)

    def set_company_label(self, company: str) -> None:
        """Set the company label in the status bar.

        Raises:
            TypeError: The window's status bar is not an FXStatusBar.
        """
        self._fx_status_bar().company_label.setText(company)

    def set_version_label(self, version: str) -> None:
        """Set the version label in the status bar.

        Raises:
            TypeError: The window's status bar is not an FXStatusBar.
        """
        self._fx_status_bar().version_label.setText(version)


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
