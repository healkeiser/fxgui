"""Cross-binding compatibility helpers for `fxgui`.

`qtpy` only exposes ``qtpy.shiboken`` under PySide6; importing it under
PyQt6 raises, so liveness checks live here.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

__all__ = [
    "QT_VERSION", "can_stall", "created_by_python", "find_pixmap", "hold",
    "is_valid", "parent_widget",
]

# Built-in
import ctypes
import functools
import os
import posixpath
import re
import sys
import time
from typing import Optional, Tuple

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


_DRIVE_REMOTE = 4


@functools.lru_cache(maxsize=None)
def _remote_drive(root: str) -> bool:
    """Return whether Windows reports drive `root` (``"X:\\"``) as remote."""
    try:
        return ctypes.windll.kernel32.GetDriveTypeW(root) == _DRIVE_REMOTE
    except (AttributeError, OSError):
        return False


# File system types whose reads go over the network.
_NETWORK_FS = frozenset({
    "nfs", "nfs4", "cifs", "smb3", "smbfs", "fuse.sshfs",
    "ceph", "fuse.ceph-fuse", "glusterfs", "fuse.glusterfs",
})
# `can_stall` runs while painting: the mount table is read this seldom.
_MOUNTS_TTL = 30.0
# (when read, network mount points longest first), or None before the first read.
_mounts_cache: Optional[Tuple[float, Tuple[str, ...]]] = None


def _read_mounts() -> str:
    """Return the Linux mount table, or "" when it cannot be read."""
    try:
        with open("/proc/mounts", encoding="utf-8", errors="replace") as table:
            return table.read()
    except OSError:
        return ""


def _network_mounts() -> Tuple[str, ...]:
    """Return the network mount points, longest first, re-read every 30 s."""
    global _mounts_cache
    now = time.monotonic()
    if _mounts_cache is not None and now - _mounts_cache[0] < _MOUNTS_TTL:
        return _mounts_cache[1]
    points = []
    for line in _read_mounts().splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[2] in _NETWORK_FS:
            # The table writes a space in a mount point as \040.
            points.append(re.sub(
                r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), fields[1]))
    _mounts_cache = (now, tuple(sorted(points, key=len, reverse=True)))
    return _mounts_cache[1]


def _on_network_mount(path: str) -> bool:
    """Return whether the POSIX `path` lies under a network mount."""
    path = posixpath.abspath(path)
    for point in _network_mounts():
        if point == "/" or path == point or path.startswith(point + "/"):
            return True
    return False


def can_stall(path: str) -> bool:
    """Return whether reading `path` may wait on a network share.

    On macOS only UNC-style paths count: `os.statvfs` does not say which
    file system a path is on.
    """
    if path.startswith(("\\\\", "//")):
        return True
    if sys.platform.startswith("linux"):
        return _on_network_mount(path)
    if sys.platform != "win32":
        return False
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    return bool(drive) and _remote_drive(drive.upper() + "\\")


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
