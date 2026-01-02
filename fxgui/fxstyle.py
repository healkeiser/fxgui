"""Styling, theming, and color management for `fxgui`.

This module provides comprehensive styling functionality including:
    - Multiple theme support with dynamic theme switching
    - Theme persistence across application restarts (via fxconfig)
    - QSS stylesheet loading with dynamic color replacement
    - Custom QProxyStyle for standard icon overrides
    - Theme toggling with icon cache invalidation
    - Color loading from JSONC configuration files

Classes:
    FXProxyStyle: Custom style providing Material Design icons for Qt standard icons.

Functions:
    load_stylesheet: Load and customize QSS stylesheets.
    get_colors: Get the cached color configuration.
    set_color_file: Set a custom color configuration file.
    apply_theme: Apply a theme to a widget (stylesheet + icons).
    get_available_themes: Get list of available theme names.
    get_theme: Get the current theme name.
    get_theme_colors: Get the color palette for the current theme.
    save_theme: Save the current theme to persistent storage.
    load_saved_theme: Load the previously saved theme.

Constants:
    STYLE_FILE: Path to the default QSS stylesheet.
    DEFAULT_COLOR_FILE: Path to the default color configuration.

Examples:
    Loading a stylesheet with a theme:

    >>> from fxgui import fxstyle
    >>> stylesheet = fxstyle.load_stylesheet(theme="dracula")
    >>> widget.setStyleSheet(stylesheet)

    Applying a theme to a window:

    >>> fxstyle.apply_theme(window, "one_dark_pro")

    Theme persistence (automatic):
    Themes are automatically saved when using `apply_theme()`.
    On next application startup, the saved theme is automatically loaded.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### Imports

# Built-in
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Third-party
from qtpy.QtGui import QColor, QFontDatabase, QIcon
from qtpy.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleFactory,
    QStyleOption,
    QWidget,
)

# Internal
from fxgui import fxconfig, fxicons


###### Public API

__all__ = [
    # Classes
    "FXProxyStyle",
    # Constants
    "STYLE_FILE",
    "DEFAULT_COLOR_FILE",
    # Color configuration
    "get_colors",
    "set_color_file",
    "get_accent_colors",
    "get_theme_colors",
    "get_icon_color",
    # Theme functions
    "get_available_themes",
    "get_theme",
    "apply_theme",
    "save_theme",
    "load_saved_theme",
    # Style functions
    "set_style",
    # Stylesheet functions
    "load_stylesheet",
    "replace_colors",
    # Utility functions
    "get_luminance",
    "get_contrast_text_color",
    "invalidate_standard_icon_map",
]


###### Constants

_parent_directory = Path(__file__).parent
STYLE_FILE = _parent_directory / "qss" / "style.qss"
DEFAULT_COLOR_FILE = _parent_directory / "style.jsonc"

# Theme persistence keys
_SETTINGS_THEME_KEY = "theme/current"
_DEFAULT_THEME = "dark"


###### Globals

_colors = None
_color_file = None  # Tracks which color file is currently loaded
_theme = None  # Will be loaded from settings on first access
_standard_icon_map = None  # Lazy-loaded icon map cache

# Pre-compiled regex pattern for JSONC comment removal
_COMMENT_PATTERN = re.compile(
    r"(\"(?:\\\"|.)*?\"|'.*?'|//.*?$|/\*.*?\*/)",
    flags=re.DOTALL | re.MULTILINE,
)


###### Private Helper Functions


def _remove_comments(text: str) -> str:
    """Remove single-line and multi-line comments from the input text.

    Args:
        text: The input text containing comments.

    Returns:
        The input text with comments removed.
    """
    return _COMMENT_PATTERN.sub(
        lambda m: "" if m.group(0).startswith("/") else m.group(0),
        text,
    )


def _hex_to_qcolor(hex_color: str) -> QColor:
    """Convert a hex color string to a QColor.

    Args:
        hex_color: Hex color string (e.g., "#353535").

    Returns:
        The corresponding QColor object.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return QColor(r, g, b)


def _load_colors_from_jsonc(jsonc_file: str = None) -> dict:
    """Load colors from a JSONC (JSON with comments) file.

    Args:
        jsonc_file: The path to the JSONC file. Defaults to
            `DEFAULT_COLOR_FILE` or the file set via `set_color_file()`.

    Returns:
        A dictionary containing color definitions.
    """
    global _colors, _color_file

    # Use the set color file, or fall back to default
    if jsonc_file is None:
        jsonc_file = _color_file if _color_file else DEFAULT_COLOR_FILE

    # Convert to string for comparison
    jsonc_file_str = str(jsonc_file)

    # Return cached if same file, otherwise reload
    if _colors is not None and _color_file == jsonc_file_str:
        return _colors

    with open(jsonc_file, "r") as f:
        jsonc_content = f.read()
        json_content = _remove_comments(jsonc_content)
        _colors = json.loads(json_content)
        _color_file = jsonc_file_str
        return _colors


###### Color Configuration


def set_color_file(jsonc_file: str) -> None:
    """Set a custom color configuration file.

    This clears the color cache and sets the new file as the active
    color source. The next call to `get_colors()` will load from this file.

    Args:
        jsonc_file: Path to the custom JSONC color configuration file.

    Examples:
        >>> fxstyle.set_color_file("path/to/custom_theme.jsonc")
        >>> colors = fxstyle.get_colors()  # Loads from custom file
    """
    global _colors, _color_file, _standard_icon_map
    _colors = None  # Clear cache to force reload
    _color_file = str(jsonc_file)
    _standard_icon_map = None  # Clear icon cache as colors may have changed


def get_colors() -> dict:
    """Get the cached color configuration dictionary.

    This is the preferred way to access colors throughout the application.
    Colors are loaded once from the JSONC file and cached for subsequent calls.

    Returns:
        The complete color configuration containing 'accent', 'feedback',
        'dcc', and 'themes' sections.

    Examples:
        >>> colors = fxstyle.get_colors()
        >>> primary_accent = colors["accent"]["primary"]
        >>> error_color = colors["feedback"]["error"]["foreground"]
        >>> dark_surface = colors["themes"]["dark"]["surface"]
    """
    return _load_colors_from_jsonc()


def get_accent_colors() -> dict:
    """Get the accent colors for the current theme.

    Returns:
        Dictionary containing 'primary' and 'secondary' accent colors
        from the current theme.

    Examples:
        >>> colors = get_accent_colors()
        >>> primary = colors["primary"]  # "#2196F3" for dark theme
        >>> secondary = colors["secondary"]  # "#1976D2" for dark theme
    """
    theme_colors = get_theme_colors()
    return {
        "primary": theme_colors.get("accent_primary", "#2196F3"),
        "secondary": theme_colors.get("accent_secondary", "#1976D2"),
    }


def get_theme_colors() -> dict:
    """Get the color palette for the current theme.

    Returns:
        Dictionary containing theme-specific colors like surface,
        text, border, etc.

    Examples:
        >>> colors = get_theme_colors()
        >>> bg = colors["surface"]  # "#302f2f" for dark, "#f0f0f0" for light
    """
    colors_dict = get_colors()
    return colors_dict["themes"].get(_theme, colors_dict["themes"]["dark"])


def get_available_themes() -> list:
    """Get a list of all available theme names from the color configuration.

    Returns:
        List of theme names (e.g., ["dark", "light", "custom"]).

    Examples:
        >>> themes = fxstyle.get_available_themes()
        >>> print(themes)  # ['dark', 'light']
    """
    colors_dict = get_colors()
    return list(colors_dict.get("themes", {}).keys())


def get_icon_color() -> str:
    """Get the icon color for the current theme.

    Returns:
        The icon color as a hex string from the current theme's configuration.

    Examples:
        >>> color = fxstyle.get_icon_color()
        >>> print(color)  # "#b4b4b4" for dark, "#424242" for light
    """
    theme_colors = get_theme_colors()
    return theme_colors.get("icon", "#b4b4b4")


###### Color Utility Functions


def get_luminance(hex_color: str) -> float:
    """Calculate the relative luminance of a color.

    Uses the WCAG 2.0 formula for relative luminance.

    Args:
        hex_color: A hex color string (e.g., "#007ACC" or "007ACC").

    Returns:
        The relative luminance value between 0 (black) and 1 (white).
    """
    # Remove # if present
    hex_color = hex_color.lstrip("#")

    # Handle shorthand hex (e.g., "FFF" -> "FFFFFF")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)

    # Parse RGB values
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    # Apply gamma correction
    def gamma(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * gamma(r) + 0.7152 * gamma(g) + 0.0722 * gamma(b)


def get_contrast_text_color(background_hex: str) -> str:
    """Determine whether to use white or black text on a given background.

    Uses WCAG luminance calculation to ensure readable contrast.

    Args:
        background_hex: The background color as a hex string.

    Returns:
        "#FFFFFF" for dark backgrounds, "#000000" for light backgrounds.
    """
    luminance = get_luminance(background_hex)
    # Use white text on dark backgrounds, black on light
    return "#FFFFFF" if luminance < 0.5 else "#000000"


###### Theme Functions


def save_theme(theme: str) -> None:
    """Save the current theme to persistent storage.

    Args:
        theme: The theme name to save.

    Examples:
        >>> fxstyle.save_theme("dracula")
    """
    fxconfig.set_value(_SETTINGS_THEME_KEY, theme)


def load_saved_theme() -> str:
    """Load the saved theme from persistent storage.

    If no theme has been saved, returns the default theme ("dark").

    Returns:
        The saved theme name, or "dark" if none is saved.

    Examples:
        >>> theme = fxstyle.load_saved_theme()
        >>> print(theme)  # "dracula" if previously saved
    """
    saved_theme = fxconfig.get_value(_SETTINGS_THEME_KEY, _DEFAULT_THEME)

    # Validate the saved theme exists
    # We need to load colors first to get available themes
    colors = _load_colors_from_jsonc()
    available_themes = list(colors.get("themes", {}).keys())

    if saved_theme in available_themes:
        return saved_theme
    return _DEFAULT_THEME


def _ensure_theme_loaded() -> None:
    """Ensure the theme is loaded from settings on first access.

    This is called internally to lazily initialize the theme from
    persistent storage.
    """
    global _theme
    if _theme is None:
        _theme = load_saved_theme()


def get_theme() -> str:
    """Get the current theme name.

    On first access, the theme is loaded from persistent storage.
    If no theme was previously saved, defaults to "dark".

    Returns:
        The current theme name (e.g., "dark", "light").
    """
    _ensure_theme_loaded()
    return _theme


def apply_theme(
    widget: QWidget,
    theme: str,
) -> str:
    """Apply a theme to the widget with full style updates.

    This function handles all necessary state updates including:
    - Switching the stylesheet
    - Updating icon colors
    - Invalidating icon caches

    Args:
        widget: The QWidget subclass to apply the theme to.
        theme: The theme name to apply (e.g., "dark", "light", or custom).

    Returns:
        The theme that was applied.

    Examples:
        Apply a specific theme:

        >>> fxstyle.apply_theme(window, "dark")
        >>> fxstyle.apply_theme(window, "light")
        >>> fxstyle.apply_theme(window, "dracula")
    """
    global _theme

    # Validate theme exists
    available_themes = get_available_themes()
    if theme not in available_themes:
        raise ValueError(
            f"Theme '{theme}' not found. Available themes: {available_themes}"
        )

    # Update global theme state first (so get_theme_colors returns correct theme)
    _theme = theme

    # Save the theme to persistent storage
    save_theme(theme)

    # Sync icon colors with the new theme (clears cache automatically)
    fxicons.sync_colors_with_theme()

    # Invalidate the standard icon map
    invalidate_standard_icon_map()

    # Apply the new stylesheet
    widget.setStyleSheet(load_stylesheet(theme=theme))

    return theme


def invalidate_standard_icon_map() -> None:
    """Invalidate the cached standard icon map.

    This should be called when changing themes so icons are regenerated
    with the new color scheme on next access.
    """
    global _standard_icon_map
    _standard_icon_map = None


def set_style(widget: QWidget, style: str = None) -> "FXProxyStyle":
    """Set the style.

    Args:
        widget: The QWidget subclass to set the style to.
        style: The style to set. Defaults to None.

    Returns:
        The custom style.

    Note:
        You can retrieve the styles available on your system with
        `QStyleFactory.keys()`. Only those string values are accepted
        in the `style` argument.
    """
    if style is not None:
        style = QStyleFactory.create(style)

    custom_style = FXProxyStyle(style)
    widget.setStyle(custom_style)
    return custom_style


###### Style Classes


def _get_standard_icon_map() -> dict:
    """Get the standard icon map, creating it lazily on first access.

    Returns:
        Mapping of QStyle.StandardPixmap to QIcon.
    """
    global _standard_icon_map
    if _standard_icon_map is not None:
        return _standard_icon_map

    colors_dict = get_colors()

    # fmt: off
    _standard_icon_map = {
        QStyle.SP_ArrowBack: fxicons.get_icon("arrow_back"),
        QStyle.SP_ArrowDown: fxicons.get_icon("arrow_downward"),
        QStyle.SP_ArrowForward: fxicons.get_icon("arrow_forward"),
        QStyle.SP_ArrowLeft: fxicons.get_icon("arrow_left"),
        QStyle.SP_ArrowRight: fxicons.get_icon("arrow_right"),
        QStyle.SP_ArrowUp: fxicons.get_icon("arrow_upward"),
        QStyle.SP_BrowserReload: fxicons.get_icon("refresh"),
        QStyle.SP_BrowserStop: fxicons.get_icon("block"),
        QStyle.SP_CommandLink: fxicons.get_icon("arrow_forward"),
        QStyle.SP_ComputerIcon: fxicons.get_icon("desktop_windows"),
        QStyle.SP_CustomBase: fxicons.get_icon("tune"),
        QStyle.SP_DesktopIcon: fxicons.get_icon("desktop_mac"),
        QStyle.SP_DialogAbortButton: fxicons.get_icon("cancel"),
        QStyle.SP_DialogApplyButton: fxicons.get_icon("check"),
        QStyle.SP_DialogCancelButton: fxicons.get_icon("cancel"),
        QStyle.SP_DialogCloseButton: fxicons.get_icon("close"),
        QStyle.SP_DialogDiscardButton: fxicons.get_icon("delete"),
        QStyle.SP_DialogHelpButton: fxicons.get_icon("help"),
        QStyle.SP_DialogIgnoreButton: fxicons.get_icon("notifications_off"),
        QStyle.SP_DialogNoButton: fxicons.get_icon("cancel"),
        QStyle.SP_DialogNoToAllButton: fxicons.get_icon("do_not_disturb"),
        QStyle.SP_DialogOkButton: fxicons.get_icon("check"),
        QStyle.SP_DialogOpenButton: fxicons.get_icon("open_in_new"),
        QStyle.SP_DialogResetButton: fxicons.get_icon("cleaning_services"),
        QStyle.SP_DialogRetryButton: fxicons.get_icon("restart_alt"),
        QStyle.SP_DialogSaveAllButton: fxicons.get_icon("save_all"),
        QStyle.SP_DialogSaveButton: fxicons.get_icon("save"),
        QStyle.SP_DialogYesButton: fxicons.get_icon("check"),
        QStyle.SP_DialogYesToAllButton: fxicons.get_icon("done_all"),
        QStyle.SP_DirClosedIcon: fxicons.get_icon("folder"),
        QStyle.SP_DirHomeIcon: fxicons.get_icon("home"),
        QStyle.SP_DirIcon: fxicons.get_icon("folder_open"),
        QStyle.SP_DirLinkIcon: fxicons.get_icon("link"),
        QStyle.SP_DirLinkOpenIcon: fxicons.get_icon("folder_open"),
        QStyle.SP_DockWidgetCloseButton: fxicons.get_icon("close"),
        QStyle.SP_DirOpenIcon: fxicons.get_icon("folder_open"),
        QStyle.SP_DriveCDIcon: fxicons.get_icon("album"),
        QStyle.SP_DriveDVDIcon: fxicons.get_icon("album"),
        QStyle.SP_DriveFDIcon: fxicons.get_icon("usb"),
        QStyle.SP_DriveHDIcon: fxicons.get_icon("usb"),
        QStyle.SP_DriveNetIcon: fxicons.get_icon("cloud"),
        QStyle.SP_FileDialogBack: fxicons.get_icon("arrow_back"),
        QStyle.SP_FileDialogContentsView: fxicons.get_icon("find_in_page"),
        QStyle.SP_FileDialogDetailedView: fxicons.get_icon("description"),
        QStyle.SP_FileDialogEnd: fxicons.get_icon("check_circle"),
        QStyle.SP_FileDialogInfoView: fxicons.get_icon("info"),
        QStyle.SP_FileDialogListView: fxicons.get_icon("view_list"),
        QStyle.SP_FileDialogNewFolder: fxicons.get_icon("create_new_folder"),
        QStyle.SP_FileDialogStart: fxicons.get_icon("insert_drive_file"),
        QStyle.SP_FileDialogToParent: fxicons.get_icon("file_upload"),
        QStyle.SP_FileIcon: fxicons.get_icon("insert_drive_file"),
        QStyle.SP_FileLinkIcon: fxicons.get_icon("link"),
        QStyle.SP_LineEditClearButton: fxicons.get_icon("close"),
        QStyle.SP_MediaPause: fxicons.get_icon("pause"),
        QStyle.SP_MediaPlay: fxicons.get_icon("play_arrow"),
        QStyle.SP_MediaSeekBackward: fxicons.get_icon("fast_rewind"),
        QStyle.SP_MediaSeekForward: fxicons.get_icon("fast_forward"),
        QStyle.SP_MediaSkipBackward: fxicons.get_icon("skip_previous"),
        QStyle.SP_MediaSkipForward: fxicons.get_icon("skip_next"),
        QStyle.SP_MediaStop: fxicons.get_icon("stop"),
        QStyle.SP_MediaVolume: fxicons.get_icon("volume_up"),
        QStyle.SP_MediaVolumeMuted: fxicons.get_icon("volume_off"),
        QStyle.SP_MessageBoxCritical: fxicons.get_icon("error", color=colors_dict["feedback"]["error"]["foreground"]),
        QStyle.SP_MessageBoxInformation: fxicons.get_icon("info", color=colors_dict["feedback"]["info"]["foreground"]),
        QStyle.SP_MessageBoxQuestion: fxicons.get_icon("help", color=colors_dict["feedback"]["success"]["foreground"]),
        QStyle.SP_MessageBoxWarning: fxicons.get_icon("warning", color=colors_dict["feedback"]["warning"]["foreground"]),
        QStyle.SP_RestoreDefaultsButton: fxicons.get_icon("restore"),
        QStyle.SP_TitleBarCloseButton: fxicons.get_icon("close"),
        QStyle.SP_TitleBarContextHelpButton: fxicons.get_icon("help"),
        QStyle.SP_TitleBarMaxButton: fxicons.get_icon("maximize"),
        QStyle.SP_TitleBarMenuButton: fxicons.get_icon("menu"),
        QStyle.SP_TitleBarMinButton: fxicons.get_icon("minimize"),
        QStyle.SP_TitleBarNormalButton: fxicons.get_icon("restore"),
        QStyle.SP_TitleBarShadeButton: fxicons.get_icon("arrow_drop_down"),
        QStyle.SP_TitleBarUnshadeButton: fxicons.get_icon("arrow_drop_up"),
        QStyle.SP_ToolBarHorizontalExtensionButton: fxicons.get_icon("arrow_right"),
        QStyle.SP_ToolBarVerticalExtensionButton: fxicons.get_icon("arrow_downward"),
        QStyle.SP_TrashIcon: fxicons.get_icon("delete"),
        QStyle.SP_VistaShield: fxicons.get_icon("security"),
    }
    # fmt: on
    return _standard_icon_map


class FXProxyStyle(QProxyStyle):
    """A custom style class that extends QProxyStyle to provide custom icons."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get icon color from theme configuration
        theme_colors = get_theme_colors()
        self.icon_color = theme_colors.get("icon", "#b4b4b4")

    def standardIcon(
        self,
        standardIcon: QStyle.StandardPixmap,
        option: Optional[QStyleOption] = None,
        widget: Optional[QWidget] = None,
    ) -> QIcon:
        """Return an icon for the given standardIcon.

        Args:
            standardIcon: The standard pixmap for which an icon should
                be returned.
            option: An option that can be used to fine-tune the look of
                the icon. Defaults to None.
            widget: The widget for which the icon is being requested.
                Defaults to None.

        Returns:
            The icon for the standardIcon. If no custom icon is found,
            the default icon is returned.
        """
        icon = _get_standard_icon_map().get(standardIcon)
        if icon is not None:
            return icon
        return super().standardIcon(standardIcon, option, widget)

    def set_icon_color(self, color: str):
        """Set the color of the icons.

        Args:
            color: The color to set the icons to.
        """
        self.icon_color = color
        self.update()


###### Stylesheet Functions


def replace_colors(
    stylesheet: str,
    colors_dict: dict = None,
    prefix: str = "",
) -> str:
    """Replace color placeholders in a stylesheet with actual color values.

    This function searches for placeholders in the format `@{prefix}{key}`
    and replaces them with the corresponding color values from the dictionary.

    Args:
        stylesheet: The stylesheet string containing color placeholders.
        colors_dict: Dictionary containing color definitions. Only top-level
            non-dict values are used. Defaults to colors from get_colors().
        prefix: Prefix for placeholder names. Defaults to empty string.

    Returns:
        The stylesheet with all matching placeholders replaced.

    Examples:
        >>> colors = {"primary": "#FF5722", "secondary": "#E64A19"}
        >>> qss = "color: @primary; background: @secondary;"
        >>> result = replace_colors(qss, colors)
        >>> print(result)
        'color: #FF5722; background: #E64A19;'
    """
    if colors_dict is None:
        colors_dict = get_colors()

    placeholders = {
        f"@{prefix}{key}": value
        for key, value in colors_dict.items()
        if not isinstance(value, dict)
    }
    for placeholder, color in placeholders.items():
        stylesheet = stylesheet.replace(placeholder, color)
    return stylesheet


def load_stylesheet(
    style_file: str = STYLE_FILE,
    extra: Optional[str] = None,
    theme: str = None,
) -> str:
    """Load the stylesheet and replace placeholders with actual values.

    Args:
        style_file: The path to the QSS file. Defaults to `STYLE_FILE`.
        extra: Extra stylesheet content to append. Defaults to None.
        theme: The theme to use (e.g., "dark", "light", "dracula").
            If None, uses the saved theme from persistent storage.

    Returns:
        The stylesheet with all placeholders replaced.
    """
    global _theme

    if not os.path.exists(style_file):
        return "None"

    # If no theme specified, use the saved theme
    if theme is None:
        theme = load_saved_theme()

    # Update the global theme state to keep it in sync
    _theme = theme

    # Load colors from JSON
    colors_dict = get_colors()

    # Get theme-specific colors from JSON
    theme_data = colors_dict["themes"].get(theme, colors_dict["themes"]["dark"])

    # Get accent colors from the theme
    accent_primary = theme_data.get("accent_primary", "#2196F3")
    accent_secondary = theme_data.get("accent_secondary", "#1976D2")

    with open(style_file, "r") as in_file:
        stylesheet = in_file.read()

    # Ensure font compatibility on multiple platforms
    if sys.platform == "win32":
        default_font = "Segoe UI"
    else:
        default_font = QFontDatabase.systemFont(
            QFontDatabase.GeneralFont
        ).family()
    font_stylesheet = f"""* {{
        font-family: "{default_font}";
    }}
    """

    # Determine which icon folder to use based on theme surface luminance
    # This allows custom themes to automatically get the right icon set
    surface_color = theme_data.get("surface", "#302f2f")
    surface_luminance = get_luminance(surface_color)
    icon_folder = (
        "stylesheet_dark" if surface_luminance < 0.5 else "stylesheet_light"
    )

    # Calculate appropriate text color for accent backgrounds based on contrast
    text_on_accent = get_contrast_text_color(accent_primary)

    # Build replacement map for all placeholders
    replace = {
        # Accent colors
        "@accent_primary": accent_primary,
        "@accent_secondary": accent_secondary,
        "@text_on_accent": text_on_accent,
        # Icon path
        "~icons": str(_parent_directory / "icons" / icon_folder).replace(
            os.sep, "/"
        ),
        # Theme colors
        "@surface": theme_data.get("surface", "#302f2f"),
        "@surface_alt": theme_data.get("surface_alt", "#2d2c2c"),
        "@input": theme_data.get("input", "#201f1f"),
        "@border": theme_data.get("border", "#3a3939"),
        "@border_subtle": theme_data.get("border_subtle", "#4a4949"),
        "@border_frame": theme_data.get("border_frame", "#444444"),
        "@text": theme_data.get("text", "#bbbbbb"),
        "@text_secondary": theme_data.get("text_secondary", "#b1b1b1"),
        "@text_disabled": theme_data.get("text_disabled", "#777777"),
        "@hover": theme_data.get("hover", "#403f3f"),
        "@pressed": theme_data.get("pressed", "#4a4949"),
        "@selected": theme_data.get("selected", "#5a5959"),
        "@disabled": theme_data.get("disabled", "#404040"),
        "@scrollbar_bg": theme_data.get("scrollbar_bg", "#2a2929"),
        "@scrollbar_handle": theme_data.get("scrollbar_handle", "#605f5f"),
        "@scrollbar_hover": theme_data.get("scrollbar_hover", "#727272"),
        "@separator": theme_data.get("separator", "#787876"),
        "@slider_handle": theme_data.get("slider_handle", "#bbbbbb"),
        "@slider_hover": theme_data.get("slider_hover", "#ffffff"),
    }

    # Sort by key length descending to avoid partial replacements
    # (e.g., @border before @border_subtle)
    for key in sorted(replace.keys(), key=len, reverse=True):
        stylesheet = stylesheet.replace(key, replace[key])

    stylesheet = (
        font_stylesheet + stylesheet + extra
        if extra
        else font_stylesheet + stylesheet
    )

    stylesheet = stylesheet + extra if extra else stylesheet

    return stylesheet
