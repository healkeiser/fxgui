"""Fuzzy search tree widget with relevance-based filtering and sorting."""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from typing import Dict, Iterator, List, Optional, Union

# Third-party
from qtpy.QtCore import Qt, Signal, Slot, QModelIndex
from qtpy.QtGui import QStandardItem
from qtpy.QtWidgets import QTreeView

# Internal
from fxgui.fxwidgets._fuzzy_search_list import _FXFuzzySearchBase


class FXFuzzySearchTree(_FXFuzzySearchBase):
    """A searchable tree widget with fuzzy matching capabilities.

    This widget combines a search bar with a tree view that uses fuzzy matching
    to filter and sort items by relevance. Items are colored based on their
    match quality.

    The tree supports hierarchical data with parent-child relationships.
    When filtering, parent items remain visible if any of their descendants
    match. Items are looked up by text: with duplicate texts the first one
    in tree order is used, and passing a `QStandardItem` as `parent` picks
    a specific one.

    Args:
        parent: Parent widget.
        placeholder: Placeholder text for the search input.
        ratio: Initial similarity ratio threshold (0.0 to 1.0).
        show_ratio_slider: Whether to show the ratio adjustment slider.
        color_match: Whether to color items based on match quality.

    Signals:
        item_selected: Emitted when an item is clicked. Passes the item text.
        item_double_clicked: Emitted when an item is double-clicked.
            Passes the item text.
        item_activated: Emitted when Enter is pressed on an item.
            Passes the item text.
        selection_changed: Emitted when the selection changes.
            Passes a list of selected item texts.
        item_expanded: Emitted when an item is expanded. Passes the item text.
        item_collapsed: Emitted when an item is collapsed. Passes the item text.

    Examples:
        Basic usage with hierarchical data:

        >>> fuzzy_tree = FXFuzzySearchTree(placeholder="Search assets...")
        >>> fuzzy_tree.add_item("Characters")
        >>> fuzzy_tree.add_item("Hero", parent="Characters")
        >>> fuzzy_tree.add_item("Villain", parent="Characters")
        >>> fuzzy_tree.item_selected.connect(lambda text: print(f"Selected: {text}"))

        With ratio slider for user adjustment:

        >>> fuzzy_tree = FXFuzzySearchTree(show_ratio_slider=True, ratio=0.6)
        >>> fuzzy_tree.set_items({
        ...     "Props": ["sword", "shield", "chair"],
        ...     "Vehicles": ["car", "truck", "motorcycle"],
        ... })
    """

    #: The role `add_item` stores its `data` dictionary under.
    DATA_ROLE = Qt.UserRole

    item_expanded = Signal(str)
    item_collapsed = Signal(str)

    def _make_view(self) -> QTreeView:
        """Return the tree view, with a proxy that keeps matches' parents."""
        self._proxy_model.setRecursiveFilteringEnabled(True)
        view = QTreeView()
        view.setHeaderHidden(True)
        view.setAnimated(True)
        return view

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        super()._connect_signals()
        self._view.expanded.connect(self._on_item_expanded)
        self._view.collapsed.connect(self._on_item_collapsed)

    @Slot(str)
    def _on_search_changed(self, text: str) -> None:
        """Filter the tree, expanding it so matches show."""
        super()._on_search_changed(text)
        if text:
            self._view.expandAll()

    @Slot(QModelIndex)
    def _on_item_expanded(self, index: QModelIndex) -> None:
        """Handle item expansion."""
        text = index.data(Qt.DisplayRole)
        if text:
            self.item_expanded.emit(text)

    @Slot(QModelIndex)
    def _on_item_collapsed(self, index: QModelIndex) -> None:
        """Handle item collapse."""
        text = index.data(Qt.DisplayRole)
        if text:
            self.item_collapsed.emit(text)

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

    def set_items(self, items: Union[List[str], Dict[str, List[str]]]) -> None:
        """Set the tree items from a list or dictionary.

        Args:
            items: Either a flat list of strings (creates top-level items),
                or a dictionary where keys are parent items and values are
                lists of child items.
        """
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
        """Add a single item to the tree.

        Args:
            text: The item text to add.
            parent: The parent item, or its text. Top level when None or
                when no item has that text.
            data: Optional dictionary stored under `DATA_ROLE`.

        Returns:
            The created QStandardItem.
        """
        item = QStandardItem(text)
        if data:
            item.setData(dict(data), self.DATA_ROLE)

        if isinstance(parent, str):
            parent = self.get_item(parent)
        if parent is not None:
            parent.appendRow(item)
        else:
            self._source_model.appendRow(item)
        return item

    def remove_item(self, text: str) -> bool:
        """Remove the first item with this text, and its children.

        Returns:
            True if the item was found and removed, False otherwise.
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

    @property
    def items(self) -> List[str]:
        """Return every item text, nested ones included, in tree order."""
        return [item.text() for item in self._walk()]

    @property
    def top_level_items(self) -> List[str]:
        """Return the top-level item texts."""
        return [
            self._source_model.item(row).text()
            for row in range(self._source_model.rowCount())
            if self._source_model.item(row)
        ]

    def select_item(self, text: str) -> bool:
        """Make the first item with this text current.

        Returns:
            True if the item was found and visible, False otherwise.
        """
        index = self._proxy_index(text)
        if index.isValid():
            self._view.setCurrentIndex(index)
            return True
        return False

    def expand_item(self, text: str) -> bool:
        """Expand the first item with this text.

        Returns:
            True if the item was found and visible, False otherwise.
        """
        index = self._proxy_index(text)
        if index.isValid():
            self._view.expand(index)
            return True
        return False

    def collapse_item(self, text: str) -> bool:
        """Collapse the first item with this text.

        Returns:
            True if the item was found and visible, False otherwise.
        """
        index = self._proxy_index(text)
        if index.isValid():
            self._view.collapse(index)
            return True
        return False

    def expand_all(self) -> None:
        """Expand all items in the tree."""
        self._view.expandAll()

    def collapse_all(self) -> None:
        """Collapse all items in the tree."""
        self._view.collapseAll()

    @property
    def tree_view(self) -> QTreeView:
        """Return the underlying QTreeView."""
        return self._view
