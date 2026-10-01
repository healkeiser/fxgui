"""Unit tests for the unified token pass in fxstyle."""

import pytest

from fxgui import fxstyle


def test_token_map_contains_flat_theme_keys(qapp):
    tokens = fxstyle._token_map("dark")
    assert tokens["@surface"].startswith("#")
    assert tokens["@text"].startswith("#")


def test_token_map_flattens_feedback_colors(qapp):
    tokens = fxstyle._token_map("dark")
    assert "@feedback_error_foreground" in tokens
    assert "@feedback_error_background" in tokens
    assert tokens["@feedback_error_foreground"].startswith("#")


def test_token_map_computes_on_accent_colors(qapp):
    tokens = fxstyle._token_map("dark")
    assert tokens["@text_on_accent_primary"] in ("#FFFFFF", "#000000") or (
        tokens["@text_on_accent_primary"].startswith("#")
    )
    assert "@icon_on_accent_primary" in tokens


def test_token_map_merges_unknown_theme_over_dark(qapp):
    # Unknown themes fall back to dark values key-by-key.
    assert fxstyle._token_map("no_such_theme") == fxstyle._token_map("dark")


def test_resolve_longest_key_first(qapp):
    qss = "a: @border; b: @border_light;"
    resolved = fxstyle.resolve(qss, "dark")
    assert "@" not in resolved
    assert "_light" not in resolved  # @border must not corrupt @border_light


def test_resolve_icons_path(qapp):
    resolved = fxstyle.resolve("url(~icons/x.svg)", "dark")
    assert "~icons" not in resolved
    assert "stylesheet_dark" in resolved or "stylesheet_light" in resolved


def test_token_map_fills_partial_theme_from_dark(qapp, monkeypatch):
    # A custom theme overriding a single key gets every other key from dark.
    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    themes["_partial"] = {"surface": "#123456"}
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})
    tokens = fxstyle._token_map("_partial")
    assert tokens["@surface"] == "#123456"
    assert tokens["@text"] == fxstyle._token_map("dark")["@text"]


def test_token_map_computes_on_accent_when_theme_omits_them(qapp, monkeypatch):
    # Only when dark itself omits the on-accent keys does the computed
    # fallback run (the baseline merge fills them in for any other theme).
    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    themes["dark"] = {
        key: value
        for key, value in themes["dark"].items()
        if not key.startswith(("text_on_accent", "icon_on_accent"))
    }
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})
    tokens = fxstyle._token_map("dark")
    expected = fxstyle._pole_from(themes["dark"]["accent_primary"])
    assert tokens["@text_on_accent_primary"] == expected
    assert tokens["@icon_on_accent_primary"] == expected


_TEXT_GROUNDS = ("surface", "surface_sunken", "surface_alt", "well", "frame",
                 "tooltip", "state_hover")


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_every_text_ink_reads_on_every_surface_it_sits_on(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    ratio = fxstyle.get_contrast_ratio
    for ground in _TEXT_GROUNDS:
        assert ratio(colors["text"], colors[ground]) >= 4.5, ground
        assert ratio(colors["text_muted"], colors[ground]) >= 4.5, ground
    # A pressed or checked fill carries text, never muted text.
    assert ratio(colors["text"], colors["state_pressed"]) >= 4.5


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_pressed_fill_stands_off_the_hover_fill(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    assert fxstyle.get_contrast_ratio(
        colors["state_pressed"], colors["state_hover"]
    ) >= fxstyle.STATE_MIN_CONTRAST


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_muted_text_stays_a_visible_step_from_text(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    assert fxstyle.get_contrast_ratio(
        colors["text"], colors["text_muted"]
    ) >= fxstyle.MUTED_STEP
