"""Enhanced search input widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, Qt, QTimer, Signal
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils


class FXSearchBar(QWidget):
    """An enhanced search input widget with built-in features.

    This widget provides a search input with:
    - Search icon
    - Clear button
    - Optional filter dropdown
    - Debounced search signal for live filtering

    Args:
        parent: Parent widget.
        placeholder: Placeholder text.
        debounce_ms: Debounce delay in milliseconds for search_changed signal.
        show_filter: Whether to show the filter dropdown.
        filters: List of filter options for the dropdown.

    Signals:
        search_changed: Emitted when the search text changes (debounced).
        search_submitted: Emitted when Enter is pressed.
        filter_changed: Emitted when the filter selection changes.

    Examples:
        >>> search = FXSearchBar(placeholder="Search assets...")
        >>> search.search_changed.connect(lambda text: print(f"Searching: {text}"))
        >>> search.set_filters(["All", "Models", "Textures", "Materials"])
    """

    search_changed = Signal(str)
    search_submitted = Signal(str)
    filter_changed = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Search...",
        debounce_ms: int = 300,
        show_filter: bool = False,
        filters: Optional[list] = None,
    ):
        super().__init__(parent)

        self._debounce_ms = debounce_ms

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Filter dropdown (optional)
        self._filter_combo = QComboBox()
        self._filter_combo.setVisible(show_filter)
        self._filter_combo.setMinimumWidth(100)
        self._filter_combo.currentTextChanged.connect(self.filter_changed.emit)
        if filters:
            self._filter_combo.addItems(filters)
        layout.addWidget(self._filter_combo)

        # Search container
        self._search_container = QWidget()
        self._search_container.setObjectName("fx_search_container")
        self._search_container.setAttribute(Qt.WA_StyledBackground, True)
        self._search_container.setProperty("focused", False)
        search_layout = QHBoxLayout(self._search_container)
        search_layout.setContentsMargins(8, 0, 4, 0)
        search_layout.setSpacing(4)

        # Search icon
        self._search_icon = QPushButton()
        fxicons.set_icon(self._search_icon, "search")
        self._search_icon.setFixedSize(20, 20)
        self._search_icon.setFlat(True)
        self._search_icon.setObjectName("fx_search_icon")
        self._search_icon.setFocusPolicy(Qt.NoFocus)
        search_layout.addWidget(self._search_icon)

        # Search input
        self._input = QLineEdit()
        self._input.setObjectName("fx_search_input")
        self._input.setPlaceholderText(placeholder)
        self._input.installEventFilter(self)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._on_return_pressed)
        search_layout.addWidget(self._input, 1)

        # Clear button
        self._clear_button = QPushButton()
        fxicons.set_icon(self._clear_button, "close")
        self._clear_button.setFixedSize(20, 20)
        self._clear_button.setFlat(True)
        self._clear_button.setCursor(Qt.PointingHandCursor)
        self._clear_button.setObjectName("fx_search_clear")
        # The bar is one Tab stop, its field; the field clears by keyboard.
        self._clear_button.setFocusPolicy(Qt.NoFocus)
        self._clear_button.clicked.connect(self.clear)
        self._clear_button.setVisible(False)
        search_layout.addWidget(self._clear_button)

        layout.addWidget(self._search_container, 1)

        # Debounce timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_search_changed)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFocusProxy(self._input)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Light the container while the field has focus."""
        if watched is self._input and event.type() in (
            QEvent.FocusIn,
            QEvent.FocusOut,
        ):
            # QSS has no :focus-within, so a property carries it.
            self._search_container.setProperty(
                "focused", event.type() == QEvent.FocusIn
            )
            fxutils.repolish(self._search_container)
        return super().eventFilter(watched, event)

    def line_edit(self) -> QLineEdit:
        """Return the field typing goes to, the bar's one Tab stop."""
        return self._input

    @property
    def text(self) -> str:
        """Return the current search text."""
        return self._input.text()

    @text.setter
    def text(self, value: str) -> None:
        """Set the search text."""
        self._input.setText(value)

    @property
    def filter(self) -> str:
        """Return the current filter selection."""
        return self._filter_combo.currentText()

    def set_filters(self, filters: list) -> None:
        """Set the filter dropdown options.

        Args:
            filters: List of filter option strings.
        """
        self._filter_combo.clear()
        self._filter_combo.addItems(filters)
        self._filter_combo.setVisible(True)

    def show_filter(self, visible: bool = True) -> None:
        """Show or hide the filter dropdown.

        Args:
            visible: Whether to show the filter dropdown.
        """
        self._filter_combo.setVisible(visible)

    def clear(self) -> None:
        """Clear the search input."""
        self._input.clear()
        self._input.setFocus()

    def set_placeholder(self, text: str) -> None:
        """Set the placeholder text.

        Args:
            text: The placeholder text.
        """
        self._input.setPlaceholderText(text)

    def _on_text_changed(self, text: str) -> None:
        """Handle text change with debouncing."""
        # Show/hide clear button
        self._clear_button.setVisible(bool(text))

        # Restart debounce timer
        self._debounce_timer.stop()
        self._debounce_timer.start(self._debounce_ms)

    def _emit_search_changed(self) -> None:
        """Emit the debounced search_changed signal."""
        self.search_changed.emit(self._input.text())

    def _on_return_pressed(self) -> None:
        """Handle Enter key press."""
        self._debounce_timer.stop()
        self.search_submitted.emit(self._input.text())



fxstyle.register_widget_style("""
FXSearchBar QWidget#fx_search_container {
    background-color: @surface_sunken;
    border: 1px solid @border;
    border-radius: 4px;
}
FXSearchBar QWidget#fx_search_container[focused="true"] {
    border-color: @accent_primary;
}
FXSearchBar QPushButton#fx_search_icon {
    background: transparent;
    border: none;
}
FXSearchBar QLineEdit#fx_search_input {
    background: transparent;
    border: none;
    padding: 6px 0;
}
FXSearchBar QPushButton#fx_search_clear {
    background: transparent;
    border: none;
    border-radius: 10px;
}
FXSearchBar QPushButton#fx_search_clear:hover {
    background: rgba(128, 128, 128, 0.2);
}
""")
