"""Custom scroll area widgets."""

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QScrollArea


class FXResizedScrollArea(QScrollArea):
    """A custom scroll area that emits a signal when resized.

    This widget extends QScrollArea to emit a `resized` signal whenever
    the widget is resized, which is useful for responsive layouts.

    Signals:
        resized: Emitted when the scroll area is resized.

    Examples:
        >>> scroll_area = FXResizedScrollArea()
        >>> scroll_area.resized.connect(lambda: print("Resized!"))
    """

    resized = Signal()

    def resizeEvent(self, event):
        """Emit the resized signal when the widget is resized."""
        self.resized.emit()
        return super().resizeEvent(event)
