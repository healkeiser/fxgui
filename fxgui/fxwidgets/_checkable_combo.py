"""A combo box whose rows are ticked, several at a time."""

# Built-in
from typing import Iterable, List, Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, Qt, Signal
from qtpy.QtGui import QIcon, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QComboBox,
    QStyle,
    QStyleOptionComboBox,
    QStylePainter,
    QWidget,
)


class FXCheckableComboBox(QComboBox):
    """A combo whose popup stays open while several rows are ticked.

    A plain `QComboBox` closes its popup on the first click, so ticking
    three values would take three openings. Here a click or Space ticks
    the row and the popup stays; the closed combo reads the ticked rows.

    Args:
        parent: Parent widget.

    Signals:
        checked_changed: The ticked rows' texts, in row order.

    Examples:
        >>> combo = FXCheckableComboBox()
        >>> combo.add_items(["render", "cache", "plate"])
        >>> combo.set_checked_items(["cache"])
    """

    checked_changed = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._said: List[str] = []
        self._setting = False
        self.setModel(QStandardItemModel(self))
        self.model().itemChanged.connect(self._on_item_changed)
        self.view().viewport().installEventFilter(self)
        self.view().installEventFilter(self)

    def add_items(self, texts: Iterable[str]) -> None:
        """Add one unticked row per text."""
        for text in texts:
            item = QStandardItem(text)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            self.model().appendRow(item)

    def checked_items(self) -> List[str]:
        """Return the ticked rows' texts, in row order."""
        return [
            item.text() for item in self._items()
            if item.checkState() == Qt.Checked
        ]

    def set_checked_items(self, texts: Iterable[str]) -> None:
        """Tick exactly the rows whose text is in `texts`."""
        wanted = set(texts)
        self._setting = True
        try:
            for item in self._items():
                item.setCheckState(
                    Qt.Checked if item.text() in wanted else Qt.Unchecked
                )
        finally:
            self._setting = False
        self._on_item_changed()

    def display_text(self) -> str:
        """Return what the closed combo reads: the ticked rows, joined."""
        return ", ".join(self.checked_items())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Tick a row on a click or Space, and keep the popup open."""
        view = self.view()
        if watched is view.viewport() and event.type() in (
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
        ):
            # The press is swallowed too: Qt closes the popup on either.
            if event.type() == QEvent.MouseButtonRelease:
                self._toggle(view.indexAt(event.pos()).row())
            return True
        if (
            watched is view
            and event.type() == QEvent.KeyPress
            and event.key() == Qt.Key_Space
        ):
            self._toggle(view.currentIndex().row())
            return True
        return super().eventFilter(watched, event)

    def paintEvent(self, event) -> None:
        """Draw the combo with the ticked rows as its text."""
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = self.display_text()
        option.currentIcon = QIcon()
        painter.drawComplexControl(QStyle.CC_ComboBox, option)
        painter.drawControl(QStyle.CE_ComboBoxLabel, option)

    def _items(self) -> List[QStandardItem]:
        model = self.model()
        return [model.item(row) for row in range(model.rowCount())]

    def _toggle(self, row: int) -> None:
        item = self.model().item(row) if row >= 0 else None
        if item is not None:
            item.setCheckState(
                Qt.Unchecked
                if item.checkState() == Qt.Checked
                else Qt.Checked
            )

    def _on_item_changed(self, *_) -> None:
        if self._setting:
            return
        self.update()
        checked = self.checked_items()
        if checked != self._said:
            self._said = checked
            self.checked_changed.emit(checked)
