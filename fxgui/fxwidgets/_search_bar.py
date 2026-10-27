"""A search field with a debounced search signal."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QTimer, Signal
from qtpy.QtGui import QResizeEvent
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets._inputs import FXIconLineEdit
from fxgui.fxwidgets._tips import FXKeycap

# The sheet draws a bar marked so as a ghost field: no edge, filled on hover.
GHOST_PROPERTY = "fxGhost"

# The keycap's gap to the field's right edge.
_KEYCAP_INSET = 6


class FXSearchBar(FXIconLineEdit):
    """A line edit with a search icon, Qt's clear button and a debounce.

    It is one Tab stop: the icon and the clear button are line edit
    actions, which take no focus.

    Args:
        parent: Parent widget.
        placeholder: Placeholder text.
        debounce_ms: How long typing pauses before `search_changed`.
        keys: The shortcut that puts the cursor here, shown as keycaps at
            the right end while the field is empty. The caller binds it.

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
        keys: str = "",
    ):
        super().__init__(parent, "search")
        self.setProperty(GHOST_PROPERTY, True)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self._keycap: Optional[FXKeycap] = None

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._emit_search_changed)
        self.textChanged.connect(self._restart_debounce)
        self.textChanged.connect(self._place_keycap)
        self.returnPressed.connect(self._on_return_pressed)
        self.set_keys(keys)

    def set_keys(self, keys: str) -> None:
        """Show `keys` as the shortcut that reaches this field; `""` hides it."""
        if self._keycap is None and keys:
            self._keycap = FXKeycap(keys, self)
        elif self._keycap is not None:
            self._keycap.set_keys(keys)
        self._place_keycap()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the keycap at the right end."""
        super().resizeEvent(event)
        self._place_keycap()

    def _place_keycap(self, _text: str = "") -> None:
        """Show the keycap at the right end while the field is empty.

        No text margin is kept for it: one would widen the field's minimum,
        and only the placeholder can sit under it.
        """
        if self._keycap is None:
            return
        self._keycap.setVisible(bool(self._keycap.keys()) and not self.text())
        size = self._keycap.sizeHint()
        self._keycap.setGeometry(
            self.width() - _KEYCAP_INSET - size.width(),
            (self.height() - size.height()) // 2,
            size.width(),
            size.height(),
        )

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
