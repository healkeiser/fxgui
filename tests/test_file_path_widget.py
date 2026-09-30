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
    qtbot.waitUntil(lambda: widget.is_valid(), timeout=2000)
    assert widget.findChildren(QThread) == []


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

    assert widget.path.split(";") == [
        QUrl.fromLocalFile(str(first)).toLocalFile(),
        QUrl.fromLocalFile(str(second)).toLocalFile(),
    ]


def test_path_widget_leaves_the_mixin(qtbot, qapp):
    widget = FXFilePathWidget()
    qtbot.addWidget(widget)


def test_a_result_for_a_deleted_widget_is_dropped(qtbot, qapp, tmp_path):
    from qtpy.QtCore import QEvent, QThreadPool

    widget = FXFilePathWidget(mode="folder")
    widget.set_path(str(tmp_path))
    widget._do_validation()
    widget.deleteLater()
    qapp.sendPostedEvents(None, QEvent.DeferredDelete)
    QThreadPool.globalInstance().waitForDone(2000)
    qapp.processEvents()
