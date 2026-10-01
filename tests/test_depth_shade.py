"""depth_shade tints a tree row by its depth and keeps its text readable."""

import pytest

from fxgui import fxstyle


def _text_contrast(ground):
    return fxstyle.get_contrast_ratio(
        fxstyle.get_theme_colors()["text"], ground)


def test_a_top_level_row_keeps_its_base():
    assert fxstyle.depth_shade("#302f2f", 0) == "#302f2f"


def test_each_level_steps_toward_border_light_until_the_cap(qapp):
    base = fxstyle.get_theme_colors()["surface"]
    tone = fxstyle.get_theme_colors()["border_light"]
    apart = [
        fxstyle.get_contrast_ratio(fxstyle.depth_shade(base, depth), tone)
        for depth in range(fxstyle.DEPTH_CAP + 1)
    ]
    assert apart == sorted(apart, reverse=True)
    assert len(set(apart)) == len(apart)
    assert fxstyle.depth_shade(base, fxstyle.DEPTH_CAP + 3) == (
        fxstyle.depth_shade(base, fxstyle.DEPTH_CAP))


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_text_stays_readable_at_every_depth(qapp, theme):
    fxstyle.apply_theme(theme)
    colors = fxstyle.get_theme_colors()
    for base in (colors["surface"], colors["surface_alt"]):
        floor = min(4.5, _text_contrast(base))
        for depth in range(1, fxstyle.DEPTH_CAP + 2):
            assert _text_contrast(fxstyle.depth_shade(base, depth)) >= floor
