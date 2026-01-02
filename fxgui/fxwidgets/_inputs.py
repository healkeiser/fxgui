"""Input widgets with icons."""

from typing import Optional

from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from fxgui import fxicons


class FXPasswordLineEdit(QWidget):
    """
    A custom widget that includes a password line edit with a show/hide button.

    Args:
        parent: The parent widget.
        icon_position: The position of the icon ('left' or 'right').
    """

    def __init__(
        self, parent: Optional[QWidget] = None, icon_position: str = "right"
    ):
        super().__init__(parent)
        self.line_edit = FXIconLineEdit(icon_position=icon_position)
        self.line_edit.setEchoMode(QLineEdit.Password)

        # Show/hide button
        self.reveal_button = self.line_edit.icon_button
        fxicons.set_icon(self.reveal_button, "visibility")
        self.reveal_button.setCursor(Qt.PointingHandCursor)
        self.reveal_button.clicked.connect(self.toggle_reveal)

        # Layout for lineEdit and button
        layout = QHBoxLayout()
        layout.addWidget(self.line_edit)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @Slot()
    def toggle_reveal(self):
        """Toggles the echo mode between password and normal, and changes the
        icon of the reveal button accordingly.
        """

        if self.line_edit.echoMode() == QLineEdit.Password:
            self.line_edit.setEchoMode(QLineEdit.Normal)
            fxicons.set_icon(self.reveal_button, "visibility_off")
        else:
            self.line_edit.setEchoMode(QLineEdit.Password)
            fxicons.set_icon(self.reveal_button, "visibility")


class FXIconLineEdit(QLineEdit):
    """A line edit that displays an icon on the left or right side.

    The icon is theme-aware and will refresh automatically when the
    application theme changes.

    Args:
            icon_name: The name of the icon to display.
            icon_position: The position of the icon ('left' or 'right').
            parent: The parent widget.
    """

    def __init__(
        self,
        icon_name: Optional[str] = None,
        icon_position: str = "left",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # Create a `QPushButton` to hold the icon
        self.icon_button = QPushButton(self)
        self.icon_button.setFlat(True)
        self.icon_button.setStyleSheet(
            "background-color: transparent; border: none;"
        )
        self.icon_button.setFixedSize(18, 18)

        # Set icon using set_icon for auto-refresh
        if icon_name is not None:
            fxicons.set_icon(self.icon_button, icon_name)

        # Create a layout to hold the icon and the line edit
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if icon_position == "left":
            self.layout.addWidget(self.icon_button)
            self.layout.addStretch()
            self.setTextMargins(22, 0, 0, 0)
        elif icon_position == "right":
            self.layout.addStretch()
            self.layout.addWidget(self.icon_button)
            self.setTextMargins(0, 0, 22, 0)
        else:
            raise ValueError("icon_position must be 'left' or 'right'")

        self.setLayout(self.layout)

    def resizeEvent(self, event):
        """Reposition the icon when the line edit is resized."""

        super().resizeEvent(event)
        if self.layout.itemAt(0).widget() == self.icon_button:
            self.icon_button.move(
                5, (self.height() - self.icon_button.height()) // 2
            )
        else:
            self.icon_button.move(
                self.width() - self.icon_button.width() - 5,
                (self.height() - self.icon_button.height()) // 2,
            )
