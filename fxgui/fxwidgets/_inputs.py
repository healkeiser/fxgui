"""Input widgets with icons."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


class FXPasswordLineEdit(fxstyle.FXThemeAware, QWidget):
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

    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styles."""
        theme_colors = fxstyle.get_theme_colors()
        hover_color = theme_colors.get(
            "state_hover", "rgba(128, 128, 128, 0.2)"
        )

        self.reveal_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            """
        )


class FXIconLineEdit(fxstyle.FXThemeAware, QLineEdit):
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

        self._icon_position = icon_position

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

        # Set text margins based on icon position
        if icon_position == "left":
            self.setTextMargins(22, 0, 0, 0)
        elif icon_position == "right":
            self.setTextMargins(0, 0, 22, 0)
        else:
            raise ValueError("icon_position must be 'left' or 'right'")

        # Position icon initially
        self._position_icon()

    def _position_icon(self):
        """Position the icon button based on the icon_position setting."""
        if self._icon_position == "left":
            self.icon_button.move(
                5, (self.height() - self.icon_button.height()) // 2
            )
        else:
            self.icon_button.move(
                self.width() - self.icon_button.width() - 5,
                (self.height() - self.icon_button.height()) // 2,
            )

    def resizeEvent(self, event):
        """Reposition the icon when the line edit is resized."""
        super().resizeEvent(event)
        self._position_icon()

    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styles."""
        # Only reposition, don't set stylesheet (parent widget may override)
        self._position_icon()


def example() -> None:
    import sys
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXInputs Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QHBoxLayout(widget)

    # Icon line edit with icon on the left
    icon_line_edit_left = FXIconLineEdit(
        icon_name="search", icon_position="left"
    )
    icon_line_edit_left.setPlaceholderText("Search...")
    layout.addWidget(icon_line_edit_left)

    # Icon line edit with icon on the right
    icon_line_edit_right = FXIconLineEdit(
        icon_name="email", icon_position="right"
    )
    icon_line_edit_right.setPlaceholderText("Enter email...")
    layout.addWidget(icon_line_edit_right)

    # Password line edit
    password_line_edit = FXPasswordLineEdit()
    password_line_edit.line_edit.setPlaceholderText("Enter password...")
    layout.addWidget(password_line_edit)

    window.resize(600, 100)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
