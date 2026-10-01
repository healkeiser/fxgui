"""Tag chips wrap, stay shown and wear a border; the signal hands a copy."""

# Third-party
import pytest
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFlowLayout, FXTagChip, FXTagInput


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


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
@pytest.mark.parametrize("removable", [False, True])
def test_a_chip_has_a_border_at_the_theme_radius(qtbot, theme, removable):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    chip = FXTagChip("comp", removable=removable)
    QVBoxLayout(window).addWidget(chip)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    image = chip.grab().toImage()
    colors = fxstyle.colors()
    radius = fxstyle.BUTTON_RADIUS

    def at(x, y):
        return image.pixelColor(x, y).name()

    middle = chip.height() // 2
    for edge in (at(radius + 2, 0), at(0, middle), at(chip.width() - 1, middle)):
        assert edge == colors.border_light.lower()
    # Rounded at the theme's radius: the corner pixel is not the border.
    assert at(0, 0) != colors.border_light.lower()
    assert at(radius + 2, middle) == colors.primary_button.lower()
