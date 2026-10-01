"""Animated loading indicator widget."""

# Built-in
import math
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QTimer
from qtpy.QtGui import QColor, QPainter, QPen
from qtpy.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle


fxstyle.register_widget_style(
    """
    FXLoadingOverlay QLabel {
        color: @text;
        font-size: 14px;
        margin-top: 12px;
    }
    """
)


class FXLoadingSpinner(QWidget):
    """A themeable animated loading indicator.

    This widget provides a modern spinning/pulsing loading indicator
    with customizable colors and animation styles.

    Args:
        parent: Parent widget.
        size: Size of the spinner in pixels. Defaults to a button's height.
        line_width: Width of the spinner lines. Defaults to a tenth of
            `size`, 2 px at least.
        color: The moving part's color. If None, the theme accent; the
            rest is the muted ``border_light``.
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
        size: Optional[int] = None,
        line_width: Optional[int] = None,
        color: Optional[str] = None,
        style: str = "spinner",
    ):
        super().__init__(parent)

        # Properties
        self._size = size or fxstyle.control_height(self)
        self._line_width = line_width or max(2, round(self._size / 10))
        self._custom_color = color  # Store custom color (None means use theme)
        self._style = style
        self._angle = 0
        self._is_spinning = False

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)

        # Setup widget
        self.setFixedSize(self._size, self._size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

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

    def showEvent(self, event) -> None:
        """Resume the animation a hide paused."""
        super().showEvent(event)
        if self._is_spinning:
            self._timer.start(16)

    def hideEvent(self, event) -> None:
        """Pause the animation while nothing can see it."""
        super().hideEvent(event)
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
        return QColor(fxstyle.colors().accent_primary)

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

    def _pen(self, color: str) -> QPen:
        pen = QPen(QColor(color))
        pen.setWidth(self._line_width)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def _ring(self) -> QRectF:
        inset = self._line_width / 2 + 1
        return QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)

    def _paint_spinner(self, painter: QPainter) -> None:
        """Paint a quarter arc of the accent running round a muted ring."""
        painter.setPen(self._pen(fxstyle.colors().border_light))
        painter.drawEllipse(self._ring())
        painter.setPen(self._pen(self._get_color().name()))
        painter.drawArc(self._ring(), -self._angle * 16, 90 * 16)

    def _paint_dots(self, painter: QPainter) -> None:
        """Paint a ring of dots, muted, the leading one in the accent."""
        center = self._size / 2
        dot = max(2.0, self._line_width * 0.9)
        radius = center - dot - 1
        count = 8
        track, accent = fxstyle.colors().border_light, self._get_color().name()
        painter.setPen(Qt.NoPen)
        for i in range(count):
            angle = math.radians(self._angle + i * 360 / count)
            # Opaque steps from the track to the accent, so no dot is a
            # see-through accent that loses its contrast on the surface.
            painter.setBrush(QColor(fxstyle.mix(track, accent, i / (count - 1))))
            painter.drawEllipse(
                QPointF(
                    center + radius * math.cos(angle),
                    center + radius * math.sin(angle),
                ),
                dot,
                dot,
            )

    def _paint_pulse(self, painter: QPainter) -> None:
        """Paint an accent ring breathing inside a muted one."""
        painter.setPen(self._pen(fxstyle.colors().border_light))
        ring = self._ring()
        painter.drawEllipse(ring)
        scale = 0.35 + 0.65 * abs(math.sin(math.radians(self._angle * 2)))
        inset = ring.width() * (1 - scale) / 2
        painter.setPen(self._pen(self._get_color().name()))
        painter.drawEllipse(ring.adjusted(inset, inset, -inset, -inset))


class FXLoadingOverlay(QWidget):
    """A loading spinner centred over the parent widget.

    By default the overlay dims the parent and takes its mouse, for a long
    operation the user must wait out. A view still usable while its rows
    load passes `dim=False, block_input=False`.

    Args:
        parent: Parent widget to overlay.
        message: Optional message to display below the spinner.
        dim: Whether to darken the parent behind the spinner.
        block_input: Whether the overlay takes the parent's mouse.
        size: The spinner's diameter in pixels.

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
        dim: bool = True,
        block_input: bool = True,
        size: int = 48,
    ):
        super().__init__(parent)
        self._dim = dim
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not block_input)
        if parent is not None:
            parent.installEventFilter(self)

        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Spinner
        self._spinner = FXLoadingSpinner(self, size=size)
        layout.addWidget(self._spinner, 0, Qt.AlignCenter)

        # Message label
        self._message_label = None
        if message:
            self._message_label = QLabel(message)
            layout.addWidget(self._message_label, 0, Qt.AlignCenter)

        self.hide()

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

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Cover the parent again when it resizes."""
        if watched is self.parent() and event.type() == QEvent.Resize:
            self.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def paintEvent(self, event) -> None:
        """Paint the semi-transparent background, if dimming."""
        if not self._dim:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))
        painter.end()
