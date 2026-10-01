"""The `frame` and `well` colour roles, computed for every theme."""

# Third-party
import pytest
from qtpy.QtGui import QColor

# Internal
from fxgui import fxstyle

THEMES = fxstyle.get_available_themes()


def _colors(monkeypatch, theme):
    monkeypatch.setattr(fxstyle, "_theme", theme)
    return dict(vars(fxstyle.colors()))


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

    colors = dict(vars(fxstyle.colors()))
    tokens = fxstyle._token_map("_custom")

    assert colors["frame"] == tokens["@frame"] == "#123456"
    assert colors["well"] == tokens["@well"] == "#654321"


def test_a_stated_frame_moves_the_computed_well(qapp, monkeypatch):
    _with_theme(monkeypatch, {
        "surface": "#303030", "surface_sunken": "#202020", "frame": "#000000",
    })

    assert fxstyle.colors().well == "#181818"


def test_a_light_theme_whose_sunken_is_lighter_gets_a_darker_frame(
    qapp, monkeypatch
):
    """A sunken surface lighter than the pane cannot frame it."""
    _with_theme(monkeypatch, {
        "surface": "#f0f0f0", "surface_sunken": "#ffffff",
    })

    frame = fxstyle.colors().frame

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

    frame = QColor(fxstyle.colors().frame)
    pane = QColor("#fdf6e3")

    assert abs(frame.hsvHue() - pane.hsvHue()) <= 2


@pytest.mark.parametrize("theme", THEMES)
def test_a_panes_edge_reads_on_the_frame(qapp, monkeypatch, theme):
    colors = _colors(monkeypatch, theme)
    tokens = fxstyle._token_map(theme)

    assert tokens["@pane_border"] == colors["pane_border"]
    assert (
        fxstyle.get_contrast_ratio(colors["pane_border"], colors["frame"])
        >= fxstyle.PANE_BORDER_MIN_CONTRAST
    )


def test_a_border_that_already_reads_is_the_panes_edge(qapp, monkeypatch):
    colors = _colors(monkeypatch, "dark")

    assert colors["pane_border"] == colors["border"]


def test_a_faint_border_is_pushed_away_from_the_frame(qapp, monkeypatch):
    _with_theme(monkeypatch, {
        "surface": "#f0f0f0", "surface_sunken": "#ffffff",
        "border": "#e0e0e0",
    })
    colors = dict(vars(fxstyle.colors()))

    assert fxstyle.get_luminance(colors["pane_border"]) < (
        fxstyle.get_luminance("#e0e0e0"))


def test_a_theme_that_states_its_pane_border_keeps_it(qapp, monkeypatch):
    _with_theme(monkeypatch, {
        "surface": "#303030", "surface_sunken": "#202020",
        "pane_border": "#abcdef",
    })

    assert fxstyle.colors().pane_border == "#abcdef"


@pytest.mark.parametrize("theme", THEMES)
def test_the_splitter_mark_reads_on_the_frame(qapp, monkeypatch, theme):
    colors = _colors(monkeypatch, theme)

    assert fxstyle._token_map(theme)["@splitter_mark"] == (
        colors["splitter_mark"])
    assert (
        fxstyle.get_contrast_ratio(colors["splitter_mark"], colors["frame"])
        >= fxstyle.SPLITTER_MARK_MIN_CONTRAST
    )


def test_the_splitter_mark_is_the_border_where_that_reads(qapp, monkeypatch):
    colors = _colors(monkeypatch, "dark")

    assert colors["splitter_mark"] == colors["border"]


def test_the_splitter_mark_falls_back_to_border_light(qapp, monkeypatch):
    """light: border #e0e0e0 is 1.04 on its frame; border_light reads."""
    colors = _colors(monkeypatch, "light")

    assert colors["splitter_mark"] == colors["border_light"]


@pytest.mark.parametrize(
    "pane", ["#000000", "#ffffff", "#0a0a0a", "#fafafa"])
def test_a_pane_at_either_end_still_gets_a_frame_and_a_well(
    qapp, monkeypatch, pane
):
    """A black pane cannot be darkened: its frame is lighter instead."""
    _with_theme(monkeypatch, {"surface": pane, "surface_sunken": pane})
    colors = dict(vars(fxstyle.colors()))
    frame, well = colors["frame"], colors["well"]

    assert frame != pane
    assert fxstyle.get_contrast_ratio(frame, pane) >= (
        fxstyle.FRAME_MIN_CONTRAST)
    assert fxstyle.get_contrast_ratio(well, pane) >= (
        fxstyle.WELL_MIN_CONTRAST)
    low, high = sorted([fxstyle.get_luminance(frame),
                        fxstyle.get_luminance(pane)])
    assert low <= fxstyle.get_luminance(well) <= high
    assert fxstyle.get_contrast_ratio(colors["pane_border"], frame) >= (
        fxstyle.PANE_BORDER_MIN_CONTRAST)
    assert fxstyle.get_contrast_ratio(colors["splitter_mark"], frame) >= (
        fxstyle.SPLITTER_MARK_MIN_CONTRAST)
