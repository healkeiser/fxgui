"""Custom scroll area widgets."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QSize
from qtpy.QtWidgets import QScrollArea, QWidget


class FXResizedScrollArea(QScrollArea):
    """A scroll area that can fit its content.

    Given a `floor` or a `cap`, its minimum height is its content's height,
    held between the two, and follows the content as rows come and go: the
    area grows with a short list and scrolls a long one. Qt loses the
    content's height a few layouts deep, so it is read here.

    Args:
        parent: Parent widget.
        floor: The least height, in pixels, however short the content.
        cap: The most height the content may ask for; past it, it scrolls.

    Examples:
        >>> checks = FXResizedScrollArea(floor=60, cap=240)
        >>> checks.setWidgetResizable(True)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        floor: Optional[int] = None,
        cap: Optional[int] = None,
    ):
        super().__init__(parent)
        self._floor = floor
        self._cap = cap

    def minimumSizeHint(self) -> QSize:
        """Return the content's height between `floor` and `cap`, if set."""
        hint = super().minimumSizeHint()
        content = self.widget()
        if content is None or (self._floor is None and self._cap is None):
            return hint
        height = max(content.sizeHint().height(), self._floor or 0)
        if self._cap is not None:
            height = min(height, self._cap)
        return QSize(hint.width(), height)

    def viewportEvent(self, event: QEvent) -> bool:
        """Tell the layout outside when the content's height changes."""
        handled = super().viewportEvent(event)
        if event.type() == QEvent.LayoutRequest:
            self.updateGeometry()
        return handled
