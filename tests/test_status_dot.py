"""One small circle that reports a state in a feedback colour, or its absence."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QPalette

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXStatusDot


FEEDBACK = ("success", "warning", "error", "info", "debug")


def _ink(key):
    return QColor(fxstyle.get_theme_colors()[f"feedback_{key}_foreground"])


def _grayed(dot):
    return dot.palette().color(QPalette.Disabled, QPalette.WindowText)


def test_it_starts_off_rather_than_guessing(qtbot):
    dot = FXStatusDot()
    qtbot.addWidget(dot)

    assert dot.color() == _grayed(dot)


@pytest.mark.parametrize("key", FEEDBACK)
def test_a_state_paints_in_its_feedback_colour(qtbot, key):
    dot = FXStatusDot()
    qtbot.addWidget(dot)

    dot.set_feedback(key, "Recording")

    assert dot.color() == _ink(key)
    assert dot.toolTip() == "Recording"
    image = dot.grab().toImage()
    centre = image.pixelColor(image.width() // 2, image.height() // 2)
    assert centre.name() == _ink(key).name()


def test_off_is_grayed_rather_than_a_feedback_colour(qtbot):
    dot = FXStatusDot()
    qtbot.addWidget(dot)
    dot.set_feedback("success")

    dot.set_feedback(None)

    assert dot.color() == _grayed(dot)
    assert dot.color().name() not in {_ink(k).name() for k in FEEDBACK}


def test_a_theme_switch_repaints_with_no_call(qtbot):
    dot = FXStatusDot()
    qtbot.addWidget(dot)
    dot.set_feedback("warning")

    fxstyle.apply_theme("light")

    assert dot.color() == _ink("warning")


def test_an_unknown_state_reads_as_off(qtbot):
    dot = FXStatusDot()
    qtbot.addWidget(dot)

    dot.set_feedback("bogus")

    assert dot.color() == _grayed(dot)


def test_a_left_click_emits_clicked(qtbot):
    dot = FXStatusDot()
    qtbot.addWidget(dot)

    with qtbot.waitSignal(dot.clicked, timeout=500):
        qtbot.mouseClick(dot, Qt.LeftButton)
    assert dot.cursor().shape() == Qt.PointingHandCursor


def test_the_diameter_is_the_widget_s_size(qtbot):
    dot = FXStatusDot(diameter=12)
    qtbot.addWidget(dot)

    assert (dot.width(), dot.height()) == (12, 12)
