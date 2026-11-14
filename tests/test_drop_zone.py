"""The drop zone's Clear button, path rules and drag state."""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QMimeData, QPoint, Qt, QUrl
from qtpy.QtGui import QDragEnterEvent

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXDropZone, _drop_zone


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
        vetted = _drop_zone._vet([path], zone.accept_mode(), zone.extensions())
        assert bool(vetted) is taken
        event, _mime = _drag(path)
        zone.dragEnterEvent(event)
        assert event.isAccepted() is taken
    assert not _drop_zone._vet(
        [tmp_path / "missing.png"], zone.accept_mode(), zone.extensions()
    )


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
        lambda: zone._drop_area.property("dropState") == "idle"
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
    assert _drop_zone._vet(
        [_file(tmp_path, "shot.png")], zone.accept_mode(), zone.extensions()
    )


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


def test_a_file_gone_from_disk_lists_with_no_size(qtbot, qapp, tmp_path):
    zone = FXDropZone()
    qtbot.addWidget(zone)
    kept = _file(tmp_path, "kept.png")

    zone.set_files([tmp_path / "gone.png", kept])

    tree = zone.file_tree()
    assert tree.topLevelItem(0).text(0) == "gone.png"
    assert tree.topLevelItem(0).text(2) == "-"
    assert tree.topLevelItem(1).text(2) != "-"


def test_an_empty_extension_set_accepts_everything_as_none_does(
    qtbot, qapp, tmp_path
):
    """An empty set is no filter, for a drop as for Browse."""
    notes = tmp_path / "notes.txt"
    notes.write_text("x")
    zone = FXDropZone(extensions=set())
    qtbot.addWidget(zone)
    assert zone.extensions() is None
    event, _mime = _drag(notes)
    zone.dragEnterEvent(event)
    assert event.isAccepted()


def test_browse_keeps_the_filter_and_flashes_when_nothing_is_left(
    qtbot, qapp, tmp_path, monkeypatch
):
    from qtpy.QtWidgets import QFileDialog

    other = tmp_path / "notes.txt"
    other.write_text("x")
    zone = FXDropZone(extensions={".png"})
    qtbot.addWidget(zone)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileNames", lambda *a, **k: ([str(other)], "")
    )

    zone._browse()

    assert zone.selected_files() == []
    assert zone._drop_area.property("dropState") == "error"


def test_a_drag_never_reads_the_disk(qtbot, qapp, tmp_path, monkeypatch):
    from pathlib import Path

    paths = []
    for name in ("a.png", "b.png", "c.png"):
        (tmp_path / name).write_text("x")
        paths.append(tmp_path / name)
    checked = []

    def recording(real):
        def wrapper(self, *args, **kwargs):
            if self in paths:
                checked.append(self)
            return real(self, *args, **kwargs)

        return wrapper

    for name in ("exists", "is_dir", "is_file", "stat"):
        monkeypatch.setattr(Path, name, recording(getattr(Path, name)))
    zone = FXDropZone()
    qtbot.addWidget(zone)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    event = QDragEnterEvent(
        QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    )

    zone.dragEnterEvent(event)

    assert event.isAccepted()
    assert checked == []


def _drop_event(paths):
    """A drop event and its mime data, which the event does not own."""
    from qtpy.QtCore import QPointF
    from qtpy.QtGui import QDropEvent

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    event = QDropEvent(
        QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    )
    return event, mime


def test_a_drop_from_a_share_never_waits_on_the_disk(
    qtbot, qapp, tmp_path, monkeypatch
):
    import threading
    import time

    from fxgui import _compat

    gate = threading.Event()
    real = _drop_zone._probe

    def slow(path):
        gate.wait(5)
        return real(path)

    monkeypatch.setattr(_compat, "can_stall", lambda _path: True)
    monkeypatch.setattr(_drop_zone, "_probe", slow)
    zone = FXDropZone()
    qtbot.addWidget(zone)
    first = _file(tmp_path)
    event, _mime = _drop_event([first])

    start = time.monotonic()
    zone.dropEvent(event)
    took = time.monotonic() - start
    gate.set()
    assert took < 1, "the drop waited on the disk"
    qtbot.waitUntil(zone.has_files)
    assert zone.selected_files() == [first]


def test_a_path_given_twice_is_listed_once(qtbot, qapp, tmp_path):
    zone = FXDropZone()
    qtbot.addWidget(zone)
    a, b, c = (_file(tmp_path, name) for name in ("a.png", "b.png", "c.png"))
    received = []
    zone.files_dropped.connect(received.append)

    zone.add_files([a, a, b])
    zone.add_files([b, c])

    assert zone.selected_files() == [a, b, c]
    assert received == [[a, b], [c]]
    assert zone.file_tree().topLevelItemCount() == 3


def test_adding_files_keeps_the_rows_already_listed(
    qtbot, qapp, tmp_path, monkeypatch
):
    probed = []
    real = _drop_zone._probe

    def recording(path):
        probed.append(path)
        return real(path)

    monkeypatch.setattr(_drop_zone, "_probe", recording)
    zone = FXDropZone()
    qtbot.addWidget(zone)
    a, b = _file(tmp_path, "a.png"), _file(tmp_path, "b.png")

    zone.add_files([a])
    tree = zone.file_tree()
    tree.topLevelItem(0).setData(0, Qt.UserRole + 1, "kept")
    zone.add_files([b])

    assert probed == [a, b]
    assert tree.topLevelItem(0).data(0, Qt.UserRole + 1) == "kept"


def test_removing_a_file_takes_only_its_row(qtbot, qapp, tmp_path):
    zone = FXDropZone()
    qtbot.addWidget(zone)
    a, b, c = (_file(tmp_path, name) for name in ("a.png", "b.png", "c.png"))
    zone.set_files([a, b, c])

    zone._remove_file(b)

    tree = zone.file_tree()
    names = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert names == ["a.png", "c.png"]
    assert zone._count_label.text() == "2 files selected"


def test_in_single_mode_only_the_newest_drop_lands(
    qtbot, qapp, tmp_path, monkeypatch
):
    import threading
    from pathlib import Path

    from fxgui import _compat

    gate = threading.Event()
    real = _drop_zone._probe

    def slow(path):
        if "slow" in path.name:
            gate.wait(5)
        return real(path)

    monkeypatch.setattr(_compat, "can_stall", lambda p: "slow" in Path(p).name)
    monkeypatch.setattr(_drop_zone, "_probe", slow)
    zone = FXDropZone(multiple=False)
    qtbot.addWidget(zone)
    slow_file, fast = _file(tmp_path, "slow.png"), _file(tmp_path, "fast.png")

    try:
        slow_event, _slow_mime = _drop_event([slow_file])
        zone.dropEvent(slow_event)
        fast_event, _fast_mime = _drop_event([fast])
        zone.dropEvent(fast_event)
        assert zone.selected_files() == [fast]
    finally:
        gate.set()
    qtbot.wait(300)
    assert zone.selected_files() == [fast]
