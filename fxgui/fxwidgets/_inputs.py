"""Input widgets with icons."""

# Built-in
import os
from typing import Optional

# Third-party
from qtpy.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
    Slot,
)
from qtpy.QtGui import QColor, QKeyEvent
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

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        self.reveal_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.state_hover};
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

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        # Only reposition, don't set stylesheet (parent widget may override)
        self._position_icon()


class FXValidatedLineEdit(fxstyle.FXThemeAware, QLineEdit):
    """A line edit that provides visual feedback when input is rejected.

    When a validator rejects input (e.g., typing an invalid character),
    this widget shows a brief shake animation with a red border flash
    to indicate to the user that their input was not accepted.

    The error color is theme-aware and uses the feedback "error" color
    from the current theme.

    Args:
        parent: The parent widget.
        shake_amplitude: Maximum horizontal displacement in pixels.
        shake_duration: Total duration of shake animation in milliseconds.
        flash_duration: Duration of red border flash in milliseconds.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> from fxgui.fxwidgets import FXValidatedLineEdit, FXCamelCaseValidator
        >>> line_edit = FXValidatedLineEdit()
        >>> line_edit.setValidator(FXCamelCaseValidator())
        >>> line_edit.setPlaceholderText("camelCase only")
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        shake_amplitude: int = 4,
        shake_duration: int = 300,
        flash_duration: int = 400,
    ):
        super().__init__(parent)

        self._shake_amplitude = shake_amplitude
        self._shake_duration = shake_duration
        self._flash_duration = flash_duration
        self._border_color_value = QColor("transparent")
        self._is_animating = False
        self._shake_offset = 0.0

    def _get_border_color(self) -> QColor:
        """Get the current animated border color."""
        return self._border_color_value

    def _set_border_color(self, color: QColor) -> None:
        """Set the animated border color and update stylesheet."""
        self._border_color_value = color
        self._update_border_style()

    # Property for animating border color
    borderColor = Property(
        QColor, _get_border_color, _set_border_color, user=True
    )

    def _get_shake_offset(self) -> float:
        """Get the current shake offset."""
        return self._shake_offset

    def _set_shake_offset(self, offset: float) -> None:
        """Set the shake offset by adjusting text margins."""
        self._shake_offset = offset
        # Use text margins to create shake effect
        left_margin = max(0, int(offset))
        right_margin = max(0, int(-offset))
        self.setTextMargins(left_margin, 0, right_margin, 0)

    # Property for animating shake
    shakeOffset = Property(
        float, _get_shake_offset, _set_shake_offset, user=True
    )

    def _get_error_color(self) -> QColor:
        """Get the theme-aware error color."""
        feedback = fxstyle.get_feedback_colors()
        return QColor(feedback["error"]["foreground"])

    def _update_border_style(self) -> None:
        """Update the stylesheet with the current border color."""
        if self._border_color_value.alpha() > 0:
            self.setStyleSheet(
                f"FXValidatedLineEdit {{ border-color: {self._border_color_value.name()}; }}"
            )
        else:
            self.setStyleSheet("")

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        # Reset stylesheet when not animating
        if not self._is_animating:
            self.setStyleSheet("")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Intercept key presses to detect rejected input.

        Args:
            event: The key event.
        """
        # Get text before the key press
        text_before = self.text()
        cursor_before = self.cursorPosition()

        # Let the base class handle the event
        super().keyPressEvent(event)

        # Skip if no validator or if it's a control key
        validator = self.validator()
        if validator is None:
            return

        # Check if this is a printable character that should have been inserted
        key_text = event.text()
        if not key_text or not key_text.isprintable():
            return

        # If text didn't change and cursor didn't move, input was likely rejected
        text_after = self.text()
        cursor_after = self.cursorPosition()

        if text_before == text_after and cursor_before == cursor_after:
            # Input was rejected by the validator
            self._show_rejection_feedback()

    def _show_rejection_feedback(self) -> None:
        """Show shake animation with red border flash."""
        if self._is_animating:
            return

        self._is_animating = True

        # Get theme-aware error color
        error_color = self._get_error_color()
        transparent = QColor(error_color)
        transparent.setAlpha(0)

        # Create shake animation using margins
        shake_group = QSequentialAnimationGroup(self)
        amplitude = self._shake_amplitude
        duration_per_shake = self._shake_duration // 5

        # Shake sequence: right -> left -> right -> left -> center
        positions = [amplitude, -amplitude, amplitude // 2, -amplitude // 2, 0]

        for offset in positions:
            anim = QPropertyAnimation(self, b"shakeOffset", self)
            anim.setDuration(duration_per_shake)
            anim.setEndValue(float(offset))
            anim.setEasingCurve(QEasingCurve.OutQuad)
            shake_group.addAnimation(anim)

        # Create border color animation (red flash)
        # Flash in
        flash_in = QPropertyAnimation(self, b"borderColor", self)
        flash_in.setDuration(self._flash_duration // 4)
        flash_in.setStartValue(transparent)
        flash_in.setEndValue(error_color)
        flash_in.setEasingCurve(QEasingCurve.OutQuad)

        # Hold
        flash_hold = QPropertyAnimation(self, b"borderColor", self)
        flash_hold.setDuration(self._flash_duration // 2)
        flash_hold.setStartValue(error_color)
        flash_hold.setEndValue(error_color)

        # Flash out
        flash_out = QPropertyAnimation(self, b"borderColor", self)
        flash_out.setDuration(self._flash_duration // 4)
        flash_out.setStartValue(error_color)
        flash_out.setEndValue(transparent)
        flash_out.setEasingCurve(QEasingCurve.InQuad)

        # Combine flash animations
        flash_group = QSequentialAnimationGroup(self)
        flash_group.addAnimation(flash_in)
        flash_group.addAnimation(flash_hold)
        flash_group.addAnimation(flash_out)

        # Connect finished signals
        shake_group.finished.connect(self._on_shake_finished)
        flash_group.finished.connect(self._on_flash_finished)

        shake_group.start()
        flash_group.start()

    def _on_shake_finished(self) -> None:
        """Reset shake offset after animation."""
        self._shake_offset = 0.0
        self.setTextMargins(0, 0, 0, 0)

    def _on_flash_finished(self) -> None:
        """Reset state after flash animation."""
        self._is_animating = False
        self._border_color_value = QColor("transparent")
        self.setStyleSheet("")


def example() -> None:
    import sys

    from qtpy.QtWidgets import QFormLayout, QLabel, QVBoxLayout

    from fxgui.fxwidgets import (
        FXApplication,
        FXCamelCaseValidator,
        FXLowerCaseValidator,
        FXMainWindow,
    )

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXInputs Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Description
    description = QLabel(
        "Test the input widgets below. FXValidatedLineEdit will shake\n"
        "and flash red when you type invalid characters."
    )
    layout.addWidget(description)

    form_layout = QFormLayout()
    layout.addLayout(form_layout)

    # Icon line edit with icon on the left
    icon_line_edit_left = FXIconLineEdit(
        icon_name="search", icon_position="left"
    )
    icon_line_edit_left.setPlaceholderText("Search...")
    form_layout.addRow("FXIconLineEdit (left):", icon_line_edit_left)

    # Icon line edit with icon on the right
    icon_line_edit_right = FXIconLineEdit(
        icon_name="email", icon_position="right"
    )
    icon_line_edit_right.setPlaceholderText("Enter email...")
    form_layout.addRow("FXIconLineEdit (right):", icon_line_edit_right)

    # Password line edit
    password_line_edit = FXPasswordLineEdit()
    password_line_edit.line_edit.setPlaceholderText("Enter password...")
    form_layout.addRow("FXPasswordLineEdit:", password_line_edit)

    # Validated line edit with CamelCase validator
    camel_case_edit = FXValidatedLineEdit()
    camel_case_edit.setValidator(FXCamelCaseValidator())
    camel_case_edit.setPlaceholderText("camelCase (e.g., myVariableName)")
    form_layout.addRow("FXValidatedLineEdit (camelCase):", camel_case_edit)

    # Validated line edit with lowercase validator
    lowercase_edit = FXValidatedLineEdit()
    lowercase_edit.setValidator(FXLowerCaseValidator(allow_underscores=True))
    lowercase_edit.setPlaceholderText("snake_case (e.g., my_variable)")
    form_layout.addRow("FXValidatedLineEdit (snake_case):", lowercase_edit)

    layout.addStretch()
    window.resize(600, 300)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
