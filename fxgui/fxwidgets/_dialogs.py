"""Floating popup dialog."""

# Built-in
import os
from typing import Optional

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import (
    QCloseEvent,
    QColor,
    QCursor,
    QFont,
    QMouseEvent,
    QPixmap,
)
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxdcc, fxicons, fxstyle


class FXFloatingDialog(fxstyle.FXThemeAware, QDialog):
    """A floating dialog that appears at the cursor's position.
    It closes when any mouse button except the right one is pressed.

    Args:
        parent (QtWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (QPixmap): The QPixmap icon.
        title (str): The dialog title.

    Attributes:
        dialog_icon (QIcon): The icon of the dialog.
        dialog_title (str): The title of the dialog.
        drop_position (QPoint): The drop position of the dialog.
        dialog_position (Tuple[int, int]): The position of the dialog.
        parent_package (int): Whether the dialog is standalone application, or belongs to a DCC parent.
        popup (bool): Whether the dialog is a popup or not.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[QPixmap] = None,
        title: Optional[str] = None,
        parent_package: Optional[int] = None,
        popup: bool = False,
    ):
        super().__init__(parent)

        # Attributes
        self._default_icon = None  # Set in _apply_theme_styles
        self.dialog_icon: QPixmap = icon
        self.dialog_title: str = title
        self._popup = popup

        self.drop_position = QCursor.pos()
        self.dialog_position = (
            self.drop_position.x() - (self.width() / 2),
            self.drop_position.y() - (self.height() / 2),
        )

        self.parent_package = parent_package

        # Methods
        self._setup_title()
        self._setup_main_widget()
        self._setup_buttons()
        self._setup_layout()
        self._handle_connections()
        self.set_dialog_icon(self.dialog_icon)
        self.set_dialog_title(self.dialog_title)

        # Window - frameless with transparent background for rounded corners
        self.setAttribute(Qt.WA_DeleteOnClose)
        if popup:
            self.setWindowFlags(
                Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
            )
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(200, 40)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        # Update default icon
        self._default_icon = fxicons.get_icon(
            "home", color=self.theme.icon
        ).pixmap(32, 32)

        # Update icon if needed
        if self.dialog_icon is None:
            self.set_dialog_icon(self._default_icon)

        # Modern dialog styling
        bg_color = self.theme.surface
        bg_alt = self.theme.surface_alt
        bg_sunken = self.theme.surface_sunken
        border_color = self.theme.border
        text_color = self.theme.text
        text_muted = self.theme.text_muted
        accent = self.theme.accent_primary

        # Container styling (opaque background with rounded corners)
        self._container.setStyleSheet(
            f"""
            #FXFloatingDialogContainer {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            """
        )

        # Title bar styling
        self.title_widget.setStyleSheet(
            f"""
            QWidget {{
                background-color: {bg_sunken};
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
            }}
            QLabel {{
                background: transparent;
                color: {text_color};
            }}
            """
        )

        # Main content styling
        self.main_widget.setStyleSheet(
            f"""
            QWidget {{
                background: transparent;
            }}
            QLabel {{
                color: {text_muted};
                background: transparent;
            }}
            """
        )

        # Button styling
        self.button_box.setStyleSheet(
            f"""
            QDialogButtonBox {{
                background: transparent;
            }}
            QPushButton {{
                background-color: {bg_alt};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {accent};
                border-color: {accent};
                color: #000000;
            }}
            QPushButton:pressed {{
                background-color: {accent};
            }}
            """
        )

        # Apply DCC-specific styling
        if self.parent_package == fxdcc.HOUDINI:
            self.title_widget.setStyleSheet(
                f"background-color: {self.theme.surface_alt};"
            )
            self._container.setStyleSheet(
                f"""
                #FXFloatingDialogContainer {{
                    border-top: 1px solid {self.theme.border_light};
                    border-left: 1px solid {self.theme.border_light};
                    border-bottom: 1px solid {self.theme.surface};
                    border-right: 1px solid {self.theme.surface};
                }}
            """
            )

        # Apply drop shadow only for non-popup dialogs (avoids artifacts)
        if not self._popup and self._shadow_effect is None:
            self._shadow_effect = QGraphicsDropShadowEffect(self._container)
            self._shadow_effect.setBlurRadius(24)
            self._shadow_effect.setOffset(0, 4)
            self._shadow_effect.setColor(QColor(0, 0, 0, 100))
            self._container.setGraphicsEffect(self._shadow_effect)

    # Private methods
    def _setup_title(self):
        """Sets up the title bar with icon and label.

        Warning:
            This method is intended for internal use only.
        """

        self._icon_label = QLabel(self)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setFixedSize(24, 24)
        self.title_widget = QWidget(self)

        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title_label.setFont(font)

        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setContentsMargins(12, 10, 12, 10)
        self.title_layout.setSpacing(10)
        self.title_layout.addWidget(self._icon_label)
        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch()

    def _setup_main_widget(self):
        """Sets up the main content widget and layout.

        Warning:
            This method is intended for internal use only.
        """

        self.main_widget = QWidget(self)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(8)

    def _setup_buttons(self):
        """Sets up the dialog button box with close button.

        Warning:
            This method is intended for internal use only.
        """

        self.button_box = QDialogButtonBox(self)
        self.button_box.setContentsMargins(12, 8, 12, 12)
        self.button_close = self.button_box.addButton(QDialogButtonBox.Close)

    def _setup_layout(self):
        """Sets up the main dialog layout with title, content, and buttons.

        Warning:
            This method is intended for internal use only.
        """

        # Container frame for opaque background with rounded corners
        self._container = QFrame(self)
        self._container.setObjectName("FXFloatingDialogContainer")

        # Container layout
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.title_widget)
        container_layout.addWidget(self.main_widget, 1)
        container_layout.addWidget(self.button_box)

        # Main dialog layout (transparent, holds the container)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)  # Margin for shadow
        self.layout.addWidget(self._container)

        # Add drop shadow effect to container (skip for popup to avoid artifacts)
        self._shadow_effect = None

    def _handle_connections(self) -> None:
        """Connects the dialog's slots."""

        self.button_box.rejected.connect(self.reject)
        self.button_box.rejected.connect(self.close)  # TODO: Check if needed

    # Public methods
    def set_dialog_icon(self, icon: Optional[QPixmap] = None) -> None:
        """Sets the dialog's icon.

        Args:
            icon (QPixmap, optional): The QPixmap icon.
        """

        icon = icon if icon else self._default_icon
        if icon is not None:
            self._icon_label.setPixmap(
                icon.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self.dialog_icon = icon

    def set_dialog_title(self, title: str = None) -> None:
        """Sets the dialog's title.

        Args:
            title (str): The title of the dialog.
        """

        self.title_label.setText(title if title else "Floating Dialog")

    def show_under_cursor(self) -> int:
        """Moves the dialog to the current cursor position and displays it.

        Returns:
            int: The result of the `QDialog exec_()` method, which is an integer.
                It returns a `DialogCode` that can be `Accepted` or `Rejected`.
        """

        self.move(*self.dialog_position)
        return self.exec_()

    # Events
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Closes the dialog when any mouse button except the right one is pressed.

        Args:
            event (QMouseEvent): The mouse press event.
        """

        if event.button() != Qt.RightButton:
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Removes the parent of the dialog and closes it.

        Args:
            event (QCloseEvent): The close event.
        """

        self.setParent(None)


def example() -> None:
    import sys
    from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget, QLabel
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXFloatingDialog Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Basic floating dialog
    def show_basic_dialog():
        dialog = FXFloatingDialog(window, title="Basic Dialog")
        dialog.main_layout.addWidget(QLabel("This is a basic floating dialog."))
        dialog.show_under_cursor()

    # Dialog with custom icon
    def show_icon_dialog():
        icon = fxicons.get_icon("settings").pixmap(32, 32)
        dialog = FXFloatingDialog(window, icon=icon, title="Settings")
        dialog.main_layout.addWidget(QLabel("Configure your settings here."))
        dialog.main_layout.addWidget(QLabel("Option 1: Enabled"))
        dialog.main_layout.addWidget(QLabel("Option 2: Disabled"))
        dialog.resize(250, 150)
        dialog.show_under_cursor()

    # Popup style dialog
    def show_popup_dialog():
        dialog = FXFloatingDialog(window, title="Quick Info", popup=True)
        dialog.main_layout.addWidget(
            QLabel("This is a popup dialog.\nClick outside to close.")
        )
        dialog.resize(200, 80)
        dialog.show_under_cursor()

    # Buttons to trigger dialogs
    btn_basic = QPushButton("Show Basic Dialog")
    btn_basic.clicked.connect(show_basic_dialog)
    layout.addWidget(btn_basic)

    btn_icon = QPushButton("Show Dialog with Icon")
    btn_icon.clicked.connect(show_icon_dialog)
    layout.addWidget(btn_icon)

    btn_popup = QPushButton("Show Popup Dialog")
    btn_popup.clicked.connect(show_popup_dialog)
    layout.addWidget(btn_popup)

    layout.addStretch()

    window.resize(300, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
