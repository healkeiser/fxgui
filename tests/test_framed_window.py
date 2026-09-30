"""A framed FXMainWindow: no banner band, one frame colour for the chrome."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect, QSize
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QToolButton,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets import FXMainWindow

THEMES = fxstyle.get_available_themes()


def _window(qtbot, framed=True, theme="dark"):
    fxstyle.apply_theme(theme)
    window = FXMainWindow(title="probe", framed=framed)
    window.set_banner_text("Probe")
    body = QWidget()
    row = QHBoxLayout(body)
    window.label = QLabel("A label")
    window.check = QCheckBox("Mine only")
    window.radio = QRadioButton("One")
    for widget in (window.label, window.check, window.radio):
        row.addWidget(widget)
    row.addStretch()
    if framed:
        fxstyle.mark_as_frame(body)
    window.setCentralWidget(body)
    window.resize(640, 360)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(10)  # FXThemeAware styles on the first event loop pass.
    return window


def _pixel(window, widget, x, y):
    image = window.grab().toImage()
    point = widget.mapTo(window, QPoint(x, y))
    return image.pixelColor(point).name()


def _frame():
    return QColor(fxstyle.get_theme_colors()["frame"]).name()


def test_a_window_keeps_its_banner_by_default(qtbot):
    window = _window(qtbot, framed=False)

    assert window.banner.isVisible()
    assert window.banner.height() == 50
    assert window.menuBar().cornerWidget() is None


def test_a_framed_window_has_no_banner_band(qtbot):
    window = _window(qtbot)
    body_top = window.label.parentWidget().mapTo(window, QPoint(0, 0)).y()
    toolbar_bottom = window.toolbar.geometry().bottom()

    assert not window.banner.isVisible()
    assert body_top == toolbar_bottom + 1


def test_the_name_moves_to_the_menu_bar_corner(qtbot):
    window = _window(qtbot)
    corner = window.menuBar().cornerWidget()

    assert corner is not None and corner.isVisible()
    assert corner.isAncestorOf(window.banner_label)
    assert window.banner_label.text() == "Probe"

    window.set_banner_text("Renamed")
    assert window.banner_label.text() == "Renamed"
    assert window.banner_label.isVisible()


def test_the_corner_takes_the_banner_icon(qtbot):
    window = _window(qtbot)
    window.set_banner_icon("widgets")
    corner = window.menuBar().cornerWidget()

    assert corner.isAncestorOf(window.banner_icon)
    assert window.banner_icon.isVisible()
    assert window.banner_icon.size() == QSize(16, 16)


def _ink_rows(image, rect, background):
    rows = []
    for y in range(rect.top(), rect.bottom() + 1):
        for x in range(rect.left(), rect.right() + 1):
            if not _close(image.pixelColor(x, y).name(), background, 40):
                rows.append(y)
                break
    return rows


def _close(one, two, step=6):
    a, b = QColor(one), QColor(two)
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()),
               abs(a.blue() - b.blue())) <= step


def test_the_name_is_centred_on_the_menu_titles(qtbot):
    """Its glyphs sit on the same rows as the menu titles' glyphs."""
    window = _window(qtbot)
    bar = window.menuBar()
    image = bar.grab().toImage()
    name = window.banner_label
    name_rect = QRect(name.mapTo(bar, QPoint(0, 0)), name.size())
    file_rect = bar.actionGeometry(bar.actions()[0])

    name_rows = _ink_rows(image, name_rect, _frame())
    file_rows = _ink_rows(image, file_rect, _frame())

    assert name_rows and file_rows
    name_middle = (name_rows[0] + name_rows[-1]) / 2
    file_middle = (file_rows[0] + file_rows[-1]) / 2
    assert abs(name_middle - file_middle) <= 1


@pytest.mark.parametrize("theme", THEMES)
def test_the_corner_has_no_fill_of_its_own(qtbot, theme):
    window = _window(qtbot, theme=theme)
    corner = window.menuBar().cornerWidget()
    name = window.banner_label

    assert _pixel(window, corner, 1, 1) == _frame()
    assert _pixel(window, name, 0, 0) == _frame()
    assert _pixel(window, name, name.width() - 1, name.height() - 1) == (
        _frame())


def test_the_corner_follows_a_theme_switch(qtbot):
    window = _window(qtbot)
    fxstyle.apply_theme("github_light")
    qtbot.wait(10)

    assert _pixel(window, window.banner_label, 0, 0) == _frame()


@pytest.mark.parametrize("theme", THEMES)
def test_the_chrome_is_one_frame_with_no_lines(qtbot, theme):
    """Down the middle of the window, from the menu bar to the status
    bar's accent line, every pixel is the frame colour."""
    window = _window(qtbot, theme=theme)
    image = window.grab().toImage()
    x = window.width() // 2
    status_top = window.statusBar().geometry().top()

    seen = {image.pixelColor(x, y).name() for y in range(status_top)}

    assert seen == {_frame()}


@pytest.mark.parametrize("theme", THEMES)
def test_the_status_bar_is_frame_and_keeps_its_accent_line(qtbot, theme):
    window = _window(qtbot, theme=theme)
    bar = window.statusBar()

    assert _pixel(window, bar, 0, 1) == QColor(
        fxstyle.get_theme_colors()["accent_primary"]).name()
    assert _pixel(window, bar, bar.width() // 2, bar.height() - 2) == (
        _frame())


@pytest.mark.parametrize("theme", THEMES)
def test_controls_on_the_frame_have_no_fill(qtbot, theme):
    window = _window(qtbot, theme=theme)

    for widget in (window.label, window.check, window.radio):
        # Inside the 1 px border a check box keeps for its focus ring.
        right = widget.width() - 3
        assert _pixel(window, widget, right, 2) == _frame(), widget.text()


@pytest.mark.parametrize("theme", THEMES)
def test_a_disabled_tool_button_on_the_frame_shows_no_box(qtbot, theme):
    window = _window(qtbot, theme=theme)
    button = QToolButton()
    button.setPopupMode(QToolButton.MenuButtonPopup)
    fxicons.set_icon(button, "home")
    button.setEnabled(False)
    window.toolbar.addWidget(button)
    qtbot.wait(10)

    assert _pixel(window, button, 1, 1) == _frame()
    assert _pixel(window, button, button.width() // 2, 2) == _frame()


def test_a_label_in_a_plain_window_keeps_the_surface(qtbot):
    window = _window(qtbot, framed=False)

    assert _pixel(window, window.label, window.label.width() - 2, 1) == (
        QColor(fxstyle.get_theme_colors()["surface"]).name())


def test_mark_as_frame_paints_a_band_of_your_own(qtbot):
    window = _window(qtbot, framed=False)
    band = window.label.parentWidget()

    fxstyle.mark_as_frame(band)
    qtbot.wait(10)

    assert band.property(fxstyle.FRAME_PROPERTY) is True
    assert _pixel(window, window.label, window.label.width() - 2, 1) == (
        _frame())


def test_the_corner_does_not_grow_the_menu_bar(qtbot):
    plain = _window(qtbot, framed=False)
    framed = _window(qtbot)

    assert framed.menuBar().height() == plain.menuBar().height()


def test_hide_banner_hides_the_corner_of_a_framed_window(qtbot):
    window = _window(qtbot)

    window.hide_banner()
    assert not window.title_corner.isVisible()
    window.show_banner()
    assert window.title_corner.isVisible()
    assert not window.banner.isVisible()
