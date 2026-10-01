"""The range slider maps pixels exactly, splits stacked handles, and reads."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

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
    fxstyle.apply_theme("light")
    image = slider.grab().toImage()
    x = int(slider._value_to_position(20))
    y = slider.height() // 2
    assert image.pixelColor(x, y).name() == QColor(
        fxstyle.colors().slider_thumb
    ).name()


def _parts(qtbot, theme, state=""):
    """Return the low handle's edge and fill, the span and the groove."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    layout = QVBoxLayout(window)
    sink = QPushButton("sink")
    slider = FXRangeSlider(minimum=0, maximum=100, low=20, high=60)
    layout.addWidget(sink)
    layout.addWidget(slider)
    window.resize(320, 120)
    qtbot.addWidget(window)
    slider.setEnabled(state != "disabled")
    window.show()
    qtbot.waitExposed(window)
    if state == "focus":
        window.activateWindow()
        QApplication.processEvents()
        slider.setFocus(Qt.TabFocusReason)
        QApplication.processEvents()
        assert slider.hasFocus()
    if state == "hover":
        slider._hover_handle = slider.HANDLE_LOW
    image = slider.grab().toImage()
    x = int(slider._value_to_position(20))
    y = slider.height() // 2
    half = slider._handle_radius

    def at(px, py):
        return image.pixelColor(px, py).name()

    return {
        "edge": at(x, y - half),
        "fill": at(x, y),
        "span": at(int(slider._value_to_position(40)), y),
        "groove": at(int(slider._value_to_position(80)), y),
    }


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_range_slider_speaks_the_slider_language(qtbot, theme):
    parts = _parts(qtbot, theme)
    colors = fxstyle.colors()
    ratio = fxstyle.get_contrast_ratio
    assert parts["edge"] == colors.control_edge
    assert ratio(parts["edge"], colors.surface) >= 3, parts
    assert parts["fill"] == colors.slider_thumb.lower()
    assert parts["span"] == colors.accent_primary.lower()
    assert ratio(parts["span"], parts["groove"]) >= 3, parts
    assert parts["groove"] == colors.surface_sunken.lower()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_range_slider_states_wear_the_slider_tokens(qtbot, theme):
    hover = _parts(qtbot, theme, "hover")
    colors = fxstyle.colors()
    # Hover lifts the fill only, so it never reads as focus.
    assert hover["edge"] == colors.control_edge
    assert hover["fill"] == colors.slider_thumb_hover.lower()
    focus = _parts(qtbot, theme, "focus")
    assert focus["edge"] == colors.accent_primary.lower()
    assert focus["fill"] == colors.text_on_accent_primary.lower()
    disabled = _parts(qtbot, theme, "disabled")
    assert disabled["edge"] == colors.border.lower()
    assert disabled["fill"] == colors.surface.lower()
    assert disabled["span"] == colors.border_strong.lower()
