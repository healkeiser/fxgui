"""Tag chips wrap and stay shown, and the tags signal hands out a copy."""

# Third-party
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFlowLayout, FXTagInput


def test_tags_changed_emits_a_copy(qtbot, qapp):
    tags = FXTagInput()
    qtbot.addWidget(tags)
    received = []
    tags.tags_changed.connect(received.append)
    tags.add_tag("python")
    received[-1].append("injected")
    assert tags.tags == ["python"]


def test_chips_wrap_onto_new_lines_and_all_stay_shown(qtbot, qapp):
    host = QWidget()
    qtbot.addWidget(host)
    column = QVBoxLayout(host)
    tags = FXTagInput()
    column.addWidget(tags)
    column.addStretch()
    host.resize(200, 400)
    host.show()
    qtbot.waitExposed(host)
    for index in range(10):
        tags.add_tag(f"tag_number_{index}")
    qapp.processEvents()
    chips = [tags._tags_layout.itemAt(i).widget() for i in range(10)]
    assert isinstance(tags._tags_layout, FXFlowLayout)
    assert len({chip.y() for chip in chips}) > 1, "chips wrapped"
    assert host.width() == 200, "the field did not widen its window"
    for chip in chips:
        assert chip.visibleRegion().boundingRect().size() == chip.size()


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
