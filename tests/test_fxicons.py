"""Tests for `fxgui.fxicons` icon-mode behavior.

The QApplication, headless platform, and cleanup are handled by pytest-qt's
`qapp`/`qtbot` fixtures (see conftest.py). Run with: ``pytest``.

Icons carry per-state pixmaps:
- Disabled  -> grayed (everywhere)
- Selected  -> accent color (selected item rows)
- Active    -> accent color (hovered rows, highlighted menu items)

Qt also renders a *focused push button*'s icon in Active mode, with no accent
behind it, so `set_icon` strips Active for push buttons. A hovered tool
button sits on the secondary accent and keeps it.
"""

import inspect

import pytest
from qtpy.QtGui import QColor, QIcon, QPixmapCache
from qtpy.QtCore import QSize
from qtpy.QtWidgets import QAction, QLabel, QPushButton, QToolButton

from fxgui import fxicons

_SIZE = QSize(48, 48)


def _img(icon: QIcon, mode):
    return icon.pixmap(_SIZE, mode).toImage()


def _active_matches_normal(icon: QIcon) -> bool:
    return _img(icon, QIcon.Active) == _img(icon, QIcon.Normal)


def test_get_icon_has_per_state_colors(qapp):
    """A bare get_icon() carries distinct Disabled / Selected / Active pixmaps
    so menus and item views recolor their icons on a highlight background."""
    icon = fxicons.get_icon("check", width=48, height=48)
    normal = _img(icon, QIcon.Normal)
    assert _img(icon, QIcon.Disabled) != normal
    assert _img(icon, QIcon.Selected) != normal
    assert _img(icon, QIcon.Active) != normal


def test_an_active_ink_of_the_normal_token_matches_normal(qapp):
    """An Active ink named like the normal one gives a button-safe icon."""
    icon = fxicons.get_icon(
        "check", width=48, height=48, inks={"active": "icon"})
    assert _active_matches_normal(icon)


def test_button_icon_drops_active_recolor(qtbot):
    """Regression: a focused QPushButton renders its icon in Active mode, so
    set_icon must strip Active for buttons or the icon recolors on focus."""
    button = QPushButton("Save")
    qtbot.addWidget(button)
    fxicons.set_icon(button, "check", width=48, height=48)

    button.show()
    qtbot.waitExposed(button)
    button.setFocus()

    icon = button.icon()
    assert not icon.isNull()
    assert _active_matches_normal(icon)


def test_toolbutton_icon_keeps_the_accent_recolor(qtbot):
    """A QToolButton hovers on the secondary accent, like a highlighted menu
    item, so its hovered icon wears the colour made for that accent."""
    from fxgui import fxstyle

    button = QToolButton()
    qtbot.addWidget(button)
    fxicons.set_icon(button, "check", width=48, height=48)
    assert not _active_matches_normal(button.icon())
    assert _ink(button.icon(), QIcon.Active) == (
        fxstyle.get_icon_on_accent_secondary().lower())


def _ink(icon: QIcon, mode) -> str:
    image = _img(icon, mode)
    for x in range(image.width()):
        for y in range(image.height()):
            colour = image.pixelColor(x, y)
            if colour.alpha() == 255:
                return colour.name().lower()
    return ""


def test_menu_action_keeps_active_recolor(qapp):
    """A QAction (menu item) is not a button: its highlighted icon must keep
    the accent recolor so it stays readable on the accent background."""
    action = QAction("Open")
    fxicons.set_icon(action, "check", width=48, height=48)
    assert not _active_matches_normal(action.icon())


def test_a_disabled_icon_wears_the_text_disabled_token(qapp):
    from fxgui import fxstyle

    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        icon = fxicons.get_icon("check")
        assert _ink(icon, QIcon.Disabled) == (
            QColor(fxstyle.colors().text_disabled).name()), theme


def test_set_icon_raises_on_a_widget_without_set_icon(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    with pytest.raises(AttributeError):
        fxicons.set_icon(label, "check")


def test_set_icon_takes_no_theme_color():
    assert "theme_color" not in inspect.signature(fxicons.set_icon).parameters


def test_one_icon_cache_remains():
    for name in (
        "_get_icon_cached",
        "_get_pixmap_cached",
        "_get_pixmap_internal",
        "clear_icon_cache",
    ):
        assert not hasattr(fxicons, name), name


def test_get_pixmap_is_the_engines_drawing(qapp):
    QPixmapCache.clear()
    pixmap = fxicons.get_pixmap("check", 16, 16, dpr=1.0)
    drawn = fxicons.get_icon("check", 16, 16).pixmap(QSize(16, 16))
    assert pixmap.toImage() == drawn.toImage()


def test_the_dead_icon_api_is_gone():
    for name in (
        "set_default_icon_library",
        "set_icon_defaults",
        "get_available_icons_in_library",
        "get_icon_color",
        "superpose_icons",
    ):
        assert not hasattr(fxicons, name), name
        assert name not in fxicons.__all__, name
    assert "change_pixmap_color" not in fxicons.__all__
    assert "badged" in fxicons.__all__


def test_a_fallback_name_keeps_the_size_and_colour_asked(qapp):
    icon = fxicons.get_icon(
        "no_such_mark", 20, 20, color="#00ff00", library="dcc",
        fallback="check")
    assert icon.actualSize(QSize(64, 64)) == QSize(20, 20)
    assert _ink(icon, QIcon.Normal) == "#00ff00"
