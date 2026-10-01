"""Animated loading indicator widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, QRectF, Qt, QTimer
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
    """A quarter arc of the accent running round a muted ring.

    The animation runs only while the spinner can be seen.

    Args:
        parent: Parent widget.
        size: Size of the spinner in pixels. Defaults to a button's height.
        line_width: Width of the ring. Defaults to a tenth of `size`, 2 px
            at least.
        color: The arc's color: a theme token name, followed through a
            switch, or a colour. Defaults to `accent_primary`; the ring is
            ``border_light``.

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
        color: str = "accent_primary",
    ):
        super().__init__(parent)
        self._size = size or fxstyle.control_height(self)
        self._line_width = line_width or max(2, round(self._size / 10))
        self._color = color
        self._angle = 0
        self._is_spinning = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(self._size, self._size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def start(self) -> None:
        """Start the animation, and show the spinner."""
        self._is_spinning = True
        self.show()
        self._run_timer()

    def stop(self) -> None:
        """Stop the animation."""
        self._is_spinning = False
        self._run_timer()

    def showEvent(self, event) -> None:
        """Resume the animation a hide paused."""
        super().showEvent(event)
        self._run_timer()

    def hideEvent(self, event) -> None:
        """Pause the animation while nothing can see it."""
        super().hideEvent(event)
        self._run_timer()

    def _run_timer(self) -> None:
        # A spinner shown under a hidden parent, such as the row of a
        # closed branch, never gets a hide event; ask whether it shows.
        if self._is_spinning and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()

    def is_spinning(self) -> bool:
        """Return whether the spinner is started."""
        return self._is_spinning

    def set_color(self, color: str) -> None:
        """Set the arc's color: a theme token name or a colour."""
        self._color = color
        self.update()

    def _rotate(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def _pen(self, color: str) -> QPen:
        pen = QPen(QColor(color))
        pen.setWidth(self._line_width)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def paintEvent(self, event) -> None:
        """Paint the muted ring, then the arc over it."""
        colors = fxstyle.colors()
        inset = self._line_width / 2 + 1
        ring = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self._pen(colors.border_light))
        painter.drawEllipse(ring)
        painter.setPen(self._pen(vars(colors).get(self._color, self._color)))
        painter.drawArc(ring, -self._angle * 16, 90 * 16)
        painter.end()


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
        # A scrim, black in every theme as a shadow is.
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))
        painter.end()
