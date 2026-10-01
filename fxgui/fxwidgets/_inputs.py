"""Input widgets with icons."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    Qt,
    Slot,
)
from qtpy.QtGui import QColor, QKeyEvent, QPainter, QPen
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


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
        self.icon_button.setObjectName("fx_icon_line_edit_button")
        self.icon_button.setFlat(True)
        self.icon_button.setFixedSize(18, 18)
        # In a dialog, Enter belongs to the default button, not the icon.
        self.icon_button.setAutoDefault(False)

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


fxstyle.register_widget_style("""
QPushButton#fx_icon_line_edit_button {
    background-color: transparent;
    border: none;
}
FXPasswordLineEdit QPushButton#fx_icon_line_edit_button {
    border-radius: @button_radius;
}
FXPasswordLineEdit QPushButton#fx_icon_line_edit_button:hover {
    background-color: @state_hover;
}
""")


class FXValidatedLineEdit(QLineEdit):
    """A line edit that provides visual feedback when input is rejected.

    When a validator rejects input (e.g., typing an invalid character),
    this widget shakes briefly and flashes a border in the theme's error
    colour. The flash is painted over the field, so the caller's own
    stylesheet and text margins are left as they were.

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
        self._base_margins = self.textMargins()
        self._shake_group: Optional[QSequentialAnimationGroup] = None
        self._flash_group: Optional[QSequentialAnimationGroup] = None
        self._flash_steps = []

    def _get_border_color(self) -> QColor:
        """Get the current animated border color."""
        return self._border_color_value

    def _set_border_color(self, color: QColor) -> None:
        """Set the animated border color and repaint."""
        self._border_color_value = color
        self.update()

    # Property for animating border color
    borderColor = Property(
        QColor, _get_border_color, _set_border_color, user=True
    )

    def _get_shake_offset(self) -> float:
        """Get the current shake offset."""
        return self._shake_offset

    def _set_shake_offset(self, offset: float) -> None:
        """Shift the text by `offset` on top of the caller's margins."""
        self._shake_offset = offset
        base = self._base_margins
        self.setTextMargins(
            base.left() + max(0, int(offset)),
            base.top(),
            base.right() + max(0, int(-offset)),
            base.bottom(),
        )

    # Property for animating shake
    shakeOffset = Property(
        float, _get_shake_offset, _set_shake_offset, user=True
    )

    def _get_error_color(self) -> QColor:
        """Get the theme-aware error color."""
        feedback = fxstyle.get_feedback_colors()
        return QColor(feedback["error"]["foreground"])

    def paintEvent(self, event) -> None:
        """Paint the field, then the rejection flash over its border."""
        super().paintEvent(event)
        if self._border_color_value.alpha() == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self._border_color_value, 1))
        painter.setBrush(Qt.NoBrush)
        edge = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(edge, 4, 4)
        painter.end()

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

    def _build_animations(self) -> None:
        """Build the shake and flash animations once, for reuse."""
        self._shake_group = QSequentialAnimationGroup(self)
        amplitude = self._shake_amplitude
        duration_per_shake = self._shake_duration // 5
        # Shake sequence: right -> left -> right -> left -> center
        for offset in (amplitude, -amplitude, amplitude // 2, -amplitude // 2, 0):
            anim = QPropertyAnimation(self, b"shakeOffset", self)
            anim.setDuration(duration_per_shake)
            anim.setEndValue(float(offset))
            anim.setEasingCurve(QEasingCurve.OutQuad)
            self._shake_group.addAnimation(anim)

        self._flash_group = QSequentialAnimationGroup(self)
        quarter = self._flash_duration // 4
        for duration, curve in (
            (quarter, QEasingCurve.OutQuad),
            (self._flash_duration // 2, QEasingCurve.Linear),
            (quarter, QEasingCurve.InQuad),
        ):
            anim = QPropertyAnimation(self, b"borderColor", self)
            anim.setDuration(duration)
            anim.setEasingCurve(curve)
            self._flash_group.addAnimation(anim)
            self._flash_steps.append(anim)

        self._shake_group.finished.connect(self._on_shake_finished)
        self._flash_group.finished.connect(self._on_flash_finished)

    def _show_rejection_feedback(self) -> None:
        """Show shake animation with red border flash."""
        if self._is_animating:
            return
        if self._shake_group is None:
            self._build_animations()

        self._is_animating = True
        self._base_margins = self.textMargins()

        # The colour is read per rejection: the theme may have changed.
        error_color = self._get_error_color()
        transparent = QColor(error_color)
        transparent.setAlpha(0)
        flash_in, flash_hold, flash_out = self._flash_steps
        flash_in.setStartValue(transparent)
        flash_in.setEndValue(error_color)
        flash_hold.setStartValue(error_color)
        flash_hold.setEndValue(error_color)
        flash_out.setStartValue(error_color)
        flash_out.setEndValue(transparent)

        self._shake_group.start()
        self._flash_group.start()

    def _on_shake_finished(self) -> None:
        """Put the caller's margins back after the shake."""
        self._shake_offset = 0.0
        self.setTextMargins(self._base_margins)

    def _on_flash_finished(self) -> None:
        """Reset state after flash animation."""
        self._is_animating = False
        self._border_color_value = QColor("transparent")
        self.update()
