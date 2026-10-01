"""Cross-binding compatibility helpers for `fxgui`.

`qtpy` only exposes ``qtpy.shiboken`` under PySide6; importing it under
PyQt6 raises, so liveness checks live here.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

__all__ = ["created_by_python", "find_pixmap", "is_valid", "parent_widget"]

# Built-in
from typing import Optional

# Third-party
from qtpy.QtGui import QPixmap, QPixmapCache


try:
    # PySide6
    from qtpy.shiboken import createdByPython as created_by_python
    from qtpy.shiboken import isValid as is_valid  # noqa: F401

except ImportError:
    # PyQt6: every wrapper is filed where Qt files its object.
    from qtpy.sip import isdeleted as _isdeleted

    created_by_python = None

    def is_valid(obj) -> bool:
        """Return `True` if the underlying C++ object is still alive."""
        try:
            return not _isdeleted(obj)
        except TypeError:
            # Not a sip-wrapped object; assume alive.
            return True


def find_pixmap(key: str) -> Optional[QPixmap]:
    """Return the pixmap QPixmapCache holds under `key`, or None."""
    found = QPixmapCache.find(key)
    return found if found is not None and not found.isNull() else None


# A parentless widget C++ made, held until C++ frees it; see parent_widget.
_held = {}


def parent_widget(widget):
    """Return `widget.parentWidget()`, leaving a widget C++ made to C++.

    PySide6 6.5 hands a parentless widget C++ made, a completer's list say,
    to Python when asked its parent, and frees it with the wrapper.
    """
    parent = widget.parentWidget()
    if (
        parent is None
        and created_by_python is not None
        and not created_by_python(widget)
        and id(widget) not in _held
    ):
        key = id(widget)
        _held[key] = widget
        widget.destroyed.connect(lambda _=None, key=key: _held.pop(key, None))
    return parent
