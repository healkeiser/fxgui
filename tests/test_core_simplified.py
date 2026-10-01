"""Tests pinning the behaviour the core modules keep after simplification."""

# Built-in
from pathlib import Path

# Internal
from fxgui import fxconfig, fxicons, fxstyle


def test_one_name_per_job_in_fxstyle():
    for name in (
        "theme_manager", "FXThemeManager", "get_theme_colors",
        "get_accent_colors", "get_icon_color", "get_icon_on_accent_primary",
        "get_icon_on_accent_secondary", "replace_colors", "load_stylesheet",
        "build_stylesheet", "set_widget_style", "WIDGET_STYLE_PROPERTY",
        "get_contrast_text_color",
    ):
        assert not hasattr(fxstyle, name), name


def test_a_theme_switch_and_a_colour_change_share_one_path(qapp, monkeypatch):
    calls = []
    monkeypatch.setattr(fxstyle, "_colors_changed", lambda: calls.append(1))

    fxstyle.apply_theme("light")

    assert calls == [1]
    assert fxstyle.get_theme() == "light"


def test_the_sheet_carries_registered_fragments(qapp):
    fxstyle.register_widget_style("FXProbeWidget { color: @accent_primary; }")
    sheet = fxstyle._build_stylesheet("dark")

    assert "FXProbeWidget" in sheet
    assert "@accent_primary" not in sheet


def test_luminance_reads_any_colour_qt_reads(qapp):
    assert fxstyle.get_luminance("white") == 1.0
    assert fxstyle.get_luminance("#FFF") == 1.0
    assert fxstyle.get_luminance("000000") == 0.0
    assert round(fxstyle.get_luminance("#007ACC"), 4) == 0.1828


def test_one_colour_walk_remains(qapp):
    assert not hasattr(fxstyle, "_shift_away")


def test_primary_button_fills_read_in_every_theme(qapp):
    for theme in fxstyle.get_available_themes():
        tokens = fxstyle._token_map(theme)
        for fill, ink in (
            ("@primary_button", "@text_on_accent_primary"),
            ("@primary_button_hover", "@text_on_accent_secondary"),
            ("@primary_button_pressed", "@text_on_accent_primary"),
        ):
            ratio = fxstyle.get_contrast_ratio(tokens[fill], tokens[ink])
            assert ratio >= 4.5, (theme, fill)
        assert tokens["@primary_button"] != tokens["@primary_button_hover"]
        assert tokens["@primary_button_pressed"] != tokens["@primary_button"]


def test_unused_icon_and_config_helpers_are_gone():
    for module, name in (
        (fxicons, "convert_icon_to_pixmap"),
        (fxicons, "get_available_libraries"),
        (fxconfig, "get_config_dir"),
        (fxconfig, "get_settings"),
        (fxstyle, "invalidate_standard_icon_map"),
    ):
        assert not hasattr(module, name), name
        assert name not in module.__all__, name


def test_settings_still_round_trip(qapp):
    fxconfig.set_value("probe/key", "value")
    assert fxconfig.get_value("probe/key") == "value"
    assert Path(fxconfig._settings().fileName()).exists()
