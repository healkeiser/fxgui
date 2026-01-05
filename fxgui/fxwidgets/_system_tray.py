"""System tray icon widget."""

# Built-in
from pathlib import Path

# Third-party
from qtpy.QtCore import QObject, QPoint, Slot
from qtpy.QtGui import QIcon
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
        icon (str, optional): The icon path. Defaults to None.

    Attributes:
        tray_icon (QSystemTrayIcon): The system tray icon.
        quit_action (QAction): The action to quit the application.
        tray_menu (QMenu): The tray menu.

    Methods:
        show: Shows the system tray icon.
        on_tray_icon_activated: Shows the tray menu above the taskbar.
        closeEvent: Closes the application.

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
        self.tray_icon = QSystemTrayIcon(QIcon(self.icon), parent)

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

        # Styling
        self.tray_menu.setStyleSheet(fxstyle.load_stylesheet())

    @Slot()
    def _handle_connections(self) -> None:
        # Right-click
        # self.tray_icon.setContextMenu(self.tray_menu)

        # Left-click
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

    @Slot()
    def _on_tray_icon_activated(self, reason):
        """Shows the tray menu at the cursor's position.

        Args:
            reason (QSystemTrayIcon.ActivationReason): The reason for the tray
                icon activation.
        """

        if reason == QSystemTrayIcon.Trigger:
            # Calculate taskbar position
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()
            available_geometry = screen.availableGeometry()
            tray_icon_geometry = self.tray_icon.geometry()

            # Calculate the center position of the tray icon
            tray_icon_center = tray_icon_geometry.center()

            menu_width = self.tray_menu.sizeHint().width()
            menu_height = self.tray_menu.sizeHint().height()

            margin = 20  # Margin between the taskbar and the system tray menu

            if available_geometry.y() > screen_geometry.y():
                # Taskbar is on the top
                pos = QPoint(
                    tray_icon_center.x() - menu_width / 2,
                    tray_icon_geometry.bottom() + margin,
                )
            elif available_geometry.x() > screen_geometry.x():
                # Taskbar is on the left
                pos = QPoint(
                    tray_icon_geometry.right() + margin,
                    tray_icon_center.y() - menu_height / 2,
                )
            elif available_geometry.height() < screen_geometry.height():
                # Taskbar is on the bottom
                pos = QPoint(
                    tray_icon_center.x() - menu_width / 2,
                    tray_icon_geometry.top() - menu_height - margin,
                )
            else:
                # Taskbar is on the right or default position
                pos = QPoint(
                    tray_icon_geometry.left() - menu_width - margin,
                    tray_icon_center.y() - menu_height / 2,
                )

            # Ensure the menu is completely visible
            if pos.x() < available_geometry.x():
                pos.setX(available_geometry.x())
            if pos.y() < available_geometry.y():
                pos.setY(available_geometry.y())
            if pos.x() + menu_width > available_geometry.right():
                pos.setX(available_geometry.right() - menu_width)
            if pos.y() + menu_height > available_geometry.bottom():
                pos.setY(available_geometry.bottom() - menu_height)

            self.tray_menu.exec_(pos)

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
        FXApplication.instance().quit()
        QApplication.instance().quit()
        self.setParent(None)


def example() -> None:
    import sys

    app = FXApplication(sys.argv)

    # Create system tray
    system_tray = FXSystemTray()

    # Add custom actions
    hello_action = QAction(
        fxicons.get_icon("visibility"), "Show Notification", system_tray
    )
    hello_action.triggered.connect(
        lambda: system_tray.tray_icon.showMessage(
            "Hello", "This is a system tray notification!"
        )
    )

    settings_action = QAction(
        fxicons.get_icon("settings"), "Settings", system_tray
    )

    # Insert actions before the quit action
    system_tray.tray_menu.insertAction(system_tray.quit_action, hello_action)
    system_tray.tray_menu.insertAction(system_tray.quit_action, settings_action)
    system_tray.tray_menu.insertSeparator(system_tray.quit_action)

    system_tray.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
