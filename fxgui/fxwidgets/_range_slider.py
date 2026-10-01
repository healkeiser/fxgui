"""Dual-handle range slider widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QRectF, QSize, Qt, Signal
from qtpy.QtGui import (
    QColor,
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
)
from qtpy.QtWidgets import QSizePolicy, QWidget

# Internal
from fxgui import fxstyle


class FXRangeSlider(QWidget):
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
    # Both handles under the press; the first move picks one.
    _HANDLE_TIED = 3

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
        self._press_x = 0.0
        self._hover_handle = self.HANDLE_NONE
        # Handle addressed by keyboard input (arrow keys); Tab toggles it
        # while the widget has focus.
        self._active_handle = self.HANDLE_LOW
        # A QSlider's 16 px handle on its 4 px groove.
        self._handle_radius = 8
        self._track_height = 4

        # Setup widget
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(70)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        # Keyboard: arrows adjust the active handle, Space switches handle
        self.setFocusPolicy(Qt.StrongFocus)
        fxstyle._watch_focus()

    def sizeHint(self):
        """Return the preferred size."""
        return QSize(200, 70)

    def minimumSizeHint(self):
        """Return the minimum size."""
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
        return round(self._minimum + ratio * value_range)

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

    def _handle_inks(self, handle: int):
        """Return a handle's fill, edge and edge width, as a QSlider's."""
        theme = fxstyle.colors()
        if not self.isEnabled():
            return theme.surface, theme.border, 2
        fill = (
            theme.accent_primary
            if handle == self._pressed_handle
            else theme.surface
        )
        edge = (
            theme.text
            if fxstyle.focus_visible(self) and self._active_handle == handle
            else theme.accent_primary
        )
        width = 4 if handle in (self._hover_handle, self._pressed_handle) else 2
        return fill, edge, width

    def paintEvent(self, event) -> None:
        """Paint the groove, the span between the handles, and the values."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        theme = fxstyle.colors()
        enabled = self.isEnabled()

        margin = self._handle_radius
        middle = self.height() // 2
        low_x = self._value_to_position(self._low)
        high_x = self._value_to_position(self._high)
        track = self._track_height
        top = middle - track // 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.surface_sunken))
        painter.drawRoundedRect(
            QRectF(margin, top, self.width() - margin * 2, track),
            track / 2,
            track / 2,
        )
        painter.setBrush(
            QColor(theme.accent_primary if enabled else theme.border_strong)
        )
        painter.drawRoundedRect(
            QRectF(low_x, top, high_x - low_x, track), track / 2, track / 2
        )

        side = self._handle_radius * 2
        for handle, x in ((self.HANDLE_LOW, low_x), (self.HANDLE_HIGH, high_x)):
            fill, edge, width = self._handle_inks(handle)
            painter.setBrush(QColor(fill))
            painter.setPen(QPen(QColor(edge), width))
            # Half the pen in, so the whole edge falls inside the circle.
            painter.drawEllipse(
                QRectF(
                    round(x) - self._handle_radius + width / 2,
                    middle - self._handle_radius + width / 2,
                    side - width,
                    side - width,
                )
            )

        if self._show_values:
            metrics = QFontMetrics(self.font())
            painter.setPen(QColor(theme.text if enabled else theme.text_disabled))
            gap = 4
            # Low label above its handle, high label below its own.
            for value, x, y in (
                (self._low, low_x, middle - self._handle_radius - gap
                 - metrics.height()),
                (self._high, high_x, middle + self._handle_radius + gap),
            ):
                text = str(value)
                width = metrics.horizontalAdvance(text)
                painter.drawText(
                    QRectF(x - width / 2, y, width, metrics.height()),
                    Qt.AlignCenter,
                    text,
                )

        painter.end()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Adjust the active handle from the keyboard.

        Left/Down and Right/Up move the active handle by 1, PageUp/PageDown
        by 10% of the range, Home/End jump it to the extremes, and Space
        switches between the low and high handle.
        """
        key = event.key()
        big_step = max(1, (self._maximum - self._minimum) // 10)

        def _adjust(delta: int) -> None:
            if self._active_handle == self.HANDLE_HIGH:
                self.high = self._high + delta
            else:
                self.low = self._low + delta

        if key in (Qt.Key_Right, Qt.Key_Up):
            _adjust(1)
        elif key in (Qt.Key_Left, Qt.Key_Down):
            _adjust(-1)
        elif key == Qt.Key_PageUp:
            _adjust(big_step)
        elif key == Qt.Key_PageDown:
            _adjust(-big_step)
        elif key == Qt.Key_Home:
            if self._active_handle == self.HANDLE_HIGH:
                self.high = self._low
            else:
                self.low = self._minimum
        elif key == Qt.Key_End:
            if self._active_handle == self.HANDLE_HIGH:
                self.high = self._maximum
            else:
                self.low = self._high
        elif key == Qt.Key_Space:
            self._active_handle = (
                self.HANDLE_HIGH
                if self._active_handle == self.HANDLE_LOW
                else self.HANDLE_LOW
            )
            self.update()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def focusInEvent(self, event) -> None:
        """Repaint to show the focus indicator."""
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:
        """Repaint to hide the focus indicator."""
        super().focusOutEvent(event)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            x = event.position().x()
            self._press_x = x
            self._pressed_handle = self._handle_at_position(x)
            if self._pressed_handle != self.HANDLE_NONE and self._low == self._high:
                self._pressed_handle = self._HANDLE_TIED
            if self._pressed_handle not in (self.HANDLE_NONE, self._HANDLE_TIED):
                # Keyboard input follows the last handle grabbed
                self._active_handle = self._pressed_handle
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move."""
        x = event.position().x()
        if self._pressed_handle == self._HANDLE_TIED:
            if x == self._press_x:
                return
            self._pressed_handle = (
                self.HANDLE_LOW if x < self._press_x else self.HANDLE_HIGH
            )
            self._active_handle = self._pressed_handle
        if self._pressed_handle != self.HANDLE_NONE:
            value = self._position_to_value(x)
            if self._pressed_handle == self.HANDLE_LOW:
                self.low = min(value, self._high)
            else:
                self.high = max(value, self._low)
        else:
            # Update hover state
            new_hover = self._handle_at_position(x)
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
