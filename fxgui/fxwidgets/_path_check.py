"""Disk checks that never make the UI thread wait on a network share."""

# Built-in
import threading
import weakref
from collections import OrderedDict
from typing import Callable, Optional, Sequence, Tuple

# Third-party
from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import _compat
from fxgui._compat import is_valid as is_valid_object


class _Relay(QObject):
    """Carries a worker's result back to the UI thread."""

    finished = Signal(object, str, object)


_relay: Optional[_Relay] = None
_lock = threading.Lock()
_live = 0
# (widget, slot) -> its newest check waiting for a thread; older ones drop.
_pending: "OrderedDict[tuple, tuple]" = OrderedDict()
# A share that does not answer holds its thread; the cap keeps dead shares
# from flooding the process with stuck threads.
THREAD_CAP = 4


def _deliver(widget_ref, slot: str, args: tuple) -> None:
    """Hand a result to its widget if the widget is still alive."""
    widget = widget_ref()
    if widget is not None and is_valid_object(widget):
        getattr(widget, slot)(*args)


def _work(job: tuple, capped: bool) -> None:
    """Run a check; a capped thread then runs any waiting one."""
    global _live
    while job is not None:
        widget_ref, slot, check = job
        try:
            _relay.finished.emit(widget_ref, slot, check())
        except Exception:  # noqa: BLE001 - a failed check must not kill the thread
            pass
        if not capped:
            return
        with _lock:
            job = _pending.popitem(last=False)[1] if _pending else None
            if job is None:
                _live -= 1


def run(
    widget: QWidget,
    slot: str,
    check: Callable[[], Tuple],
    paths: Sequence[str],
    inline: bool = True,
) -> None:
    """Call `widget.slot(*check())` without the UI thread waiting on a share.

    A check that reads a path that may stall runs on a daemon thread, at
    most `THREAD_CAP` of them at once; past the cap, each widget's newest
    check waits for a free one. Any other check runs at once, or with
    `inline` False on a thread of its own outside the cap, so dead shares
    never hold it up. Not the host's `QThreadPool`: a stuck check would
    starve it and hold its quit; a daemon thread never delays the exit.

    Args:
        widget: Takes the result; a result for a deleted widget is dropped.
        slot: The name of `widget`'s method that takes `*check()`.
        check: Reads the disk and returns the slot's arguments. It may run
            on a worker thread, so it must not touch a widget.
        paths: Every path `check` reads.
        inline: Whether a check none of whose paths may stall runs at once
            on the calling thread.
    """
    stalls = any(_compat.can_stall(p) for p in paths)
    if not stalls and inline:
        getattr(widget, slot)(*check())
        return
    global _relay, _live
    if _relay is None:
        _relay = _Relay()
        _relay.finished.connect(_deliver)
    job = (weakref.ref(widget), slot, check)
    if stalls:
        with _lock:
            if _live >= THREAD_CAP:
                _pending.pop((id(widget), slot), None)
                _pending[(id(widget), slot)] = job
                return
            _live += 1
    # shortcut: a local path that links to a share takes an uncapped thread; cap it too if stuck threads pile up.
    threading.Thread(
        target=_work, args=(job, stalls), name="fxgui-path-check", daemon=True
    ).start()
