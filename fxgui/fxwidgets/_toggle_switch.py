"""Animated toggle switch widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
)
from qtpy.QtGui import QColor, QPainter, QPainterPath
from qtpy.QtWidgets import QAbstractButton, QSizePolicy, QWidget

# Internal
from fxgui import fxstyle


# WCAG's minimum contrast for the parts of a control.
_PARTS = 3.0


class FXToggleSwitch(QAbstractButton):
    """A modern iOS/Material-style animated toggle switch.

    This widget provides a sleek alternative to QCheckBox with smooth
    sliding animation and theme-aware colors.

    Args:
        parent: Parent widget.
        on_color: Color when switch is on. If None, uses theme accent.
        off_color: Color when switch is off. If None, uses theme surface.
        thumb_color: Color of the thumb/knob. If None, uses the theme's
            slider thumb colour.

    Signals:
        toggled: Emitted when the switch state changes.

    Examples:
        >>> switch = FXToggleSwitch()
        >>> switch.toggled.connect(lambda checked: print(f"Switch: {checked}"))
        >>> switch.setChecked(True)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_color: Optional[str] = None,
        off_color: Optional[str] = None,
        thumb_color: Optional[str] = None,
    ):
        super().__init__(parent)

        # Store user-provided colors (None means use theme colors)
        self._custom_on_color = on_color
        self._custom_off_color = off_color
        self._custom_thumb_color = thumb_color

        # Animation position (0.0 = off, 1.0 = on)
        self._position = 0.0

        # Setup animation
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._animation.setDuration(150)

        # Setup widget
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        # Keyboard: focusable via Tab and mouse; QAbstractButton then
        # handles Space to toggle.
        self.setFocusPolicy(Qt.StrongFocus)

        # Connect signals
        self.toggled.connect(self._on_toggled)

    def sizeHint(self):
        """Return the preferred size of the switch."""
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        """Return the minimum size of the switch."""
        return QSize(44, 24)

    def hitButton(self, pos):
        """Return True if pos is inside the clickable area."""
        return self.rect().contains(pos)

    @Property(float)
    def position(self) -> float:
        """The current animation position (0.0-1.0)."""
        return self._position

    @position.setter
    def position(self, value: float) -> None:
        """Set the animation position and trigger repaint."""
        self._position = value
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        """Slide to the new state, or jump there while nobody sees it."""
        self._animation.stop()
        end = 1.0 if checked else 0.0
        if not self.isVisible():
            self.position = end
            return
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(end)
        self._animation.start()

    def focusInEvent(self, event) -> None:
        """Repaint to show the focus indicator."""
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:
        """Repaint to hide the focus indicator."""
        super().focusOutEvent(event)
        self.update()

    def enterEvent(self, event) -> None:
        """Repaint to show the hover state."""
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:
        """Repaint to hide the hover state."""
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the toggle switch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        theme = fxstyle.colors()
        on_color = self._custom_on_color or fxstyle.readable_ink(
            theme.surface, theme.accent_primary, _PARTS
        )
        off_color = self._custom_off_color or theme.surface_sunken
        # The off fill sits close to the surface; the edge is what reads.
        edge = fxstyle.readable_ink(theme.surface, theme.border_strong, _PARTS)
        thumb_off = self._custom_thumb_color or fxstyle.readable_ink(
            off_color, theme.text_muted, _PARTS
        )
        thumb_on = self._custom_thumb_color or fxstyle.readable_ink(
            on_color, theme.text_on_accent_primary, _PARTS
        )

        # Calculate dimensions
        width = self.width()
        height = self.height()
        margin = 3
        corner_radius = 4  # Less rounded, more rectangular
        thumb_size = height - margin * 2
        thumb_corner_radius = (
            corner_radius - 1
        )  # Slightly smaller to fit inside

        # Determine colors based on state
        if not self.isEnabled():
            disabled_color = QColor(theme.text_disabled)
            track_color = disabled_color
            thumb_color = disabled_color.lighter(150)
            current_border_color = disabled_color
        else:
            position = self._position
            track_color = QColor(fxstyle.mix(off_color, on_color, position))
            thumb_color = QColor(fxstyle.mix(thumb_off, thumb_on, position))
            current_border_color = QColor(
                fxstyle.mix(edge, on_color, position)
            )
            # Focus indicator: keyboard users need to see where focus is.
            # The ring must contrast with the track at any position (an
            # accent ring would vanish on the accent-colored "on" track).
            if self.hasFocus():
                current_border_color = QColor(
                    "#ffffff" if track_color.lightness() < 128 else "#000000"
                )
            elif self.underMouse():
                current_border_color = QColor(theme.accent_secondary)

        # Draw track (rounded rectangle with border)
        track_path = QPainterPath()
        track_rect = QRect(0, 0, width, height)
        # QPainterPath.addRoundedRect only has QRectF overloads; PySide
        # converts a QRect implicitly, PyQt raises TypeError.
        track_path.addRoundedRect(
            QRectF(track_rect), corner_radius, corner_radius
        )
        painter.fillPath(track_path, track_color)

        # Draw track border, half a pixel in so the whole line is drawn
        painter.setPen(current_border_color)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            QRectF(track_rect).adjusted(0.5, 0.5, -0.5, -0.5),
            corner_radius,
            corner_radius,
        )

        # Calculate thumb position
        thumb_x = margin + self._position * (width - thumb_size - margin * 2)
        thumb_y = margin

        # Draw thumb shadow (subtle)
        if self.isEnabled():
            shadow_color = QColor(0, 0, 0, 30)
            painter.setBrush(shadow_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(
                int(thumb_x + 1),
                int(thumb_y + 1),
                thumb_size,
                thumb_size,
                thumb_corner_radius,
                thumb_corner_radius,
            )

        # Draw thumb with border (matching track roundness)
        painter.setBrush(thumb_color)
        painter.setPen(current_border_color)
        painter.drawRoundedRect(
            int(thumb_x),
            int(thumb_y),
            thumb_size,
            thumb_size,
            thumb_corner_radius,
            thumb_corner_radius,
        )

        painter.end()
