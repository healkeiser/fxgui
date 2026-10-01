"""The dcc library carries a mark for every application a studio launches."""

import pytest

from fxgui import fxicons

MARKS = [
    "adobe_after_effects",
    "cinema_4d",
    "davinci_resolve",
    "unreal_engine",
    "vlc",
    "xstudio",
]


@pytest.mark.parametrize("name", MARKS)
def test_each_mark_draws_in_colour(qapp, name):
    image = fxicons.get_pixmap(name, library="dcc", dpr=1.0).toImage()
    assert not image.isNull()
    centre = image.pixelColor(image.width() // 2, image.height() // 2)
    assert centre.alpha() > 0


def test_the_library_lists_every_mark(qapp):
    assert set(MARKS) <= set(fxicons.get_available_icons_in_library("dcc"))


@pytest.mark.parametrize("name", ["alembic", "deadline", "kitsu", "python"])
def test_each_vendor_logo_resolves_and_draws(qapp, name):
    icon = fxicons.get_icon(name, library="dcc")
    assert not icon.isNull()
    image = icon.pixmap(48, 48).toImage()
    assert any(
        image.pixelColor(x, y).alpha() > 0
        for x in range(image.width())
        for y in range(image.height())
    )
