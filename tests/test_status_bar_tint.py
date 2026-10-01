"""A tinted status bar writes its labels in an ink that reads on the tint."""

import re

import pytest

from fxgui import fxstyle
from fxgui.fxwidgets import CRITICAL, DEBUG, ERROR, INFO, SUCCESS, WARNING
from fxgui.fxwidgets._status_bar import FXStatusBar

_SEVERITIES = (CRITICAL, ERROR, WARNING, SUCCESS, INFO, DEBUG)


def _ink_and_ground(bar: FXStatusBar) -> tuple:
    sheet = bar.styleSheet()
    ground = re.search(r"background: (#[0-9a-fA-F]{6})", sheet).group(1)
    ink = re.search(r"QLabel \{\s*color: (#[0-9a-fA-F]{6})", sheet).group(1)
    return ink, ground


@pytest.mark.parametrize("theme", sorted(fxstyle.get_available_themes()))
@pytest.mark.parametrize("severity", _SEVERITIES)
def test_the_labels_read_on_every_tint(qtbot, theme, severity):
    fxstyle.apply_theme(theme)
    bar = FXStatusBar()
    qtbot.addWidget(bar)

    bar.showMessage("something happened", severity, duration=30)

    ink, ground = _ink_and_ground(bar)
    assert fxstyle.get_contrast_ratio(ink, ground) >= 4.5, (theme, severity)


@pytest.mark.parametrize("ground", ["#ffe08a", "#f5f5f5", "#7fbf7f"])
def test_a_light_custom_tint_turns_the_ink_dark(qtbot, ground):
    bar = FXStatusBar()
    qtbot.addWidget(bar)

    bar.showMessage("light", INFO, duration=30, background_color=ground)

    ink, painted = _ink_and_ground(bar)
    assert painted.lower() == ground
    assert fxstyle.get_contrast_ratio(ink, ground) >= 4.5, ink


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_tint_is_the_themes_own_feedback_colour(qtbot, theme):
    fxstyle.apply_theme(theme)
    bar = FXStatusBar()
    qtbot.addWidget(bar)

    bar.showMessage("something happened", INFO, duration=30)

    expected = fxstyle.get_feedback_colors()["info"]["background"]
    assert bar.tint() == expected.lower()
