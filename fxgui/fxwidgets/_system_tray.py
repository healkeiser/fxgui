"""System tray icon widget."""

# Built-in
from typing import Optional, Union

# Third-party
from qtpy.QtCore import QObject
from qtpy.QtGui import QCursor, QIcon
from qtpy.QtWidgets import QApplication, QMenu, QSystemTrayIcon

# Internal
from fxgui import fxconstants, fxstyle, fxutils
from fxgui.fxwidgets._application import FXApplication


class FXSystemTray(QSystemTrayIcon):
    """A tray icon whose menu opens on a left click too, ending in Quit.

    Args:
        parent: The parent object. Defaults to `None`.
        icon: The tray icon: a path to an image, or a `QIcon`. Defaults to
            fxgui's own logo.

    Attributes:
        quit_action (QAction): Quits an `FXApplication`; a DCC host keeps
            running.

    Examples:
        >>> app = FXApplication()
        >>> tray = FXSystemTray()
        >>> menu = tray.contextMenu()
        >>> menu.insertAction(tray.quit_action, QAction("Set Project", menu))
        >>> tray.show()
        >>> app.exec()
    """

    def __init__(
        self,
        parent: Optional[QObject] = None,
        icon: Optional[Union[str, QIcon]] = None,
    ):
        super().__init__(
            QIcon(icon or str(fxconstants.IMAGES_ROOT / "fxgui_logo_light.svg")),
            parent,
        )
        self.quit_action = fxutils.create_action(
            self, "Quit", trigger=self.quit, icon_name="close")
        # Held here: the tray does not own the menu it is given.
        self._menu = QMenu()
        self._menu.addAction(self.quit_action)
        self.setContextMenu(self._menu)
        # A parentless menu under a DCC host gets no application sheet.
        fxstyle.register_themed_root(self._menu)
        self.activated.connect(self._on_tray_icon_activated)

    def _on_tray_icon_activated(self, reason) -> None:
        """Open the menu at the cursor on a left click; Qt keeps it on screen."""
        if reason == QSystemTrayIcon.Trigger:
            self.contextMenu().exec_(QCursor.pos())

    def quit(self) -> None:
        """Quit the application, unless it is a host fxgui does not own."""
        application = QApplication.instance()
        if isinstance(application, FXApplication):
            application.quit()
