"""readable_ink returns an ink that reads on a background."""

import pytest

from fxgui import fxstyle


def test_white_stays_on_a_dark_background():
    assert fxstyle.readable_ink("#1e1e1e") == "#ffffff"


def test_white_turns_dark_on_a_light_background():
    ink = fxstyle.readable_ink("#f5f5f5")

    assert fxstyle.get_contrast_ratio(ink, "#f5f5f5") >= 4.5
    assert fxstyle.get_luminance(ink) < fxstyle.get_luminance("#f5f5f5")


@pytest.mark.parametrize("ground", ["#777777", "#7fbf7f", "#3a7bd5"])
def test_a_mid_background_gets_an_ink_that_reads(ground):
    ink = fxstyle.readable_ink(ground)

    assert fxstyle.get_contrast_ratio(ink, ground) >= 4.5, ink


def test_a_preferred_ink_that_reads_is_kept():
    assert fxstyle.readable_ink("#ffffff", "#336699") == "#336699"


def test_a_preferred_ink_that_fails_steps_away_from_the_background():
    ink = fxstyle.readable_ink("#202020", "#404040")

    assert fxstyle.get_contrast_ratio(ink, "#202020") >= 4.5
    assert fxstyle.get_luminance(ink) > fxstyle.get_luminance("#404040")
    assert ink != "#ffffff", "the first step that reads, not the pole"


def test_the_floor_is_the_callers():
    ink = fxstyle.readable_ink("#f5f5f5", floor=7.0)

    assert fxstyle.get_contrast_ratio(ink, "#f5f5f5") >= 7.0


def test_a_qcolor_reads_as_its_name():
    from qtpy.QtGui import QColor

    assert fxstyle.readable_ink(QColor("#1e1e1e"), QColor("#ffffff")) == (
        fxstyle.readable_ink("#1e1e1e"))
