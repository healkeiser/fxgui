"""A search bar over a tree (or a flat list) that matches loosely."""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from typing import Dict, Iterator, List, Optional, Union

# Third-party
from qtpy.QtCore import QModelIndex, Qt, Signal, Slot
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons
from fxgui.fxcore import FXSortFilterProxyModel
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._tips import apply_tip


class FXFuzzySearchTree(QWidget):
    """A search bar, an optional ratio slider and a fuzzy-filtered tree.

    Rows are ranked and coloured by how well they match. A parent stays
    visible while one of its descendants matches. Given only top-level
    items it is a flat list: the tree draws no branch column until an item
    has a parent. Items are looked up by text, the first in tree order;
    pass a `QStandardItem` as `parent` to pick a specific one.

    Args:
        parent: Parent widget.
        placeholder: Placeholder text for the search input.
        ratio: Initial similarity ratio threshold (0.0 to 1.0).
        show_ratio_slider: Whether to show the ratio adjustment slider.
        color_match: Whether to color items based on match quality.

    Signals:
        item_selected: An item was clicked; its text.
        item_double_clicked: An item was double-clicked; its text.
        item_activated: Enter was pressed on an item; its text.
        selection_changed: The selection changed; the selected texts.
        item_expanded: An item was expanded; its text.
        item_collapsed: An item was collapsed; its text.

    Examples:
        >>> fuzzy = FXFuzzySearchTree(placeholder="Search fruits...")
        >>> fuzzy.set_items(["apple", "apricot", "banana"])
        >>> fuzzy.item_selected.connect(print)
        >>> fuzzy.set_items({"Props": ["sword", "shield"]})
    """

    #: The role `add_item` stores its `data` dictionary under.
    DATA_ROLE = Qt.UserRole

    item_selected = Signal(str)
    item_double_clicked = Signal(str)
    item_activated = Signal(str)
    selection_changed = Signal(list)
    item_expanded = Signal(str)
    item_collapsed = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Search...",
        ratio: float = 0.5,
        show_ratio_slider: bool = False,
        color_match: bool = True,
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._search_bar = FXSearchBar(
            parent=self, placeholder=placeholder, debounce_ms=150
        )
        layout.addWidget(self._search_bar)
        self.setFocusProxy(self._search_bar)

        self._slider_container = QWidget()
        slider_layout = QHBoxLayout(self._slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(8)

        self._ratio_icon = FXIconLabel()
        fxicons.set_icon(self._ratio_icon, "tune")
        apply_tip(
            self._ratio_icon, "Sensitivity", "Adjust fuzzy matching sensitivity"
        )
        slider_layout.addWidget(self._ratio_icon)

        self._ratio_slider = QSlider(Qt.Horizontal)
        self._ratio_slider.setRange(0, 100)
        apply_tip(
            self._ratio_slider,
            "Match Threshold",
            "Lower = more results (looser match), Higher = fewer results "
            "(stricter match)",
        )
        slider_layout.addWidget(self._ratio_slider, 1)

        self._ratio_label = QLabel()
        self._ratio_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._ratio_label.setMinimumWidth(
            self._ratio_label.fontMetrics().horizontalAdvance("100%")
        )
        slider_layout.addWidget(self._ratio_label)

        self._slider_container.setVisible(show_ratio_slider)
        layout.addWidget(self._slider_container)

        self._source_model = QStandardItemModel(self)
        self._proxy_model = FXSortFilterProxyModel(
            ratio=ratio, color_match=color_match, parent=self
        )
        self._proxy_model.setRecursiveFilteringEnabled(True)
        self._proxy_model.setSourceModel(self._source_model)
        self.set_ratio(ratio)

        self._view = QTreeView()
        self._view.setHeaderHidden(True)
        self._view.setAnimated(True)
        self._view.setRootIsDecorated(False)
        self._view.setModel(self._proxy_model)
        self._view.setAlternatingRowColors(True)
        self._view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._view, 1)

        self._search_bar.search_changed.connect(self._on_search_changed)
        self._search_bar.search_submitted.connect(self._on_search_submitted)
        self._ratio_slider.valueChanged.connect(
            lambda value: self.set_ratio(value / 100.0)
        )
        self._view.clicked.connect(self._emitter(self.item_selected))
        self._view.doubleClicked.connect(
            self._emitter(self.item_double_clicked)
        )
        self._view.activated.connect(self._emitter(self.item_activated))
        self._view.expanded.connect(self._emitter(self.item_expanded))
        self._view.collapsed.connect(self._emitter(self.item_collapsed))
        self._view.selectionModel().selectionChanged.connect(
            lambda *_: self.selection_changed.emit(self.selected_items())
        )

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @staticmethod
    def _emitter(signal):
        """Return a slot that emits `signal` with an index's text, if any."""

        def emit(index: QModelIndex) -> None:
            text = index.data(Qt.DisplayRole)
            if text:
                signal.emit(text)

        return emit

    @Slot(str)
    def _on_search_changed(self, text: str) -> None:
        """Filter the tree, expanding it so matches show."""
        self._proxy_model.set_filter_text(text)
        if text:
            self._view.expandAll()

    @Slot(str)
    def _on_search_submitted(self, _text: str) -> None:
        """Make the first row current and activate it."""
        if self._proxy_model.rowCount() > 0:
            first = self._proxy_model.index(0, 0)
            self._view.setCurrentIndex(first)
            self.item_activated.emit(first.data(Qt.DisplayRole))

    def _walk(self) -> Iterator[QStandardItem]:
        """Yield every item, depth first, in tree order."""
        stack = [
            self._source_model.item(row)
            for row in reversed(range(self._source_model.rowCount()))
        ]
        while stack:
            item = stack.pop()
            yield item
            stack.extend(
                item.child(row) for row in reversed(range(item.rowCount()))
            )

    def _proxy_index(self, text: str) -> QModelIndex:
        """Return the proxy index of the first item with this text."""
        item = self.get_item(text)
        if item is None:
            return QModelIndex()
        return self._proxy_model.mapFromSource(item.index())

    # Public API

    def view(self) -> QTreeView:
        """Return the tree view."""
        return self._view

    def source_model(self) -> QStandardItemModel:
        """Return the model the items live in."""
        return self._source_model

    def proxy_model(self) -> FXSortFilterProxyModel:
        """Return the filtering proxy the view shows."""
        return self._proxy_model

    def clear(self) -> None:
        """Remove every item."""
        self._source_model.clear()
        self._view.setRootIsDecorated(False)

    def set_items(self, items: Union[List[str], Dict[str, List[str]]]) -> None:
        """Replace the items with a flat list, or parents mapped to children."""
        self.clear()
        if isinstance(items, dict):
            for parent_text, children in items.items():
                parent_item = self.add_item(parent_text)
                for child_text in children:
                    self.add_item(child_text, parent=parent_item)
        else:
            for item_text in items:
                self.add_item(item_text)

    def add_item(
        self,
        text: str,
        parent: Optional[Union[str, QStandardItem]] = None,
        data: Optional[dict] = None,
    ) -> QStandardItem:
        """Add one item and return it.

        Args:
            text: The item text.
            parent: The parent item, or its text. Top level when None or
                when no item has that text.
            data: A dictionary stored under `DATA_ROLE`.
        """
        item = QStandardItem(text)
        if data:
            item.setData(dict(data), self.DATA_ROLE)
        if isinstance(parent, str):
            parent = self.get_item(parent)
        if parent is not None:
            parent.appendRow(item)
            self._view.setRootIsDecorated(True)
        else:
            self._source_model.appendRow(item)
        return item

    def remove_item(self, text: str) -> bool:
        """Remove the first item with this text and its children.

        Returns:
            True if an item was found and removed.
        """
        item = self.get_item(text)
        if item is None:
            return False
        parent = item.parent() or self._source_model.invisibleRootItem()
        parent.removeRow(item.row())
        return True

    def get_item(self, text: str) -> Optional[QStandardItem]:
        """Return the first item with this text, or None."""
        return next(
            (item for item in self._walk() if item.text() == text), None
        )

    def items(self) -> List[str]:
        """Return every item text, nested ones included, in tree order."""
        return [item.text() for item in self._walk()]

    def selected_items(self) -> List[str]:
        """Return the texts of the selected items."""
        selection = self._view.selectionModel().selectedIndexes()
        return [index.data(Qt.DisplayRole) for index in selection if index.data()]

    def current_item(self) -> Optional[str]:
        """Return the current item's text, or None."""
        index = self._view.currentIndex()
        return index.data(Qt.DisplayRole) if index.isValid() else None

    def select_item(self, text: str) -> bool:
        """Make the first item with this text current.

        Returns:
            True if the item was found and is visible.
        """
        index = self._proxy_index(text)
        if index.isValid():
            self._view.setCurrentIndex(index)
            return True
        return False

    def expand_item(self, text: str) -> bool:
        """Expand the first item with this text; False if not shown."""
        index = self._proxy_index(text)
        if index.isValid():
            self._view.expand(index)
            return True
        return False

    def collapse_item(self, text: str) -> bool:
        """Collapse the first item with this text; False if not shown."""
        index = self._proxy_index(text)
        if index.isValid():
            self._view.collapse(index)
            return True
        return False

    def expand_all(self) -> None:
        """Expand every item."""
        self._view.expandAll()

    def collapse_all(self) -> None:
        """Collapse every item."""
        self._view.collapseAll()

    def search_text(self) -> str:
        """Return the search text."""
        return self._search_bar.text

    def set_search_text(self, text: str) -> None:
        """Set the search text."""
        self._search_bar.text = text

    def ratio(self) -> float:
        """Return the similarity threshold, 0.0 to 1.0."""
        return self._proxy_model.ratio()

    def set_ratio(self, ratio: float) -> None:
        """Set the similarity threshold, clamped to 0.0 to 1.0."""
        ratio = max(0.0, min(1.0, ratio))
        blocked = self._ratio_slider.blockSignals(True)
        self._ratio_slider.setValue(round(ratio * 100))
        self._ratio_slider.blockSignals(blocked)
        self._ratio_label.setText(f"{round(ratio * 100)}%")
        self._proxy_model.set_ratio(ratio)

    def show_ratio_slider(self, visible: bool = True) -> None:
        """Show or hide the ratio slider."""
        self._slider_container.setVisible(visible)
