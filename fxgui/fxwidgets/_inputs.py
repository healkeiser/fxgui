"""Line edits: with an icon, for a password, and with rejection feedback."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    Qt,
    Slot,
)
from qtpy.QtGui import QAction, QColor, QKeyEvent, QPainter, QPen
from qtpy.QtWidgets import QLineEdit, QWidget

# Internal
from fxgui import fxicons, fxstyle


_POSITIONS = {
    "left": QLineEdit.LeadingPosition,
    "right": QLineEdit.TrailingPosition,
}


class FXIconLineEdit(QLineEdit):
    """A line edit with an icon inside it, on the left or the right.

    The icon is a `QLineEdit.addAction` action, so Qt places it and keeps
    it out of the Tab chain.

    Args:
        parent: The parent widget.
        icon_name: The icon to show; `None` for none.
        icon_position: `"left"` or `"right"`.

    Raises:
        ValueError: If `icon_position` is neither.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon_name: Optional[str] = None,
        icon_position: str = "left",
    ):
        super().__init__(parent)
        if icon_position not in _POSITIONS:
            raise ValueError("icon_position must be 'left' or 'right'")
        self._icon_action: Optional[QAction] = None
        if icon_name is not None:
            self._icon_action = self.addAction(
                fxicons.get_icon(icon_name), _POSITIONS[icon_position]
            )


class FXPasswordLineEdit(FXIconLineEdit):
    """A password field whose eye icon shows or hides what was typed.

    Args:
        parent: The parent widget.
        icon_position: `"left"` or `"right"`.
    """

    def __init__(
        self, parent: Optional[QWidget] = None, icon_position: str = "right"
    ):
        super().__init__(parent, "visibility", icon_position)
        self.setEchoMode(QLineEdit.Password)
        self._icon_action.setCheckable(True)
        self._icon_action.setToolTip("Show or hide the password")
        self._icon_action.toggled.connect(self._reveal)

    @Slot(bool)
    def _reveal(self, shown: bool) -> None:
        """Show the text while `shown`, and swap the eye icon to match."""
        self.setEchoMode(QLineEdit.Normal if shown else QLineEdit.Password)
        fxicons.set_icon(
            self._icon_action, "visibility_off" if shown else "visibility"
        )


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
    borderColor = Property(QColor, _get_border_color, _set_border_color)

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
    shakeOffset = Property(float, _get_shake_offset, _set_shake_offset)

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
        radius = fxstyle.BUTTON_RADIUS
        painter.drawRoundedRect(edge, radius, radius)
        painter.end()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Shake when a typed character changed nothing: it was rejected."""
        before = (self.text(), self.cursorPosition())
        super().keyPressEvent(event)
        typed = event.text()
        if (
            self.validator() is not None
            and typed
            and typed.isprintable()
            and (self.text(), self.cursorPosition()) == before
        ):
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

    def _show_rejection_feedback(self) -> None:
        """Show shake animation with red border flash."""
        if self._shake_group is None:
            self._build_animations()
        elif self._flash_group.state() == QAbstractAnimation.Running:
            return

        self._base_margins = self.textMargins()

        # The colour is read per rejection: the theme may have changed.
        error_color = QColor(fxstyle.colors().feedback_error_foreground)
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
