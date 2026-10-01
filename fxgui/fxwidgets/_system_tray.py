"""System tray icon widget."""

# Built-in
from pathlib import Path

# Third-party
from qtpy.QtCore import QObject
from qtpy.QtGui import QCursor, QIcon
from qtpy.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QSystemTrayIcon,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._application import FXApplication


class FXSystemTray(QObject):
    """A system tray icon with a context menu.

    Args:
        parent (QWidget, optional): The parent widget. Defaults to None.
        icon (str or QIcon, optional): The tray icon: a path to an image,
            or a `QIcon` for an application whose mark comes out of an
            icon set rather than off disk -- `fxicons.get_icon` returns
            one, and a path was the only shape this took. Defaults to
            None, which is fxgui's own logo.

    Attributes:
        tray_icon (QSystemTrayIcon): The system tray icon.
        quit_action (QAction): The action to quit the application.
        tray_menu (QMenu): The tray menu.

    Methods:
        show: Shows the system tray icon.
        on_tray_icon_activated: Opens the tray menu at the cursor.
        closeEvent: Quits an FXApplication; a DCC host keeps running.

    Examples:
        >>> app = FXApplication()
        >>> system_tray = FXSystemTray()
        >>> hello_action = QAction(
        ...     fxicons.get_icon("visibility"), "Set Project", system_tray
        ... )
        >>> system_tray.tray_menu.insertAction(
        ...     system_tray.quit_action, hello_action
        ... )
        >>> system_tray.tray_menu.insertSeparator(system_tray.quit_action)
        >>> system_tray.show()
        >>> app.exec_()

    Note:
        Inherits from QObject, not QSystemTrayIcon.
    """

    def __init__(self, parent=None, icon=None):
        super().__init__(parent)

        self.icon = (
            icon
            or (
                Path(__file__).parent.parent / "images" / "fxgui_logo_light.svg"
            ).as_posix()
        )
        # A `QIcon` is passed through rather than round-tripped. Measured:
        # `QIcon(QIcon)` is Qt's own copy constructor, so the previous
        # expression already accepted one -- the signature above is
        # widening a documented promise to match behaviour that was
        # always there, not repairing a break.
        self.tray_icon = QSystemTrayIcon(
            self.icon if isinstance(self.icon, QIcon) else QIcon(self.icon),
            parent,
        )

        # Methods
        self._create_actions()
        self._create_menu()
        self._handle_connections()

    # Private methods
    def _create_actions(self) -> None:
        """Creates the actions for the window.

        Warning:
            This method is intended for internal use only.
        """

        # Main menu
        self.quit_action = fxutils.create_action(
            self,
            "Quit",
            fxicons.get_icon("close"),
            self.closeEvent,
            enable=True,
            visible=True,
        )

    def _create_menu(self) -> None:
        self.tray_menu = QMenu(self.parent())
        self.tray_menu.addAction(self.quit_action)

        # A parentless menu under a DCC host gets no application sheet.
        if not isinstance(QApplication.instance(), FXApplication):
            fxstyle.register_themed_root(self.tray_menu)

    def _handle_connections(self) -> None:
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

    def _on_tray_icon_activated(self, reason) -> None:
        """Open the menu at the cursor on a left click; Qt keeps it on screen."""
        if reason == QSystemTrayIcon.Trigger:
            self.tray_menu.exec_(QCursor.pos())

    # Public methods
    def add_action(self, action: QAction) -> None:
        """Adds an action to the tray menu.

        Args:
            action: The action to add to the tray menu.
        """

        self.tray_menu.addAction(action)

    def set_icon(self, icon_path: str) -> None:
        """Sets a new icon for the system tray.

        Args:
            icon_path: The path to the new icon.
        """

        self.icon = icon_path
        self.tray_icon.setIcon(QIcon(self.icon))

    def show(self):
        """Shows the system tray icon."""

        self.tray_icon.show()

    # Events
    def closeEvent(self, _) -> None:
        """Quit the application, unless it is a host fxgui does not own."""
        application = QApplication.instance()
        if isinstance(application, FXApplication):
            application.quit()
