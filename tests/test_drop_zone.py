"""The drop zone's Clear button, path rules and drag state."""

# Built-in

# Third-party
from qtpy.QtCore import QMimeData, QPoint, Qt, QUrl
from qtpy.QtGui import QDragEnterEvent

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXDropZone
from fxgui.fxwidgets._drop_zone import _FileDropTree


def test_clear_is_enabled_once_files_are_set_without_a_tree(qtbot, qapp, tmp_path):
    zone = FXDropZone(show_tree=False)
    qtbot.addWidget(zone)
    target = tmp_path / "a.png"
    target.write_text("x")
    zone.set_files([target])
    assert zone._clear_btn.isEnabled()


def test_zone_and_tree_accept_the_same_paths(qtbot, qapp, tmp_path):
    upper = tmp_path / "SHOT.PNG"
    upper.write_text("x")
    other = tmp_path / "notes.txt"
    other.write_text("x")
    zone = FXDropZone(extensions={".png"})
    tree = _FileDropTree(extensions={".png"})
    qtbot.addWidget(zone)
    qtbot.addWidget(tree)
    for path in (upper, other, tmp_path, tmp_path / "missing.png"):
        assert zone._is_valid_drop([path]) == tree._is_valid_path(path)
    assert zone._is_valid_drop([upper]) is True


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
