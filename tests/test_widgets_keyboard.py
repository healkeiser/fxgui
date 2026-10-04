"""The toggle switch, rating and range slider work from the keyboard."""

# Third-party
import pytest
from qtpy.QtCore import Qt

# Internal
from fxgui.fxwidgets import FXRangeSlider, FXRatingWidget, FXToggleSwitch


def test_toggle_switch_is_focusable_and_space_toggles(qtbot):
    toggle = FXToggleSwitch()
    qtbot.addWidget(toggle)
    toggle.show()
    toggle.setFocus()

    assert toggle.focusPolicy() == Qt.StrongFocus
    assert not toggle.isChecked()

    qtbot.keyClick(toggle, Qt.Key_Space)
    assert toggle.isChecked()

    qtbot.keyClick(toggle, Qt.Key_Space)
    assert not toggle.isChecked()


def test_rating_widget_keyboard(qtbot):
    rating = FXRatingWidget(max_rating=5)
    qtbot.addWidget(rating)
    rating.show()
    rating.setFocus()

    assert rating.focusPolicy() == Qt.StrongFocus

    qtbot.keyClick(rating, Qt.Key_Right)
    assert rating.rating() == 1

    qtbot.keyClick(rating, Qt.Key_3)
    assert rating.rating() == 3

    qtbot.keyClick(rating, Qt.Key_Left)
    assert rating.rating() == 2

    with qtbot.waitSignal(rating.rating_changed):
        qtbot.keyClick(rating, Qt.Key_End)
    assert rating.rating() == 5

    qtbot.keyClick(rating, Qt.Key_Delete)
    assert rating.rating() == 0


def test_rating_widget_half_star_step(qtbot):
    rating = FXRatingWidget(max_rating=5, allow_half=True)
    qtbot.addWidget(rating)
    rating.show()
    rating.setFocus()

    qtbot.keyClick(rating, Qt.Key_Right)
    assert rating.rating() == 0.5


def test_range_slider_keyboard(qtbot):
    slider = FXRangeSlider(minimum=0, maximum=100, low=10, high=90)
    qtbot.addWidget(slider)
    slider.show()
    slider.setFocus()

    assert slider.focusPolicy() == Qt.StrongFocus

    # Low handle is active by default
    qtbot.keyClick(slider, Qt.Key_Right)
    assert slider.low() == 11

    # Space switches to the high handle
    qtbot.keyClick(slider, Qt.Key_Space)
    qtbot.keyClick(slider, Qt.Key_Left)
    assert slider.high() == 89

    qtbot.keyClick(slider, Qt.Key_PageUp)
    assert slider.high() == 99

    qtbot.keyClick(slider, Qt.Key_End)
    assert slider.high() == 100

    # Back to the low handle
    qtbot.keyClick(slider, Qt.Key_Space)
    qtbot.keyClick(slider, Qt.Key_Home)
    assert slider.low() == 0


def test_range_slider_keyboard_clamps(qtbot):
    slider = FXRangeSlider(minimum=0, maximum=10, low=5, high=6)
    qtbot.addWidget(slider)
    slider.show()
    slider.setFocus()

    # Low handle cannot cross the high handle
    for _ in range(5):
        qtbot.keyClick(slider, Qt.Key_Right)
    assert slider.low() == 6
    assert slider.high() == 6


def test_the_initial_rating_is_held_in_range_and_rounded(qtbot):
    rating = FXRatingWidget(max_rating=5, initial_rating=9.4)
    qtbot.addWidget(rating)
    assert rating.rating() == 5
    rounded = FXRatingWidget(max_rating=5, initial_rating=2.6)
    qtbot.addWidget(rounded)
    assert rounded.rating() == 3


@pytest.mark.parametrize("given, held", [(1.5, 2), (2.5, 3), (3.5, 4)])
def test_a_whole_star_rating_rounds_a_half_up(qtbot, given, held):
    """round() would take 2.5 to 2 and 3.5 to 4."""
    rating = FXRatingWidget(max_rating=5)
    qtbot.addWidget(rating)
    rating.set_rating(given)
    assert rating.rating() == held
