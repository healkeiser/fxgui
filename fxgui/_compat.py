"""Cross-binding and cross-host compatibility helpers for `fxgui`.

`qtpy` only exposes ``qtpy.shiboken`` under PySide bindings; importing it
under PyQt5/PyQt6 raises ``QtBindingMissingModuleError``, so liveness checks
live here. So do the helpers that keep fxgui working on the older PySide a
host ships (`later`) and around PySide's wrapper lifetimes (`rehome`).
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

__all__ = ["focus_step", "is_valid", "later", "rehome"]

# Third-party
from qtpy.QtCore import QTimer


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


def later(ms: int, owner, call) -> None:
    """Run `call` once after `ms` milliseconds, unless `owner` died first.

    Stands in for `QTimer.singleShot(ms, owner, call)`, which Houdini 21's
    PySide6 6.5 lacks. Call it on `owner`'s thread: the timer is its child.
    """
    timer = QTimer(owner)
    timer.setSingleShot(True)
    timer.timeout.connect(call)
    timer.timeout.connect(timer.deleteLater)
    timer.start(ms)


def rehome(widget):
    """Give `widget`'s Python wrapper back to its own parent's; return it.

    PySide files a widget a getter returns under the widget asked, and
    kills that one's wrapped children when it dies: a window reached from
    a dying button lost its live menu bar's wrapper. Qt skips a
    `setParent` to the same parent; the binding files the wrapper back.
    """
    if widget is not None:
        widget.setParent(widget.parentWidget())
    return widget


def focus_step(widget, forward: bool = True):
    """Return the widget after `widget` in the focus chain, or before it."""
    return rehome(
        widget.nextInFocusChain() if forward
        else widget.previousInFocusChain()
    )
