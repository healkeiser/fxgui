"""FXToggleSwitch sits where its state says before it is first shown."""

# Internal
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
