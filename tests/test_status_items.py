"""Status items: an icon and a word on the bar, readable on any ground."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor, QStatusTipEvent
from qtpy.QtWidgets import QApplication

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import ERROR, INFO, FXMainWindow, FXStatusItem

from _helpers import hover, pixel


FLOOR = 4.5 - 0.01


@pytest.fixture(params=sorted(fxstyle.get_available_themes()))
def any_theme(request):
    fxstyle.apply_theme(request.param)
    return request.param


def _window(qtbot, framed=True):
    window = FXMainWindow(framed=framed, version="1.0", company="Studio")
    qtbot.addWidget(window)
    bar = window.statusBar()
    bar.warnings = FXStatusItem()
    bar.add_item(bar.warnings)
    bar.warnings.show_state("1", "warning", tone="warning")
    bar.artist = FXStatusItem()
    bar.add_item(bar.artist)
    bar.artist.show_state("Valentin Beaumont", "person")
    bar.refreshed = FXStatusItem("Refreshed 10:00")
    bar.add_item(bar.refreshed, side="right")
    bar.project_label.setText("Show")
    window.resize(900, 300)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(20)
    return window


def _items(window):
    return [item for item in window.statusBar().findChildren(FXStatusItem)
            if item.isVisible()]


def test_every_item_reads_on_every_theme(qtbot, any_theme):
    window = _window(qtbot)
    bar = window.statusBar()

    items = _items(window)
    assert {bar.warnings, bar.artist, bar.refreshed, bar.project_label,
            bar.version_label, bar.company_label} <= set(items)
    for item in items:
        assert fxstyle.get_contrast_ratio(item.ink(), bar.ground()) >= FLOOR, (
            any_theme, item.text())
    left = bar.artist.parentWidget()
    spot = QPoint(left.width() - 5, left.height() // 2)
    assert pixel(window, left, spot) == QColor(bar.ground()).name(), (
        "the items sit on the bar, with no fill")


def test_an_item_with_no_text_hides(qtbot):
    window = _window(qtbot)
    item = window.statusBar().artist

    item.setText("")

    assert not item.isVisible()


def test_a_message_keeps_a_gap_from_the_window_s_left_edge(qtbot):
    window = FXMainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    bar = window.statusBar()

    bar.showMessage("something happened", INFO, duration=30)
    qtbot.wait(20)

    first = bar.icon_label if bar.icon_label.isVisible() else bar.message_label
    assert first.mapTo(window, QPoint(0, 0)).x() >= 6


def test_a_message_keeps_the_items_shown_and_readable(qtbot, any_theme):
    window = _window(qtbot)
    bar = window.statusBar()
    before = _items(window)

    for severity in (INFO, ERROR):
        bar.showMessage("something happened", severity, duration=30)
        qtbot.wait(20)
        assert _items(window) == before
        assert bar.message_label.isVisible()
        ground = bar.ground()
        assert bar.tint() == ground
        assert ground != fxstyle.colors().frame, "tinted"
        spot = QPoint(bar.width() // 2, bar.height() - 2)
        assert pixel(window, bar, spot) == QColor(ground).name(), (
            "the ink is chosen against the tint painted")
        for item in before:
            assert fxstyle.get_contrast_ratio(item.ink(), ground) >= FLOOR, (
                any_theme, severity, item.text())
    bar.clearMessage()
    qtbot.wait(20)
    assert bar.tint() is None
    assert bar.ground() == fxstyle.colors().frame


@pytest.mark.parametrize("theme", ["catppuccin_latte", "dracula"])
def test_a_theme_switch_mid_message_keeps_the_items_readable(qtbot, theme):
    window = _window(qtbot)
    bar = window.statusBar()
    bar.showMessage("something broke", ERROR, duration=30)
    qtbot.wait(20)

    fxstyle.apply_theme(theme)
    qtbot.wait(50)

    spot = QPoint(bar.width() // 2, bar.height() - 2)
    painted = pixel(window, bar, spot)
    assert painted == QColor(bar.ground()).name(), (
        "the ground is what the bar paints")
    for item in _items(window):
        assert fxstyle.get_contrast_ratio(item.ink(), painted) >= FLOOR, (
            theme, item.text())


def _icon_ink(window, item):
    """Return the icon's painted colour: its pixel farthest from the bar."""
    image = window.grab().toImage()
    ground = QColor(window.statusBar().ground())
    icon = item.iconSize()
    left = item.mapTo(window, QPoint(0, (item.height() - icon.height()) // 2))
    pixels = [
        QColor(image.pixel(left.x() + x, left.y() + y))
        for x in range(item.width() // 2) for y in range(icon.height())]
    return max(pixels, key=lambda c: abs(c.red() - ground.red())
               + abs(c.green() - ground.green())
               + abs(c.blue() - ground.blue()))


@pytest.mark.parametrize("severity", [INFO, ERROR])
def test_on_a_tint_a_toned_icon_wears_the_text_s_ink(qtbot, severity):
    window = _window(qtbot)
    bar = window.statusBar()
    bar.showMessage("something happened", severity, duration=30)
    qtbot.wait(20)

    item = bar.warnings
    painted, ink = _icon_ink(window, item), QColor(item.ink())
    assert max(abs(painted.red() - ink.red()),
               abs(painted.green() - ink.green()),
               abs(painted.blue() - ink.blue())) <= 24, (
        painted.name(), ink.name())


def test_off_a_tint_a_toned_icon_wears_its_tone(qtbot):
    window = _window(qtbot)
    item = window.statusBar().warnings

    painted = _icon_ink(window, item)

    assert painted.name() != QColor(item.ink()).name()


def test_a_hover_tip_shows_after_the_items_not_over_them(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()
    before = _items(window)

    QApplication.sendEvent(window, QStatusTipEvent("Where this leads"))

    assert bar.currentMessage() == "", "Qt paints no tip of its own"
    assert bar.message_label.text() == "Where this leads"
    assert bar.message_label.isVisible() and _items(window) == before
    last = max(item.geometry().right() for item in before
               if item.parent() is bar.artist.parent())
    assert bar.message_label.geometry().left() > last
    QApplication.sendEvent(window, QStatusTipEvent(""))
    assert not bar.message_label.isVisible()


def test_a_tip_over_a_message_gives_the_message_back(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()
    bar.showMessage("saved", INFO, duration=30)
    said = bar.message_label.text()

    bar.show_tip("Where this leads")
    bar.show_tip("")

    assert bar.message_label.text() == said
    assert bar.icon_label.isVisible()


def test_a_clickable_item_lights_under_the_mouse(qtbot):
    window = _window(qtbot)
    item = window.statusBar().artist
    lit = QColor(fxstyle.colors().state_hover).name()

    hover(qtbot, item)

    assert pixel(window, item, QPoint(4, item.height() // 2)) == lit
    assert pixel(window, item, QPoint(0, 0)) != lit, "the corners round"


def test_a_plain_item_takes_no_mouse_until_it_is_clickable(qtbot):
    window = _window(qtbot)
    item = window.statusBar().project_label
    spot = item.mapTo(window, item.rect().center())

    assert window.childAt(spot) is not item, "a click passes through"
    item.set_clickable(True)
    assert window.childAt(spot) is item


def test_set_tip_leaves_no_status_tip(qtbot):
    item = FXStatusItem("Show")
    qtbot.addWidget(item)

    item.set_tip("Project", "Choose another project")

    assert item.statusTip() == ""
    assert "Project" in item.toolTip()


def test_the_version_and_company_are_plain_items(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()

    assert isinstance(bar.version_label, FXStatusItem)
    assert isinstance(bar.company_label, FXStatusItem)
    assert bar.version_label.text() == "1.0"
    order = [bar.project_label, bar.version_label, bar.refreshed,
             bar.company_label]
    assert [item.x() for item in order] == sorted(item.x() for item in order)


def test_a_right_item_after_one_went_still_sits_before_the_company(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()
    bar.removeWidget(bar.refreshed)
    bar.refreshed.deleteLater()
    qtbot.wait(10)

    later = FXStatusItem("Synced")
    bar.add_item(later, side="right")
    qtbot.wait(10)

    assert bar.version_label.x() < later.x() < bar.company_label.x()
    assert bar.company_label.isVisible()


@pytest.mark.parametrize("side", ["left", "right"])
def test_an_item_added_to_a_shown_bar_sits_in_it(qtbot, side):
    window = _window(qtbot)
    bar = window.statusBar()

    item = FXStatusItem("Late")
    bar.add_item(item, side=side)
    qtbot.wait(10)

    assert not item.isWindow()
    assert bar.rect().contains(item.mapTo(bar, item.rect().center()))
