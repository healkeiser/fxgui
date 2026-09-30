"""The drop zone's Clear button, path rules and drag state."""

# Built-in

# Third-party
from qtpy.QtCore import QMimeData, QPoint, Qt, QUrl
from qtpy.QtGui import QDragEnterEvent

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXDropZone


def test_clear_is_enabled_once_files_are_set_without_a_tree(qtbot, qapp, tmp_path):
    zone = FXDropZone(show_tree=False)
    qtbot.addWidget(zone)
    target = tmp_path / "a.png"
    target.write_text("x")
    zone.set_files([target])
    assert zone._clear_btn.isEnabled()


def _drag(path):
    """A drag event and its mime data, which the event does not own."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDragEnterEvent(
        QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    )
    return event, mime


def test_zone_and_tree_accept_the_same_paths(qtbot, qapp, tmp_path):
    upper = tmp_path / "SHOT.PNG"
    upper.write_text("x")
    other = tmp_path / "notes.txt"
    other.write_text("x")
    zone = FXDropZone(extensions={".png"})
    qtbot.addWidget(zone)
    for path, taken in ((upper, True), (other, False), (tmp_path, False)):
        assert zone._accepts(path) is taken
        event, _mime = _drag(path)
        zone.file_tree.dragEnterEvent(event)
        assert event.isAccepted() is taken
    assert zone._accepts(tmp_path / "missing.png") is False


def test_drag_state_is_a_property_the_theme_sheet_styles(qtbot, qapp, tmp_path):
    zone = FXDropZone()
    qtbot.addWidget(zone)
    assert not isinstance(zone, fxstyle.FXThemeAware)
    target = tmp_path / "a.png"
    target.write_text("x")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(target))])
    event = QDragEnterEvent(
        QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    )
    zone._handle_drag_enter(event)
    assert zone._drop_area.property("dropState") == "drag"
    assert zone._drop_area.styleSheet() == ""
    assert 'FXDropZoneArea[dropState="drag"]' in fxstyle.build_stylesheet()


def test_a_drop_on_the_tree_adds_to_the_zone(qtbot, qapp, tmp_path):
    from qtpy.QtCore import QPointF
    from qtpy.QtGui import QDropEvent

    zone = FXDropZone(multiple=False)
    qtbot.addWidget(zone)
    first, second = tmp_path / "a.png", tmp_path / "b.png"
    for path in (first, second):
        path.write_text("x")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in (first, second)])
    received = []
    zone.files_dropped.connect(received.append)
    zone.file_tree.dropEvent(
        QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton,
                   Qt.NoModifier)
    )
    assert zone.selected_files == [first]
    assert received == [[first]]
