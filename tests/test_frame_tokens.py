"""The `frame` and `well` colour roles, computed for every theme."""

# Third-party
import pytest
from qtpy.QtGui import QColor

# Internal
from fxgui import fxstyle

THEMES = fxstyle.get_available_themes()


def _colors(monkeypatch, theme):
    monkeypatch.setattr(fxstyle, "_theme", theme)
    return fxstyle.get_theme_colors()


@pytest.mark.parametrize("theme", THEMES)
def test_every_theme_has_a_frame_and_a_well(qapp, monkeypatch, theme):
    colors = _colors(monkeypatch, theme)
    tokens = fxstyle._token_map(theme)

    assert colors["frame"].startswith("#")
    assert colors["well"].startswith("#")
    assert tokens["@frame"] == colors["frame"]
    assert tokens["@well"] == colors["well"]


@pytest.mark.parametrize("theme", THEMES)
def test_the_frame_is_darker_than_the_pane_by_a_step(qapp, monkeypatch, theme):
    colors = _colors(monkeypatch, theme)
    frame, surface = colors["frame"], colors["surface"]

    assert frame != surface
    assert fxstyle.get_luminance(frame) < fxstyle.get_luminance(surface)
    assert (
        fxstyle.get_contrast_ratio(frame, surface)
        >= fxstyle.FRAME_MIN_CONTRAST
    )


@pytest.mark.parametrize("theme", THEMES)
def test_the_well_sits_between_the_pane_and_the_frame(
    qapp, monkeypatch, theme
):
    colors = _colors(monkeypatch, theme)
    surface, well, frame = colors["surface"], colors["well"], colors["frame"]

    assert (
        fxstyle.get_luminance(frame)
        < fxstyle.get_luminance(well)
        < fxstyle.get_luminance(surface)
    )
    assert (
        fxstyle.get_contrast_ratio(well, surface)
        >= fxstyle.WELL_MIN_CONTRAST
    )


@pytest.mark.parametrize(
    "theme",
    [t for t in THEMES if QColor(
        fxstyle.get_colors()["themes"][t]["surface"]).lightness() <= 128],
)
def test_a_dark_theme_frames_in_its_sunken_surface(qapp, monkeypatch, theme):
    colors = _colors(monkeypatch, theme)

    assert colors["frame"] == colors["surface_sunken"]


def _with_theme(monkeypatch, theme):
    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    themes["_custom"] = theme
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})
    monkeypatch.setattr(fxstyle, "_theme", "_custom")


def test_a_theme_that_states_its_frame_keeps_it(qapp, monkeypatch):
    _with_theme(monkeypatch, {
        "surface": "#303030", "surface_sunken": "#202020",
        "frame": "#123456", "well": "#654321",
    })

    colors = fxstyle.get_theme_colors()
    tokens = fxstyle._token_map("_custom")

    assert colors["frame"] == tokens["@frame"] == "#123456"
    assert colors["well"] == tokens["@well"] == "#654321"


def test_a_stated_frame_moves_the_computed_well(qapp, monkeypatch):
    _with_theme(monkeypatch, {
        "surface": "#303030", "surface_sunken": "#202020", "frame": "#000000",
    })

    assert fxstyle.get_theme_colors()["well"] == "#181818"


def test_a_light_theme_whose_sunken_is_lighter_gets_a_darker_frame(
    qapp, monkeypatch
):
    """A sunken surface lighter than the pane cannot frame it."""
    _with_theme(monkeypatch, {
        "surface": "#f0f0f0", "surface_sunken": "#ffffff",
    })

    frame = fxstyle.get_theme_colors()["frame"]

    assert fxstyle.get_luminance(frame) < fxstyle.get_luminance("#f0f0f0")
    assert (
        fxstyle.get_contrast_ratio(frame, "#f0f0f0")
        >= fxstyle.FRAME_MIN_CONTRAST
    )


def test_a_darkened_frame_keeps_the_panes_hue(qapp, monkeypatch):
    """Neutral: no accent comes into it, the pane's own tint stays."""
    _with_theme(monkeypatch, {
        "surface": "#fdf6e3", "surface_sunken": "#fdf6e3",
        "accent_primary": "#268bd2",
    })

    frame = QColor(fxstyle.get_theme_colors()["frame"])
    pane = QColor("#fdf6e3")

    assert abs(frame.hsvHue() - pane.hsvHue()) <= 2
