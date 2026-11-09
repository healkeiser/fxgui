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
    """Make every path a share whose check waits until the event is set."""
    import threading

    from fxgui import _compat
    from fxgui.fxwidgets import _file_path_widget

    gate = threading.Event()
    real = _file_path_widget._path_is_valid

    def slow(path, mode):
        gate.wait(5)
        return real(path, mode)

    monkeypatch.setattr(_file_path_widget, "_path_is_valid", slow)
    monkeypatch.setattr(_compat, "can_stall", lambda _path: True)
    return gate


def _dead_share(monkeypatch):
    """Make a check of a share path hang until the event is set, then pass."""
    import threading

    from fxgui.fxwidgets import _file_path_widget

    gate = threading.Event()
    real = _file_path_widget._path_is_valid

    def hang(path, mode):
        if path.startswith(("\\\\", "//")):
            gate.wait(10)
            return True
        return real(path, mode)

    monkeypatch.setattr(_file_path_widget, "_path_is_valid", hang)
    return gate


def _drop(widget, path):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path)])
    widget.dropEvent(
        QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    )


def test_stuck_share_checks_never_hold_up_a_local_one(
    qtbot, qapp, tmp_path, monkeypatch
):
    gate = _dead_share(monkeypatch)
    stuck = FXFilePathWidget(mode="folder")
    qtbot.addWidget(stuck)
    try:
        for share in (r"\\dead\a", r"\\dead\b", r"\\dead\c"):
            stuck.set_path(share)
            stuck._do_validation()
        widget = FXFilePathWidget(mode="folder")
        qtbot.addWidget(widget)
        widget.set_path(str(tmp_path))
        widget._do_validation()
        qtbot.waitUntil(widget.is_valid)
        _drop(widget, str(tmp_path / "missing"))
        _drop(widget, str(tmp_path))
        assert widget.path() == QUrl.fromLocalFile(str(tmp_path)).toLocalFile()
    finally:
        gate.set()


def test_only_the_latest_drop_lands(qtbot, qapp, tmp_path, monkeypatch):
    gate = _dead_share(monkeypatch)
    widget = FXFilePathWidget(mode="folder")
    qtbot.addWidget(widget)
    _drop(widget, "//dead/share")
    _drop(widget, str(tmp_path))
    local = QUrl.fromLocalFile(str(tmp_path)).toLocalFile()
    assert widget.path() == local
    gate.set()
    # The share's late answer arrives, and is not shown.
    qtbot.wait(300)
    assert widget.path() == local


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


def test_a_typed_local_path_is_checked_off_the_ui_thread(
    qtbot, qapp, tmp_path, monkeypatch
):
    import threading

    from fxgui import _compat
    from fxgui.fxwidgets import _file_path_widget

    monkeypatch.setattr(_compat, "can_stall", lambda _path: False)
    threads = []
    real = _file_path_widget._path_is_valid

    def record(path, mode):
        threads.append(threading.current_thread())
        return real(path, mode)

    monkeypatch.setattr(_file_path_widget, "_path_is_valid", record)
    widget = FXFilePathWidget(mode="folder")
    qtbot.addWidget(widget)
    widget.set_path(str(tmp_path))
    widget._do_validation()

    qtbot.waitUntil(widget.is_valid)
    assert threading.main_thread() not in threads


def test_only_the_latest_check_of_one_text_lands(qtbot, qapp, monkeypatch):
    import threading

    from fxgui.fxwidgets import _file_path_widget

    gate = threading.Event()
    answers = iter([True, False])

    def answer(path, mode):
        found = next(answers)
        if found:
            gate.wait(10)
        return found

    monkeypatch.setattr(_file_path_widget, "_path_is_valid", answer)
    widget = FXFilePathWidget(mode="folder")
    qtbot.addWidget(widget)
    widget.set_path(r"\\srv\gone")
    with qtbot.waitSignal(widget.path_valid):
        widget._do_validation()
        widget._do_validation()
    gate.set()
    qtbot.wait(200)

    assert not widget.is_valid()


def test_at_the_thread_cap_only_the_newest_check_waits(
    qtbot, qapp, tmp_path, monkeypatch
):
    from fxgui.fxwidgets import _file_path_widget

    gate = _dead_share(monkeypatch)
    monkeypatch.setattr(_file_path_widget, "_THREAD_CAP", 1)
    checked = []
    hang = _file_path_widget._path_is_valid

    def record(path, mode):
        checked.append(path)
        return hang(path, mode)

    monkeypatch.setattr(_file_path_widget, "_path_is_valid", record)
    widget = FXFilePathWidget(mode="folder")
    qtbot.addWidget(widget)
    try:
        widget.set_path(r"\\dead\share")
        widget._do_validation()
        qtbot.waitUntil(lambda: bool(checked))
        for name in ("a", "b", str(tmp_path)):
            widget.set_path(name)
            widget._do_validation()
    finally:
        gate.set()

    qtbot.waitUntil(widget.is_valid)
    assert checked == [r"\\dead\share", str(tmp_path)]
