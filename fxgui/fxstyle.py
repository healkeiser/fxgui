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

Theme Font Reference
--------------------
The color file may also name typefaces by role, in a ``fonts:`` mapping
that a theme can override role by role:

    - ``title``: Reached from QSS through the ``fxTitle`` property; see
      :func:`mark_as_title`
    - ``body``: Every widget, through the ``*`` selector
    - ``mono``: Code, logs, anything whose columns must line up

Each role is a family stack. A missing section, a missing role or an
empty value all mean the platform default UI font, so a color file
written before roles existed renders unchanged. Families the running Qt
does not have are dropped and the platform default appended, so a role
always resolves to something real.

Because :func:`set_color_file` replaces this file wholesale, a consumer
declaring ``fonts:`` in its own copy has full typographic control with no
further API. Font files those names refer to are registered with
:func:`register_fonts`.

Classes:
    FXProxyStyle: Custom style providing Material Design icons for Qt standard icons.
    FXThemeManager: Singleton that emits signals when theme changes.
    FXThemeAware: Mixin for widgets that auto-update on theme changes.

Functions:
    load_stylesheet: Load and customize QSS stylesheets.
    get_colors: Get the cached color configuration.
    set_color_file: Set a custom color configuration file.
    apply_theme: Apply a theme to all registered roots (stylesheet + icons).
    get_available_themes: Get list of available theme names.
    get_theme: Get the current theme name.
    get_theme_colors: Get the color palette for the current theme.
    get_accent_colors: Get primary/secondary accent colors.
    get_icon_color: Get the icon tint color for current theme.
    register_fonts: Register font files so a color file may name them.
    get_fonts: Get the resolved font stack for every role.
    get_font_family: Get the resolved font stack for one role.
    mark_as_title: Draw a widget's text in the title font role.
    is_light_theme: Check if the current theme is light or dark.
    save_theme: Save the current theme to persistent storage.
    load_saved_theme: Load the previously saved theme.
    set_default_theme: Set the theme to fall back to when none is saved.
    get_default_theme: Get the theme to fall back to when none is saved.

Constants:
    STYLE_FILE: Path to the default QSS stylesheet.
    DEFAULT_COLOR_FILE: Path to the default color configuration.
    TITLE_PROPERTY: Dynamic property name selecting the title font role.

Examples:
    Loading a stylesheet with a theme:

    >>> from fxgui import fxstyle
    >>> stylesheet = fxstyle.load_stylesheet(theme="dracula")
    >>> widget.setStyleSheet(stylesheet)

    New code should prefer `apply_theme` / `register_themed_root` instead.

    Applying a theme to a window:

    >>> fxstyle.apply_theme("one_dark_pro")

    For DCC-embedded windows, call `fxstyle.register_themed_root(window)`
    once at construction; `FXMainWindow` does this automatically.

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
import hashlib
import os
import sys
import warnings
import weakref
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional

# Third-party
import yaml
from qtpy.QtCore import QObject, QTimer, Signal
from qtpy.QtGui import QColor, QFontDatabase, QIcon
from qtpy.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleFactory,
    QStyleOption,
    QWidget,
)

# Internal
from fxgui import _compat, fxconfig, fxicons, fxutils


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

    def __getattr__(self, name: str):
        # Only called for missing attributes; give a helpful error instead of
        # a bare AttributeError deep inside a paintEvent.
        available = ", ".join(sorted(self.__dict__)) or "none"
        raise AttributeError(
            f"Unknown theme color role '{name}'. Available roles: {available}"
        )

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"FXThemeColors({attrs})"


class FXThemeManager(QObject):
    """Singleton that emits theme_changed(str) when the theme changes."""

    theme_changed = Signal(str)
    _instance = None
    # Class-level default so the re-init guard resolves through the class.
    # Probing an *instance* attribute before super().__init__() raises
    # RuntimeError under PyQt (sip), which made `import fxgui` fail outright
    # on PyQt5/PyQt6.
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
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

# Canonical module-level alias: connect side-effect widgets to
# fxstyle.theme_changed without going through the manager object.
theme_changed = theme_manager.theme_changed


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

        Note:
            The returned object is a shared, cached snapshot of the current
            theme; treat it as read-only. It is rebuilt whenever the theme
            changes.
        """
        return _get_theme_namespace()

    def __handle_theme_change(self, _theme_name: str = None) -> None:
        """Internal handler for theme changes."""
        # Check if the C++ object is still valid (prevents RuntimeError).
        # Uses fxgui._compat so this works under PyQt bindings too, where
        # qtpy.shiboken does not exist.
        if not _compat.is_valid(self):
            # Drop the connection so the manager stops notifying a widget
            # whose C++ side is gone; otherwise connections accumulate for
            # every widget ever created.
            try:
                theme_manager.theme_changed.disconnect(
                    self.__handle_theme_change
                )
            except (RuntimeError, TypeError):
                pass
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

        # Replace @tokens with actual colors. Only string values are tokens:
        # themes may contain nested sections (e.g. the per-theme "feedback"
        # block). Longest keys first so @border does not corrupt
        # @border_light into "<hex>_light".
        flat_colors = {
            key: value
            for key, value in colors.items()
            if isinstance(value, str)
        }
        for key in sorted(flat_colors, key=len, reverse=True):
            stylesheet = stylesheet.replace(f"@{key}", flat_colors[key])

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
    "theme_changed",
    # Constants
    "STYLE_FILE",
    "DEFAULT_COLOR_FILE",
    "TITLE_PROPERTY",
    # Color configuration
    "colors",
    "get_colors",
    "set_color_file",
    "get_accent_colors",
    "get_feedback_colors",
    "get_theme_colors",
    "get_icon_color",
    "get_icon_on_accent_primary",
    "get_icon_on_accent_secondary",
    # Font configuration
    "register_fonts",
    "get_fonts",
    "get_font_family",
    "mark_as_title",
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
    "build_stylesheet",
    "register_widget_style",
    "set_default_theme",
    "get_default_theme",
    "register_themed_root",
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

# Dynamic property routing a widget to the title font role. Set it
# through mark_as_title() rather than by hand.
TITLE_PROPERTY = "fxTitle"

# CSS generic keywords rather than family names: emitted unquoted, never
# looked up in the font database, and terminal, so nothing is appended
# after one.
_GENERIC_FONT_FAMILIES = frozenset(
    {"cursive", "fantasy", "monospace", "sans-serif", "serif"}
)

# Font roles used when the color file declares no `fonts:` section, no
# value for a role, or an empty one. An empty list means the platform
# default UI font, which is what every role used before roles existed.
_DEFAULT_FONTS = {
    "title": [],
    "body": [],
    "mono": ["Consolas", "Courier New", "monospace"],
}


###### Globals

_colors = None
_color_file = None  # Tracks which color file is currently loaded
_theme = None  # Will be loaded from settings on first access
_default_theme = _DEFAULT_THEME  # What load_saved_theme() falls back to
_standard_icon_map = None  # Lazy-loaded icon map cache
_theme_namespace = None  # Cached FXThemeColors for the current theme
_widget_fragments: "OrderedDict[str, str]" = OrderedDict()
_themed_roots: "weakref.WeakSet" = weakref.WeakSet()

# GATE from the spike (tests/test_style_cascade.py): False when Qt's
# cascade reliably repaints custom-painted descendants after an ancestor
# restyle; True enables an explicit update() walk as fallback.
_FORCE_UPDATE_WALK = False


def _invalidate_theme_namespace() -> None:
    """Drop the cached FXThemeColors snapshot (theme or colors changed)."""
    global _theme_namespace
    _theme_namespace = None


def _get_theme_namespace() -> "FXThemeColors":
    """Return a cached FXThemeColors for the current theme.

    Widgets read `self.theme` in paintEvent hot paths; rebuilding the
    namespace object on every access would allocate per frame.
    """
    global _theme_namespace
    if _theme_namespace is None:
        _theme_namespace = FXThemeColors(get_theme_colors())
    return _theme_namespace


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
    _invalidate_theme_namespace()


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

    **Icon Colors**:

    - ``icon``: Tint color for monochrome icons
    - ``icon_on_accent_primary``: Icon color on accent_primary backgrounds (optional)
    - ``icon_on_accent_secondary``: Icon color on accent_secondary backgrounds (optional)

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


def get_icon_on_accent_primary() -> str:
    """Get the icon color for accent_primary backgrounds.

    This color should be used for icons displayed on selected items or other
    elements that use the accent_primary color as their background.

    If not explicitly defined in the theme, falls back to text_on_accent_primary,
    which is auto-computed based on the accent_primary color's luminance.

    Returns:
        The icon color as a hex string for use on accent_primary backgrounds.

    Examples:
        >>> color = fxstyle.get_icon_on_accent_primary()
        >>> print(color)  # "#ffffff" for dark theme with blue accent
    """
    theme_colors = get_theme_colors()
    # Fallback chain: icon_on_accent_primary -> text_on_accent_primary -> computed
    if "icon_on_accent_primary" in theme_colors:
        return theme_colors["icon_on_accent_primary"]
    if "text_on_accent_primary" in theme_colors:
        return theme_colors["text_on_accent_primary"]
    accent = theme_colors.get("accent_primary", "#2196F3")
    return get_contrast_text_color(accent)


def get_icon_on_accent_secondary() -> str:
    """Get the icon color for accent_secondary backgrounds.

    This color should be used for icons displayed on hovered items or other
    elements that use the accent_secondary color as their background.

    If not explicitly defined in the theme, falls back to text_on_accent_secondary,
    which is auto-computed based on the accent_secondary color's luminance.

    Returns:
        The icon color as a hex string for use on accent_secondary backgrounds.

    Examples:
        >>> color = fxstyle.get_icon_on_accent_secondary()
        >>> print(color)  # "#ffffff" for dark theme with blue accent
    """
    theme_colors = get_theme_colors()
    # Fallback chain: icon_on_accent_secondary -> text_on_accent_secondary -> computed
    if "icon_on_accent_secondary" in theme_colors:
        return theme_colors["icon_on_accent_secondary"]
    if "text_on_accent_secondary" in theme_colors:
        return theme_colors["text_on_accent_secondary"]
    accent = theme_colors.get("accent_secondary", "#1976D2")
    return get_contrast_text_color(accent)


###### Font Configuration


def _platform_default_font() -> str:
    """Return the platform's default UI font family."""
    if sys.platform == "win32":
        return "Segoe UI"
    return QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()


def register_fonts(paths) -> Dict[str, list]:
    """Register font files with Qt so a color file may name them.

    Hands each file to ``QFontDatabase.addApplicationFont`` and reports
    the outcome per file instead of swallowing it: a face that fails to
    load is not an error Qt raises, it is a family that silently is not
    there, and the stylesheet naming it then renders as an arbitrary
    substitution. Themed roots are restyled afterwards, so registering
    late is safe and call order does not matter.

    Args:
        paths: A font file path, or an iterable of them. Anything
            ``QFontDatabase`` accepts (``.ttf``, ``.otf``).

    Returns:
        Mapping of each path, as given, to the family names Qt
        registered from it. **An empty list means that file did not
        load.** Those family names are the ones to put in the color
        file's ``fonts:`` section; a file's family is not always
        predictable from its filename.

    Examples:
        >>> loaded = fxstyle.register_fonts(brand_dir.glob("*.ttf"))
        >>> missing = [path for path, families in loaded.items()
        ...            if not families]

    Note:
        Qt needs a live QApplication before it will accept an
        application font. Called earlier than that, every file reports
        as failed.
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    results: Dict[str, list] = {}
    for path in paths:
        key = str(path)
        font_id = QFontDatabase.addApplicationFont(key)
        if font_id == -1:
            results[key] = []
        else:
            results[key] = QFontDatabase.applicationFontFamilies(font_id)

    if any(results.values()):
        _reapply_to_roots()
    return results


def _font_config(theme_name: str) -> dict:
    """Return the raw font role definitions for a theme.

    Precedence, lowest first: the built-in defaults, the color file's
    top-level ``fonts:`` block, then a ``fonts:`` block inside the
    theme. Merging is per role, so a file or theme naming only ``title``
    keeps the other roles.

    Args:
        theme_name: Theme to resolve.

    Returns:
        Mapping of role name to its configured family list or string.
    """
    colors_dict = get_colors()
    themes = colors_dict.get("themes", {})
    theme_data = {**themes.get("dark", {}), **themes.get(theme_name, {})}

    fonts = dict(_DEFAULT_FONTS)
    for source in (colors_dict.get("fonts"), theme_data.get("fonts")):
        if isinstance(source, dict):
            fonts.update(source)
    return fonts


def _resolve_font_stack(entries) -> str:
    """Turn one role's configured families into a QSS ``font-family``.

    An empty value yields the platform default alone, which is what the
    single hardcoded font block emitted before roles existed.

    Families the running Qt does not have are dropped rather than named.
    Naming an absent family is not a loud failure: Qt answers by
    substituting whichever family sorts first, so the stylesheet and
    :func:`get_fonts` would both claim a face that is not being drawn.
    The platform default is appended so a role can never resolve to
    nothing, unless the stack already ends in a CSS generic, which is
    terminal on its own.

    Args:
        entries: A family name, an iterable of them in preference order,
            or an empty value.

    Returns:
        A comma-separated QSS value, quoted except for CSS generics.
    """
    if not entries:
        entries = []
    elif isinstance(entries, str):
        entries = [entries]

    available = set(QFontDatabase.families())

    stack = []
    for entry in entries:
        name = str(entry).strip()
        if name.lower() in _GENERIC_FONT_FAMILIES:
            stack.append(name.lower())
        elif name in available:
            stack.append(f'"{name}"')

    if not stack or stack[-1] not in _GENERIC_FONT_FAMILIES:
        stack.append(f'"{_platform_default_font()}"')
    return ", ".join(stack)


def get_fonts(theme: Optional[str] = None) -> Dict[str, str]:
    """Get the resolved font stack for every role in a theme.

    Args:
        theme: Theme name. Defaults to the current theme.

    Returns:
        Mapping of role name ("title", "body", "mono") to a QSS
        ``font-family`` value, with unavailable families already
        removed, so this reports what will actually be drawn.

    Examples:
        >>> fxstyle.get_fonts()["body"]
        '"Segoe UI"'
    """
    if theme is None:
        theme = get_theme()
    return {
        role: _resolve_font_stack(entries)
        for role, entries in _font_config(theme).items()
    }


def get_font_family(role: str = "body", theme: Optional[str] = None) -> str:
    """Get the resolved font stack for a single role.

    Args:
        role: One of "title", "body", or "mono". Unknown roles fall back
            to "body". Defaults to "body".
        theme: Theme name. Defaults to the current theme.

    Returns:
        A QSS ``font-family`` value.

    Examples:
        >>> fxstyle.get_font_family("mono")
        '"Consolas", "Courier New", monospace'
    """
    fonts = get_fonts(theme)
    return fonts.get(role) or fonts["body"]


def mark_as_title(widget: QWidget, is_title: bool = True) -> None:
    """Draw a widget's text in the theme's title font role.

    Sets the dynamic property the theme stylesheet keys the title role
    on, then repolishes so the change lands on an already-shown widget.
    Only the family changes: size and weight keep coming from whatever
    rule or ``setFont`` call already governed the widget.

    With a color file that leaves ``title`` empty, or names the same
    family for both roles, this is a no-op visually.

    Args:
        widget: The widget whose text is a title.
        is_title: False removes the mark and returns the widget to the
            body role. Defaults to True.

    Examples:
        >>> heading = QLabel("Render Settings")
        >>> fxstyle.mark_as_title(heading)
    """
    widget.setProperty(TITLE_PROPERTY, bool(is_title))
    fxutils.repolish(widget)


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


def _token_map(theme_name: str) -> Dict[str, str]:
    """Build the ``@token`` -> value map for a theme.

    Single source of truth for stylesheet token resolution. Includes:
    flat theme color roles, flattened feedback colors
    (``@feedback_<level>_<part>``), computed on-accent colors, and the
    ``~icons`` folder path.

    Args:
        theme_name: Theme to resolve. Unknown names fall back to "dark"
            key-by-key (the dark theme acts as the defaults baseline).

    Returns:
        Mapping of placeholder (including the ``@``/``~`` prefix) to value.
    """
    colors_dict = get_colors()
    themes = colors_dict.get("themes", {})
    base = themes.get("dark", {})
    theme_data = {**base, **themes.get(theme_name, {})}

    tokens: Dict[str, str] = {
        f"@{key}": value
        for key, value in theme_data.items()
        if isinstance(value, str)
    }

    # Feedback colors flatten to @feedback_<level>_<part>. Theme-level
    # block wins over the deprecated top-level one.
    feedback = theme_data.get("feedback") or colors_dict.get("feedback") or {}
    for level, pair in feedback.items():
        if isinstance(pair, dict):
            for part, value in pair.items():
                tokens[f"@feedback_{level}_{part}"] = value

    # On-accent colors: theme value if defined, computed otherwise.
    accent_primary = theme_data.get("accent_primary", "#2196F3")
    accent_secondary = theme_data.get("accent_secondary", "#1976D2")
    tokens.setdefault("@accent_primary", accent_primary)
    tokens.setdefault("@accent_secondary", accent_secondary)
    text_on_primary = theme_data.get(
        "text_on_accent_primary", get_contrast_text_color(accent_primary)
    )
    text_on_secondary = theme_data.get(
        "text_on_accent_secondary", get_contrast_text_color(accent_secondary)
    )
    tokens["@text_on_accent_primary"] = text_on_primary
    tokens["@text_on_accent_secondary"] = text_on_secondary
    tokens["@icon_on_accent_primary"] = theme_data.get(
        "icon_on_accent_primary", text_on_primary
    )
    tokens["@icon_on_accent_secondary"] = theme_data.get(
        "icon_on_accent_secondary", text_on_secondary
    )

    # Font roles flatten to @font_<role>, resolved against the families
    # Qt actually has so the sheet never names one it cannot honour.
    for role, entries in _font_config(theme_name).items():
        tokens[f"@font_{role}"] = _resolve_font_stack(entries)

    # Icon folder path used by url(~icons/...) in QSS, chosen by the
    # target theme's surface lightness (not the globally current theme).
    surface = QColor(theme_data.get("surface", "#000000"))
    icon_folder = (
        "stylesheet_light" if surface.lightness() > 128 else "stylesheet_dark"
    )
    tokens["~icons"] = str(_parent_directory / "icons" / icon_folder).replace(
        os.sep, "/"
    )
    return tokens


def _resolve_tokens(qss: str, theme_name: str) -> str:
    """Replace all ``@token``/``~icons`` placeholders in a stylesheet.

    Args:
        qss: Stylesheet text containing placeholders.
        theme_name: Theme whose values to substitute.

    Returns:
        The stylesheet with placeholders replaced, longest keys first so
        ``@border`` cannot corrupt ``@border_light``.
    """
    tokens = _token_map(theme_name)
    for key in sorted(tokens, key=len, reverse=True):
        qss = qss.replace(key, tokens[key])
    return qss


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


def set_default_theme(theme: str) -> None:
    """Set the theme an application falls back to when none is saved.

    "dark" unless this is called. For an application that ships a theme
    of its own in a custom color file: without this, its own first run
    is indistinguishable from a person having chosen "dark", so it
    cannot both honour a saved choice and default to its own brand.

    Not validated here, because the color file that has to offer the
    theme may be set afterwards; `load_saved_theme` falls back to "dark"
    if the file turns out not to offer it.

    Args:
        theme: The theme name to fall back to.

    Examples:
        >>> fxstyle.set_color_file("studio_colors.yaml")
        >>> fxstyle.set_default_theme("studio")
        >>> fxstyle.apply_theme(fxstyle.load_saved_theme())
    """
    global _default_theme
    _default_theme = theme


def get_default_theme() -> str:
    """Get the theme an application falls back to when none is saved.

    Returns:
        The name set by `set_default_theme`, or "dark".
    """
    return _default_theme


def load_saved_theme() -> str:
    """Load the saved theme from persistent storage.

    If no theme has been saved, returns the default theme -- "dark", or
    whatever `set_default_theme` was given.

    Returns:
        The saved theme name, or the default if none is saved or the
        saved one is not offered by the current color file.

    Examples:
        >>> theme = fxstyle.load_saved_theme()
        >>> print(theme)  # "dracula" if previously saved
    """
    default = get_default_theme()
    saved_theme = fxconfig.get_value(_SETTINGS_THEME_KEY, default)

    # Validate the saved theme exists
    # We need to load colors first to get available themes
    colors = _load_colors_from_yaml()
    available_themes = list(colors.get("themes", {}).keys())

    if saved_theme in available_themes:
        return saved_theme
    # The configured default gets the same check: a name no color file
    # offers would reach apply_theme() and raise there instead.
    if default in available_themes:
        return default
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


def colors() -> "FXThemeColors":
    """Get the current theme colors as a namespace (canonical read API).

    Cheap enough for ``paintEvent`` hot paths: the namespace is cached
    per theme and rebuilt only on theme switches. Treat it as read-only.

    Returns:
        FXThemeColors with one attribute per color role.

    Examples:
        >>> def paintEvent(self, event):
        ...     painter = QPainter(self)
        ...     painter.fillRect(self.rect(), QColor(fxstyle.colors().surface))
    """
    _ensure_theme_loaded()
    return _get_theme_namespace()


def apply_theme(*args, widget: Optional[QWidget] = None, theme: Optional[str] = None) -> str:
    """Apply a theme everywhere.

    Canonical form::

        fxstyle.apply_theme("dracula")

    Updates the persistent theme state, rebuilds the theme stylesheet,
    re-applies it to every registered root (see
    :func:`register_themed_root`), refreshes icon colors, and emits
    ``theme_changed``.

    .. deprecated::
        The old form ``apply_theme(widget, theme)`` still works: it
        registers ``widget`` as a themed root and proceeds. Prefer
        ``apply_theme(theme)``.

    Args:
        theme: The theme name to apply (e.g., "dark", "light").
        widget: Deprecated. A widget to register as a themed root.

    Returns:
        The theme that was applied.

    Raises:
        ValueError: If the theme does not exist.
        TypeError: If no theme name was provided.
    """
    global _theme

    # Untangle the two calling conventions.
    if args:
        if isinstance(args[0], str):
            if len(args) > 1 or theme is not None:
                raise TypeError("apply_theme() takes a single theme name")
            theme = args[0]
        else:
            if widget is not None:
                raise TypeError("apply_theme() got widget twice")
            widget = args[0]
            if len(args) == 2:
                if theme is not None:
                    raise TypeError("apply_theme() got theme twice")
                theme = args[1]
            elif len(args) > 2:
                raise TypeError("apply_theme() takes at most 2 arguments")
    if theme is None:
        raise TypeError("apply_theme() missing required 'theme'")

    available_themes = get_available_themes()
    if theme not in available_themes:
        raise ValueError(
            f"Theme '{theme}' not found. Available themes: {available_themes}"
        )

    if widget is not None:
        warnings.warn(
            "apply_theme(widget, theme) is deprecated; call "
            "apply_theme(theme) once. For DCC-embedded windows, use "
            "register_themed_root(widget) at construction instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        _themed_roots.add(widget)

    _theme = theme
    _invalidate_theme_namespace()
    save_theme(theme)
    fxicons.sync_colors_with_theme()
    invalidate_standard_icon_map()
    _reapply_to_roots()
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

    # Theme-aware feedback colors with fallbacks; the top-level "feedback"
    # YAML block is deprecated and may be absent from custom color files.
    feedback_colors = get_feedback_colors()

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
        QStyle.SP_MessageBoxCritical: fxicons.get_icon("error", color=feedback_colors["error"]["foreground"]),
        QStyle.SP_MessageBoxInformation: fxicons.get_icon("info", color=feedback_colors["info"]["foreground"]),
        QStyle.SP_MessageBoxQuestion: fxicons.get_icon("help", color=feedback_colors["success"]["foreground"]),
        QStyle.SP_MessageBoxWarning: fxicons.get_icon("warning", color=feedback_colors["warning"]["foreground"]),
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
    """A custom style class that extends QProxyStyle to provide custom icons.

    This style provides theme-aware standard icons (file dialogs, message boxes,
    etc.) using Material Design icons from the fxicons library.

    Note:
        Qt stylesheets bypass QProxyStyle's drawControl() method, which means
        icon colorization for item views (lists, trees) and menus cannot be
        handled here when stylesheets are applied. Use ``FXIconColorDelegate``
        from fxwidgets for icon colorization in item views instead.

    Examples:
        >>> from fxgui import fxstyle
        >>> # Apply to application
        >>> fxstyle.set_style(app, "Fusion")
    """

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
    # Longest placeholders first so e.g. @border does not corrupt
    # @border_light.
    for placeholder in sorted(placeholders, key=len, reverse=True):
        stylesheet = stylesheet.replace(placeholder, placeholders[placeholder])
    return stylesheet


def _font_stylesheet() -> str:
    """Return the font block mapping the font roles onto selectors.

    Emits ``@font_*`` tokens rather than resolved values; the caller runs
    it through :func:`_resolve_tokens` with the rest of the sheet.

    The title rule is an attribute selector, which outranks both a
    widget's own stylesheet and an explicit ``setFont``, so a marked
    title takes the title family and keeps its size and weight. With a
    color file that leaves the roles empty, both rules resolve to the
    same platform font and the sheet behaves as it did with one block.
    """
    return (
        "* {\n    font-family: @font_body;\n}\n"
        f'[{TITLE_PROPERTY}="true"] {{\n'
        "    font-family: @font_title;\n}\n"
    )


def build_stylesheet(theme: Optional[str] = None) -> str:
    """Build the complete theme stylesheet.

    Concatenates the platform font block, the base ``style.qss``, and all
    fragments registered via :func:`register_widget_style`, then resolves
    every ``@token`` in a single pass. Pure: no global state is modified.

    Args:
        theme: Theme name. Defaults to the current theme.

    Returns:
        The ready-to-apply stylesheet string.
    """
    if theme is None:
        theme = get_theme()
    parts = [_font_stylesheet()]
    if os.path.exists(STYLE_FILE):
        with open(STYLE_FILE, "r", encoding="utf-8") as in_file:
            parts.append(in_file.read())
    parts.extend(_widget_fragments.values())
    return _resolve_tokens("\n".join(parts), theme)


def register_widget_style(qss: str) -> None:
    """Register a widget's QSS fragment with the theme stylesheet.

    Call once at module import time. The fragment may use ``@tokens``
    (e.g. ``@surface``, ``@border``); use your widget's class name as
    selector to scope the rules. Identical fragments are registered once.

    If themed roots already exist, the rebuilt sheet is re-applied to
    them immediately, so late registration is safe.

    Args:
        qss: Stylesheet fragment with optional ``@token`` placeholders.

    Examples:
        >>> fxstyle.register_widget_style('''
        ...     MyWidget { background: @surface; border: 1px solid @border; }
        ... ''')
    """
    key = hashlib.sha1(qss.encode("utf-8")).hexdigest()
    if key in _widget_fragments:
        return
    _widget_fragments[key] = qss
    _reapply_to_roots()


def register_themed_root(root: QObject) -> None:
    """Register a widget (or QApplication) as a themed root.

    The current theme stylesheet is applied to it immediately and
    re-applied on every subsequent :func:`apply_theme` call. Qt cascades
    the sheet to all descendants, so children need no registration.

    Standalone apps: ``FXApplication`` registers itself; nothing to do.
    DCC-embedded windows: ``FXMainWindow`` registers itself when the
    running QApplication is foreign, so the host app is never restyled.

    Roots are held weakly; destroyed widgets drop out automatically.

    Args:
        root: Any object with ``setStyleSheet`` (QWidget or QApplication).
    """
    _ensure_theme_loaded()
    fxicons.sync_colors_with_theme()
    _themed_roots.add(root)
    root.setStyleSheet(build_stylesheet())


def _reapply_to_roots() -> None:
    """Re-apply the current theme sheet to all live registered roots."""
    if not _themed_roots:
        return
    sheet = build_stylesheet()
    for root in list(_themed_roots):
        if not _compat.is_valid(root):
            continue
        root.setStyleSheet(sheet)
        if _FORCE_UPDATE_WALK and hasattr(root, "findChildren"):
            for child in root.findChildren(QWidget):
                child.update()


def load_stylesheet(
    style_file: str = STYLE_FILE,
    extra: Optional[str] = None,
    theme: str = None,
) -> str:
    """Load the stylesheet and replace placeholders with actual values.

    Note:
        Kept for backward compatibility and manual DCC styling. New code
        should rely on :func:`register_themed_root` /
        :func:`apply_theme`, which use :func:`build_stylesheet`
        (including registered widget fragments; this function does not).

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
        # An empty string is a valid "no-op" stylesheet.
        return ""

    if theme is None:
        theme = load_saved_theme()

    # Keep the historical side effects: global theme state stays in sync
    # and icon colors follow (important for startup with a saved theme).
    _theme = theme
    _invalidate_theme_namespace()
    fxicons.sync_colors_with_theme()

    with open(style_file, "r", encoding="utf-8") as in_file:
        stylesheet = in_file.read()

    # The font block carries @font_* tokens, so it has to go through the
    # resolver with the rest of the sheet rather than be prepended after.
    stylesheet = _resolve_tokens(_font_stylesheet() + stylesheet, theme)
    if extra:
        stylesheet += extra

    return stylesheet
