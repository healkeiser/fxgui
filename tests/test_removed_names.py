"""Every name 13.0.0 removed stays gone: one public name per job."""

# Built-in
import importlib
import importlib.util
import inspect

# Third-party
import pytest

_GONE = {
    "fxgui._compat": ("later", "rehome", "focus_step"),
    "fxgui.fxconfig": (
        "get_application_name", "SETTINGS_FILE", "CONFIG_DIR",
        "get_config_dir", "get_settings",
    ),
    "fxgui.fxicons": (
        "convert_icon_to_pixmap", "get_available_libraries",
        "set_default_icon_library", "set_icon_defaults",
        "get_available_icons_in_library", "get_icon_color",
        "superpose_icons", "change_pixmap_color", "has_transparency",
        "sync_colors_with_theme", "refresh_all_icons", "_icon_widgets",
        "_theme_ink",
    ),
    "fxgui.fxstyle": (
        "FXThemeAware", "invalidate_standard_icon_map", "theme_manager",
        "FXThemeManager", "get_theme_colors", "get_accent_colors",
        "get_icon_color", "get_icon_on_accent_primary",
        "get_icon_on_accent_secondary", "replace_colors", "load_stylesheet",
        "build_stylesheet", "set_widget_style", "WIDGET_STYLE_PROPERTY",
        "get_contrast_text_color", "_FORCE_UPDATE_WALK",
        "get_feedback_colors", "get_fonts", "get_font_family",
    ),
    "fxgui.fxstyle:FXProxyStyle": ("set_icon_color", "icon_color"),
    "fxgui.fxutils": (
        "deprecated", "set_formatted_tooltip", "get_formatted_time",
        "add_shadows",
    ),
    "fxgui.fxwidgets": (
        "FXThemeAware", "FXAccordionSection", "FXWidget",
        "FXColorLabelDelegate", "FXFuzzySearchTree", "FXFuzzySearchList",
    ),
    "fxgui.fxwidgets:FXCollapsibleWidget": (
        "header_widget", "content_area", "toggle_button", "title_label",
        "title_icon_label", "set_title_icon", "get_title_icon", "NO_CAP",
    ),
    "fxgui.fxwidgets:FXThumbnailDelegate": (
        "TRANSPARENT_SELECTION_STYLE", "markdown_to_plain_text",
        "show_child_count", "show_starred", "STARRED_ROLE",
        "STARRED_COLOR_ROLE", "STATUS_LABEL_ICON_ROLE",
        "_get_column_position", "_as_color",
    ),
    "fxgui.fxwidgets:FXMainWindow": (
        "_move_window", "_refresh_dialog_button_icons", "_add_shadows",
        "_live_menu_bar", "_create_banner",
    ),
    "fxgui.fxwidgets._code_block": ("get_supported_languages",),
    "fxgui.fxwidgets._delegates": ("_find_cached",),
}


def _owner(path: str):
    module, _, attribute = path.partition(":")
    owner = importlib.import_module(module)
    return getattr(owner, attribute) if attribute else owner


@pytest.mark.parametrize(
    ("path", "name"),
    [(path, name) for path, names in _GONE.items() for name in names],
)
def test_a_removed_name_is_gone(path, name):
    owner = _owner(path)
    assert not hasattr(owner, name)
    assert name not in getattr(owner, "__all__", ())


def test_the_removed_modules_and_overrides_are_gone(qapp):
    from fxgui import fxstyle
    from fxgui.fxwidgets import FXMainWindow, _validators

    assert importlib.util.find_spec("fxgui.fxdcc") is None
    assert not hasattr(fxstyle.FXProxyStyle(), "icon_color")
    assert "closeEvent" not in FXMainWindow.__dict__
    assert "setRegExp" not in inspect.getsource(_validators)
