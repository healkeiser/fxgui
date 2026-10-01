"""A theme_changed connection to a widget's method dies with the widget."""

import gc

from qtpy.QtCore import SIGNAL, QCoreApplication, QEvent
from qtpy.QtWidgets import QWidget

from fxgui import fxstyle


class _Listener(QWidget):
    calls = []

    def on_theme(self, name: str) -> None:
        _Listener.calls.append(name)


def _receivers() -> int:
    return fxstyle._signals.receivers(SIGNAL("theme_changed(QString)"))


def _settled() -> int:
    """Return the receiver count once earlier tests' widgets are freed."""
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    gc.collect()
    return _receivers()


def test_qt_deleting_the_widget_drops_the_connection(qapp):
    fxstyle.apply_theme("dark")
    before = _settled()
    parent = QWidget()
    widget = _Listener(parent)
    fxstyle.theme_changed.connect(widget.on_theme)
    assert _receivers() == before + 1
    _Listener.calls.clear()
    parent.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert _receivers() == before
    fxstyle.apply_theme("light")
    assert _Listener.calls == []


def test_python_dropping_the_widget_drops_the_connection(qapp):
    fxstyle.apply_theme("dark")
    before = _settled()
    widget = _Listener()
    fxstyle.theme_changed.connect(widget.on_theme)
    assert _receivers() == before + 1
    _Listener.calls.clear()
    del widget
    gc.collect()
    assert _receivers() == before
    fxstyle.apply_theme("light")
    assert _Listener.calls == []
