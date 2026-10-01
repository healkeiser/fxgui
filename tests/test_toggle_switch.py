"""FXToggleSwitch sits where its state says before it is first shown."""

# Third-party
import pytest

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXToggleSwitch


def test_a_switch_checked_before_it_shows_is_drawn_on(qtbot):
    switch = FXToggleSwitch()
    qtbot.addWidget(switch)
    switch.setChecked(True)
    assert switch.position == 1.0


def test_a_shown_switch_still_slides(qtbot):
    switch = FXToggleSwitch()
    qtbot.addWidget(switch)
    switch.show()
    switch.setChecked(True)
    assert switch.position < 1.0
    qtbot.waitUntil(lambda: switch.position == 1.0)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
@pytest.mark.parametrize("checked", [False, True])
def test_the_switch_reads_in_every_theme(qtbot, theme, checked):
    fxstyle.apply_theme(theme)
    switch = FXToggleSwitch()
    qtbot.addWidget(switch)
    switch.resize(44, 24)
    switch.setChecked(checked)
    image = switch.grab().toImage()

    def at(x, y):
        return image.pixelColor(x, y).name()

    on, off = (at(32, 12), at(8, 12)), (at(12, 12), at(36, 12))
    thumb, track = on if checked else off
    edge = at(22, 0)
    surface = fxstyle.colors().surface
    # WCAG's minimum for a control's parts: 3:1.
    assert fxstyle.get_contrast_ratio(thumb, track) >= 3, (thumb, track)
    assert fxstyle.get_contrast_ratio(edge, surface) >= 3, (edge, surface)
