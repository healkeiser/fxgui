"""Cross-binding compatibility helpers for `fxgui`.

`qtpy` only exposes ``qtpy.shiboken`` under PySide6; importing it under
PyQt6 raises, so liveness checks live here.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

__all__ = [
    "QT_VERSION", "created_by_python", "find_pixmap", "hold", "is_valid",
    "parent_widget",
]

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import qVersion
from qtpy.QtGui import QPixmap, QPixmapCache

# The running Qt's (major, minor), for the few looks that differ by version.
QT_VERSION = tuple(int(part) for part in qVersion().split(".")[:2])


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


# Python objects held until Qt destroys them; see hold.
_held = {}


def hold(obj) -> None:
    """Keep `obj`'s Python side alive until Qt destroys the object.

    PySide keeps a child's wrapper only through its parent's wrapper; under
    a parent C++ made, that one is freed at will and takes the child's
    overrides with it, while Qt keeps the widget.
    """
    key = id(obj)
    if key in _held:
        return
    _held[key] = obj
    obj.destroyed.connect(lambda _=None, key=key: _held.pop(key, None))


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
    ):
        hold(widget)
    return parent
