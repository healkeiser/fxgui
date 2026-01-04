"""FXToggleSwitch - Animated toggle switch widget."""

import os
from typing import Optional

from qtpy.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
)
from qtpy.QtGui import QColor, QMouseEvent, QPainter, QPainterPath
from qtpy.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from fxgui import fxstyle


class FXToggleSwitch(QAbstractButton):
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

        # Get theme colors
        theme_colors = fxstyle.get_theme_colors()
        accent_colors = fxstyle.get_accent_colors()

        # Colors
        self._on_color = QColor(on_color or accent_colors["primary"])
        self._off_color = QColor(off_color or theme_colors["surface_alt"])
        self._thumb_color = QColor(thumb_color or "#ffffff")
        self._disabled_color = QColor(theme_colors["text_disabled"])

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

        # Calculate dimensions
        width = self.width()
        height = self.height()
        margin = 2
        thumb_radius = (height - margin * 2) // 2

        # Determine colors based on state
        if not self.isEnabled():
            track_color = self._disabled_color
            thumb_color = self._disabled_color.lighter(150)
        else:
            # Interpolate between off and on colors
            track_color = self._interpolate_color(
                self._off_color, self._on_color, self._position
            )
            thumb_color = self._thumb_color

        # Draw track (rounded rectangle)
        track_path = QPainterPath()
        track_rect = QRect(0, 0, width, height)
        track_path.addRoundedRect(track_rect, height / 2, height / 2)
        painter.fillPath(track_path, track_color)

        # Calculate thumb position
        thumb_x = margin + self._position * (width - height)
        thumb_y = margin

        # Draw thumb shadow (subtle)
        if self.isEnabled():
            shadow_color = QColor(0, 0, 0, 40)
            painter.setBrush(shadow_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(thumb_x + 1),
                int(thumb_y + 1),
                thumb_radius * 2,
                thumb_radius * 2,
            )

        # Draw thumb
        painter.setBrush(thumb_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(thumb_x), int(thumb_y), thumb_radius * 2, thumb_radius * 2
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

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to toggle state."""
        if event.button() == Qt.LeftButton and self.hitButton(event.pos()):
            self.setChecked(not self.isChecked())
        super().mouseReleaseEvent(event)


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    import os
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
