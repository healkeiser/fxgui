"""Animated loading indicator widget."""

# Built-in
import os
import math
from typing import Optional

# Third-party
from qtpy.QtCore import Property, Qt, QTimer
from qtpy.QtGui import QColor, QPainter, QPen
from qtpy.QtWidgets import QSizePolicy, QWidget

# Internal
from fxgui import fxstyle


class FXLoadingSpinner(fxstyle.FXThemeAware, QWidget):
    """A themeable animated loading indicator.

    This widget provides a modern spinning/pulsing loading indicator
    with customizable colors and animation styles.

    Args:
        parent: Parent widget.
        size: Size of the spinner in pixels.
        line_width: Width of the spinner lines.
        color: Spinner color. If None, uses theme accent.
        style: Animation style ('spinner', 'dots', 'pulse').

    Examples:
        >>> spinner = FXLoadingSpinner(size=32)
        >>> spinner.start()
        >>> # ... do some work ...
        >>> spinner.stop()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        size: int = 32,
        line_width: int = 3,
        color: Optional[str] = None,
        style: str = "spinner",
    ):
        super().__init__(parent)

        # Properties
        self._size = size
        self._line_width = line_width
        self._custom_color = color  # Store custom color (None means use theme)
        self._style = style
        self._angle = 0
        self._is_spinning = False

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)

        # Setup widget
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    @Property(int)
    def angle(self) -> int:
        """The current rotation angle."""
        return self._angle

    @angle.setter
    def angle(self, value: int) -> None:
        """Set the rotation angle."""
        self._angle = value % 360
        self.update()

    def start(self) -> None:
        """Start the loading animation."""
        if not self._is_spinning:
            self._is_spinning = True
            self._timer.start(16)  # ~60 FPS
            self.show()

    def stop(self) -> None:
        """Stop the loading animation."""
        self._is_spinning = False
        self._timer.stop()

    def is_spinning(self) -> bool:
        """Return whether the spinner is currently animating."""
        return self._is_spinning

    def set_color(self, color: str) -> None:
        """Set the spinner color.

        Args:
            color: Color string (hex, rgb, etc.).
        """
        self._custom_color = color
        self.update()

    def _get_color(self) -> QColor:
        """Get the current spinner color (theme-aware)."""
        if self._custom_color:
            return QColor(self._custom_color)
        return QColor(self.theme.accent_primary)

    def set_style(self, style: str) -> None:
        """Set the animation style.

        Args:
            style: Animation style ('spinner', 'dots', 'pulse').
        """
        self._style = style
        self.update()

    def _rotate(self) -> None:
        """Rotate the spinner."""
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the loading spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._style == "spinner":
            self._paint_spinner(painter)
        elif self._style == "dots":
            self._paint_dots(painter)
        elif self._style == "pulse":
            self._paint_pulse(painter)
        else:
            self._paint_spinner(painter)

        painter.end()

    def _paint_spinner(self, painter: QPainter) -> None:
        """Paint the spinner style."""

        # Get current color (theme-aware)
        color = self._get_color()

        # Create gradient arc
        pen = QPen(color)
        pen.setWidth(self._line_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Draw arc segments with varying opacity
        num_segments = 12
        segment_angle = 360 // num_segments

        for i in range(num_segments):
            # Calculate opacity based on segment position
            opacity = (i + 1) / num_segments
            segment_color = QColor(color)
            segment_color.setAlphaF(opacity)

            pen.setColor(segment_color)
            painter.setPen(pen)

            # Calculate start angle for this segment
            start_angle = (self._angle + i * segment_angle) % 360

            # Draw arc segment
            painter.drawArc(
                self._line_width,
                self._line_width,
                self._size - self._line_width * 2,
                self._size - self._line_width * 2,
                start_angle * 16,
                segment_angle * 16,
            )

    def _paint_dots(self, painter: QPainter) -> None:
        """Paint the dots style."""
        center = self._size // 2
        radius = center - 6
        num_dots = 8
        dot_radius = 3

        # Get current color (theme-aware)
        color = self._get_color()

        for i in range(num_dots):
            # Calculate dot position
            angle_rad = math.radians(self._angle + i * (360 / num_dots))
            x = center + radius * math.cos(angle_rad)
            y = center + radius * math.sin(angle_rad)

            # Calculate opacity based on position
            opacity = (i + 1) / num_dots
            dot_color = QColor(color)
            dot_color.setAlphaF(opacity)

            painter.setBrush(dot_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(x - dot_radius),
                int(y - dot_radius),
                dot_radius * 2,
                dot_radius * 2,
            )

    def _paint_pulse(self, painter: QPainter) -> None:
        """Paint the pulse style."""
        center = self._size // 2

        # Get current color (theme-aware)
        color = self._get_color()

        # Calculate pulse scale based on angle
        scale = 0.5 + 0.5 * abs(math.sin(math.radians(self._angle * 2)))
        radius = int((center - self._line_width) * scale)

        # Calculate opacity (inverse of scale for breathing effect)
        opacity = 1.0 - scale * 0.5

        pulse_color = QColor(color)
        pulse_color.setAlphaF(opacity)

        pen = QPen(pulse_color)
        pen.setWidth(self._line_width)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        painter.drawEllipse(
            center - radius, center - radius, radius * 2, radius * 2
        )

        # Inner circle
        inner_radius = int(radius * 0.5)
        inner_color = QColor(color)
        inner_color.setAlphaF(opacity * 0.5)
        painter.setBrush(inner_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            center - inner_radius,
            center - inner_radius,
            inner_radius * 2,
            inner_radius * 2,
        )


class FXLoadingOverlay(fxstyle.FXThemeAware, QWidget):
    """A loading overlay that blocks the parent widget.

    This widget creates a semi-transparent overlay with a loading
    spinner, useful for indicating that a long operation is in progress.

    Args:
        parent: Parent widget to overlay.
        message: Optional message to display below the spinner.

    Examples:
        >>> overlay = FXLoadingOverlay(my_widget, "Loading assets...")
        >>> overlay.show()
        >>> # ... do some work ...
        >>> overlay.hide()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: Optional[str] = None,
    ):
        super().__init__(parent)

        from qtpy.QtWidgets import QVBoxLayout, QLabel

        # Setup overlay
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(
            """
            FXLoadingOverlay {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """
        )

        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Spinner
        self._spinner = FXLoadingSpinner(self, size=48)
        layout.addWidget(self._spinner, 0, Qt.AlignCenter)

        # Message label
        self._message_label = None
        if message:
            self._message_label = QLabel(message)
            layout.addWidget(self._message_label, 0, Qt.AlignCenter)

        self.hide()

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        if self._message_label:
            self._message_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {self.theme.text};
                    font-size: 14px;
                    margin-top: 12px;
                }}
            """
            )

    def show(self) -> None:
        """Show the overlay and start the spinner."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().show()
        self.raise_()
        self._spinner.start()

    def hide(self) -> None:
        """Hide the overlay and stop the spinner."""
        self._spinner.stop()
        super().hide()

    def resizeEvent(self, event) -> None:
        """Handle parent resize."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        """Paint the semi-transparent background."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))
        painter.end()


def example() -> None:
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QGroupBox
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXLoadingSpinner Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QHBoxLayout(widget)

    # Spinner style
    spinner_group = QGroupBox("Spinner")
    spinner_layout = QVBoxLayout(spinner_group)
    spinner = FXLoadingSpinner(size=48, style="spinner")
    spinner.start()
    spinner_layout.addWidget(spinner)
    layout.addWidget(spinner_group)

    # Dots style
    dots_group = QGroupBox("Dots")
    dots_layout = QVBoxLayout(dots_group)
    dots = FXLoadingSpinner(size=48, style="dots")
    dots.start()
    dots_layout.addWidget(dots)
    layout.addWidget(dots_group)

    # Pulse style
    pulse_group = QGroupBox("Pulse")
    pulse_layout = QVBoxLayout(pulse_group)
    pulse = FXLoadingSpinner(size=48, style="pulse")
    pulse.start()
    pulse_layout.addWidget(pulse)
    layout.addWidget(pulse_group)

    window.adjustSize()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
