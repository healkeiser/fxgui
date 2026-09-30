"""FXProgressCard: a description set later shows; the theme sheet styles it."""

# Third-party
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import SUCCESS, FXProgressCard


def _card(qtbot, **kwargs):
    host = QWidget()
    QVBoxLayout(host).addWidget(FXProgressCard(**kwargs))
    fxstyle.register_themed_root(host)
    qtbot.addWidget(host)
    host.resize(300, 120)
    host.show()
    qtbot.waitExposed(host)
    return host, host.findChild(FXProgressCard)


def test_a_description_set_later_shows(qtbot):
    _host, card = _card(qtbot, title="Render")

    card.set_description("Frame 5 of 10")

    labels = [label.text() for label in card.findChildren(type(card._title_label))
              if label.isVisible()]
    assert "Frame 5 of 10" in labels


def test_an_emptied_description_hides(qtbot):
    _host, card = _card(qtbot, title="Render", description="Frame 1")

    card.set_description("")

    assert not card._description_label.isVisible()


def test_the_card_carries_no_sheet_and_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    host, card = _card(qtbot, title="Render", status=SUCCESS)
    fxstyle.apply_theme("github_light")
    qtbot.wait(10)

    image = host.grab().toImage()
    inside = card.mapTo(host, QPoint(card.width() - 4, card.height() // 2))

    assert card.styleSheet() == ""
    assert card._title_label.styleSheet() == ""
    assert image.pixelColor(inside).name() == QColor(
        fxstyle.colors().surface).name()


def test_the_bar_keeps_its_own_flat_fill_over_the_base_sheet(qtbot):
    host, card = _card(qtbot, title="Render", progress=50)
    bar = card._progress_bar
    image = host.grab().toImage()

    filled = bar.mapTo(host, QPoint(bar.width() // 4, bar.height() // 2))
    empty = bar.mapTo(host, QPoint(bar.width() * 3 // 4, bar.height() // 2))

    assert image.pixelColor(filled).name() == QColor(
        fxstyle.colors().accent_primary).name()
    assert image.pixelColor(empty).name() == QColor(
        fxstyle.colors().surface_sunken).name()
