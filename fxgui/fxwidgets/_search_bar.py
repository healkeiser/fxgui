"""A search field with a debounced search signal."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QTimer, Signal
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets._inputs import FXIconLineEdit


class FXSearchBar(FXIconLineEdit):
    """A line edit with a search icon, Qt's clear button and a debounce.

    It is one Tab stop: the icon and the clear button are line edit
    actions, which take no focus.

    Args:
        parent: Parent widget.
        placeholder: Placeholder text.
        debounce_ms: How long typing pauses before `search_changed`.

    Signals:
        search_changed: The text, once typing pauses.
        search_submitted: The text, on Enter; cancels a pending change.

    Examples:
        >>> search = FXSearchBar(placeholder="Search assets...")
        >>> search.search_changed.connect(lambda text: print(text))
    """

    search_changed = Signal(str)
    search_submitted = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Search...",
        debounce_ms: int = 300,
    ):
        super().__init__(parent, "search")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._emit_search_changed)
        self.textChanged.connect(self._restart_debounce)
        self.returnPressed.connect(self._on_return_pressed)

    def _restart_debounce(self, _text: str = "") -> None:
        """Start the debounce over; `start` restarts a running timer."""
        self._debounce_timer.start()

    def _emit_search_changed(self) -> None:
        """Emit the debounced search_changed signal."""
        self.search_changed.emit(self.text())

    def _on_return_pressed(self) -> None:
        """Submit the text and drop the pending change."""
        self._debounce_timer.stop()
        self.search_submitted.emit(self.text())
