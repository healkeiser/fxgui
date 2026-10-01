"""A small clickable circle reporting a state in a feedback colour."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QRectF, Qt, Signal
from qtpy.QtGui import QColor, QPainter, QPalette
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import fxstyle


_FEEDBACK = ("success", "warning", "error", "info", "debug")


class FXStatusDot(QWidget):
    """A filled circle in a feedback colour, or grey for no state.

    Grey rather than a colour for off: every feedback colour is saturated,
    and a coloured dot reads as a state, not its absence.

    Args:
        parent: Parent widget.
        diameter: The circle's size in pixels.

    Signals:
        clicked: A left-button release landed on the dot.

    Examples:
        >>> dot = FXStatusDot()
        >>> dot.set_feedback("success", "Recording")
    """

    clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None, diameter: int = 8):
        super().__init__(parent)
        self._feedback: Optional[str] = None
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.PointingHandCursor)

    def set_feedback(self, key: Optional[str], tooltip: str = "") -> None:
        """Show feedback `key` ("success", "warning", ...); None for off.

        An unknown key shows as off. Repaints only on a change, so a timer
        may call this constantly.
        """
        known = key if key in _FEEDBACK else None
        self.setToolTip(tooltip)
        if known != self._feedback:
            self._feedback = known
            self.update()

    def color(self) -> QColor:
        """Return the colour the dot paints in now."""
        if self._feedback is None:
            return self.palette().color(QPalette.Disabled, QPalette.WindowText)
        token = f"feedback_{self._feedback}_foreground"
        return QColor(fxstyle.get_theme_colors()[token])

    def paintEvent(self, event) -> None:
        """Fill one antialiased circle, inset half a pixel so no edge is cut."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color())
        painter.drawEllipse(
            QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        )

    def mouseReleaseEvent(self, event) -> None:
        """Emit `clicked` on a left-button release."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)
