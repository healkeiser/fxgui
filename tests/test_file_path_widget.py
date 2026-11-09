"""The path widget checks paths off the UI thread and keeps every dropped file."""

# Third-party
from qtpy.QtCore import QMimeData, QPointF, Qt, QThread, QUrl
from qtpy.QtGui import QDropEvent

# Internal
from fxgui.fxwidgets import FXFilePathWidget


def test_checks_run_on_the_pool_not_on_owned_threads(qtbot, qapp, tmp_path):
    widget = FXFilePathWidget(mode="file")
    qtbot.addWidget(widget)
    target = tmp_path / "a.txt"
    target.write_text("x")

    for text in ("nope", str(tmp_path / "missing"), str(target)):
        widget.set_path(text)
        widget._do_validation()
    qtbot.waitUntil(lambda: widget.is_valid())
    assert widget.findChildren(QThread) == []


def test_a_missing_path_shows_the_error_indicator(qtbot, qapp, tmp_path):
    widget = FXFilePathWidget(mode="file")
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.path_valid) as blocker:
        widget.set_path(str(tmp_path / "missing"))
        widget._do_validation()
    assert blocker.args == [False]
    assert widget._indicator.toolTip() == "Path does not exist"


def test_a_multi_file_drop_keeps_every_file(qtbot, qapp, tmp_path):
    widget = FXFilePathWidget(mode="files")
    qtbot.addWidget(widget)
    first, second = tmp_path / "a.txt", tmp_path / "b.txt"
    first.write_text("a")
    second.write_text("b")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(first)), QUrl.fromLocalFile(str(second))])
    event = QDropEvent(
        QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    )

    widget.dropEvent(event)

    qtbot.waitUntil(lambda: widget.path() != "")
    assert widget.path().split(";") == [
        QUrl.fromLocalFile(str(first)).toLocalFile(),
        QUrl.fromLocalFile(str(second)).toLocalFile(),
    ]


def test_a_result_for_a_deleted_widget_is_dropped(qtbot, qapp, tmp_path):
    from qtpy.QtCore import QEvent

    widget = FXFilePathWidget(mode="folder")
    widget.set_path(str(tmp_path))
    widget._do_validation()
    widget.deleteLater()
    qapp.sendPostedEvents(None, QEvent.DeferredDelete)
    qtbot.wait(200)


def test_an_unknown_mode_is_refused(qtbot, qapp):
    import pytest

    with pytest.raises(ValueError):
        FXFilePathWidget(mode="directory")
    widget = FXFilePathWidget(mode="folder")
    qtbot.addWidget(widget)
    with pytest.raises(ValueError):
        widget.set_mode("dir")


def test_the_indicator_is_an_icon_label_with_no_sheet(qtbot, qapp):
    from fxgui.fxwidgets import FXIconLabel

    widget = FXFilePathWidget()
    qtbot.addWidget(widget)

    assert isinstance(widget._indicator, FXIconLabel)
    assert widget._indicator.styleSheet() == ""


def test_a_drop_on_the_field_reaches_the_widget(qtbot, qapp):
    widget = FXFilePathWidget()
    qtbot.addWidget(widget)

    assert not widget._input.acceptDrops()
    assert widget.acceptDrops()


def _blocked_disk(monkeypatch):
    """Make every disk check in the widget wait until the event is set."""
    import threading

    from fxgui.fxwidgets import _file_path_widget

    gate = threading.Event()
    real = _file_path_widget._path_is_valid

    def slow(path, mode):
        gate.wait(5)
        return real(path, mode)

    monkeypatch.setattr(_file_path_widget, "_path_is_valid", slow)
    return gate


def test_a_stuck_check_leaves_the_host_pool_free(qtbot, qapp, tmp_path, monkeypatch):
    from qtpy.QtCore import QThreadPool

    gate = _blocked_disk(monkeypatch)
    widget = FXFilePathWidget(mode="folder")
    qtbot.addWidget(widget)
    widget.set_path(str(tmp_path))
    widget._do_validation()
    try:
        assert QThreadPool.globalInstance().activeThreadCount() == 0
    finally:
        gate.set()
    qtbot.waitUntil(widget.is_valid)


def test_a_drop_checks_the_disk_off_the_ui_thread(qtbot, qapp, tmp_path, monkeypatch):
    import time

    gate = _blocked_disk(monkeypatch)
    widget = FXFilePathWidget(mode="folder")
    qtbot.addWidget(widget)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(tmp_path))])
    event = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)

    start = time.monotonic()
    widget.dropEvent(event)
    took = time.monotonic() - start
    gate.set()
    assert took < 1, "the drop waited on the disk"
    qtbot.waitUntil(lambda: widget.path() != "")
    assert widget.path() == QUrl.fromLocalFile(str(tmp_path)).toLocalFile()
