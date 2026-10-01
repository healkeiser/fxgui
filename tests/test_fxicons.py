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
from qtpy.QtGui import QColor, QIcon, QImage, QPixmap, QPixmapCache
from qtpy.QtCore import QSize
from qtpy.QtWidgets import QAction, QLabel, QPushButton, QToolButton

from fxgui import fxicons, fxstyle

from _helpers import first_ink

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


def test_a_hovered_tool_button_icon_keeps_its_normal_ink(qtbot):
    """A QToolButton hovers on the neutral hover fill, so Qt's Active icon
    is drawn in the ink it has at rest."""
    button = QToolButton()
    qtbot.addWidget(button)
    fxicons.set_icon(button, "check", width=48, height=48)
    assert _active_matches_normal(button.icon())


def test_menu_action_keeps_active_recolor(qapp, monkeypatch):
    """A QAction (menu item) is not a button: a current menu row is filled
    with the primary accent, so its icon takes the ink made for it. A theme
    whose two on-accent inks differ tells them apart."""
    from fxgui import fxstyle

    colors = fxstyle.get_colors()
    split = dict(colors["themes"]["dark"])
    split.update({
        "icon_on_accent_primary": "#ffffff",
        "icon_on_accent_secondary": "#000000",
    })
    patched = dict(colors, themes={**colors["themes"], "split": split})
    monkeypatch.setattr(fxstyle, "get_colors", lambda: patched)
    fxstyle.apply_theme("split")
    action = QAction("Open")
    fxicons.set_icon(action, "check", width=48, height=48)
    assert not _active_matches_normal(action.icon())
    assert first_ink(_img(action.icon(), QIcon.Active)) == (
        fxstyle.colors().icon_on_accent_primary.lower())


@pytest.mark.parametrize("theme", __import__("fxgui.fxstyle").fxstyle
                         .get_available_themes())
def test_a_current_menu_row_icon_reads_on_the_accent(qapp, theme):
    """WCAG's 3:1 for a control's part, in every bundled theme."""
    from fxgui import fxstyle

    fxstyle.apply_theme(theme)
    icon = fxicons.get_icon("check", width=48, height=48)
    ink = first_ink(_img(icon, QIcon.Active))
    assert fxstyle.get_contrast_ratio(
        ink, fxstyle.colors().accent_primary) >= 3.0, ink


def test_a_disabled_icon_wears_the_text_disabled_token(qapp):
    from fxgui import fxstyle

    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        icon = fxicons.get_icon("check")
        assert first_ink(_img(icon, QIcon.Disabled)) == (
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


def test_a_fallback_name_keeps_the_size_and_colour_asked(qapp):
    icon = fxicons.get_icon(
        "no_such_mark", 20, 20, color="#00ff00", library="dcc",
        fallback="check")
    assert icon.actualSize(QSize(64, 64)) == QSize(20, 20)
    assert first_ink(_img(icon, QIcon.Normal)) == "#00ff00"


def _count_calls(monkeypatch, module, name):
    calls = []
    original = getattr(module, name)

    def counting(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, name, counting)
    return calls


def test_get_icon_reads_the_colour_cache(qapp, monkeypatch):
    fxstyle.colors()
    depth = _count_calls(monkeypatch, fxstyle, "_depth_colors")
    for name in ("add", "close", "save"):
        fxicons.get_icon(name)

    assert depth == []


def test_an_opaque_pixmap_recolours(qapp):
    pixmap = QPixmap(8, 8)
    pixmap.fill(QColor("#ff0000"))

    out = fxicons._tint(pixmap, "#00ff00")

    assert out.toImage().pixelColor(4, 4) == QColor("#00ff00")


def _png_library(monkeypatch, tmp_path):
    folder = tmp_path / "studio"
    folder.mkdir()
    image = QImage(8, 8, QImage.Format_ARGB32)
    image.fill(QColor("#ff0000"))
    image.save(str(folder / "square.png"))
    monkeypatch.setattr(
        fxicons, "_libraries_info", dict(fxicons._libraries_info)
    )
    fxicons.add_library(
        "studio",
        pattern="{root}/{library}/{icon_name}.{extension}",
        defaults={
            "extension": "png",
            "style": None,
            "color": "#00ff00",
            "width": 8,
            "height": 8,
        },
        root=str(tmp_path),
    )


def test_an_opaque_png_icon_recolours(qapp, monkeypatch, tmp_path):
    _png_library(monkeypatch, tmp_path)

    pixmap = fxicons.get_pixmap("square", library="studio", dpr=1.0)

    assert pixmap.toImage().pixelColor(4, 4) == QColor("#00ff00")
