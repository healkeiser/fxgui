"""A thin accent line along a widget's top edge while it is busy."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
)
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QProgressBar, QWidget

# Internal
from fxgui import _compat, fxstyle

# The line's thickness.
_HEIGHT = 2
# An indeterminate wait shows only past this, then creeps toward
# `_CREEP_TO` over `_CREEP_MS`, never quite arriving.
_DELAY_MS = 150
_CREEP_TO = 0.9
_CREEP_MS = 8000
# finish() runs the line to the end, then fades it, over this.
_FINISH_MS = fxstyle.MOTION_SLOW * 2


def _creep_curve() -> QEasingCurve:
    """Return the creep's curve: quick at first, slower and slower."""
    curve = QEasingCurve(QEasingCurve.BezierSpline)
    curve.addCubicBezierSegment(
        QPointF(0.1, 0.6), QPointF(0.2, 1.0), QPointF(1.0, 1.0))
    return curve


class FXTopProgress(QProgressBar):
    """A 2 px accent line over the top edge of its parent, while it works.

    Indeterminate by default: `start` shows it past 150 ms and it creeps
    toward 90 % until `finish` runs it to the end and fades it. Give a real
    fraction with `set_value` instead. It follows the parent's resizes,
    lets the mouse through, and is a progress bar to screen readers, busy
    while indeterminate. Under reduced motion, an indeterminate wait is a
    still, full line and `finish` hides it at once.

    Args:
        parent: The widget whose top edge the line runs along.

    Examples:
        >>> progress = FXTopProgress(panel)
        >>> progress.start()
        >>> progress.set_value(0.4)
        >>> progress.finish()
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 0)
        self.setFixedHeight(_HEIGHT)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName("Loading")
        # How much of the width the line covers, and how opaque it is.
        self._fraction = 0.0
        self._opacity = 1.0
        self._from = 0.0

        self._delay = QTimer(self)
        self._delay.setSingleShot(True)
        self._delay.setInterval(_DELAY_MS)
        self._delay.timeout.connect(self._creep)

        self._creeping = QVariantAnimation(self)
        self._creeping.setStartValue(0.0)
        self._creeping.setEndValue(_CREEP_TO)
        self._creeping.setDuration(_CREEP_MS)
        self._creeping.setEasingCurve(_creep_curve())
        self._creeping.valueChanged.connect(self._set_fraction)

        self._finishing = QVariantAnimation(self)
        self._finishing.setStartValue(0.0)
        self._finishing.setEndValue(1.0)
        self._finishing.setDuration(_FINISH_MS)
        self._finishing.setEasingCurve(fxstyle.ease_out())
        self._finishing.valueChanged.connect(self._finish_step)
        self._finishing.finished.connect(self.hide)

        if parent is not None:
            parent.installEventFilter(self)
            # A view's viewport is made by Qt, which keeps it past Python.
            _compat.hold(self)
            self._fit()
        self.hide()

    def fraction(self) -> float:
        """Return how much of the width the line covers now, 0 to 1."""
        return self._fraction

    def is_indeterminate(self) -> bool:
        """Return whether the line shows a wait of unknown length."""
        return self.maximum() == 0

    def start(self) -> None:
        """Show an indeterminate wait: a line creeping on until `finish`."""
        self._stop()
        self.setRange(0, 0)
        self._opacity = 1.0
        if not fxstyle.motion():
            self._set_fraction(1.0)
            self._show()
            return
        self._set_fraction(0.0)
        self._delay.start()

    def set_value(self, value: float) -> None:
        """Show a known progress: `value` from 0 (none) to 1 (done).

        Args:
            value: The fraction done; clamped to 0 to 1.
        """
        self._stop()
        value = min(1.0, max(0.0, float(value)))
        self.setRange(0, 100)
        self.setValue(round(value * 100))
        self._opacity = 1.0
        self._set_fraction(value)
        self._show()

    def finish(self) -> None:
        """End the wait: run the line to the end and fade it out."""
        waiting = self._delay.isActive()
        self._stop()
        if waiting or not self.isVisible() or not fxstyle.motion():
            # Never shown, or no motion: nothing to run out.
            self.hide()
            return
        if self.is_indeterminate():
            self.setRange(0, 100)
        self.setValue(100)
        self._from = self._fraction
        self._finishing.start()

    def _stop(self) -> None:
        self._delay.stop()
        self._creeping.stop()
        self._finishing.stop()

    def _creep(self) -> None:
        self._show()
        self._creeping.start()

    def _show(self) -> None:
        self._fit()
        self.show()
        self.raise_()

    def _set_fraction(self, value) -> None:
        self._fraction = float(value)
        self.update()

    def _finish_step(self, value) -> None:
        # The first half runs the line to the end; the second fades it.
        value = float(value)
        self._fraction = self._from + (1.0 - self._from) * min(1.0, value * 2)
        self._opacity = 1.0 - max(0.0, value * 2 - 1.0)
        self.update()

    def _fit(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(0, 0, parent.width(), _HEIGHT)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Follow the parent's width when it resizes."""
        if watched is self.parent() and event.type() == QEvent.Resize:
            self._fit()
        return super().eventFilter(watched, event)

    def paintEvent(self, event) -> None:
        """Paint the line, from the left, as far as `fraction`."""
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        painter.fillRect(
            QRectF(0, 0, self.width() * self._fraction, self.height()),
            QColor(fxstyle.colors().accent_primary),
        )
        painter.end()
