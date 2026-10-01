"""FXToggleSwitch: where it sits, how tall it is, and how every state reads."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

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


_THEMES = fxstyle.get_available_themes()


def _read(c):
    return fxstyle.get_contrast_ratio(*c)


def _grab(qtbot, theme, checked, state=""):
    """Return the switch's pixels in `theme`: thumb, track, edge, surface."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    layout = QVBoxLayout(window)
    sink = QPushButton("sink")
    switch = FXToggleSwitch()
    layout.addWidget(sink)
    layout.addWidget(switch)
    qtbot.addWidget(window)
    switch.setChecked(checked)
    if state == "disabled":
        switch.setEnabled(False)
    window.show()
    qtbot.waitExposed(window)
    if state == "focus":
        window.activateWindow()
        QApplication.processEvents()
        switch.setFocus(Qt.TabFocusReason)
        QApplication.processEvents()
        assert switch.hasFocus()
    if state == "hover":
        switch.setAttribute(Qt.WA_UnderMouse, True)
    image = switch.grab().toImage()
    track = switch.track_rect()
    middle = track.center().y()
    half = track.height() // 2
    thumb_x = track.right() - half if checked else track.left() + half
    track_x = track.left() + 4 if checked else track.right() - 4

    def at(x, y):
        return image.pixelColor(x, y).name()

    return (
        at(thumb_x, middle),
        at(track_x, middle),
        at(track.center().x(), track.top()),
        fxstyle.colors().surface,
    )


def test_the_switch_is_as_tall_as_a_button(qtbot):
    window = QWidget()
    fxstyle.register_themed_root(window)
    layout = QVBoxLayout(window)
    button, switch = QPushButton("Publish"), FXToggleSwitch()
    layout.addWidget(button)
    layout.addWidget(switch)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    # The row is a button's height; the track inside is the indicator size.
    assert switch.height() == button.height() == fxstyle.control_height(button)
    track = switch.track_rect()
    assert track.height() == fxstyle.INDICATOR_SIZE
    assert track.width() == 2 * fxstyle.INDICATOR_SIZE
    assert abs(track.center().y() - switch.rect().center().y()) <= 1


@pytest.mark.parametrize("theme", _THEMES)
@pytest.mark.parametrize("checked", [False, True])
@pytest.mark.parametrize("state", ["", "hover", "focus"])
def test_the_switch_reads_in_every_theme(qtbot, theme, checked, state):
    thumb, track, edge, surface = _grab(qtbot, theme, checked, state)
    # WCAG's minimum for a control's parts: 3:1.
    assert _read((thumb, track)) >= 3, (thumb, track)
    assert _read((edge, surface)) >= 3, (edge, surface)
    assert _read((track if checked else edge, surface)) >= 3


@pytest.mark.parametrize("theme", _THEMES)
@pytest.mark.parametrize("checked", [False, True])
def test_hover_and_focus_change_the_switch(qtbot, theme, checked):
    rest = _grab(qtbot, theme, checked)
    hover = _grab(qtbot, theme, checked, "hover")
    focus = _grab(qtbot, theme, checked, "focus")
    accent = fxstyle.colors().accent_primary.lower()
    assert hover[:3] != rest[:3]
    if checked:
        # On the accent fill the ring is the text, as on a primary button.
        assert focus[2] == fxstyle.colors().text.lower()
    else:
        assert focus[2] == fxstyle.readable_ink(
            fxstyle.colors().surface, accent, fxstyle.CONTROL_CONTRAST)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("checked", [False, True])
def test_a_disabled_switch_wears_the_disabled_button_tokens(
    qtbot, theme, checked
):
    thumb, track, edge, _ = _grab(qtbot, theme, checked, "disabled")
    colors = fxstyle.colors()
    assert thumb == colors.text_disabled.lower()
    assert track == (colors.surface_alt if checked else colors.surface).lower()
    assert edge == colors.border.lower()
