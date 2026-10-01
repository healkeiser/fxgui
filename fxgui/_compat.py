"""Cross-binding compatibility helpers for `fxgui`.

`qtpy` only exposes ``qtpy.shiboken`` under PySide bindings; importing it
under PyQt5/PyQt6 raises, so liveness checks live here. So does the one
`QPixmapCache.find` call both PySide generations accept.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

__all__ = ["created_by_python", "find_pixmap", "is_valid"]

# Built-in
from typing import Optional

# Third-party
from qtpy.QtGui import QPixmap, QPixmapCache


try:
    # PySide2 / PySide6
    from qtpy.shiboken import createdByPython as created_by_python
    from qtpy.shiboken import isValid as is_valid  # noqa: F401

except ImportError:
    # PyQt5 / PyQt6: every wrapper is filed where Qt files its object.
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
    try:
        found = QPixmapCache.find(key)
    except TypeError:  # PySide2 only offers find(key, pixmap)
        found = QPixmap()
        if not QPixmapCache.find(key, found):
            return None
    return found if found is not None and not found.isNull() else None


def __getattr__(name):
    # TODO: shim; delete once fxdocking.py:35 imports these from fxutils.
    if name in ("focus_step", "later", "rehome"):
        from fxgui import fxutils

        return getattr(fxutils, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
