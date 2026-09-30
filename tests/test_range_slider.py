"""The range slider maps pixels to values exactly and splits stacked handles."""

# Third-party
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtTest import QTest

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXRangeSlider


def _slider(qtbot, **kwargs):
    slider = FXRangeSlider(**kwargs)
    qtbot.addWidget(slider)
    slider.resize(317, 70)
    slider.show()
    qtbot.waitExposed(slider)
    return slider


def test_every_value_survives_a_round_trip_through_its_pixel(qtbot, qapp):
    slider = _slider(qtbot, minimum=0, maximum=100)
    for value in range(101):
        x = slider._value_to_position(value)
        assert slider._position_to_value(x) == value


def test_stacked_handles_split_toward_the_drag(qtbot, qapp):
    slider = _slider(qtbot, minimum=0, maximum=100, low=50, high=50)
    x = int(slider._value_to_position(50))
    y = slider.height() // 2

    QTest.mousePress(slider, Qt.LeftButton, Qt.NoModifier, QPoint(x, y))
    QTest.mouseMove(slider, QPoint(x - 40, y))
    QTest.mouseRelease(slider, Qt.LeftButton, Qt.NoModifier, QPoint(x - 40, y))

    assert slider.low < 50
    assert slider.high == 50


def test_handles_are_painted_in_the_theme_thumb_colour(qtbot, qapp):
    slider = _slider(qtbot, minimum=0, maximum=100, low=20, high=80)
    assert not isinstance(slider, fxstyle.FXThemeAware)
    fxstyle.apply_theme("light")
    image = slider.grab().toImage()
    x = int(slider._value_to_position(20))
    y = slider.height() // 2
    assert image.pixelColor(x, y).name() == QColor(
        fxstyle.colors().slider_thumb
    ).name()
