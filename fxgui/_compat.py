"""Cross-binding compatibility helpers for `fxgui`.

`qtpy` only exposes ``qtpy.shiboken`` under PySide bindings; importing it
under PyQt5/PyQt6 raises ``QtBindingMissingModuleError``. This module provides
the small subset fxgui needs (C++ object liveness checks) on every binding so
the advertised PySide2/PySide6/PyQt5/PyQt6 support holds.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

__all__ = ["is_valid"]


try:
    # PySide2 / PySide6
    from qtpy.shiboken import isValid as is_valid  # noqa: F401

except Exception:
    try:
        # PyQt5 / PyQt6
        from qtpy.sip import isdeleted as _isdeleted

        def is_valid(obj) -> bool:
            """Return `True` if the underlying C++ object is still alive."""
            try:
                return not _isdeleted(obj)
            except TypeError:
                # Not a sip-wrapped object; assume alive.
                return True

    except Exception:

        def is_valid(obj) -> bool:
            """Fallback when no liveness API is available; assume alive."""
            return True
