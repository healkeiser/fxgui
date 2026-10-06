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

from _helpers import first_ink

_SIZE = QSize(32, 32)


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
    assert first_ink(icon.pixmap(_SIZE)) == _name(fxstyle.colors().icon)

    fxstyle.apply_theme("light")

    assert first_ink(icon.pixmap(_SIZE)) == _name(fxstyle.colors().icon)
    assert fxstyle.colors().icon.lower() != "#b4b4b4"


def test_an_explicit_colour_ignores_the_theme(qapp):
    icon = fxicons.get_icon("check", color="#00ff00")
    fxstyle.apply_theme("light")
    assert first_ink(icon.pixmap(_SIZE)) == "#00ff00"


def test_a_disabled_button_icon_wears_the_disabled_colour(qtbot):
    button = QPushButton("Save")
    qtbot.addWidget(button)
    fxicons.set_icon(button, "check")
    button.setEnabled(False)

    pixmap = button.icon().pixmap(_SIZE, QIcon.Disabled)
    expected = QColor(fxstyle.colors().text_disabled)
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

    # A copy detaches, and clones, only while the original is held.
    originals = [fxicons.get_icon("check") for _ in range(50)]
    icons = []
    for original in originals:
        icon = QIcon(original)
        icon.addPixmap(QPixmap(4, 4), QIcon.Normal, QIcon.On)
        icons.append(icon)
    gc.collect()

    assert all(not icon.pixmap(_SIZE).isNull() for icon in icons)
    assert len(fxicons._clones) >= 50  # the only owner of each clone
    del icons, icon, originals, original
    gc.collect()
    held = fxicons.get_icon("check")
    last = QIcon(held)
    last.addPixmap(QPixmap(4, 4), QIcon.Normal, QIcon.On)
    assert len(fxicons._clones) == 1  # dead clones dropped on the next one


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


# Monochrome and full-colour libraries


def test_a_full_colour_icon_ignores_a_colour(qapp):
    plain = fxicons.get_icon("blender", library="brands").pixmap(_SIZE).toImage()
    asked = fxicons.get_icon(
        "blender", library="brands", color="#00ff00").pixmap(_SIZE).toImage()
    pixmap = fxicons.get_pixmap(
        "blender", library="brands", color="#00ff00", dpr=1.0).toImage()
    raw = fxicons.get_pixmap("blender", library="brands", dpr=1.0).toImage()

    assert asked == plain
    assert pixmap == raw


def test_a_monochrome_icon_takes_a_colour(qapp):
    icon = fxicons.get_icon("check", library="material", color="#00ff00")
    assert first_ink(icon.pixmap(_SIZE)) == "#00ff00"


def test_libraries_declare_whether_they_recolour(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr(fxicons, "_libraries_info", dict(fxicons._libraries_info))
    recolor = {name: info["recolor"] for name, info in fxicons._libraries_info.items()}
    assert recolor == {
        "beacon": True, "brands": False, "material": True,
        "fontawesome": True, "simple": True,
    }
    defaults = {"extension": "svg", "style": None, "color": None,
                "width": 8, "height": 8}
    fxicons.add_library("mono", "{root}/{icon_name}.{extension}", defaults,
                        root=str(tmp_path))
    fxicons.add_library("logos", "{root}/{icon_name}.{extension}", defaults,
                        root=str(tmp_path), recolor=False)
    assert fxicons._libraries_info["mono"]["recolor"] is True
    assert fxicons._libraries_info["logos"]["recolor"] is False


def test_recolouring_scans_no_pixels(qapp):
    pixmap = QPixmap(512, 512)
    pixmap.fill(QColor("#ff0000"))
    start = time.perf_counter()
    fxicons._tint(pixmap, "#00ff00")
    assert time.perf_counter() - start < 0.05
    assert not hasattr(fxicons, "has_transparency")


def test_a_failing_draw_answers_a_blank_pixmap(qapp, monkeypatch, capsys):
    """An exception escaping the engine would kill the process."""
    icon = fxicons.get_icon("check")

    def broken(*_args):
        raise RuntimeError("theme table broken")

    monkeypatch.setattr(fxicons._ThemedIconEngine, "_ink", broken)
    assert icon.pixmap(QSize(20, 20)).isNull()
    assert "theme table broken" in capsys.readouterr().err


def test_cloned_icons_alive_at_exit_do_not_crash_the_interpreter():
    """Python quits with cloned icons still held by widgets and by itself."""
    import subprocess
    import sys

    code = (
        "import os;"
        "os.environ['QT_QPA_PLATFORM']='offscreen';"
        "from qtpy.QtGui import QIcon, QPixmap;"
        "from qtpy.QtWidgets import QApplication, QPushButton;"
        "app=QApplication([]);"
        "from fxgui import fxicons;"
        "icons=[];buttons=[];held=[];\n"
        "for _ in range(20):\n"
        "    held.append(fxicons.get_icon('check'))\n"
        "    icon=QIcon(held[-1])\n"
        "    icon.addPixmap(QPixmap(4,4),QIcon.Normal,QIcon.On)\n"
        "    icons.append(icon)\n"
        "    button=QPushButton()\n"
        "    button.setIcon(icon)\n"
        "    buttons.append(button)\n"
        "assert fxicons._clones\n"
        "assert not icons[0].pixmap(16,16).isNull()\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        timeout=120,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "ok" in result.stdout
    assert "Fatal" not in output and "access violation" not in output, output
