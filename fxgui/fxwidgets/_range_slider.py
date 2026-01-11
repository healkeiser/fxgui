"""Dual-handle range slider widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import (
    QColor,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
)
from qtpy.QtWidgets import QSizePolicy, QWidget

# Internal
from fxgui import fxstyle


class FXRangeSlider(fxstyle.FXThemeAware, QWidget):
    """A slider with two handles for selecting a min/max range.

    This widget provides a dual-handle slider perfect for filtering
    values within a range (e.g., frame ranges, price ranges).

    Args:
        parent: Parent widget.
        minimum: Minimum value of the range.
        maximum: Maximum value of the range.
        low: Initial low value.
        high: Initial high value.
        show_values: Whether to show value labels.

    Signals:
        range_changed: Emitted when either handle changes (low, high).
        low_changed: Emitted when the low value changes.
        high_changed: Emitted when the high value changes.

    Examples:
        >>> slider = FXRangeSlider(minimum=0, maximum=100)
        >>> slider.range_changed.connect(lambda l, h: print(f"Range: {l}-{h}"))
        >>> slider.set_range(25, 75)
    """

    range_changed = Signal(int, int)
    low_changed = Signal(int)
    high_changed = Signal(int)

    # Handle being dragged
    HANDLE_NONE = 0
    HANDLE_LOW = 1
    HANDLE_HIGH = 2

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        minimum: int = 0,
        maximum: int = 100,
        low: Optional[int] = None,
        high: Optional[int] = None,
        show_values: bool = True,
    ):
        super().__init__(parent)

        # Range values
        self._minimum = minimum
        self._maximum = maximum
        self._low = low if low is not None else minimum
        self._high = high if high is not None else maximum
        self._show_values = show_values

        # UI state
        self._pressed_handle = self.HANDLE_NONE
        self._hover_handle = self.HANDLE_NONE
        self._handle_radius = 8
        self._track_height = 4

        # Setup widget
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(70)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        """Return the preferred size."""
        from qtpy.QtCore import QSize

        return QSize(200, 70)

    def minimumSizeHint(self):
        """Return the minimum size."""
        from qtpy.QtCore import QSize

        return QSize(100, 70)

    @property
    def low(self) -> int:
        """Return the low value."""
        return self._low

    @low.setter
    def low(self, value: int) -> None:
        """Set the low value."""
        value = max(self._minimum, min(value, self._high))
        if value != self._low:
            self._low = value
            self.low_changed.emit(value)
            self.range_changed.emit(self._low, self._high)
            self.update()

    @property
    def high(self) -> int:
        """Return the high value."""
        return self._high

    @high.setter
    def high(self, value: int) -> None:
        """Set the high value."""
        value = max(self._low, min(value, self._maximum))
        if value != self._high:
            self._high = value
            self.high_changed.emit(value)
            self.range_changed.emit(self._low, self._high)
            self.update()

    def set_range(self, low: int, high: int) -> None:
        """Set both low and high values.

        Args:
            low: The low value.
            high: The high value.
        """
        low = max(self._minimum, min(low, high))
        high = max(low, min(high, self._maximum))

        changed = low != self._low or high != self._high
        self._low = low
        self._high = high

        if changed:
            self.low_changed.emit(low)
            self.high_changed.emit(high)
            self.range_changed.emit(low, high)
            self.update()

    def set_minimum(self, minimum: int) -> None:
        """Set the minimum value."""
        self._minimum = minimum
        if self._low < minimum:
            self.low = minimum
        self.update()

    def set_maximum(self, maximum: int) -> None:
        """Set the maximum value."""
        self._maximum = maximum
        if self._high > maximum:
            self.high = maximum
        self.update()

    def _value_to_position(self, value: int) -> float:
        """Convert a value to a pixel position."""
        margin = self._handle_radius
        available_width = self.width() - margin * 2
        value_range = self._maximum - self._minimum

        if value_range == 0:
            return margin

        ratio = (value - self._minimum) / value_range
        return margin + ratio * available_width

    def _position_to_value(self, pos: float) -> int:
        """Convert a pixel position to a value."""
        margin = self._handle_radius
        available_width = self.width() - margin * 2
        value_range = self._maximum - self._minimum

        if available_width == 0:
            return self._minimum

        ratio = (pos - margin) / available_width
        ratio = max(0.0, min(1.0, ratio))
        return int(self._minimum + ratio * value_range)

    def _handle_at_position(self, pos: int) -> int:
        """Return which handle is at the given x position."""
        low_x = self._value_to_position(self._low)
        high_x = self._value_to_position(self._high)

        low_dist = abs(pos - low_x)
        high_dist = abs(pos - high_x)

        if low_dist <= self._handle_radius * 1.5:
            if high_dist <= self._handle_radius * 1.5:
                # Both handles close, pick the nearest
                return (
                    self.HANDLE_LOW
                    if low_dist < high_dist
                    else self.HANDLE_HIGH
                )
            return self.HANDLE_LOW
        elif high_dist <= self._handle_radius * 1.5:
            return self.HANDLE_HIGH

        return self.HANDLE_NONE

    def paintEvent(self, event) -> None:
        """Paint the range slider."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get current theme colors (dynamic for theme switching)
        track_color = QColor(self.theme.surface_sunken)
        handle_color = QColor("#ffffff")
        handle_border_color = QColor(self.theme.accent_primary)

        # Calculate positions
        margin = self._handle_radius
        track_y = self.height() // 2
        low_x = self._value_to_position(self._low)
        high_x = self._value_to_position(self._high)

        # Draw background track
        track_path = QPainterPath()
        track_path.addRoundedRect(
            margin,
            track_y - self._track_height // 2,
            self.width() - margin * 2,
            self._track_height,
            self._track_height // 2,
            self._track_height // 2,
        )
        painter.fillPath(track_path, track_color)

        # Draw range (selected area) with gradient
        range_path = QPainterPath()
        range_path.addRoundedRect(
            low_x,
            track_y - self._track_height // 2,
            high_x - low_x,
            self._track_height,
            self._track_height // 2,
            self._track_height // 2,
        )
        range_gradient = QLinearGradient(low_x, 0, high_x, 0)
        range_gradient.setColorAt(0, QColor(self.theme.accent_primary))
        range_gradient.setColorAt(1, QColor(self.theme.accent_secondary))
        painter.fillPath(range_path, range_gradient)

        # Draw handles
        for handle_type, x_pos in [
            (self.HANDLE_LOW, low_x),
            (self.HANDLE_HIGH, high_x),
        ]:
            is_hovered = self._hover_handle == handle_type
            is_pressed = self._pressed_handle == handle_type

            # Handle shadow
            painter.setBrush(QColor(0, 0, 0, 30))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(x_pos - self._handle_radius + 1),
                int(track_y - self._handle_radius + 1),
                self._handle_radius * 2,
                self._handle_radius * 2,
            )

            # Handle fill
            current_handle_color = handle_color
            if is_pressed:
                current_handle_color = handle_color.darker(110)
            elif is_hovered:
                current_handle_color = handle_color.darker(105)

            painter.setBrush(current_handle_color)
            painter.setPen(handle_border_color)
            painter.drawEllipse(
                int(x_pos - self._handle_radius),
                int(track_y - self._handle_radius),
                self._handle_radius * 2,
                self._handle_radius * 2,
            )

        # Draw value labels
        if self._show_values:
            font = painter.font()
            font.setPointSize(8)
            # font.setBold(True)
            painter.setFont(font)

            text_color = QColor(self.theme.text)
            bg_color = QColor(self.theme.surface)
            bg_color.setAlpha(200)

            from qtpy.QtCore import QRectF
            from qtpy.QtGui import QFontMetrics

            fm = QFontMetrics(font)

            # Low value label
            low_text = str(self._low)
            low_text_width = fm.horizontalAdvance(low_text) + 8
            low_text_height = fm.height() + 4
            low_rect = QRectF(
                low_x - low_text_width / 2,
                track_y - self._handle_radius - low_text_height - 4,
                low_text_width,
                low_text_height,
            )
            painter.setBrush(bg_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(low_rect, 3, 3)
            painter.setPen(text_color)
            painter.drawText(low_rect, Qt.AlignCenter, low_text)

            # High value label
            high_text = str(self._high)
            high_text_width = fm.horizontalAdvance(high_text) + 8
            high_text_height = fm.height() + 4
            high_rect = QRectF(
                high_x - high_text_width / 2,
                track_y + self._handle_radius + 4,
                high_text_width,
                high_text_height,
            )
            painter.setBrush(bg_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(high_rect, 3, 3)
            painter.setPen(text_color)
            painter.drawText(high_rect, Qt.AlignCenter, high_text)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            self._pressed_handle = self._handle_at_position(event.x())
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move."""
        if self._pressed_handle != self.HANDLE_NONE:
            value = self._position_to_value(event.x())
            if self._pressed_handle == self.HANDLE_LOW:
                self.low = min(value, self._high)
            else:
                self.high = max(value, self._low)
        else:
            # Update hover state
            new_hover = self._handle_at_position(event.x())
            if new_hover != self._hover_handle:
                self._hover_handle = new_hover
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._pressed_handle = self.HANDLE_NONE
            self.update()

    def leaveEvent(self, event) -> None:
        """Handle mouse leave."""
        self._hover_handle = self.HANDLE_NONE
        self.update()


def example() -> None:
    import sys
    from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXRangeSlider Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("Frame Range:"))
    slider1 = FXRangeSlider(minimum=1, maximum=250, low=50, high=200)
    slider1.range_changed.connect(lambda l, h: print(f"Range: {l} - {h}"))
    layout.addWidget(slider1)

    layout.addWidget(QLabel("Price Range ($):"))
    slider2 = FXRangeSlider(minimum=0, maximum=1000, low=100, high=500)
    layout.addWidget(slider2)

    layout.addWidget(QLabel("Percentage:"))
    slider3 = FXRangeSlider(minimum=0, maximum=100, low=25, high=75)
    layout.addWidget(slider3)

    layout.addStretch()
    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
