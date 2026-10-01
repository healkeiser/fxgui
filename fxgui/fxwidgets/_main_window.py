"""Custom main window widget."""

# Built-in
import os
from typing import Dict, Optional, Tuple, Union
from urllib.parse import urlparse
from webbrowser import open_new_tab

# Third-party
from qtpy.QtCore import QEvent, QObject, QSize, Qt
from qtpy.QtGui import QAction, QIcon, QStatusTipEvent
from qtpy.QtWidgets import (
    QActionGroup,
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QToolBar,
    QWidget,
)

from fxgui import fxconstants, fxicons, fxstyle, fxutils
from fxgui.fxwidgets._status_bar import FXStatusBar
from fxgui.fxwidgets._labels import FXIconLabel

# fxgui's menus, found on whichever menu bar the window has by these names.
_MENU_NAMES = {
    "main_menu": "fxMainMenu",
    "window_menu": "fxWindowMenu",
    "theme_menu": "fxThemeMenu",
    "help_menu": "fxHelpMenu",
}


class FXCommandRow(QToolBar):
    """A toolbar fixed in place: no handle, no floating, nothing to hide it.

    Its margins and spacing hold through style and theme changes, which
    otherwise reset a toolbar's layout to the style's own.

    Args:
        title: The toolbar's window title. Defaults to "Command row".
        parent: Parent widget. Defaults to `None`.
        margins: Left, top, right and bottom, in pixels. Defaults to the
            style's own.
        spacing: Between controls, in pixels. Defaults to the style's own.
        icon_size: The side of its tool button icons. Defaults to 17.

    Examples:
        >>> row = FXCommandRow(margins=(6, 6, 6, 0), spacing=6)
        >>> window.addToolBar(Qt.TopToolBarArea, row)
    """

    def __init__(
        self,
        title: str = "Command row",
        parent: Optional[QWidget] = None,
        margins: Optional[Tuple[int, int, int, int]] = None,
        spacing: Optional[int] = None,
        icon_size: int = 17,
    ):
        super().__init__(title, parent)
        self.setObjectName("fxCommandRow")
        self._margins = margins
        self._spacing = spacing
        self.setMovable(False)
        self.setFloatable(False)
        # The menu bar's right-click would offer to hide it.
        self.toggleViewAction().setVisible(False)
        self.setIconSize(QSize(icon_size, icon_size))
        self._fit()

    def changeEvent(self, event: QEvent) -> None:
        """Put the margins back after a style change resets them."""
        super().changeEvent(event)
        if event.type() == QEvent.StyleChange:
            self._fit()

    def _fit(self) -> None:
        layout = self.layout()
        if self._margins is not None:
            left, top, right, bottom = self._margins
            # Qt's toolbar layout places the first control at (its top
            # margin, its left margin) but sizes by left + right and top +
            # bottom, in either orientation. A side short of 0 stays at 0.
            layout.setContentsMargins(
                top,
                left,
                max(left + right - top, 0),
                max(top + bottom - left, 0),
            )
        if self._spacing is not None:
            layout.setSpacing(self._spacing)


class FXMainWindow(QMainWindow):
    """Customized QMainWindow class.

    The window's icon and name sit at the menu bar's right end, in
    `title_corner`; `set_banner_text` and `set_banner_icon` change them.
    The project, version and company live on the status bar's items, which
    the About dialog reads.

    Args:
        parent: Parent widget. Defaults to `None`.
        icon: The window's icon: a path to an image, or a `QIcon`. With
            neither, an icon already set on the running `QApplication` is
            left in place and fxgui's own logo is used only if there is
            none. Defaults to `None`.
        title: Title of the window, and the name in the menu bar corner.
            Defaults to `None`.
        size: Window size as width and height. Defaults to 500 x 600.
        documentation: URL the Help menu's Documentation opens; the entry
            is disabled without a valid one. Defaults to `None`.
        project: The status bar's project. Defaults to `None`, hidden.
        version: The status bar's version. Defaults to `None`, hidden.
        company: The status bar's company. Defaults to `None`, hidden.
        ui_file: A Designer file loaded as the central widget, kept as
            `ui`. Defaults to `None`.
        fit_to_contents: Whether to grow to the layout's own `sizeHint`
            on first show, grow-only and bounded by the screen. Defaults
            to `False`.
        framed: Whether to draw the window as a frame around its panes.
            The menu bar, toolbars, status bar and the window behind the
            central widget paint the theme's ``frame`` color with no lines
            between them, even for bars set later. Icon-only push buttons
            on those bands go flat (``fxRole="flat"``) unless they carry a
            role already. Mark bands of your own with
            `fxstyle.mark_as_frame`. Defaults to `False`.

    Attributes:
        title_corner (QWidget): The widget at the menu bar's right end
            holding `banner_icon` and `banner_label`.
        main_menu, window_menu, theme_menu, help_menu (QMenu): fxgui's
            menus on the current menu bar, or `None` with none.
        refresh_action (QAction): Ctrl+Alt+R, on no menu; an application
            adds it where its refresh belongs.
    """

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
        fit_to_contents: bool = False,
        framed: bool = False,
    ):
        super().__init__(parent)
        self._framed: bool = framed
        self._fit_to_contents: bool = fit_to_contents
        self._fitted: bool = False
        self._documentation: Optional[str] = None
        self.ui: Optional[QWidget] = None
        self.theme_actions: Dict[str, QAction] = {}

        self._create_actions()
        self._create_title_corner(title)
        if ui_file is not None:
            self.ui = fxutils.load_ui(self, ui_file)
            self.setCentralWidget(self.ui)
        self.setWindowTitle(title)
        self._set_window_icon(icon)
        self.resize(QSize(*size) if size else QSize(500, 600))
        self._adopt_menu_bar(self.menuBar())
        self.setStatusBar(
            FXStatusBar(
                parent=self,
                project=project,
                version=version,
                company=company,
            )
        )
        self.set_documentation(documentation)
        if framed:
            fxstyle.mark_as_frame(self)

        # A themed root; fxstyle skips it under a themed application.
        fxstyle.register_themed_root(self)
        fxstyle.theme_changed.connect(self._on_theme_changed)

    # Private methods
    def _set_window_icon(self, icon: Optional[Union[str, QIcon]]) -> None:
        """Set the window icon: a `QIcon`, a path, the app's, or fxgui's logo.

        Warning:
            This method is intended for internal use only.
        """
        if isinstance(icon, QIcon):
            self.setWindowIcon(icon)
            return
        if icon and os.path.isfile(icon):
            self.setWindowIcon(QIcon(icon))
            return
        # The application's own mark wins over fxgui's logo.
        application = QApplication.instance()
        if application is not None and not application.windowIcon().isNull():
            return
        self.setWindowIcon(QIcon(str(
            fxconstants.IMAGES_ROOT / "fxgui_logo_background_dark.svg")))

    def showEvent(self, event) -> None:
        """Grow once to the layout's own size, if this window asked to.

        Grow-only, so a larger requested size stays, and once, so a window
        dragged smaller is not pushed back out. Bounded by the screen the
        window is on.
        """
        super().showEvent(event)
        if not self._fit_to_contents or self._fitted:
            return
        self._fitted = True
        wanted = self.sizeHint().boundedTo(
            self.screen().availableGeometry().size())
        self.resize(self.size().expandedTo(wanted))

    def _create_actions(self) -> None:
        """Create the actions for the window.

        Warning:
            This method is intended for internal use only.
        """
        self.about_action = fxutils.create_action(
            self, "About", trigger=self._show_about_dialog, icon_name="help")
        self.close_action = fxutils.create_action(
            self,
            "Close",
            trigger=self.close,
            shortcut="Ctrl+Alt+q",
            icon_name="close",
        )
        self.window_on_top_action = fxutils.create_action(
            self,
            "Always on Top",
            trigger=self._toggle_window_on_top,
            shortcut="Ctrl+Shift+t",
            checkable=True,
            icon_name="hdr_strong",
        )
        self.minimize_window_action = fxutils.create_action(
            self,
            "Minimize",
            trigger=self.showMinimized,
            shortcut="Ctrl+Alt+m",
            icon_name="minimize",
        )
        self.maximize_window_action = fxutils.create_action(
            self,
            "Maximize",
            trigger=self.showMaximized,
            shortcut="Ctrl+Alt+f",
            icon_name="maximize",
        )

        group = QActionGroup(self)
        group.setExclusive(True)
        for theme_name in fxstyle.get_available_themes():
            action = fxutils.create_action(
                self,
                theme_name.title().replace("_", " "),
                trigger=lambda _=False, t=theme_name: fxstyle.apply_theme(t),
                checkable=True,
            )
            action.setChecked(theme_name == fxstyle.get_theme())
            group.addAction(action)
            self.theme_actions[theme_name] = action

        self.open_documentation_action = fxutils.create_action(
            self,
            "Documentation",
            trigger=self._open_documentation,
            icon_name="menu_book",
        )
        self.refresh_action = fxutils.create_action(
            self, "Refresh", shortcut="Ctrl+Alt+r", icon_name="refresh")

    def _create_menus(self, bar: QMenuBar) -> None:
        """Build fxgui's File, Window and Help menus on `bar`.

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
        main_menu.addAction(self.close_action)
        bar.addMenu(main_menu)

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

    def _create_title_corner(self, title: Optional[str]) -> None:
        """Build the icon and name that sit at the menu bar's right end.

        Warning:
            This method is intended for internal use only.
        """
        self.title_corner = QWidget(self)
        self.title_corner.setObjectName("fxMenuBarCorner")
        layout = QHBoxLayout(self.title_corner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.banner_icon = FXIconLabel(parent=self.title_corner)
        self.banner_icon.setFixedSize(16, 16)
        self.banner_icon.hide()
        # Takes the menu bar's own font and color from the theme sheet.
        self.banner_label = QLabel(title or "", self.title_corner)
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

    def add_corner_widget(self, widget: QWidget) -> None:
        """Add `widget` to the menu bar corner, left of the icon and name.

        The corner is placed again whenever `widget` grows or shrinks.
        """
        layout = self.title_corner.layout()
        layout.insertWidget(layout.indexOf(self.banner_icon), widget)
        widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Fit the corner to the bar, re-place it, and flatten framed bands."""
        kind = event.type()
        if kind == QEvent.Resize and watched is self._current_menu_bar():
            self._fit_title_corner()
        elif kind == QEvent.LayoutRequest:
            if (
                isinstance(watched, QWidget)
                and watched.parentWidget() is self.title_corner
                and self.title_corner.isVisible()
            ):
                # QMenuBar places a corner widget only as it shows, so a
                # tool added later would fall into the overflow menu.
                self.title_corner.hide()
                self.title_corner.show()
            if self._framed and self._is_band(watched):
                self._flatten_icon_buttons(watched)
        return super().eventFilter(watched, event)

    def _is_band(self, widget: QObject) -> bool:
        """Return whether `widget` is a bar of this window's frame.

        Warning:
            This method is intended for internal use only.
        """
        return isinstance(widget, (QToolBar, QStatusBar, QMenuBar)) and (
            widget.parent() is self)

    @staticmethod
    def _flatten_icon_buttons(band: QWidget) -> None:
        """Give `band`'s icon-only push buttons without a role the flat one.

        Warning:
            This method is intended for internal use only.
        """
        for button in band.findChildren(QPushButton):
            if (
                not button.text()
                and not button.icon().isNull()
                and button.property("fxRole") is None
            ):
                button.setProperty("fxRole", "flat")
                fxutils.repolish(button)

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

    def _about_text(self) -> str:
        """Return the About dialog's lines: the title, then the bar's items.

        Warning:
            This method is intended for internal use only.
        """
        lines = [self.windowTitle()]
        bar = self.statusBar()
        if isinstance(bar, FXStatusBar):
            lines += [
                item.text()
                for item in (
                    bar.project_label, bar.version_label, bar.company_label)
            ]
        return "\n".join(line for line in lines if line)

    def _show_about_dialog(self) -> None:
        """Show the About dialog.

        Warning:
            This method is intended for internal use only.
        """
        QMessageBox.about(self, "About", self._about_text())

    def _open_documentation(self, _=False) -> None:
        open_new_tab(self._documentation)

    def _toggle_window_on_top(self) -> None:
        """Keep the window above the others while the action is checked.

        Warning:
            This method is intended for internal use only.
        """
        self.setWindowFlag(
            Qt.WindowStaysOnTopHint, self.window_on_top_action.isChecked())
        self.show()

    def _on_theme_changed(self) -> None:
        """Refit the corner and check the theme in force; override to extend.

        Warning:
            This method is intended for internal use only.
        """
        # A theme may change the menu font, and with it the first title.
        self._fit_title_corner()
        action = self.theme_actions.get(fxstyle.get_theme())
        if action is not None:
            action.setChecked(True)

    # Public methods
    def documentation(self) -> Optional[str]:
        """Return the URL Help > Documentation opens, or `None`."""
        return self._documentation

    def set_documentation(self, url: Optional[str]) -> None:
        """Set the URL Help > Documentation opens; no valid URL disables it."""
        self._documentation = url
        self.open_documentation_action.setEnabled(_is_valid_url(url))

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

    def event(self, event: QEvent) -> bool:
        """Route status tips after the items; watch a framed window's bands."""
        if (
            event.type() == QEvent.ChildPolished
            and getattr(self, "_framed", False)
            and self._is_band(event.child())
        ):
            band = event.child()
            band.installEventFilter(self)
            self._flatten_icon_buttons(band)
        if isinstance(event, QStatusTipEvent):
            bar = self.statusBar()
            if isinstance(bar, FXStatusBar):
                bar.show_tip(event.tip())
                return True
        return super().event(event)

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
            self.banner_icon.setFixedSize(size, size)
            self.banner_icon.setIconSize(QSize(size, size))
        if isinstance(icon, str):
            icon = fxicons.get_icon(icon)
        self.banner_icon.setIcon(icon)
        self.banner_icon.show()


def _is_valid_url(url: Optional[str]) -> bool:
    """Return whether `url` has a scheme and a host."""
    if not url:
        return False
    try:
        result = urlparse(url)
    except ValueError:
        # An unclosed IPv6 bracket, such as "http://[".
        return False
    return bool(result.scheme and result.netloc)
