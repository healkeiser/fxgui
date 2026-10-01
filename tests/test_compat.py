"""Tests for `fxgui._compat` cross-binding liveness checks.

Regression: fxstyle/fxicons used to import ``qtpy.shiboken`` directly, which
raises under PyQt5/PyQt6.
"""

# Third-party
from qtpy.QtCore import QCoreApplication, QEvent, QObject

# Internal
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



class _PySide2Cache:
    """QPixmapCache as PySide2 binds it: find(key) needs a pixmap to fill."""

    finds = 0

    @classmethod
    def find(cls, key, pixmap=None):
        from qtpy.QtGui import QPixmapCache

        cls.finds += 1
        if pixmap is None:
            raise TypeError("find(key) takes a pixmap on PySide2")
        found = QPixmapCache.find(key)
        if found is None or found.isNull():
            return False
        pixmap.swap(found)
        return True


def test_find_pixmap_reads_both_bindings(qapp, monkeypatch):
    from qtpy.QtGui import QColor, QPixmap, QPixmapCache

    from fxgui import _compat

    stored = QPixmap(4, 4)
    stored.fill(QColor("#00ff00"))
    QPixmapCache.insert("fxgui.test|green", stored)
    assert _compat.find_pixmap("fxgui.test|green").cacheKey() == (
        stored.cacheKey())
    assert _compat.find_pixmap("fxgui.test|missing") is None

    monkeypatch.setattr(_compat, "QPixmapCache", _PySide2Cache)
    found = _compat.find_pixmap("fxgui.test|green")
    assert found is not None and found.toImage() == stored.toImage()
    assert _compat.find_pixmap("fxgui.test|missing") is None


def test_the_icon_engine_finds_through_the_compat_helper(qapp, monkeypatch):
    from qtpy.QtCore import QSize
    from qtpy.QtGui import QPixmapCache

    from fxgui import _compat, fxicons

    QPixmapCache.clear()
    _PySide2Cache.finds = 0
    monkeypatch.setattr(_compat, "QPixmapCache", _PySide2Cache)
    icon = fxicons.get_icon("check")
    first = icon.pixmap(QSize(16, 16))
    second = icon.pixmap(QSize(16, 16))

    assert _PySide2Cache.finds >= 2
    assert not first.isNull() and first.cacheKey() == second.cacheKey()
