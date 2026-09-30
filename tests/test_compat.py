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

