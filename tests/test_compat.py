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



def test_find_pixmap_answers_none_for_a_miss(qapp):
    from qtpy.QtGui import QColor, QPixmap, QPixmapCache

    from fxgui import _compat

    stored = QPixmap(4, 4)
    stored.fill(QColor("#00ff00"))
    QPixmapCache.insert("fxgui.test|green", stored)
    assert _compat.find_pixmap("fxgui.test|green").cacheKey() == (
        stored.cacheKey())
    assert _compat.find_pixmap("fxgui.test|missing") is None
