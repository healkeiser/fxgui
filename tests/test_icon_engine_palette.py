"""Tests for the theme palette and the pull-model icon engine."""

# Built-in
import time

# Third-party
import pytest
from qtpy.QtCore import QSize
from qtpy.QtGui import QColor, QIcon, QImage, QPainter, QPalette, QPixmap
from qtpy.QtWidgets import QApplication, QListWidget, QListWidgetItem, QPushButton, QWidget

# Internal
from fxgui import fxicons, fxstyle

_SIZE = QSize(32, 32)


def _ink(pixmap) -> str:
    image = pixmap.toImage()
    for x in range(image.width()):
        for y in range(image.height()):
            colour = image.pixelColor(x, y)
            if colour.alpha() == 255:
                return colour.name().lower()
    return ""


def _name(value: str) -> str:
    return QColor(value).name().lower()


# Palette


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_root_wears_the_theme_palette(qtbot, theme):
    fxstyle.apply_theme(theme)
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)

    colors = fxstyle.colors()
    palette = root.palette()
    assert palette.color(QPalette.Highlight).name() == _name(colors.accent_primary)
    assert palette.color(QPalette.Base).name() == _name(colors.surface_sunken)
    assert palette.color(QPalette.Text).name() == _name(colors.text)
    assert palette.color(QPalette.Disabled, QPalette.Text).name() == (
        _name(colors.text_disabled))


def test_a_switch_repaints_the_root_palette(qtbot):
    fxstyle.apply_theme("dark")
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)

    fxstyle.apply_theme("light")

    assert root.palette().color(QPalette.Base).name() == (
        _name(fxstyle.colors().surface_sunken))


def test_palette_reads_a_named_theme(qapp):
    light = fxstyle.get_colors()["themes"]["light"]
    palette = fxstyle.palette("light")
    assert palette.color(QPalette.Window).name() == _name(light["surface"])


def test_a_foreign_app_palette_is_untouched(qtbot):
    before = QApplication.palette().color(QPalette.Highlight).name()
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    fxstyle.apply_theme("dracula")

    assert QApplication.palette().color(QPalette.Highlight).name() == before


# Icon engine


def test_an_icon_follows_a_theme_switch_by_itself(qapp):
    fxstyle.apply_theme("dark")
    icon = fxicons.get_icon("check")
    assert _ink(icon.pixmap(_SIZE)) == _name(fxstyle.colors().icon)

    fxstyle.apply_theme("light")

    assert _ink(icon.pixmap(_SIZE)) == _name(fxstyle.colors().icon)
    assert fxstyle.colors().icon.lower() != "#b4b4b4"


def test_an_explicit_colour_ignores_the_theme(qapp):
    icon = fxicons.get_icon("check", color="#00ff00")
    fxstyle.apply_theme("light")
    assert _ink(icon.pixmap(_SIZE)) == "#00ff00"


def test_a_disabled_button_icon_wears_the_disabled_colour(qtbot):
    button = QPushButton("Save")
    qtbot.addWidget(button)
    fxicons.set_icon(button, "check")
    button.setEnabled(False)

    pixmap = button.icon().pixmap(_SIZE, QIcon.Disabled)
    expected = QColor(fxicons._get_disabled_icon_color(fxstyle.colors().icon))
    image = pixmap.toImage()
    # Premultiplied storage rounds each channel by one step.
    assert any(
        abs(seen.red() - expected.red()) <= 2
        and abs(seen.green() - expected.green()) <= 2
        and abs(seen.blue() - expected.blue()) <= 2
        for seen in (
            image.pixelColor(x, y)
            for x in range(image.width())
            for y in range(image.height())
        )
        if seen.alpha() == expected.alpha()
    )


def test_a_repeat_draw_is_served_from_the_cache(qapp):
    icon = fxicons.get_icon("check")
    first = icon.pixmap(_SIZE)
    second = icon.pixmap(_SIZE)
    assert first.cacheKey() == second.cacheKey()


def test_an_icon_copy_that_detaches_still_draws(qapp):
    """QIcon.addPixmap on a shared icon clones the engine Qt must keep."""
    import gc

    icons = []
    for _ in range(50):
        icon = QIcon(fxicons.get_icon("check"))
        icon.addPixmap(QPixmap(4, 4), QIcon.Normal, QIcon.On)
        icons.append(icon)
    gc.collect()

    assert all(not icon.pixmap(_SIZE).isNull() for icon in icons)
    del icons
    gc.collect()
    assert len(fxicons._clones) <= 1 + 50


def test_the_widget_registry_is_gone(qapp):
    for name in ("sync_colors_with_theme", "refresh_all_icons", "_icon_widgets"):
        assert not hasattr(fxicons, name), name


def test_two_thousand_icon_draws_fit_a_small_budget(qtbot):
    names = ["check", "close", "save", "add", "delete", "folder", "home",
             "search", "settings", "refresh"]
    view = QListWidget()
    qtbot.addWidget(view)
    view.setIconSize(QSize(16, 16))
    for index in range(2000):
        QListWidgetItem(fxicons.get_icon(names[index % len(names)]), str(index), view)
    image = QImage(16, 16, QImage.Format_ARGB32_Premultiplied)
    painter = QPainter(image)

    start = time.perf_counter()
    for index in range(2000):
        view.item(index).icon().paint(painter, 0, 0, 16, 16)
    elapsed = time.perf_counter() - start
    painter.end()

    print(f"2000 icon draws: {elapsed * 1000:.1f} ms")
    assert elapsed < 0.25
