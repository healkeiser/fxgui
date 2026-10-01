"""A tinted status bar writes its labels in an ink that reads on the tint."""

import inspect

import pytest
from qtpy.QtWidgets import QWidget

from fxgui import fxstyle
from fxgui.fxwidgets import CRITICAL, DEBUG, ERROR, INFO, SUCCESS, WARNING
from fxgui.fxwidgets._status_bar import FXStatusBar

_SEVERITIES = (CRITICAL, ERROR, WARNING, SUCCESS, INFO, DEBUG)


def _bar(qtbot) -> FXStatusBar:
    host = QWidget()
    qtbot.addWidget(host)
    bar = FXStatusBar(host)
    # qtbot holds widgets weakly; the bar holds its host.
    bar.host = host
    fxstyle.register_themed_root(host)
    host.show()
    return bar


def _ink_and_ground(bar: FXStatusBar) -> tuple:
    label = bar.message_label
    ink = label.palette().color(label.foregroundRole()).name()
    painted = bar.grab().toImage().pixelColor(bar.width() - 2, bar.height() - 2)
    return ink, painted.name()


@pytest.mark.parametrize("theme", sorted(fxstyle.get_available_themes()))
@pytest.mark.parametrize("severity", _SEVERITIES)
def test_the_labels_read_on_every_tint(qtbot, theme, severity):
    fxstyle.apply_theme(theme)
    bar = _bar(qtbot)

    bar.showMessage("something happened", severity, duration=30)

    ink, ground = _ink_and_ground(bar)
    assert fxstyle.get_contrast_ratio(ink, ground) >= 4.5, (theme, severity)


def test_a_message_takes_no_colour_or_pixmap_of_its_own():
    parameters = inspect.signature(FXStatusBar.showMessage).parameters

    assert "background_color" not in parameters
    assert "pixmap" not in parameters


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_tint_is_the_themes_own_feedback_colour(qtbot, theme):
    fxstyle.apply_theme(theme)
    bar = _bar(qtbot)

    bar.showMessage("something happened", INFO, duration=30)

    expected = fxstyle.get_feedback_colors()["info"]["background"]
    assert bar.tint() == expected.lower()


def test_a_switch_keeps_the_message_and_recolours_the_tint(qtbot):
    fxstyle.apply_theme("dark")
    bar = _bar(qtbot)
    bar.show()
    bar.showMessage("Render queued", WARNING, duration=30)

    fxstyle.apply_theme("light")

    warning = fxstyle.get_feedback_colors()["warning"]["background"].lower()
    assert bar.message_label.isVisible()
    assert bar.tint() == warning
    assert _ink_and_ground(bar)[1] == warning
