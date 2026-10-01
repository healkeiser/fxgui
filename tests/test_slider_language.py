"""Every QSlider reads in every theme: handle, groove and filled span."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFuzzySearchTree


def _plain():
    slider = QSlider(Qt.Horizontal)
    return slider, slider


def _in(kind):
    def make():
        widget = kind(show_ratio_slider=True)
        return widget, widget._ratio_slider

    return make


def _parts(qtbot, theme, enabled=True, make=_plain):
    """Return the handle's edge and fill, the span and the groove pixels."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    widget, slider = make()
    slider.setValue(40)
    slider.setEnabled(enabled)
    QVBoxLayout(window).addWidget(widget)
    window.resize(240, 60)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    option = QStyleOptionSlider()
    slider.initStyleOption(option)
    handle = slider.style().subControlRect(
        QStyle.CC_Slider, option, QStyle.SC_SliderHandle, slider
    )
    image = slider.grab().toImage()
    middle = handle.center().y()

    def at(x, y):
        return image.pixelColor(x, y).name()

    return {
        "edge": at(handle.center().x(), handle.top()),
        "fill": at(handle.center().x(), middle),
        "span": at(handle.left() - 12, middle),
        "groove": at(handle.right() + 40, middle),
    }


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
@pytest.mark.parametrize(
    "make",
    [_plain, _in(FXFuzzySearchTree)],
    ids=["QSlider", "FXFuzzySearchTree"],
)
def test_a_slider_reads_in_every_theme(qtbot, theme, make):
    parts = _parts(qtbot, theme, make=make)
    colors = fxstyle.colors()
    ratio = fxstyle.get_contrast_ratio
    assert parts["edge"] == colors.control_edge
    assert ratio(parts["edge"], colors.surface) >= 3, parts
    # The span carries the value, so it reads on the groove at 3:1.
    assert parts["span"] == colors.accent_primary.lower()
    assert ratio(parts["span"], parts["groove"]) >= 3, parts
    assert parts["groove"] == colors.surface_sunken.lower()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_disabled_slider_wears_the_disabled_button_tokens(qtbot, theme):
    parts = _parts(qtbot, theme, enabled=False)
    colors = fxstyle.colors()
    assert parts["edge"] == colors.border.lower()
    assert parts["fill"] == colors.surface.lower()
    assert parts["span"] == colors.border_strong.lower()
