"""Unit tests for the unified token pass in fxstyle."""

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


def test_resolve_tokens_longest_key_first(qapp):
    qss = "a: @border; b: @border_light;"
    resolved = fxstyle._resolve_tokens(qss, "dark")
    assert "@" not in resolved
    assert "_light" not in resolved  # @border must not corrupt @border_light


def test_resolve_tokens_icons_path(qapp):
    resolved = fxstyle._resolve_tokens("url(~icons/x.svg)", "dark")
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
    expected = fxstyle.get_contrast_text_color(
        themes["dark"]["accent_primary"]
    )
    assert tokens["@text_on_accent_primary"] == expected
    assert tokens["@icon_on_accent_primary"] == expected
