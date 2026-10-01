"""The breadcrumb reads on whatever it sits on, in every theme, with no hook.

The strip's own tokens fail on a framed window: `pane_border` can be a
fill exactly, and in solarized_light `border_light` holds the text to
1.41:1. So the strip, its edge and its ink are worked out when painted.
"""

# Third-party
import pytest
from qtpy.QtCore import SIGNAL, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QMainWindow, QPushButton, QToolBar, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXBreadcrumb
from fxgui.fxwidgets._breadcrumb import _ground, _strip_colors


PATH = ["Projects", "MyShow", "Assets", "Hero"]
THEMES = fxstyle.get_available_themes()


@pytest.mark.parametrize("ground", ["frame", "surface"])
@pytest.mark.parametrize("theme", THEMES)
def test_the_strip_reads_on_its_ground_in_every_theme(qapp, theme, ground):
    fxstyle.apply_theme(theme)
    colors = fxstyle.get_theme_colors()
    rest, hover, edge, ink = _strip_colors(
        colors,
        ground,
        FXBreadcrumb.STRIP_RESTING_TOKEN,
        FXBreadcrumb.STRIP_HOVERED_TOKEN,
    )
    ratio = fxstyle.get_contrast_ratio

    assert ratio(ink, rest) >= 4.5 and ratio(ink, hover) >= 4.5
    for other in (colors[ground], rest, hover):
        assert ratio(edge, other) >= fxstyle.PANE_BORDER_MIN_CONTRAST
    assert rest != colors[ground], "the strip stands off its ground"


def test_a_crumb_in_a_marked_band_sits_on_the_frame(qtbot):
    band = QWidget()
    fxstyle.mark_as_frame(band)
    qtbot.addWidget(band)
    crumb = FXBreadcrumb(band)

    assert _ground(crumb) == "frame"


def test_a_crumb_on_a_framed_window_s_toolbar_sits_on_the_frame(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    fxstyle.mark_as_frame(window)
    window.setCentralWidget(QWidget())
    bar = QToolBar()
    window.addToolBar(bar)
    crumb = FXBreadcrumb()
    bar.addWidget(crumb)
    inside = FXBreadcrumb(window.centralWidget())

    assert _ground(crumb) == "frame"
    assert _ground(inside) == "surface", "a pane keeps the surface"


def test_a_crumb_on_a_plain_window_sits_on_the_surface(qtbot):
    host = QWidget()
    qtbot.addWidget(host)

    assert _ground(FXBreadcrumb(host)) == "surface"


def _shown(qtbot):
    crumb = FXBreadcrumb(home_icon="")
    qtbot.addWidget(crumb)
    crumb.resize(400, 32)
    crumb.set_path(PATH)
    crumb.show()
    qtbot.waitExposed(crumb)
    return crumb


def _strip_pixel(crumb):
    """The strip's fill, read off a grab away from its edge and text."""
    strip = crumb._container
    image = strip.grab().toImage()
    return image.pixelColor(image.width() - 6, image.height() // 2).name()


def test_the_strip_paints_the_fill_it_works_out(qtbot):
    crumb = _shown(qtbot)

    assert _strip_pixel(crumb) == QColor(crumb._colors()[0]).name()


def test_a_theme_switch_repaints_the_strip_without_a_rebuild(qtbot):
    crumb = _shown(qtbot)
    buttons = crumb._container.findChildren(QPushButton)

    fxstyle.apply_theme("solarized_light")

    assert _strip_pixel(crumb) == QColor(crumb._colors()[0]).name()
    assert crumb._container.findChildren(QPushButton) == buttons


def test_the_breadcrumb_holds_no_theme_hook(qtbot):
    count = lambda: fxstyle.theme_manager.receivers(  # noqa: E731
        SIGNAL("theme_changed(QString)")
    )
    before = count()
    crumb = _shown(qtbot)

    assert count() == before
    assert crumb._container.styleSheet() == ""
    assert all(
        b.styleSheet() == ""
        for b in crumb._container.findChildren(QPushButton)
    )


def test_a_segment_writes_in_the_strip_s_ink(qtbot):
    fxstyle.apply_theme("solarized_light")
    crumb = _shown(qtbot)
    ink = QColor(crumb._colors()[3]).name()
    segment = crumb._container.findChildren(QPushButton)[-1]

    image = segment.grab().toImage()
    inked = {
        image.pixelColor(x, y).name()
        for x in range(image.width())
        for y in range(image.height())
    }

    assert ink in inked
    assert QColor(fxstyle.get_theme_colors()["text"]).name() != ink, (
        "solarized_light's own text does not read on the strip"
    )


def test_segments_can_take_no_tab_stops(qtbot):
    crumb = FXBreadcrumb(segments_focusable=False)
    qtbot.addWidget(crumb)
    crumb.set_path(PATH)
    fxstyle.apply_theme("light")
    crumb.set_path(PATH[:2])

    for segment in crumb._container.findChildren(QPushButton):
        assert segment.focusPolicy() == Qt.NoFocus
    assert crumb._line_edit.focusPolicy() != Qt.NoFocus, "the editor types"


def test_segments_take_tab_stops_by_default(qtbot):
    crumb = FXBreadcrumb()
    qtbot.addWidget(crumb)
    crumb.set_path(PATH)

    assert all(
        s.focusPolicy() != Qt.NoFocus
        for s in crumb._container.findChildren(QPushButton)
    )


def test_the_never_scrolling_scroller_takes_no_tab_stop(qtbot):
    crumb = FXBreadcrumb()
    qtbot.addWidget(crumb)

    assert crumb._scroll_area.focusPolicy() == Qt.NoFocus


def test_the_editor_hint_can_be_set(qtbot):
    crumb = FXBreadcrumb()
    qtbot.addWidget(crumb)

    crumb.set_edit_placeholder("Type a shot")

    assert crumb._line_edit.placeholderText() == "Type a shot"
