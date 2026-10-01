"""A layout that wraps its widgets onto new lines, like words in a paragraph."""

# Built-in
from typing import List, Optional

# Third-party
from qtpy.QtCore import QPoint, QRect, QSize, Qt
from qtpy.QtWidgets import QLayout, QLayoutItem, QWidget


class FXFlowLayout(QLayout):
    """Lay widgets out left to right, wrapping to a new line when full.

    A `QHBoxLayout` asks for every item's width at once, so a row of tags
    in a narrow dock widens the dock; this one grows taller instead.

    Args:
        parent: Widget the layout is set on.
        spacing: Gap in pixels between items, across and down.

    Examples:
        >>> flow = FXFlowLayout(spacing=4)
        >>> for tag in ("comp", "lighting", "fx"):
        ...     flow.addWidget(QLabel(tag))
    """

    def __init__(self, parent: Optional[QWidget] = None, spacing: int = 4):
        super().__init__(parent)
        self._items: List[QLayoutItem] = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:
        """Keep `item`, in order."""
        self._items.append(item)

    def count(self) -> int:
        """Return how many items are laid out."""
        return len(self._items)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        """Return the item at `index`, or `None` past the end."""
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        """Remove and return the item at `index`, or `None` past the end."""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        """Grow in neither direction: the width decides the height."""
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:
        """Say the height follows the width, as a wrap does."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Return the height wrapping into `width` takes."""
        return self._place(QRect(0, 0, width, 0), move=False)

    def setGeometry(self, rect: QRect) -> None:
        """Place every item inside `rect`, wrapping."""
        super().setGeometry(rect)
        self._place(rect, move=True)

    def sizeHint(self) -> QSize:
        """Return the minimum size: asking for more would widen the parent."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Return the widest single item: nothing narrower can hold it."""
        size = QSize()
        for item in self._shown():
            size = size.expandedTo(item.minimumSize())
        return size

    def _shown(self) -> List[QLayoutItem]:
        """Return the items that take room: a hidden widget takes none."""
        return [item for item in self._items if not item.isEmpty()]

    def _place(self, rect: QRect, move: bool) -> int:
        """Lay the items out in `rect`, moving them if `move`; return height."""
        x, y, line = rect.x(), rect.y(), 0
        for item in self._shown():
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line > 0:
                x, y, line = rect.x(), y + line + self.spacing(), 0
            if move:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self.spacing()
            line = max(line, hint.height())
        return y + line - rect.y()
