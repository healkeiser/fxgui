"""Tests for `fxgui._compat` cross-binding liveness checks.

Regression: fxstyle/fxicons used to import ``qtpy.shiboken`` directly, which
raises under PyQt5/PyQt6 and crashed every FXThemeAware widget construction.
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


def test_theme_aware_widget_constructs_without_shiboken_import(qtbot):
    """FXThemeAware widgets must construct and process the deferred theme
    apply on every binding (the old code imported qtpy.shiboken inside the
    theme-change handler)."""
    from qtpy.QtWidgets import QWidget

    from fxgui import fxstyle

    class Probe(fxstyle.FXThemeAware, QWidget):
        pass

    widget = Probe()
    qtbot.addWidget(widget)
    # Fire the handler directly: this used to be the crash site under PyQt
    fxstyle.theme_manager.notify_theme_changed(fxstyle.get_theme())
