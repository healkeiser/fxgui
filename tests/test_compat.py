"""Tests for `fxgui._compat` cross-binding liveness checks.

Regression: fxstyle/fxicons used to import ``qtpy.shiboken`` directly, which
raises under PyQt5/PyQt6.
"""

# Built-in
import sys

# Third-party
from qtpy.QtCore import QCoreApplication, QEvent, QObject

# Internal
from fxgui import _compat
from fxgui._compat import is_valid


def test_is_valid_on_live_object(qapp):
    obj = QObject()
    assert is_valid(obj)


def test_is_valid_after_cpp_deletion(qapp):
    obj = QObject()
    obj.deleteLater()
    # Flush the deferred-delete queue so the C++ object is destroyed
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not is_valid(obj)



def test_find_pixmap_answers_none_for_a_miss(qapp):
    from qtpy.QtGui import QColor, QPixmap, QPixmapCache

    from fxgui import _compat

    stored = QPixmap(4, 4)
    stored.fill(QColor("#00ff00"))
    QPixmapCache.insert("fxgui.test|green", stored)
    assert _compat.find_pixmap("fxgui.test|green").cacheKey() == (
        stored.cacheKey())
    assert _compat.find_pixmap("fxgui.test|missing") is None


_MOUNTS = "\n".join((
    "fileserver:/export/projects /mnt/projects nfs4 rw,relatime 0 0",
    r"//nas/shows /mnt/my\040shows cifs rw 0 0",
    "/dev/nvme0n1p2 / ext4 rw,relatime 0 0",
    "/dev/nvme0n1p3 /mnt/projects/local ext4 rw 0 0",
))


def _fake_mounts(monkeypatch, table=_MOUNTS):
    """Serve `table` as /proc/mounts, with nothing cached."""
    reads = []

    def read():
        reads.append(True)
        return table

    monkeypatch.setattr(_compat, "_read_mounts", read)
    monkeypatch.setattr(_compat, "_mounts_cache", None)
    return reads


def test_a_path_on_a_network_mount_may_stall(monkeypatch):
    _fake_mounts(monkeypatch)
    assert _compat._on_network_mount("/mnt/projects/shot/a.exr")
    assert _compat._on_network_mount("/mnt/projects")
    assert _compat._on_network_mount("/mnt/my shows/ep01")


def test_a_local_path_beside_a_network_mount_does_not(monkeypatch):
    _fake_mounts(monkeypatch)
    assert not _compat._on_network_mount("/home/me/a.exr")
    # A sibling whose name only starts like the mount point.
    assert not _compat._on_network_mount("/mnt/projects2/a.exr")


def test_the_mount_table_is_read_once_per_interval(monkeypatch):
    reads = _fake_mounts(monkeypatch)
    for _ in range(3):
        _compat._on_network_mount("/mnt/projects/a")
    assert len(reads) == 1

    when, points = _compat._mounts_cache
    monkeypatch.setattr(_compat, "_mounts_cache", (when - 31, points))
    _compat._on_network_mount("/mnt/projects/a")
    assert len(reads) == 2


def test_on_linux_can_stall_reads_the_mounts(monkeypatch):
    _fake_mounts(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    assert _compat.can_stall("/mnt/projects/a.exr")
    assert not _compat.can_stall("/home/me/a.exr")
    assert _compat.can_stall("//server/share/a.exr")
