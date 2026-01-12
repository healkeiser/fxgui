"""Animated toggle switch widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
)
from qtpy.QtGui import QColor, QPainter, QPainterPath
from qtpy.QtWidgets import QAbstractButton, QSizePolicy, QWidget

# Internal
from fxgui import fxstyle


class FXToggleSwitch(fxstyle.FXThemeAware, QAbstractButton):
    """A modern iOS/Material-style animated toggle switch.

    This widget provides a sleek alternative to QCheckBox with smooth
    sliding animation and theme-aware colors.

    Args:
        parent: Parent widget.
        on_color: Color when switch is on. If None, uses theme accent.
        off_color: Color when switch is off. If None, uses theme surface.
        thumb_color: Color of the thumb/knob. If None, uses white.

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

        # Connect signals
        self.toggled.connect(self._on_toggled)

    def sizeHint(self):
        """Return the preferred size of the switch."""
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        """Return the minimum size of the switch."""
        from qtpy.QtCore import QSize

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
        """Handle toggle state change with animation."""
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def paintEvent(self, event) -> None:
        """Paint the toggle switch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get current theme colors (dynamic for theme switching)
        on_color = QColor(self._custom_on_color or self.theme.accent_primary)
        off_color = QColor(
            self._custom_off_color or self.theme.surface_sunken
        )
        thumb_color = QColor(self._custom_thumb_color or "#ffffff")
        border_color = QColor(self.theme.border)
        disabled_color = QColor(self.theme.text_disabled)

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
            track_color = disabled_color
            thumb_color = disabled_color.lighter(150)
            current_border_color = disabled_color
        else:
            # Interpolate between off and on colors
            track_color = self._interpolate_color(
                off_color, on_color, self._position
            )
            current_border_color = border_color

        # Draw track (rounded rectangle with border)
        track_path = QPainterPath()
        track_rect = QRect(0, 0, width, height)
        track_path.addRoundedRect(track_rect, corner_radius, corner_radius)
        painter.fillPath(track_path, track_color)

        # Draw track border
        painter.setPen(current_border_color)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(track_rect, corner_radius, corner_radius)

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

    def _interpolate_color(
        self, color1: QColor, color2: QColor, ratio: float
    ) -> QColor:
        """Interpolate between two colors."""
        r = int(color1.red() + (color2.red() - color1.red()) * ratio)
        g = int(color1.green() + (color2.green() - color1.green()) * ratio)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * ratio)
        return QColor(r, g, b)


def example() -> None:
    import sys
    from qtpy.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXToggleSwitch Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Toggle 1
    row1 = QWidget()
    row1_layout = QHBoxLayout(row1)
    row1_layout.addWidget(QLabel("Enable Feature:"))
    toggle1 = FXToggleSwitch()
    toggle1.toggled.connect(lambda checked: print(f"Feature: {checked}"))
    row1_layout.addWidget(toggle1)
    row1_layout.addStretch()
    layout.addWidget(row1)

    # Toggle 2 (pre-checked)
    row2 = QWidget()
    row2_layout = QHBoxLayout(row2)
    row2_layout.addWidget(QLabel("Dark Mode:"))
    toggle2 = FXToggleSwitch()
    toggle2.setChecked(True)
    row2_layout.addWidget(toggle2)
    row2_layout.addStretch()
    layout.addWidget(row2)

    # Toggle 3 (disabled)
    row3 = QWidget()
    row3_layout = QHBoxLayout(row3)
    row3_layout.addWidget(QLabel("Disabled:"))
    toggle3 = FXToggleSwitch()
    toggle3.setEnabled(False)
    row3_layout.addWidget(toggle3)
    row3_layout.addStretch()
    layout.addWidget(row3)

    layout.addStretch()
    window.resize(300, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
