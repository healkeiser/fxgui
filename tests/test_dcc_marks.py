"""The brands library carries a mark for every tool a studio uses."""

import re
from pathlib import Path

import pytest

from fxgui import fxicons

MARKS = [
    "adobe_after_effects",
    "cinema_4d",
    "cinema_4d_no_badge",
    "davinci_resolve",
    "redshift",
    "redshift_no_badge",
    "unreal_engine",
    "vlc",
    "xstudio",
]


@pytest.mark.parametrize("name", MARKS)
def test_each_mark_draws_in_colour(qapp, name):
    image = fxicons.get_pixmap(name, library="brands", dpr=1.0).toImage()
    assert not image.isNull()
    centre = image.pixelColor(image.width() // 2, image.height() // 2)
    assert centre.alpha() > 0


@pytest.mark.parametrize("name", MARKS)
def test_the_library_holds_every_mark(name):
    assert fxicons.get_icon_path(name, library="brands")


MARK_FILES = sorted(
    path.stem
    for path in Path(fxicons.get_icon_path("houdini_mark", library="brands")).parent.glob(
        "*_mark.svg"
    )
)


@pytest.mark.parametrize("name", MARK_FILES)
def test_each_one_colour_mark_is_grey_and_takes_the_ink(qapp, name):
    assert name in fxicons._libraries_info["brands"]["recolor_names"]
    svg = Path(fxicons.get_icon_path(name, library="brands")).read_text(encoding="utf-8")
    assert set(re.findall(r"#[0-9a-fA-F]{3,6}\b", svg)) == {"#808080"}
    image = fxicons.get_icon(name, library="brands", color="#00ff00").pixmap(48, 48).toImage()
    inks = {
        image.pixelColor(x, y).name()
        for x in range(48)
        for y in range(48)
        if image.pixelColor(x, y).alpha() == 255
    }
    assert inks == {"#00ff00"}


@pytest.mark.parametrize("name", ["alembic", "deadline", "kitsu", "python"])
def test_each_vendor_logo_resolves_and_draws(qapp, name):
    icon = fxicons.get_icon(name, library="brands")
    assert not icon.isNull()
    image = icon.pixmap(48, 48).toImage()
    assert any(
        image.pixelColor(x, y).alpha() > 0
        for x in range(image.width())
        for y in range(image.height())
    )


def test_the_old_dcc_name_still_reaches_the_brands_library(qapp):
    assert fxicons.get_icon_path("houdini", library="dcc") == fxicons.get_icon_path(
        "houdini", library="brands"
    )
    assert not fxicons.get_icon("houdini_mark", library="dcc").isNull()
