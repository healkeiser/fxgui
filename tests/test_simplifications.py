"""Behaviour the simplification pass must keep."""

# Third-party
from qtpy.QtCore import QMimeData, QPoint, Qt, QUrl
from qtpy.QtGui import QDragEnterEvent, QDragLeaveEvent
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

# Internal
from fxgui.fxwidgets import (
    FXCollapsibleWidget,
    FXDropZone,
    FXRangeSlider,
    FXTimelineSlider,
)


def _tall_content(rows):
    content = QWidget()
    layout = QVBoxLayout(content)
    for index in range(rows):
        layout.addWidget(QLabel(f"row {index}"))
    return content


def test_collapsible_scrolls_only_content_taller_than_its_cap(qtbot, qapp):
    tall = FXCollapsibleWidget(title="Tall", max_content_height=60)
    short = FXCollapsibleWidget(title="Short", max_content_height=600)
    for section, rows in ((tall, 20), (short, 2)):
        qtbot.addWidget(section)
        section.set_content_widget(_tall_content(rows))
        section.resize(300, 400)
        section.show()
        section.expand(animate=False)
    qtbot.waitUntil(
        lambda: tall._content_area.verticalScrollBar().isVisible(),
        timeout=1000,
    )
    assert not short._content_area.verticalScrollBar().isVisible()
    tall.collapse(animate=False)
    assert tall._content_area.height() == 0


def test_a_click_on_the_timeline_track_scrubs_to_that_frame(qtbot, qapp):
    timeline = FXTimelineSlider(start_frame=0, end_frame=100)
    qtbot.addWidget(timeline)
    timeline.resize(600, 60)
    timeline.show()
    qtbot.waitExposed(timeline)
    track = timeline._track_widget
    x = track.EDGE_PAD + (track.width() - 2 * track.EDGE_PAD) // 2
    QTest.mouseClick(track, Qt.LeftButton, Qt.NoModifier, QPoint(x, 10))
    assert timeline.current_frame() == 50


def test_range_slider_hover_follows_the_pointer(qtbot, qapp):
    slider = FXRangeSlider(low=20, high=80)
    qtbot.addWidget(slider)
    slider.resize(317, 70)
    slider.show()
    qtbot.waitExposed(slider)
    x = int(slider._value_to_position(80))
    QTest.mouseMove(slider, QPoint(x, slider.height() // 2))
    assert slider._hover_handle == slider.HANDLE_HIGH


def test_drop_zone_tree_follows_rules_set_after_construction(
    qtbot, qapp, tmp_path
):
    zone = FXDropZone(extensions={".png"})
    qtbot.addWidget(zone)
    text = tmp_path / "notes.txt"
    text.write_text("x")
    def taken(path):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        event = QDragEnterEvent(
            QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        zone.dragEnterEvent(event)
        return event.isAccepted()

    assert not taken(text)
    zone.set_extensions({".txt"})
    assert taken(text)
    zone.set_accept_mode("folders")
    assert not taken(text)
    assert taken(tmp_path)


def test_drop_zone_drag_leave_returns_to_idle(qtbot, qapp, tmp_path):
    zone = FXDropZone()
    qtbot.addWidget(zone)
    target = tmp_path / "a.png"
    target.write_text("x")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(target))])
    zone.dragEnterEvent(QDragEnterEvent(
        QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    ))
    assert zone._drop_area.property("dropState") == "drag"
    zone.dragLeaveEvent(QDragLeaveEvent())
    assert zone._drop_area.property("dropState") == "idle"


def test_code_block_language_lives_on_its_highlighter(qtbot, qapp):
    from fxgui.fxwidgets._code_block import FXCodeBlock

    block = FXCodeBlock("fn main() {}", language="python")
    qtbot.addWidget(block)
    block.set_language("rust")
    assert block._highlighter.language() == "rust"


def test_breadcrumb_edit_mode_opens_and_closes_publicly(qtbot, qapp):
    from fxgui.fxwidgets import FXBreadcrumb

    crumb = FXBreadcrumb()
    qtbot.addWidget(crumb)
    crumb.set_path(["a", "b"])
    crumb.enter_edit_mode()
    assert crumb.is_editing()
    crumb.exit_edit_mode()
    assert not crumb.is_editing()


def test_avatar_shows_a_new_photo_and_a_new_size(qtbot, qapp):
    from qtpy.QtGui import QColor, QPixmap

    from fxgui.fxwidgets import FXAvatar

    def photo(colour):
        pixmap = QPixmap(40, 40)
        pixmap.fill(QColor(colour))
        return pixmap

    avatar = FXAvatar("Anne Martin", size=32, pixmap=photo("#ff0000"))
    qtbot.addWidget(avatar)
    assert avatar.grab().toImage().pixelColor(16, 16).name() == "#ff0000"
    avatar.set_pixmap(photo("#0000ff"))
    assert avatar.grab().toImage().pixelColor(16, 16).name() == "#0000ff"
    avatar.set_size(48)
    assert avatar.grab().toImage().pixelColor(24, 24).name() == "#0000ff"
