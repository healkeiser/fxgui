"""Fuzzy search tree widget with relevance-based filtering and sorting."""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from typing import Dict, List, Optional, Tuple, Union

# Third-party
from qtpy.QtCore import Qt, Signal, Slot, QModelIndex
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSizePolicy,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxcore import FXSortFilterProxyModel
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._tooltip import FXTooltip


class FXFuzzySearchTree(fxstyle.FXThemeAware, QWidget):
    """A searchable tree widget with fuzzy matching capabilities.

    This widget combines a search bar with a tree view that uses fuzzy matching
    to filter and sort items by relevance. Items are colored based on their
    match quality (green for good matches, red for poor matches).

    The tree supports hierarchical data with parent-child relationships.
    When filtering, parent items remain visible if any of their children match.

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

        self._ratio = ratio
        self._color_match = color_match
        self._item_map: Dict[str, QStandardItem] = {}

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Search bar
        self._search_bar = FXSearchBar(
            parent=self,
            placeholder=placeholder,
            debounce_ms=150,
        )
        layout.addWidget(self._search_bar)

        # Ratio slider (optional)
        self._slider_container = QWidget()
        slider_layout = QHBoxLayout(self._slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(8)

        self._ratio_icon = QPushButton()
        fxicons.set_icon(self._ratio_icon, "tune")
        self._ratio_icon.setFixedSize(20, 20)
        self._ratio_icon.setFlat(True)
        self._ratio_icon.setStyleSheet("background: transparent; border: none;")
        self._ratio_icon_tooltip = FXTooltip(
            parent=self._ratio_icon,
            title="Sensitivity",
            description="Adjust fuzzy matching sensitivity",
        )
        slider_layout.addWidget(self._ratio_icon)

        self._ratio_slider = QSlider(Qt.Horizontal)
        self._ratio_slider.setRange(0, 100)
        self._ratio_slider.setValue(int(ratio * 100))
        self._ratio_slider_tooltip = FXTooltip(
            parent=self._ratio_slider,
            title="Match Threshold",
            description="Lower = more results (looser match), Higher = fewer results (stricter match)",
        )
        slider_layout.addWidget(self._ratio_slider, 1)

        self._ratio_label = QLabel(f"{int(ratio * 100)}%")
        self._ratio_label.setFixedWidth(35)
        self._ratio_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_layout.addWidget(self._ratio_label)

        self._slider_container.setVisible(show_ratio_slider)
        layout.addWidget(self._slider_container)

        # Model setup
        self._source_model = QStandardItemModel(self)
        self._proxy_model = _FXTreeSortFilterProxyModel(
            ratio=ratio,
            color_match=color_match,
            parent=self,
        )
        self._proxy_model.setSourceModel(self._source_model)

        # Tree view
        self._tree_view = QTreeView()
        self._tree_view.setModel(self._proxy_model)
        self._tree_view.setAlternatingRowColors(True)
        self._tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tree_view.setHeaderHidden(True)
        self._tree_view.setAnimated(True)
        layout.addWidget(self._tree_view, 1)

        # Connect signals
        self._connect_signals()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Search bar -> proxy model
        self._search_bar.search_changed.connect(self._on_search_changed)
        self._search_bar.search_submitted.connect(self._on_search_submitted)

        # Slider -> proxy model
        self._ratio_slider.valueChanged.connect(self._on_ratio_changed)

        # Tree view signals
        self._tree_view.clicked.connect(self._on_item_clicked)
        self._tree_view.doubleClicked.connect(self._on_item_double_clicked)
        self._tree_view.activated.connect(self._on_item_activated)
        self._tree_view.expanded.connect(self._on_item_expanded)
        self._tree_view.collapsed.connect(self._on_item_collapsed)
        self._tree_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

    @Slot(str)
    def _on_search_changed(self, text: str) -> None:
        """Handle search text changes."""
        self._proxy_model.set_filter_text(text)
        # Auto-expand all items when searching to show matches
        if text:
            self._tree_view.expandAll()

    @Slot(int)
    def _on_ratio_changed(self, value: int) -> None:
        """Handle ratio slider changes."""
        ratio = value / 100.0
        self._ratio = ratio
        self._ratio_label.setText(f"{value}%")
        self._proxy_model.set_ratio(ratio)

    @Slot(str)
    def _on_search_submitted(self, _text: str) -> None:
        """Handle Enter key in search bar - select first item if available."""
        if self._proxy_model.rowCount() > 0:
            first_index = self._proxy_model.index(0, 0)
            self._tree_view.setCurrentIndex(first_index)
            self._on_item_activated(first_index)

    @Slot(QModelIndex)
    def _on_item_clicked(self, index: QModelIndex) -> None:
        """Handle item click."""
        text = index.data(Qt.DisplayRole)
        if text:
            self.item_selected.emit(text)

    @Slot(QModelIndex)
    def _on_item_double_clicked(self, index: QModelIndex) -> None:
        """Handle item double-click."""
        text = index.data(Qt.DisplayRole)
        if text:
            self.item_double_clicked.emit(text)

    @Slot(QModelIndex)
    def _on_item_activated(self, index: QModelIndex) -> None:
        """Handle item activation (Enter key)."""
        text = index.data(Qt.DisplayRole)
        if text:
            self.item_activated.emit(text)

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

    @Slot()
    def _on_selection_changed(self) -> None:
        """Handle selection changes."""
        selected = self.selected_items
        self.selection_changed.emit(selected)

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
                    self.add_item(child_text, parent=parent_text)
        else:
            for item_text in items:
                self.add_item(item_text)

    def add_item(
        self,
        text: str,
        parent: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> QStandardItem:
        """Add a single item to the tree.

        Args:
            text: The item text to add.
            parent: The parent item text. If None, adds as top-level item.
            data: Optional dictionary of user data to store on the item.

        Returns:
            The created QStandardItem.
        """
        item = QStandardItem(text)
        if data:
            for key, value in data.items():
                item.setData(value, Qt.UserRole + hash(key) % 1000)

        if parent and parent in self._item_map:
            parent_item = self._item_map[parent]
            parent_item.appendRow(item)
        else:
            self._source_model.appendRow(item)

        self._item_map[text] = item
        return item

    def remove_item(self, text: str) -> bool:
        """Remove an item from the tree by its text.

        Args:
            text: The item text to remove.

        Returns:
            True if the item was found and removed, False otherwise.
        """
        if text not in self._item_map:
            return False

        item = self._item_map[text]
        parent = item.parent()

        if parent:
            parent.removeRow(item.row())
        else:
            self._source_model.removeRow(item.row())

        # Remove from map, including any children
        self._remove_from_map(item)
        return True

    def _remove_from_map(self, item: QStandardItem) -> None:
        """Recursively remove item and its children from the item map."""
        text = item.text()
        if text in self._item_map:
            del self._item_map[text]

        for row in range(item.rowCount()):
            child = item.child(row)
            if child:
                self._remove_from_map(child)

    def clear(self) -> None:
        """Clear all items from the tree."""
        self._source_model.clear()
        self._item_map.clear()

    def clear_search(self) -> None:
        """Clear the search input."""
        self._search_bar.clear()

    def get_item(self, text: str) -> Optional[QStandardItem]:
        """Get an item by its text.

        Args:
            text: The item text to find.

        Returns:
            The QStandardItem if found, None otherwise.
        """
        return self._item_map.get(text)

    @property
    def items(self) -> List[str]:
        """Return all item texts in the source model.

        Returns:
            List of all item texts (including nested items).
        """
        return list(self._item_map.keys())

    @property
    def top_level_items(self) -> List[str]:
        """Return top-level item texts.

        Returns:
            List of top-level item texts only.
        """
        return [
            self._source_model.item(row).text()
            for row in range(self._source_model.rowCount())
            if self._source_model.item(row)
        ]

    @property
    def selected_items(self) -> List[str]:
        """Return currently selected items.

        Returns:
            List of selected item texts.
        """
        selection = self._tree_view.selectionModel().selectedIndexes()
        return [
            index.data(Qt.DisplayRole) for index in selection if index.data()
        ]

    @property
    def current_item(self) -> Optional[str]:
        """Return the current item text.

        Returns:
            The current item text, or None if no item is current.
        """
        index = self._tree_view.currentIndex()
        return index.data(Qt.DisplayRole) if index.isValid() else None

    @property
    def search_text(self) -> str:
        """Return the current search text.

        Returns:
            The current search text.
        """
        return self._search_bar.text

    @search_text.setter
    def search_text(self, value: str) -> None:
        """Set the search text.

        Args:
            value: The search text to set.
        """
        self._search_bar.text = value

    @property
    def ratio(self) -> float:
        """Return the current similarity ratio threshold.

        Returns:
            The ratio threshold (0.0 to 1.0).
        """
        return self._ratio

    @ratio.setter
    def ratio(self, value: float) -> None:
        """Set the similarity ratio threshold.

        Args:
            value: The ratio threshold (0.0 to 1.0).
        """
        self._ratio = max(0.0, min(1.0, value))
        self._ratio_slider.setValue(int(self._ratio * 100))
        self._proxy_model.set_ratio(self._ratio)

    def show_ratio_slider(self, visible: bool = True) -> None:
        """Show or hide the ratio adjustment slider.

        Args:
            visible: Whether to show the slider.
        """
        self._slider_container.setVisible(visible)

    def set_color_match(self, enabled: bool) -> None:
        """Enable or disable color-coded match quality.

        Args:
            enabled: Whether to enable color matching.
        """
        self._color_match = enabled
        self._proxy_model.set_color_match(enabled)

    def set_placeholder(self, text: str) -> None:
        """Set the search bar placeholder text.

        Args:
            text: The placeholder text.
        """
        self._search_bar.set_placeholder(text)

    def set_selection_mode(self, mode: QAbstractItemView.SelectionMode) -> None:
        """Set the tree view selection mode.

        Args:
            mode: The selection mode (e.g., SingleSelection, ExtendedSelection).
        """
        self._tree_view.setSelectionMode(mode)

    def select_item(self, text: str) -> bool:
        """Select an item by its text.

        Args:
            text: The item text to select.

        Returns:
            True if the item was found and selected, False otherwise.
        """
        if text not in self._item_map:
            return False

        item = self._item_map[text]
        source_index = self._source_model.indexFromItem(item)
        proxy_index = self._proxy_model.mapFromSource(source_index)

        if proxy_index.isValid():
            self._tree_view.setCurrentIndex(proxy_index)
            return True
        return False

    def expand_item(self, text: str) -> bool:
        """Expand an item by its text.

        Args:
            text: The item text to expand.

        Returns:
            True if the item was found and expanded, False otherwise.
        """
        if text not in self._item_map:
            return False

        item = self._item_map[text]
        source_index = self._source_model.indexFromItem(item)
        proxy_index = self._proxy_model.mapFromSource(source_index)

        if proxy_index.isValid():
            self._tree_view.expand(proxy_index)
            return True
        return False

    def collapse_item(self, text: str) -> bool:
        """Collapse an item by its text.

        Args:
            text: The item text to collapse.

        Returns:
            True if the item was found and collapsed, False otherwise.
        """
        if text not in self._item_map:
            return False

        item = self._item_map[text]
        source_index = self._source_model.indexFromItem(item)
        proxy_index = self._proxy_model.mapFromSource(source_index)

        if proxy_index.isValid():
            self._tree_view.collapse(proxy_index)
            return True
        return False

    def expand_all(self) -> None:
        """Expand all items in the tree."""
        self._tree_view.expandAll()

    def collapse_all(self) -> None:
        """Collapse all items in the tree."""
        self._tree_view.collapseAll()

    def setFocus(self) -> None:
        """Set focus to the search input."""
        self._search_bar.setFocus()

    @property
    def source_model(self) -> QStandardItemModel:
        """Return the source model for advanced customization.

        Returns:
            The underlying QStandardItemModel.
        """
        return self._source_model

    @property
    def proxy_model(self) -> "FXSortFilterProxyModel":
        """Return the proxy model for advanced customization.

        Returns:
            The underlying proxy model.
        """
        return self._proxy_model

    @property
    def tree_view(self) -> QTreeView:
        """Return the tree view for advanced customization.

        Returns:
            The underlying QTreeView.
        """
        return self._tree_view


class _FXTreeSortFilterProxyModel(FXSortFilterProxyModel):
    """Extended proxy model for tree views that keeps parents visible when children match."""

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        """Determine whether a row should be accepted by the filter.

        For tree views, a parent row is accepted if any of its descendants match.

        Args:
            source_row: The source row index.
            source_parent: The source parent index.

        Returns:
            bool: True if the row is accepted, False otherwise.
        """
        # Check if the item itself matches
        if super().filterAcceptsRow(source_row, source_parent):
            return True

        # Check if any child matches (recursively)
        source_index = self.sourceModel().index(source_row, 0, source_parent)
        for row in range(self.sourceModel().rowCount(source_index)):
            if self.filterAcceptsRow(row, source_index):
                return True

        return False


def example() -> None:
    """Run an example demonstrating the FXFuzzySearchTree widget."""
    import sys
    from qtpy.QtWidgets import QHBoxLayout, QTextEdit
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXFuzzySearchTree Demo")

    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QHBoxLayout(widget)

    # Sample data - VFX asset hierarchy
    ASSETS = {
        "Characters": [
            "character_hero_body",
            "character_hero_head",
            "character_villain_body",
            "character_sidekick",
        ],
        "Props": [
            "prop_sword_metal",
            "prop_shield_wooden",
            "prop_chair_office",
            "prop_table_dining",
        ],
        "Vehicles": [
            "vehicle_car_sports",
            "vehicle_truck_pickup",
            "vehicle_motorcycle",
        ],
        "Environment": [
            "environment_tree_oak",
            "environment_tree_pine",
            "environment_rock_large",
            "environment_grass_patch",
        ],
        "FX": [
            "fx_explosion_fire",
            "fx_smoke_trail",
            "fx_sparks_electric",
        ],
        "Materials": [
            "texture_wood_diffuse",
            "texture_metal_normal",
            "texture_brick_albedo",
            "material_glass_clear",
            "material_skin_subsurface",
            "material_fabric_cloth",
        ],
    }

    # Fuzzy search tree
    fuzzy_tree = FXFuzzySearchTree(
        placeholder="Search assets (try 'hero', 'char', 'veh')...",
        ratio=0.4,
        show_ratio_slider=True,
        color_match=True,
    )
    fuzzy_tree.set_items(ASSETS)
    fuzzy_tree.expand_all()
    layout.addWidget(fuzzy_tree, 1)

    # Info panel
    info_panel = QTextEdit()
    info_panel.setReadOnly(True)
    info_panel.setMaximumWidth(300)
    layout.addWidget(info_panel)

    def update_info():
        selected = fuzzy_tree.selected_items
        total = len(fuzzy_tree.items)
        search = fuzzy_tree.search_text
        ratio = fuzzy_tree.ratio

        info = [
            f"<b>Search:</b> '{search or '(empty)'}'",
            f"<b>Ratio:</b> {ratio:.0%}",
            f"<b>Total Items:</b> {total}",
            "",
            "<b>Selected:</b>",
        ]
        if selected:
            for item in selected:
                info.append(f"  - {item}")
        else:
            info.append("  (none)")

        info_panel.setHtml("<br>".join(info))

    fuzzy_tree.item_selected.connect(lambda _: update_info())
    fuzzy_tree.selection_changed.connect(lambda _: update_info())
    fuzzy_tree._search_bar.search_changed.connect(lambda _: update_info())
    fuzzy_tree._ratio_slider.valueChanged.connect(lambda _: update_info())

    fuzzy_tree.item_double_clicked.connect(
        lambda text: info_panel.append(f"<br><i>Double-clicked: {text}</i>")
    )
    fuzzy_tree.item_expanded.connect(
        lambda text: info_panel.append(f"<br><i>Expanded: {text}</i>")
    )
    fuzzy_tree.item_collapsed.connect(
        lambda text: info_panel.append(f"<br><i>Collapsed: {text}</i>")
    )

    # Initial info
    update_info()

    window.resize(700, 500)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
