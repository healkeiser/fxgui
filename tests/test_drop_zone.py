"""The drop zone's Clear button, path rules and drag state."""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QMimeData, QPoint, Qt, QUrl
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
        zone.dragEnterEvent(event)
        assert event.isAccepted() is taken
    assert zone._accepts(tmp_path / "missing.png") is False


def test_drag_state_is_a_property_the_theme_sheet_styles(qtbot, qapp, tmp_path):
    zone = FXDropZone()
    qtbot.addWidget(zone)
    target = tmp_path / "a.png"
    target.write_text("x")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(target))])
    event = QDragEnterEvent(
        QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    )
    zone.dragEnterEvent(event)
    assert zone._drop_area.property("dropState") == "drag"
    assert zone._drop_area.styleSheet() == ""
    assert 'FXDropZoneArea[dropState="drag"]' in fxstyle._build_stylesheet()


def test_a_drop_on_the_zone_adds_one_file_in_single_mode(qtbot, qapp, tmp_path):
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
    zone.dropEvent(
        QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton,
                   Qt.NoModifier)
    )
    assert zone.selected_files() == [first]
    assert received == [[first]]


def _file(tmp_path, name="a.png", size=1):
    path = tmp_path / name
    path.write_bytes(b"x" * size)
    return path


def test_the_children_pass_drops_up_to_the_zone(qtbot, qapp):
    zone = FXDropZone()
    qtbot.addWidget(zone)

    assert zone.acceptDrops()
    assert not zone._drop_area.acceptDrops()
    assert not zone.file_tree().acceptDrops()
    assert not zone.file_tree().viewport().acceptDrops()


def test_two_flashes_share_one_owned_timer(qtbot, qapp, tmp_path):
    zone = FXDropZone(show_tree=False)
    qtbot.addWidget(zone)
    zone.FLASH_MS = 30

    zone._flash_feedback("error")
    zone._flash_feedback("success")

    assert zone._flash_timer.parent() is zone
    assert zone._drop_area.property("dropState") == "success"
    qtbot.waitUntil(
        lambda: zone._drop_area.property("dropState") == "idle", timeout=1000
    )


def test_a_context_menu_is_freed_once_it_closes(qtbot, qapp, tmp_path):
    from qtpy.QtWidgets import QMenu

    zone = FXDropZone()
    qtbot.addWidget(zone)
    zone.set_files([_file(tmp_path, "a.png"), _file(tmp_path, "b.png")])
    zone.show()
    qtbot.waitExposed(zone)
    tree = zone.file_tree()
    spot = tree.visualItemRect(tree.topLevelItem(1)).center()

    zone._show_context_menu(spot)
    menu = zone.findChild(QMenu)
    removed = []
    zone.file_removed.connect(removed.append)
    menu.actions()[0].trigger()
    menu.hide()
    qapp.sendPostedEvents(None, QEvent.DeferredDelete)

    assert zone.findChild(QMenu) is None
    assert [p.name for p in removed] == ["b.png"]


def test_an_unknown_accept_mode_is_refused(qtbot, qapp):
    with pytest.raises(ValueError):
        FXDropZone(accept_mode="images")


def test_extensions_take_any_case_and_dot(qtbot, qapp, tmp_path):
    zone = FXDropZone(extensions={"PNG", ".Exr"})
    qtbot.addWidget(zone)

    assert zone.extensions() == {".png", ".exr"}
    assert zone._accepts(_file(tmp_path, "shot.png"))


def test_files_dropped_hands_out_a_copy(qtbot, qapp, tmp_path):
    zone = FXDropZone(multiple=False)
    qtbot.addWidget(zone)
    received = []
    zone.files_dropped.connect(received.append)

    zone.add_files([_file(tmp_path)])
    received[-1].append("injected")

    assert zone.selected_files() == [tmp_path / "a.png"]


def test_clear_empties_the_list_and_disables_the_button(qtbot, qapp, tmp_path):
    zone = FXDropZone()
    qtbot.addWidget(zone)
    zone.set_files([_file(tmp_path)])
    cleared = []
    zone.files_cleared.connect(lambda: cleared.append(True))

    zone._clear_btn.click()

    assert not zone.has_files()
    assert not zone._clear_btn.isEnabled()
    assert zone.file_tree().topLevelItemCount() == 0
    assert cleared == [True]


def test_the_size_column_is_qt_s_own_format(qtbot, qapp, tmp_path):
    from qtpy.QtCore import QLocale

    zone = FXDropZone()
    qtbot.addWidget(zone)
    zone.set_files([_file(tmp_path, size=1536)])

    assert zone.file_tree().topLevelItem(0).text(2) == (
        QLocale().formattedDataSize(1536, 1, QLocale.DataSizeTraditionalFormat)
    )


def test_the_labels_take_the_root_font_size():
    sheet = fxstyle._build_stylesheet()
    zone_rules = sheet[sheet.index("FXDropZone QWidget#FXDropZoneArea"):]
    zone_rules = zone_rules[: zone_rules.index("FXDropZoneCount")]

    assert "font-size" not in zone_rules
