"""The range slider maps pixels exactly, splits stacked handles, and reads."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
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


def _parts(qtbot, theme, state=""):
    """Return the low handle's edge, centre and corners, the span and groove."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
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
    if state == "pressed":
        slider._pressed_handle = slider.HANDLE_LOW
    # The window, not the slider: the slider paints no background.
    image = window.grab().toImage()
    x = round(slider._value_to_position(20))
    y = slider.height() // 2
    half = slider._handle_radius

    def at(px, py):
        return image.pixelColor(slider.mapTo(window, QPoint(px, py))).name()

    return {
        "edge": at(x, y - half + 1),
        "inner": at(x, y - half + 3),
        "fill": at(x, y),
        "corners": {
            at(x - half, y - half),
            at(x + half - 1, y - half),
            at(x - half, y + half - 1),
            at(x + half - 1, y + half - 1),
        },
        "span": at(int(slider._value_to_position(40)), y),
        "groove": at(int(slider._value_to_position(80)), y),
        "track": (slider._handle_radius, slider._track_height),
    }


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_range_slider_speaks_the_slider_language(qtbot, theme):
    parts = _parts(qtbot, theme)
    colors = fxstyle.colors()
    ratio = fxstyle.get_contrast_ratio
    # A QSlider's 16 px round handle on its 4 px groove.
    assert parts["track"] == (8, 4)
    assert parts["corners"] == {colors.surface.lower()}, parts
    assert parts["edge"] == colors.accent_primary.lower()
    assert parts["fill"] == colors.surface.lower()
    assert parts["span"] == colors.accent_primary.lower()
    assert parts["groove"] == colors.control_edge.lower()
    # Both read at 3:1 on the surface; no theme has room for 3:1 between.
    assert ratio(parts["groove"], colors.surface) >= 3, parts
    assert ratio(parts["span"], colors.surface) >= 3, parts
    assert parts["span"] != parts["groove"]


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_range_slider_states_wear_the_slider_tokens(qtbot, theme):
    colors = fxstyle.colors
    rest = _parts(qtbot, theme)
    hover = _parts(qtbot, theme, "hover")
    assert rest["inner"] == colors().surface.lower()
    assert hover["inner"] == colors().accent_primary.lower()
    assert hover["fill"] == colors().surface.lower()
    pressed = _parts(qtbot, theme, "pressed")
    assert pressed["fill"] == colors().accent_primary.lower()
    focus = _parts(qtbot, theme, "focus")
    assert focus["edge"] == colors().text.lower()
    assert focus["fill"] == colors().surface.lower()
    disabled = _parts(qtbot, theme, "disabled")
    assert disabled["edge"] == colors().border.lower()
    assert disabled["fill"] == colors().surface.lower()
    assert disabled["span"] == colors().border_strong.lower()
