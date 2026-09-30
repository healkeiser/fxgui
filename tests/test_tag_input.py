"""Tag chips stay reachable, and the tags signal hands out a copy."""

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXTagInput


def test_tags_changed_emits_a_copy(qtbot, qapp):
    tags = FXTagInput()
    qtbot.addWidget(tags)
    received = []
    tags.tags_changed.connect(received.append)
    tags.add_tag("python")
    received[-1].append("injected")
    assert tags.tags == ["python"]


def test_chips_wider_than_the_field_can_be_scrolled_to(qtbot, qapp):
    tags = FXTagInput()
    qtbot.addWidget(tags)
    tags.resize(200, 120)
    tags.show()
    qtbot.waitExposed(tags)
    for index in range(10):
        tags.add_tag(f"tag_number_{index}")
    qtbot.waitUntil(
        lambda: tags._scroll_area.horizontalScrollBar().isVisible(),
        timeout=1000,
    )
    last = tags._tags_layout.itemAt(9).widget()
    tags._scroll_area.ensureWidgetVisible(last)
    qapp.processEvents()
    assert last.visibleRegion().boundingRect().width() == last.width()


def test_chips_style_through_the_theme_sheet(qtbot, qapp):
    tags = FXTagInput()
    qtbot.addWidget(tags)
    tags.add_tag("python")
    chip = tags._tags_layout.itemAt(0).widget()
    assert chip.styleSheet() == "" and chip.label.styleSheet() == ""
    assert tags._input.styleSheet() == ""
    sheet = fxstyle.build_stylesheet()
    ink = fxstyle.colors().text_on_accent_primary
    assert f"FXTagChip QLabel {{\n    color: {ink};" in sheet
