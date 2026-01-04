"""FXSearchBar - Enhanced search input widget."""

from typing import Optional

from qtpy.QtCore import Qt, Signal, QTimer
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from fxgui import fxicons, fxstyle


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

        # Get theme colors
        theme_colors = fxstyle.get_theme_colors()
        accent_colors = fxstyle.get_accent_colors()

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
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(8, 0, 4, 0)
        search_layout.setSpacing(4)

        search_container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme_colors['input']};
                border: 1px solid {theme_colors['border']};
                border-radius: 4px;
            }}
            QWidget:focus-within {{
                border-color: {accent_colors['primary']};
            }}
        """)

        # Search icon
        self._search_icon = QPushButton()
        self._search_icon.setIcon(fxicons.get_icon("search"))
        self._search_icon.setFixedSize(20, 20)
        self._search_icon.setFlat(True)
        self._search_icon.setStyleSheet("background: transparent; border: none;")
        search_layout.addWidget(self._search_icon)

        # Search input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                padding: 6px 0;
            }
        """)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._on_return_pressed)
        search_layout.addWidget(self._input, 1)

        # Clear button
        self._clear_button = QPushButton()
        self._clear_button.setIcon(fxicons.get_icon("close"))
        self._clear_button.setFixedSize(20, 20)
        self._clear_button.setFlat(True)
        self._clear_button.setCursor(Qt.PointingHandCursor)
        self._clear_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 0.2);
            }
        """)
        self._clear_button.clicked.connect(self.clear)
        self._clear_button.setVisible(False)
        search_layout.addWidget(self._clear_button)

        layout.addWidget(search_container, 1)

        # Debounce timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_search_changed)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

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

    def setFocus(self) -> None:
        """Set focus to the search input."""
        self._input.setFocus()


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    import os
    import sys
    from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXSearchBar Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("Basic Search:"))
    search1 = FXSearchBar(placeholder="Search assets...")
    search1.search_changed.connect(lambda t: print(f"Search: {t}"))
    layout.addWidget(search1)

    layout.addWidget(QLabel("Search with Filter:"))
    search2 = FXSearchBar(
        placeholder="Search...",
        show_filter=True,
        filters=["All", "Models", "Textures", "Materials", "Scripts"]
    )
    search2.filter_changed.connect(lambda f: print(f"Filter: {f}"))
    layout.addWidget(search2)

    layout.addStretch()
    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())
