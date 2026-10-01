"""Every QSlider reads in every theme: a round handle on a 4 px pill."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QPushButton,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFuzzySearchTree

from _helpers import hover


def _plain(orientation=Qt.Horizontal):
    def make():
        slider = QSlider(orientation)
        return slider, slider

    return make


_HORIZONTAL = _plain()


def _in(kind):
    def make():
        widget = kind(show_ratio_slider=True)
        return widget, widget._ratio_slider

    return make


def _rect(slider, control):
    option = QStyleOptionSlider()
    slider.initStyleOption(option)
    return slider.style().subControlRect(
        QStyle.CC_Slider, option, control, slider
    )


def _slider(qtbot, theme, state="", make=_HORIZONTAL):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    widget, slider = make()
    slider.setValue(40)
    slider.setEnabled(state != "disabled")
    layout = QVBoxLayout(window)
    layout.addWidget(QPushButton("sink"))
    layout.addWidget(widget)
    window.resize(240, 240)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    if state == "hover":
        hover(qtbot, slider, _rect(slider, QStyle.SC_SliderHandle).center())
    if state == "pressed":
        QTest.mousePress(
            slider,
            Qt.LeftButton,
            Qt.NoModifier,
            _rect(slider, QStyle.SC_SliderHandle).center(),
        )
    if state == "focus":
        window.activateWindow()
        QApplication.processEvents()
        slider.setFocus(Qt.TabFocusReason)
        QApplication.processEvents()
        assert fxstyle.focus_visible(slider)
    QApplication.processEvents()
    # The slider's wrapper keeps its window alive for the caller.
    slider.window_ = window
    return slider


def _parts(qtbot, theme, state="", make=_HORIZONTAL):
    """Return the handle's edge, centre and corners, the span and groove."""
    slider = _slider(qtbot, theme, state, make)
    handle = _rect(slider, QStyle.SC_SliderHandle)
    # The window, not the slider: a slider grabbed alone has no background.
    window = slider.window()
    image = window.grab().toImage()
    if state == "pressed":
        QTest.mouseRelease(
            slider, Qt.LeftButton, Qt.NoModifier, handle.center())
    middle = handle.center()

    def at(x, y):
        return image.pixelColor(slider.mapTo(window, QPoint(x, y))).name()

    if slider.orientation() == Qt.Horizontal:
        span = at(handle.left() - 12, middle.y())
        groove = at(handle.right() + 40, middle.y())
    else:
        # A vertical slider fills from the bottom up.
        span = at(middle.x(), handle.bottom() + 12)
        groove = at(middle.x(), handle.top() - 12)
    return {
        "edge": at(middle.x(), handle.top() + 1),
        "inner": at(middle.x(), handle.top() + 3),
        "fill": at(middle.x(), middle.y()),
        "corners": {
            at(handle.left(), handle.top()),
            at(handle.right(), handle.top()),
            at(handle.left(), handle.bottom()),
            at(handle.right(), handle.bottom()),
        },
        "span": span,
        "groove": groove,
    }


ORIENTATIONS = pytest.mark.parametrize(
    "make",
    [_plain(Qt.Horizontal), _plain(Qt.Vertical)],
    ids=["horizontal", "vertical"],
)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
@pytest.mark.parametrize(
    "make",
    [
        _plain(Qt.Horizontal),
        _plain(Qt.Vertical),
        _in(FXFuzzySearchTree),
    ],
    ids=["horizontal", "vertical", "FXFuzzySearchTree"],
)
def test_a_slider_reads_in_every_theme(qtbot, theme, make):
    parts = _parts(qtbot, theme, make=make)
    colors = fxstyle.colors()
    ratio = fxstyle.get_contrast_ratio
    assert parts["edge"] == colors.accent_primary.lower()
    assert parts["fill"] == colors.surface.lower()
    assert parts["span"] == colors.accent_primary.lower()
    assert parts["groove"] == colors.control_edge.lower()
    # Both read at 3:1 on the surface; no theme has room for 3:1 between.
    assert ratio(parts["groove"], colors.surface) >= 3, parts
    assert ratio(parts["span"], colors.surface) >= 3, parts
    assert parts["span"] != parts["groove"]


@pytest.mark.parametrize("theme", ["dark", "light"])
@ORIENTATIONS
def test_the_handle_is_a_circle(qtbot, theme, make):
    parts = _parts(qtbot, theme, make=make)
    colors = fxstyle.colors()
    # A square handle would paint its corners in its edge colour.
    assert parts["corners"] == {colors.surface.lower()}, parts
    assert parts["edge"] == colors.accent_primary.lower()


@ORIENTATIONS
def test_the_groove_is_a_4px_pill_and_the_handle_is_whole(qtbot, make):
    slider = _slider(qtbot, "dark", make=make)
    groove = _rect(slider, QStyle.SC_SliderGroove)
    handle = _rect(slider, QStyle.SC_SliderHandle)
    horizontal = slider.orientation() == Qt.Horizontal
    assert (groove.height() if horizontal else groove.width()) == 4
    assert handle.width() == handle.height() == 16
    assert slider.rect().contains(handle), (slider.rect(), handle)
    if horizontal:
        assert handle.center().y() == groove.center().y()
        end, inside = (groove.right(), groove.top()), (
            groove.right() - 2,
            groove.center().y(),
        )
    else:
        assert handle.center().x() == groove.center().x()
        end, inside = (groove.left(), groove.top()), (
            groove.center().x(),
            groove.top() + 2,
        )
    # A rounded end leaves the groove's corner pixel unpainted.
    window = slider.window()
    image = window.grab().toImage()
    sunken = fxstyle.colors().control_edge.lower()

    def at(x, y):
        return image.pixelColor(slider.mapTo(window, QPoint(x, y))).name()

    assert at(*end) != sunken
    assert at(*inside) == sunken


@pytest.mark.parametrize("theme", ["dark", "light"])
@ORIENTATIONS
def test_each_state_wears_its_tokens(qtbot, theme, make):
    colors = fxstyle.colors
    rest = _parts(qtbot, theme, make=make)
    # Hover thickens the accent edge inward, so the box does not move.
    hover = _parts(qtbot, theme, "hover", make=make)
    assert rest["inner"] == colors().surface.lower()
    assert hover["inner"] == colors().accent_primary.lower()
    assert hover["fill"] == colors().surface.lower()
    pressed = _parts(qtbot, theme, "pressed", make=make)
    assert pressed["fill"] == colors().accent_primary.lower()
    focus = _parts(qtbot, theme, "focus", make=make)
    assert focus["edge"] == colors().text.lower()
    assert focus["fill"] == colors().surface.lower()
    disabled = _parts(qtbot, theme, "disabled", make=make)
    assert disabled["edge"] == colors().border.lower()
    assert disabled["fill"] == colors().surface.lower()
    assert disabled["span"] == colors().border_strong.lower()


def test_a_clicked_slider_shows_no_focus_ring(qtbot):
    slider = _slider(qtbot, "dark")
    slider.setFocus(Qt.MouseFocusReason)
    QApplication.processEvents()
    assert slider.hasFocus()
    handle = _rect(slider, QStyle.SC_SliderHandle)
    image = slider.grab().toImage()
    edge = image.pixelColor(handle.center().x(), handle.top() + 1).name()
    assert edge == fxstyle.colors().accent_primary.lower()
