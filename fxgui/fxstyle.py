"""Styling, theming, and color management for `fxgui`.

This module provides comprehensive styling functionality including:
    - Multiple theme support with dynamic theme switching
    - Theme persistence across application restarts (via fxconfig)
    - QSS stylesheet loading with dynamic color replacement
    - Custom QProxyStyle for standard icon overrides
    - Theme toggling with icon cache invalidation
    - Color loading from YAML configuration files with inheritance support

Theme Color Reference
---------------------
Each theme in ``style.yaml`` defines these semantic color roles:

**Accent Colors** (interactive highlights):
    - ``accent_primary``: Hover borders, selections, progress gradients (end)
    - ``accent_secondary``: Gradient starts, item hover backgrounds

**Surface Colors** (backgrounds):
    - ``surface``: Main widget/window backgrounds, buttons, selected tabs
    - ``surface_alt``: Alternate row backgrounds in lists/tables
    - ``surface_sunken``: Recessed areas - inputs, lists, menus, status bar
    - ``tooltip``: Tooltip backgrounds

**Border Colors**:
    - ``border``: Standard borders on inputs, containers, menus
    - ``border_light``: Subtle borders - tooltips, buttons, tabs
    - ``border_strong``: Emphasized borders - frames, separators

**Text Colors**:
    - ``text``: Primary text for all widgets
    - ``text_muted``: De-emphasized text - inactive tabs, placeholders
    - ``text_disabled``: Disabled widget text
    - ``text_on_accent_primary``: Text on accent_primary backgrounds (optional, auto-computed)
    - ``text_on_accent_secondary``: Text on accent_secondary backgrounds (optional, auto-computed)

**Interactive States**:
    - ``state_hover``: Hover state backgrounds
    - ``state_pressed``: Pressed/checked/active backgrounds

**Scrollbar**:
    - ``scrollbar_track``: Track/gutter background
    - ``scrollbar_thumb``: Draggable thumb
    - ``scrollbar_thumb_hover``: Thumb hover state

**Layout**:
    - ``grid``: Table gridlines, header borders
    - ``separator``: Separator/splitter hover backgrounds

**Slider**:
    - ``slider_thumb``: Slider handle color
    - ``slider_thumb_hover``: Slider handle hover/pressed

**Icon**:
    - ``icon``: Monochrome icon tint color

Classes:
    FXProxyStyle: Custom style providing Material Design icons for Qt standard icons.
    FXThemeManager: Singleton that emits signals when theme changes.
    FXThemeAware: Mixin for widgets that auto-update on theme changes.

Functions:
    load_stylesheet: Load and customize QSS stylesheets.
    get_colors: Get the cached color configuration.
    set_color_file: Set a custom color configuration file.
    apply_theme: Apply a theme to a widget (stylesheet + icons).
    get_available_themes: Get list of available theme names.
    get_theme: Get the current theme name.
    get_theme_colors: Get the color palette for the current theme.
    get_accent_colors: Get primary/secondary accent colors.
    get_icon_color: Get the icon tint color for current theme.
    is_light_theme: Check if the current theme is light or dark.
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

    Getting colors for custom widgets:

    >>> colors = fxstyle.get_theme_colors()
    >>> surface = colors["surface"]  # Main background
    >>> sunken = colors["surface_sunken"]  # Input/list backgrounds
    >>> text = colors["text"]  # Primary text color

    Theme persistence (automatic):
    Themes are automatically saved when using `apply_theme()`.
    On next application startup, the saved theme is automatically loaded.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### Imports

# Built-in
import os
import sys
from pathlib import Path
from typing import Optional

# Third-party
import yaml
from qtpy.QtCore import QObject, QTimer, Signal
from qtpy.QtGui import QFontDatabase, QIcon
from qtpy.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleFactory,
    QStyleOption,
    QWidget,
)

# Internal
from fxgui import fxconfig, fxicons


###### Theme Management


class FXThemeColors:
    """Namespace for accessing theme colors with dot notation.

    This class provides a convenient way to access theme colors using
    attribute access instead of dictionary lookup.

    Examples:
        >>> colors = FXThemeColors(fxstyle.get_theme_colors())
        >>> colors.surface  # "#302f2f"
        >>> colors.accent_primary  # "#2196F3"
    """

    def __init__(self, colors_dict: dict):
        """Initialize with a colors dictionary.

        Args:
            colors_dict: Dictionary of color name to hex value mappings.
        """
        for key, value in colors_dict.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"FXThemeColors({attrs})"


class FXThemeManager(QObject):
    """Singleton that emits theme_changed(str) when the theme changes."""

    theme_changed = Signal(str)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._current_theme: str = ""

    def notify_theme_changed(self, theme_name: str) -> None:
        """Called by apply_theme() when theme changes."""
        self._current_theme = theme_name
        self.theme_changed.emit(theme_name)

    @property
    def current_theme(self) -> str:
        """Return the current theme name."""
        return self._current_theme


# Global singleton instance
theme_manager = FXThemeManager()


class FXThemeAware:
    """Mixin that makes widgets automatically respond to theme changes.

    This mixin provides automatic theme updates for custom widgets. When the
    theme changes, connected widgets are notified and can update their appearance.

    Usage:
        1. Inherit from FXThemeAware **FIRST**: `class MyWidget(FXThemeAware, QWidget)`
        2. Override `_on_theme_changed()` to apply custom colors (optional)
        3. Use `self.theme` property to access current theme colors
        4. Optionally declare a `theme_style` class attribute for automatic QSS

    Examples:
        New API (recommended):
        >>> from fxgui import fxstyle
        >>> class FXMyWidget(FXThemeAware, QWidget):
        ...     # Option 1: Declarative QSS with color tokens
        ...     theme_style = '''
        ...         FXMyWidget {
        ...             background: @surface;
        ...             border: 1px solid @border;
        ...         }
        ...     '''
        ...
        ...     # Option 2: Programmatic colors in paintEvent
        ...     def paintEvent(self, event):
        ...         painter = QPainter(self)
        ...         painter.fillRect(self.rect(), QColor(self.theme.surface))

        Legacy API (deprecated, still works):
        >>> class FXMyWidget(FXThemeAware, QWidget):
        ...     def _apply_theme_styles(self):
        ...         colors = fxstyle.get_theme_colors()
        ...         self.setStyleSheet(f"background: {colors['surface']};")

    Attributes:
        theme: Property returning current theme colors as a FXThemeColors object.
        theme_style: Optional class attribute with QSS containing @color tokens.
    """

    # Class attribute for declarative QSS styling (optional)
    theme_style: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        theme_manager.theme_changed.connect(self.__handle_theme_change)
        # Auto-apply theme after widget is fully initialized
        QTimer.singleShot(0, self.__handle_theme_change)

    @property
    def theme(self) -> FXThemeColors:
        """Get current theme colors as a namespace object.

        Returns:
            FXThemeColors object with color attributes (e.g., theme.surface,
            theme.accent_primary, theme.text).

        Examples:
            >>> def paintEvent(self, event):
            ...     painter = QPainter(self)
            ...     painter.fillRect(self.rect(), QColor(self.theme.surface))
            ...     painter.setPen(QColor(self.theme.text))
        """
        return FXThemeColors(get_theme_colors())

    def __handle_theme_change(self, _theme_name: str = None) -> None:
        """Internal handler for theme changes."""
        # Check if the C++ object is still valid (prevents RuntimeError)
        from qtpy.shiboken import isValid as is_valid

        if not is_valid(self):
            return

        # Process theme_style class attribute if defined
        if self.theme_style:
            self.__apply_theme_style_attribute()

        # Call the override point for custom logic
        self._on_theme_changed()

        # Always trigger repaint
        if hasattr(self, "update"):
            self.update()

    def __apply_theme_style_attribute(self) -> None:
        """Process the theme_style class attribute and apply it."""
        if not self.theme_style:
            return

        stylesheet = self.theme_style
        colors = get_theme_colors()

        # Replace @tokens with actual colors
        for key, value in colors.items():
            stylesheet = stylesheet.replace(f"@{key}", value)

        if hasattr(self, "setStyleSheet"):
            self.setStyleSheet(stylesheet)

    def _on_theme_changed(self) -> None:
        """Override this to apply custom theme styling.

        Called automatically when the theme changes. Use this for:
        - Updating child widget styles
        - Refreshing cached colors
        - Any custom theme-dependent logic

        Note:
            You don't need to call `self.update()` - it's called automatically
            after this method returns.

        Examples:
            >>> def _on_theme_changed(self):
            ...     # Update a child widget that isn't theme-aware
            ...     self.custom_label.setStyleSheet(
            ...         f"color: {self.theme.text};"
            ...     )
        """
        # Check if subclass overrides the deprecated _apply_theme_styles
        # If so, call it for backward compatibility
        if (
            self.__class__._apply_theme_styles
            is not FXThemeAware._apply_theme_styles
        ):
            import warnings

            warnings.warn(
                f"{self.__class__.__name__}._apply_theme_styles() is deprecated. "
                "Override _on_theme_changed() instead, or use the theme_style "
                "class attribute for declarative QSS.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._apply_theme_styles()

    def _apply_theme_styles(self) -> None:
        """Deprecated: Override _on_theme_changed() instead.

        .. deprecated::
            This method is deprecated. Use `_on_theme_changed()` for custom
            logic or the `theme_style` class attribute for declarative QSS.
        """
        pass

    # Deprecated methods kept for backward compatibility
    def _safe_apply_theme_styles(self) -> None:
        """Deprecated: No longer needed, theme changes are handled automatically.

        .. deprecated::
            This internal method is no longer used. Override `_on_theme_changed()`
            for custom theme logic.
        """
        import warnings

        warnings.warn(
            "_safe_apply_theme_styles() is deprecated and no longer used. "
            "Override _on_theme_changed() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._apply_theme_styles()


###### Public API

__all__ = [
    # Classes
    "FXProxyStyle",
    "FXThemeManager",
    "FXThemeAware",
    "FXThemeColors",
    # Singleton
    "theme_manager",
    # Constants
    "STYLE_FILE",
    "DEFAULT_COLOR_FILE",
    # Color configuration
    "get_colors",
    "set_color_file",
    "get_accent_colors",
    "get_feedback_colors",
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
DEFAULT_COLOR_FILE = _parent_directory / "style.yaml"

# Theme persistence keys
_SETTINGS_THEME_KEY = "theme/current"
_DEFAULT_THEME = "dark"


###### Globals

_colors = None
_color_file = None  # Tracks which color file is currently loaded
_theme = None  # Will be loaded from settings on first access
_standard_icon_map = None  # Lazy-loaded icon map cache


###### Private Helper Functions


def _load_colors_from_yaml(yaml_file: str = None) -> dict:
    """Load colors from a YAML configuration file.

    YAML supports anchors and aliases for theme inheritance, allowing
    themes to extend base themes and override specific colors.

    Args:
        yaml_file: The path to the YAML file. Defaults to
            `DEFAULT_COLOR_FILE` or the file set via `set_color_file()`.

    Returns:
        A dictionary containing color definitions.
    """
    global _colors, _color_file

    # Use the set color file, or fall back to default
    if yaml_file is None:
        yaml_file = _color_file if _color_file else DEFAULT_COLOR_FILE

    # Convert to string for comparison
    yaml_file_str = str(yaml_file)

    # Return cached if same file, otherwise reload
    if _colors is not None and _color_file == yaml_file_str:
        return _colors

    with open(yaml_file, "r", encoding="utf-8") as f:
        _colors = yaml.safe_load(f)
        _color_file = yaml_file_str
        return _colors


###### Color Configuration


def set_color_file(color_file: str) -> None:
    """Set a custom color configuration file.

    This clears the color cache and sets the new file as the active
    color source. The next call to `get_colors()` will load from this file.

    Supports both YAML (.yaml, .yml) files with inheritance via anchors.

    Args:
        color_file: Path to the custom YAML color configuration file.

    Examples:
        >>> fxstyle.set_color_file("path/to/custom_theme.yaml")
        >>> colors = fxstyle.get_colors()  # Loads from custom file
    """
    global _colors, _color_file, _standard_icon_map
    _colors = None  # Clear cache to force reload
    _color_file = str(color_file)
    _standard_icon_map = None  # Clear icon cache as colors may have changed


def get_colors() -> dict:
    """Get the cached color configuration dictionary.

    This is the preferred way to access colors throughout the application.
    Colors are loaded once from the YAML file and cached for subsequent calls.

    Returns:
        The complete color configuration containing 'feedback', 'dcc', and
        'themes' sections.

    Examples:
        >>> colors = fxstyle.get_colors()
        >>> error_color = colors["feedback"]["error"]["foreground"]
        >>> dark_surface = colors["themes"]["dark"]["surface"]
    """
    return _load_colors_from_yaml()


def get_accent_colors() -> dict:
    """Get the accent colors for the current theme.

    Accent colors are used for interactive elements:

    - **primary**: Hover borders on input widgets (QLineEdit, QComboBox, etc.),
      selection backgrounds, progress bar/slider gradients (end color),
      menu bar selections, pressed/selected items in item views.

    - **secondary**: Progress bar/slider gradients (start color),
      widget item hover backgrounds, menu pressed backgrounds,
      list/tree item hover highlights.

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


def get_feedback_colors() -> dict:
    """Get the feedback/status colors for notifications and logging.

    These colors are used by ``FXNotificationBanner``, ``FXLogWidget``,
    and other status/feedback widgets.

    Each level provides both a ``foreground`` (text/icon) and ``background``
    color designed to work together with appropriate contrast.

    The function first checks for theme-specific feedback colors (defined
    within the current theme), then falls back to the global feedback colors
    for backward compatibility.

    Returns:
        Dictionary with keys: 'debug', 'info', 'success', 'warning', 'error'.
        Each value is a dict with 'foreground' and 'background' keys.

    Examples:
        >>> colors = fxstyle.get_feedback_colors()
        >>> colors["error"]["foreground"]  # "#ff4444"
        >>> colors["error"]["background"]  # "#7b2323"
        >>> colors["success"]["foreground"]  # "#8ac549"
    """
    # Default fallback colors
    default_feedback = {
        "debug": {"foreground": "#26C6DA", "background": "#006064"},
        "info": {"foreground": "#7661f6", "background": "#372d75"},
        "success": {"foreground": "#8ac549", "background": "#466425"},
        "warning": {"foreground": "#ffbb33", "background": "#7b5918"},
        "error": {"foreground": "#ff4444", "background": "#7b2323"},
    }

    # First, try to get theme-specific feedback colors
    theme_colors = get_theme_colors()
    if "feedback" in theme_colors:
        return theme_colors["feedback"]

    # Fall back to global feedback colors for backward compatibility
    colors_dict = get_colors()
    return colors_dict.get("feedback", default_feedback)


def get_theme_colors() -> dict:
    """Get the color palette for the current theme.

    Returns a dictionary with all semantic color roles:

    **Surface Colors (Backgrounds)**:

    - ``surface``: Main widget/window backgrounds, buttons, selected tabs
    - ``surface_alt``: Alternate row backgrounds in lists/tables
    - ``surface_sunken``: Recessed areas - input fields, lists, menus
    - ``tooltip``: Tooltip backgrounds

    **Border Colors**:

    - ``border``: Standard borders on inputs, containers, menus
    - ``border_light``: Subtle borders - tooltips, buttons, tabs
    - ``border_strong``: Emphasized borders - frames, separators

    **Text Colors**:

    - ``text``: Primary text for all widgets
    - ``text_muted``: De-emphasized text - inactive tabs, placeholders
    - ``text_disabled``: Disabled widget text
    - ``text_on_accent_primary``: Text on accent_primary backgrounds (optional)
    - ``text_on_accent_secondary``: Text on accent_secondary backgrounds (optional)

    **Interactive States**:

    - ``state_hover``: Hover state backgrounds
    - ``state_pressed``: Pressed/checked/active backgrounds

    **Scrollbar Colors**:

    - ``scrollbar_track``: Track/gutter background
    - ``scrollbar_thumb``: Draggable thumb
    - ``scrollbar_thumb_hover``: Thumb hover state

    **Layout Colors**:

    - ``grid``: Table gridlines, header borders
    - ``separator``: Separator/splitter hover backgrounds

    **Slider Colors**:

    - ``slider_thumb``: Slider handle color
    - ``slider_thumb_hover``: Slider handle hover/pressed

    **Icon**:

    - ``icon``: Tint color for monochrome icons

    Returns:
        Dictionary containing theme-specific colors.

    Examples:
        >>> colors = get_theme_colors()
        >>> bg = colors["surface"]  # "#302f2f" for dark
        >>> sunken = colors["surface_sunken"]  # Input/list backgrounds
        >>> text = colors["text"]  # Primary text color
    """
    colors_dict = get_colors()
    return colors_dict["themes"].get(_theme, colors_dict["themes"]["dark"])


def get_available_themes() -> list:
    """Get a list of all available theme names from the color configuration.

    Returns:
        List of theme names (e.g., ["dark", "light", "dracula", "one_dark_pro"]).

    Examples:
        >>> themes = fxstyle.get_available_themes()
        >>> print(themes)  # ['dark', 'light', 'dracula', 'one_dark_pro']
    """
    colors_dict = get_colors()
    return list(colors_dict.get("themes", {}).keys())


def get_icon_color() -> str:
    """Get the icon color for the current theme.

    This color is used to tint monochrome SVG icons so they match the theme.
    It's applied by ``fxicons.get_icon()`` and ``FXProxyStyle`` for standard
    Qt icons.

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


def is_light_theme() -> bool:
    """Check if the current theme is a light theme.

    Determines theme brightness by analyzing the surface color's lightness.
    This is more reliable than checking the theme name since it works with
    any custom theme.

    Returns:
        True if the current theme is light, False if dark.

    Examples:
        >>> if fxstyle.is_light_theme():
        ...     use_dark_icons()
        ... else:
        ...     use_light_icons()
    """
    from qtpy.QtGui import QColor

    colors = get_theme_colors()
    surface_color = QColor(colors.get("surface", "#000000"))
    return surface_color.lightness() > 128


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
    colors = _load_colors_from_yaml()
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

    # Notify theme manager so FXThemeAware widgets update
    theme_manager.notify_theme_changed(theme)

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

    # Sync icon colors with the theme (important for startup with saved theme)
    fxicons.sync_colors_with_theme()

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

    # Determine which icon folder to use based on theme brightness
    icon_folder = "stylesheet_light" if is_light_theme() else "stylesheet_dark"

    # Text color for accent backgrounds: use theme value if defined,
    # otherwise compute based on each accent's luminance
    text_on_accent_primary = theme_data.get(
        "text_on_accent_primary", get_contrast_text_color(accent_primary)
    )
    text_on_accent_secondary = theme_data.get(
        "text_on_accent_secondary", get_contrast_text_color(accent_secondary)
    )

    # Build replacement map for all placeholders
    # Uses new semantic naming scheme
    replace = {
        # Accent colors
        "@accent_primary": accent_primary,
        "@accent_secondary": accent_secondary,
        "@text_on_accent_primary": text_on_accent_primary,
        "@text_on_accent_secondary": text_on_accent_secondary,
        # Icon path
        "~icons": str(_parent_directory / "icons" / icon_folder).replace(
            os.sep, "/"
        ),
        # Surface colors
        "@surface": theme_data.get("surface", "#302f2f"),
        "@surface_alt": theme_data.get("surface_alt", "#2d2c2c"),
        "@surface_sunken": theme_data.get("surface_sunken", "#201f1f"),
        "@tooltip": theme_data.get("tooltip", "#202020"),
        # Border colors
        "@border": theme_data.get("border", "#3a3939"),
        "@border_light": theme_data.get("border_light", "#4a4949"),
        "@border_strong": theme_data.get("border_strong", "#444444"),
        # Text colors
        "@text": theme_data.get("text", "#bbbbbb"),
        "@text_muted": theme_data.get("text_muted", "#b1b1b1"),
        "@text_disabled": theme_data.get("text_disabled", "#777777"),
        # Interactive states
        "@state_hover": theme_data.get("state_hover", "#403f3f"),
        "@state_pressed": theme_data.get("state_pressed", "#4a4949"),
        # Scrollbar colors
        "@scrollbar_track": theme_data.get("scrollbar_track", "#2a2929"),
        "@scrollbar_thumb": theme_data.get("scrollbar_thumb", "#605f5f"),
        "@scrollbar_thumb_hover": theme_data.get(
            "scrollbar_thumb_hover", "#727272"
        ),
        # Layout colors
        "@grid": theme_data.get("grid", "#4a4949"),
        "@separator": theme_data.get("separator", "#787876"),
        # Slider colors
        "@slider_thumb": theme_data.get("slider_thumb", "#bbbbbb"),
        "@slider_thumb_hover": theme_data.get("slider_thumb_hover", "#ffffff"),
    }

    # Sort by key length descending to avoid partial replacements
    # (e.g., @border before @border_light)
    for key in sorted(replace.keys(), key=len, reverse=True):
        stylesheet = stylesheet.replace(key, replace[key])

    stylesheet = (
        font_stylesheet + stylesheet + extra
        if extra
        else font_stylesheet + stylesheet
    )

    stylesheet = stylesheet + extra if extra else stylesheet

    return stylesheet
