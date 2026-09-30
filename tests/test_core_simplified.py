"""Tests pinning the behaviour the core modules keep after simplification."""

# Built-in
import inspect

# Internal
from fxgui import fxconfig, fxicons, fxstyle


def test_the_theme_manager_is_a_plain_signal_holder(qapp):
    received = []
    fxstyle.theme_changed.connect(received.append)
    try:
        fxstyle.theme_manager.notify_theme_changed("light")
    finally:
        fxstyle.theme_changed.disconnect(received.append)

    assert received == ["light"]
    assert fxstyle.theme_changed is fxstyle.theme_manager.theme_changed
    for name in ("_instance", "_initialized", "current_theme"):
        assert not hasattr(fxstyle.FXThemeManager, name), name


def test_a_theme_switch_and_a_colour_change_share_one_path(qapp, monkeypatch):
    calls = []
    monkeypatch.setattr(fxstyle, "_colors_changed", lambda: calls.append(1))

    fxstyle.apply_theme("light")

    assert calls == [1]
    assert fxstyle.get_theme() == "light"


def test_load_stylesheet_carries_registered_fragments(qapp):
    fxstyle.register_widget_style("FXProbeWidget { color: @accent_primary; }")
    sheet = fxstyle.load_stylesheet(theme="dark")

    assert "FXProbeWidget" in sheet
    assert sheet == fxstyle.build_stylesheet("dark")


def test_replace_colors_takes_no_prefix():
    assert "prefix" not in inspect.signature(fxstyle.replace_colors).parameters


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


def test_accent_getters_read_the_cache(qapp):
    colors = fxstyle.colors()
    assert fxstyle.get_accent_colors() == {
        "primary": colors.accent_primary,
        "secondary": colors.accent_secondary,
    }
    assert fxstyle.get_icon_color() == colors.icon
    assert fxstyle.get_icon_on_accent_primary() == colors.icon_on_accent_primary


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
    assert fxconfig.SETTINGS_FILE.exists()
