"""The single-colour dcc marks follow the theme and carry no tile."""

from pathlib import Path

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QImage, QPainter

from fxgui import fxicons, fxstyle

MARKS = ["alembic", "3d_equalizer", "rez", "zbrush"]
SVG_DIR = Path(__file__).parent.parent / "fxgui" / "icons" / "dcc" / "svg"


def _ink(icon):
    image = icon.pixmap(48, 48).toImage()
    seen = [
        image.pixelColor(x, y)
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 200
    ]
    assert seen
    return QColor(
        sum(c.red() for c in seen) // len(seen),
        sum(c.green() for c in seen) // len(seen),
        sum(c.blue() for c in seen) // len(seen),
    ).name()


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_each_mark_reads_on_the_surface(qapp, theme):
    fxstyle.apply_theme(theme)
    surface = fxstyle.colors().surface
    for name in MARKS:
        ink = _ink(fxicons.get_icon(name, library="dcc"))
        assert fxstyle.get_contrast_ratio(ink, surface) >= 3.0, (name, ink)


@pytest.mark.parametrize("name", MARKS)
def test_a_theme_switch_redraws_the_mark(qapp, name):
    icon = fxicons.get_icon(name, library="dcc")
    fxstyle.apply_theme("light")
    on_light = _ink(icon)
    fxstyle.apply_theme("dark")
    assert _ink(icon) != on_light


@pytest.mark.parametrize("name", MARKS)
def test_no_tile_behind_the_mark(qapp, name):
    from qtpy.QtSvg import QSvgRenderer

    image = QImage(256, 256, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(str(SVG_DIR / f"{name}.svg")).render(painter)
    painter.end()
    # A tile fills its corners; a bare mark leaves them empty.
    for x, y in [(26, 26), (229, 26), (26, 229), (229, 229)]:
        assert image.pixelColor(x, y).alpha() == 0, (x, y)
