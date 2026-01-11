"""Fuzzy search list widget with relevance-based filtering and sorting."""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from typing import List, Optional, Union

# Third-party
from qtpy.QtCore import Qt, Signal, Slot, QModelIndex
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QSlider,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxcore import FXSortFilterProxyModel
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._tooltip import FXTooltip


class FXFuzzySearchList(fxstyle.FXThemeAware, QWidget):
    """A searchable list widget with fuzzy matching capabilities.

    This widget combines a search bar with a list view that uses fuzzy matching
    to filter and sort items by relevance. Items are colored based on their
    match quality (green for good matches, red for poor matches).

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

    Examples:
        Basic usage with a list of strings:

        >>> fuzzy_list = FXFuzzySearchList(placeholder="Search fruits...")
        >>> fuzzy_list.set_items(["apple", "apricot", "banana", "cherry"])
        >>> fuzzy_list.item_selected.connect(lambda text: print(f"Selected: {text}"))

        With ratio slider for user adjustment:

        >>> fuzzy_list = FXFuzzySearchList(show_ratio_slider=True, ratio=0.6)
        >>> fuzzy_list.set_items(["character_hero", "character_villain", "prop_chair"])
    """

    item_selected = Signal(str)
    item_double_clicked = Signal(str)
    item_activated = Signal(str)
    selection_changed = Signal(list)

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
        self._proxy_model = FXSortFilterProxyModel(
            ratio=ratio,
            color_match=color_match,
            parent=self,
        )
        self._proxy_model.setSourceModel(self._source_model)

        # List view
        self._list_view = QListView()
        self._list_view.setModel(self._proxy_model)
        self._list_view.setAlternatingRowColors(True)
        self._list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._list_view, 1)

        # Connect signals
        self._connect_signals()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Search bar -> proxy model
        self._search_bar.search_changed.connect(
            self._proxy_model.set_filter_text
        )
        self._search_bar.search_submitted.connect(self._on_search_submitted)

        # Slider -> proxy model
        self._ratio_slider.valueChanged.connect(self._on_ratio_changed)

        # List view signals
        self._list_view.clicked.connect(self._on_item_clicked)
        self._list_view.doubleClicked.connect(self._on_item_double_clicked)
        self._list_view.activated.connect(self._on_item_activated)
        self._list_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

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
            self._list_view.setCurrentIndex(first_index)
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

    @Slot()
    def _on_selection_changed(self) -> None:
        """Handle selection changes."""
        selected = self.selected_items
        self.selection_changed.emit(selected)

    # Public API

    def set_items(self, items: List[str]) -> None:
        """Set the list items from a list of strings.

        Args:
            items: List of strings to display.
        """
        self._source_model.clear()
        for item in items:
            self._source_model.appendRow(QStandardItem(item))

    def add_item(self, text: str) -> None:
        """Add a single item to the list.

        Args:
            text: The item text to add.
        """
        self._source_model.appendRow(QStandardItem(text))

    def remove_item(self, text: str) -> bool:
        """Remove an item from the list by its text.

        Args:
            text: The item text to remove.

        Returns:
            True if the item was found and removed, False otherwise.
        """
        for row in range(self._source_model.rowCount()):
            item = self._source_model.item(row)
            if item and item.text() == text:
                self._source_model.removeRow(row)
                return True
        return False

    def clear(self) -> None:
        """Clear all items from the list."""
        self._source_model.clear()

    def clear_search(self) -> None:
        """Clear the search input."""
        self._search_bar.clear()

    @property
    def items(self) -> List[str]:
        """Return all items in the source model.

        Returns:
            List of all item texts.
        """
        return [
            self._source_model.item(row).text()
            for row in range(self._source_model.rowCount())
            if self._source_model.item(row)
        ]

    @property
    def visible_items(self) -> List[str]:
        """Return currently visible (filtered) items.

        Returns:
            List of visible item texts.
        """
        return [
            self._proxy_model.index(row, 0).data(Qt.DisplayRole)
            for row in range(self._proxy_model.rowCount())
        ]

    @property
    def selected_items(self) -> List[str]:
        """Return currently selected items.

        Returns:
            List of selected item texts.
        """
        selection = self._list_view.selectionModel().selectedIndexes()
        return [
            index.data(Qt.DisplayRole) for index in selection if index.data()
        ]

    @property
    def current_item(self) -> Optional[str]:
        """Return the current item text.

        Returns:
            The current item text, or None if no item is current.
        """
        index = self._list_view.currentIndex()
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
        """Set the list view selection mode.

        Args:
            mode: The selection mode (e.g., SingleSelection, ExtendedSelection).
        """
        self._list_view.setSelectionMode(mode)

    def select_item(self, text: str) -> bool:
        """Select an item by its text.

        Args:
            text: The item text to select.

        Returns:
            True if the item was found and selected, False otherwise.
        """
        for row in range(self._proxy_model.rowCount()):
            index = self._proxy_model.index(row, 0)
            if index.data(Qt.DisplayRole) == text:
                self._list_view.setCurrentIndex(index)
                return True
        return False

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
    def proxy_model(self) -> FXSortFilterProxyModel:
        """Return the proxy model for advanced customization.

        Returns:
            The underlying FXSortFilterProxyModel.
        """
        return self._proxy_model

    @property
    def list_view(self) -> QListView:
        """Return the list view for advanced customization.

        Returns:
            The underlying QListView.
        """
        return self._list_view


def example() -> None:
    """Run an example demonstrating the FXFuzzySearchList widget."""
    import sys
    from qtpy.QtWidgets import QHBoxLayout, QTextEdit
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXFuzzySearchList Demo")

    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QHBoxLayout(widget)

    # Sample data - VFX asset names
    ASSETS = [
        "character_hero_body",
        "character_hero_head",
        "character_villain_body",
        "character_sidekick",
        "prop_sword_metal",
        "prop_shield_wooden",
        "prop_chair_office",
        "prop_table_dining",
        "vehicle_car_sports",
        "vehicle_truck_pickup",
        "vehicle_motorcycle",
        "environment_tree_oak",
        "environment_tree_pine",
        "environment_rock_large",
        "environment_grass_patch",
        "fx_explosion_fire",
        "fx_smoke_trail",
        "fx_sparks_electric",
        "texture_wood_diffuse",
        "texture_metal_normal",
        "texture_brick_albedo",
        "material_glass_clear",
        "material_skin_subsurface",
        "material_fabric_cloth",
    ]

    # Fuzzy search list
    fuzzy_list = FXFuzzySearchList(
        placeholder="Search assets (try 'hero', 'char', 'veh')...",
        ratio=0.4,
        show_ratio_slider=True,
        color_match=True,
    )
    fuzzy_list.set_items(ASSETS)
    layout.addWidget(fuzzy_list, 1)

    # Info panel
    info_panel = QTextEdit()
    info_panel.setReadOnly(True)
    info_panel.setMaximumWidth(300)
    layout.addWidget(info_panel)

    def update_info():
        selected = fuzzy_list.selected_items
        visible = fuzzy_list.visible_items
        total = len(fuzzy_list.items)
        search = fuzzy_list.search_text
        ratio = fuzzy_list.ratio

        info = [
            f"<b>Search:</b> '{search or '(empty)'}'",
            f"<b>Ratio:</b> {ratio:.0%}",
            f"<b>Visible:</b> {len(visible)} / {total} items",
            "",
            "<b>Selected:</b>",
        ]
        if selected:
            for item in selected:
                info.append(f"  - {item}")
        else:
            info.append("  (none)")

        info_panel.setHtml("<br>".join(info))

    fuzzy_list.item_selected.connect(lambda _: update_info())
    fuzzy_list.selection_changed.connect(lambda _: update_info())
    fuzzy_list._search_bar.search_changed.connect(lambda _: update_info())
    fuzzy_list._ratio_slider.valueChanged.connect(lambda _: update_info())

    fuzzy_list.item_double_clicked.connect(
        lambda text: info_panel.append(f"<br><i>Double-clicked: {text}</i>")
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
