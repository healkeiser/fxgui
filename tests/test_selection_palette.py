"""Selected text wears the theme's selection fill, and follows a switch."""

import pytest
from qtpy.QtGui import QColor, QPalette, QTextCursor
from qtpy.QtWidgets import QGraphicsScene, QGraphicsTextItem, QGraphicsView

from fxgui import fxstyle


@pytest.fixture
def themed_app(qapp):
    """The application as a themed root, as FXApplication makes it."""
    sheet, font, palette = qapp.styleSheet(), qapp.font(), qapp.palette()
    fxstyle.register_themed_root(qapp)
    yield qapp
    fxstyle._themed_roots.discard(qapp)
    qapp.setStyleSheet(sheet)
    qapp.setFont(font)
    qapp.setPalette(palette)


def _highlight(palette):
    return (
        palette.color(QPalette.Highlight).name(),
        palette.color(QPalette.HighlightedText).name(),
    )


def _theme_highlight():
    colors = fxstyle.colors()
    return (
        QColor(colors.selection).name(),
        QColor(colors.text_on_selection).name(),
    )


def test_the_app_palette_highlight_follows_a_switch(themed_app):
    fxstyle.apply_theme("dracula")
    assert _highlight(themed_app.palette()) == _theme_highlight()
    fxstyle.apply_theme("light")
    assert _highlight(themed_app.palette()) == _theme_highlight()


@pytest.mark.parametrize("theme", ["dracula", "light"])
def test_a_graphics_text_item_selects_in_the_theme_accent(qtbot, themed_app,
                                                          theme):
    # Qt copies the palette into the item when it is built and offers no
    # way to refresh it, so an item built before a switch keeps the old one.
    fxstyle.apply_theme(theme)
    scene = QGraphicsScene()
    item = QGraphicsTextItem("selected words")
    scene.addItem(item)
    view = QGraphicsView(scene)
    qtbot.addWidget(view)
    view.resize(300, 100)
    view.show()
    qtbot.waitExposed(view)
    cursor = item.textCursor()
    cursor.select(QTextCursor.Document)
    item.setTextCursor(cursor)
    image = view.grab().toImage()
    drawn = {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
    }
    assert _theme_highlight()[0] in drawn


def test_the_selection_fill_is_the_accent_over_the_pane_unless_named(
        qapp, monkeypatch):
    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    themes["soft"] = {**themes["dark"], "selection": "#2a1a12",
                      "selection_border": "#ff4200"}
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})
    dark, soft = fxstyle._colour_tokens("dark"), fxstyle._colour_tokens("soft")
    assert dark["selection"] == fxstyle.mix_oklab(
        dark["surface"], dark["accent_primary"], fxstyle.SELECTION_TINT)
    assert soft["selection"] == "#2a1a12"
    assert dark["selection_border"] == dark["accent_primary"]
    assert soft["selection_border"] == "#ff4200"
    for ink in ("text_on_selection", "icon_on_selection"):
        assert fxstyle.get_contrast_ratio(soft[ink], "#2a1a12") >= 4.5, ink
