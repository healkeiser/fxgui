"""Themes for `fxgui`: the stylesheet, palette, font and colours of each.

A themed root (see `register_themed_root`) wears the theme's stylesheet
(shapes, borders, states, each widget's look), palette (default fills)
and font (body family, `FONT_SIZE`). `apply_theme(name)` puts the new
theme on every root and emits `theme_changed`. Custom painting reads
`colors()`; icons name their colours by token (see `fxicons`). Every
colour role is listed at the top of ``style.yaml``; font roles (title,
body, mono) come from its ``fonts:`` block.

Examples:
    >>> from fxgui import fxstyle
    >>> fxstyle.apply_theme("one_dark_pro")
    >>> fxstyle.register_themed_root(window)  # a window inside a host
    >>> surface = fxstyle.colors().surface
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### Imports

# Built-in
import hashlib
import os
import sys
import weakref
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

# Third-party
import yaml
from qtpy.QtCore import QEvent, QObject, Qt, Signal
from qtpy.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QPainter,
    QPalette,
    QTransform,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QProxyStyle,
    QSplitter,
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
    """Hold the `theme_changed(str)` signal `apply_theme` emits."""

    theme_changed = Signal(str)

    def notify_theme_changed(self, theme_name: str) -> None:
        """Emit `theme_changed` with the theme now applied."""
        self.theme_changed.emit(theme_name)


# Global singleton instance
theme_manager = FXThemeManager()

# Canonical module-level alias: connect side-effect widgets to
# fxstyle.theme_changed without going through the manager object.
theme_changed = theme_manager.theme_changed


###### Public API

__all__ = [
    # Classes
    "FXProxyStyle",
    "FXThemeManager",
    "FXThemeColors",
    # Singleton
    "theme_manager",
    "theme_changed",
    # Constants
    "STYLE_FILE",
    "DEFAULT_COLOR_FILE",
    "TITLE_PROPERTY",
    "BUTTON_RADIUS",
    "FONT_SIZE",
    "ROOT_PROPERTY",
    # Color configuration
    "colors",
    "get_colors",
    "set_color_file",
    "overlay_color_file",
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
    "resolve",
    "build_stylesheet",
    "register_widget_style",
    "set_default_theme",
    "get_default_theme",
    "register_themed_root",
    "palette",
    "font",
    # Utility functions
    "get_luminance",
    "get_contrast_text_color",
    "get_contrast_ratio",
    "readable_ink",
    "mix",
    "step_toward",
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

# Dynamic property painting a widget in the frame colour. Set it through
# mark_as_frame() rather than by hand.
FRAME_PROPERTY = "fxFrame"

# Styles QPushButton through @button_radius; widgets that draw a button
# shape of their own read it here.
BUTTON_RADIUS = 4

# Least WCAG contrast between a pane (`surface`) and the `frame` around
# it. github_light's own pair, #ffffff on #f6f8fa, is 1.065.
FRAME_MIN_CONTRAST = 1.06

# Least contrast between a pane and a `well` inside it. Rendered in
# github_light, whose half-way well (1.030) read as no well at all.
WELL_MIN_CONTRAST = 1.04

# Least contrast between a pane's 1 px edge (`pane_border`) and the frame
# around it; `light`'s own border, #e0e0e0 on #e4e4e4, is 1.04 and vanishes.
PANE_BORDER_MIN_CONTRAST = 1.3

# Least contrast between the splitter mark's dots and the frame.
SPLITTER_MARK_MIN_CONTRAST = 1.3

# CSS generic keywords rather than family names: emitted unquoted, never
# looked up in the font database, and terminal, so nothing is appended
# after one.
# The body text size, in pixels, of every themed root.
FONT_SIZE = 12

# The dynamic property a widget registered as a themed root carries.
ROOT_PROPERTY = "fxThemedRoot"

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

# A face's `weight:` in the color file, on the CSS scale QSS also reads.
_WEIGHTS = {
    100: QFont.Thin,
    200: QFont.ExtraLight,
    300: QFont.Light,
    400: QFont.Normal,
    500: QFont.Medium,
    600: QFont.DemiBold,
    700: QFont.Bold,
    800: QFont.ExtraBold,
    900: QFont.Black,
}

# A face's `hinting:` in the color file.
_HINTING = {
    "default": QFont.PreferDefaultHinting,
    "none": QFont.PreferNoHinting,
    "vertical": QFont.PreferVerticalHinting,
    "full": QFont.PreferFullHinting,
}


###### Globals

_colors = None
_color_file = None  # Tracks which color file is currently loaded
_theme = None  # Will be loaded from settings on first access
_default_theme = _DEFAULT_THEME  # What load_saved_theme() falls back to
_standard_icon_map = None  # Lazy-loaded icon map cache
_theme_namespace = None  # Cached FXThemeColors for the current theme
_theme_namespace_key = None  # (theme, colour dict id) the cache was built for
_widget_fragments: "OrderedDict[str, str]" = OrderedDict()
_themed_roots: "weakref.WeakSet" = weakref.WeakSet()

_DEFAULT_FEEDBACK = {
    "debug": {"foreground": "#26C6DA", "background": "#006064"},
    "info": {"foreground": "#7661f6", "background": "#372d75"},
    "success": {"foreground": "#8ac549", "background": "#466425"},
    "warning": {"foreground": "#ffbb33", "background": "#7b5918"},
    "error": {"foreground": "#ff4444", "background": "#7b2323"},
}


def _invalidate_theme_namespace() -> None:
    """Drop the cached FXThemeColors snapshot (theme or colors changed)."""
    global _theme_namespace
    _theme_namespace = None


def _get_theme_namespace() -> "FXThemeColors":
    """Return the cached resolved colours of the current theme.

    Keyed on the colour dict too, so a swapped `_colors` never serves the
    old file's colours.
    """
    global _theme_namespace, _theme_namespace_key
    _ensure_theme_loaded()
    key = (_theme, id(get_colors()))
    if _theme_namespace is None or _theme_namespace_key != key:
        _theme_namespace = FXThemeColors({
            name[1:]: value
            for name, value in _token_map(_theme).items()
            if name.startswith("@")
        })
        _theme_namespace_key = key
    return _theme_namespace


###### Private Helper Functions


def _load_colors_from_yaml() -> dict:
    """Return the loaded colour file, reading it on first use."""
    global _colors, _color_file
    path = _color_file or str(DEFAULT_COLOR_FILE)
    if _colors is None or _color_file != path:
        with open(path, "r", encoding="utf-8") as in_file:
            _colors = yaml.safe_load(in_file)
        _color_file = path
    return _colors


@lru_cache(maxsize=1)
def _builtin_theme() -> dict:
    """Return the default file's dark theme, the baseline for every key.

    Keys computed from others are left out, so a file whose accent differs
    gets them computed from its own accent.
    """
    with open(DEFAULT_COLOR_FILE, "r", encoding="utf-8") as in_file:
        theme = yaml.safe_load(in_file)["themes"][_DEFAULT_THEME]
    return {
        key: value for key, value in theme.items()
        if not key.startswith(("text_on_accent", "icon_on_accent"))
    }


def _theme_data(theme_name: str) -> dict:
    """Return a theme's raw values over the file's dark and the built-in dark."""
    themes = get_colors().get("themes", {})
    return {
        **_builtin_theme(),
        **themes.get(_DEFAULT_THEME, {}),
        **themes.get(theme_name, {}),
    }


def _deep_merge(base: dict, over: dict) -> dict:
    """Return `base` with `over` merged in, nested dicts key by key."""
    merged = dict(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            value = _deep_merge(merged[key], value)
        merged[key] = value
    return merged


def _colors_changed() -> None:
    """Re-apply the current theme after the theme or colour file changed."""
    _invalidate_theme_namespace()
    _reapply_to_roots()
    theme_manager.notify_theme_changed(get_theme())


###### Color Configuration


def set_color_file(color_file: str) -> None:
    """Replace the whole colour file, then re-apply the theme everywhere.

    A file setting only a few keys belongs in `overlay_color_file`.

    Args:
        color_file: Path to the YAML color configuration file.
    """
    global _colors, _color_file
    _colors = None
    _color_file = str(color_file)
    _colors_changed()


def overlay_color_file(color_file: str) -> None:
    """Merge a colour file onto the loaded one, then re-apply the theme.

    Nested mappings (`themes`, each theme, `fonts`) merge key by key, so
    the file needs only the keys it changes. A new theme takes every key
    it omits from the dark theme.

    Args:
        color_file: Path to the YAML file holding the keys to change.

    Examples:
        >>> fxstyle.overlay_color_file("studio_colors.yaml")
    """
    global _colors
    with open(color_file, "r", encoding="utf-8") as in_file:
        over = yaml.safe_load(in_file) or {}
    _colors = _deep_merge(get_colors(), over)
    _colors_changed()


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
    theme = colors()
    return {"primary": theme.accent_primary, "secondary": theme.accent_secondary}


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
    return _feedback(get_theme())


def _feedback(theme_name: str) -> dict:
    """Return a theme's feedback block: its own, dark's, the file's, built-in."""
    colors_dict = get_colors()
    themes = colors_dict.get("themes", {})
    for source in (
        themes.get(theme_name, {}),
        themes.get(_DEFAULT_THEME, {}),
        colors_dict,
        _builtin_theme(),
    ):
        if isinstance(source.get("feedback"), dict):
            return source["feedback"]
    return _DEFAULT_FEEDBACK


def get_theme_colors() -> dict:
    """Get the resolved colours of the current theme, one key per role.

    The roles are listed at the top of ``style.yaml``'s ``themes:`` section.

    Returns:
        Every ``@token`` of the theme sheet, without the ``@``: a copy of
        the cache `colors` reads, with keys the theme omits filled from
        the default theme.

    Examples:
        >>> colors = get_theme_colors()
        >>> bg = colors["surface"]  # "#302f2f" for dark
        >>> sunken = colors["surface_sunken"]  # Input/list backgrounds
        >>> text = colors["text"]  # Primary text color
    """
    return dict(vars(_get_theme_namespace()))


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
    return colors().icon


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
    return colors().icon_on_accent_primary


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
    return colors().icon_on_accent_secondary


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
    fonts = dict(_DEFAULT_FONTS)
    theme_fonts = _theme_data(theme_name).get("fonts")
    for source in (get_colors().get("fonts"), theme_fonts):
        if isinstance(source, dict):
            fonts.update(source)
    fonts.pop("ranks", None)
    return fonts


def _families(entry):
    """Return a role's families: the entry itself, or its `family` key."""
    return entry.get("family") if isinstance(entry, dict) else entry


def _shape(theme_name: str, role: str) -> Tuple[Optional[int], Optional[str]]:
    """Return a role's configured weight and hinting, each None when unset."""
    entry = _font_config(theme_name).get(role)
    if not isinstance(entry, dict):
        return None, None
    weight, hinting = entry.get("weight"), entry.get("hinting")
    if weight is not None and weight not in _WEIGHTS:
        raise ValueError(
            f"Font weight {weight!r} for '{role}' is not one of "
            f"{sorted(_WEIGHTS)}")
    if hinting is not None and hinting not in _HINTING:
        raise ValueError(
            f"Font hinting {hinting!r} for '{role}' is not one of "
            f"{sorted(_HINTING)}")
    return weight, hinting


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
    entries = _families(entries)
    if not entries:
        entries = []
    elif isinstance(entries, str):
        entries = [entries]

    # QFontDatabase needs a QGuiApplication; before one, only the default.
    available = (
        set(QFontDatabase.families()) if QGuiApplication.instance() else set()
    )

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


def mark_as_frame(widget: QWidget, is_frame: bool = True) -> None:
    """Paint a widget in the theme's ``frame`` color, as window chrome.

    Labels, check boxes, radio buttons and disabled tool buttons placed
    directly in it lose their own fill, so they sit on the frame. A
    `QSplitter` so marked draws its handles as frame-colored gaps with a
    short centred mark; its width stays whatever `setHandleWidth` says.

    Args:
        widget: The band, bar or splitter that is part of the frame.
        is_frame: False removes the mark. Defaults to True.

    Examples:
        >>> fxstyle.mark_as_frame(project_bar)
        >>> splitter.setHandleWidth(6)
        >>> fxstyle.mark_as_frame(splitter)
    """
    widget.setProperty(FRAME_PROPERTY, bool(is_frame))
    # Direct children only: a nested marked splitter's mark is not this one's.
    marked = widget.findChild(_SplitterMark, "", Qt.FindDirectChildrenOnly)
    if isinstance(widget, QSplitter) and marked is None:
        _SplitterMark(widget)
    fxutils.repolish(widget)
    # Child selectors are matched when the child polishes, not the parent.
    for child in widget.findChildren(QWidget):
        if child.parentWidget() is widget:
            fxutils.repolish(child)


###### Color Utility Functions


def get_luminance(hex_color: str) -> float:
    """Calculate the relative luminance of a color.

    Uses the WCAG 2.0 formula for relative luminance.

    Args:
        hex_color: Any colour QColor reads ("#007ACC", "white"), or hex
            without its "#" ("007ACC").

    Returns:
        The relative luminance value between 0 (black) and 1 (white).
    """
    color = QColor(hex_color if hex_color[:1] == "#" else f"#{hex_color}")
    if not color.isValid():
        color = QColor(hex_color)

    def gamma(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = color.redF(), color.greenF(), color.blueF()
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


def get_contrast_ratio(one_hex: str, two_hex: str) -> float:
    """Return the WCAG contrast ratio between two colors, 1.0 to 21.0."""
    low, high = sorted([get_luminance(one_hex), get_luminance(two_hex)])
    return (high + 0.05) / (low + 0.05)


def readable_ink(
    background: str, preferred: Optional[str] = None, floor: float = 4.5
) -> str:
    """Return an ink that reads on `background` at `floor`:1 or better.

    Args:
        background: The color the ink is drawn on.
        preferred: The ink to keep if it reads. Defaults to white.
        floor: The minimum WCAG contrast ratio.

    Returns:
        `preferred` when it reads, else the first color from it toward
        black or white, whichever stands further from `background`, that
        does. The pole itself when none does.
    """
    ground = QColor(background).name()
    start = QColor(preferred or "#ffffff").name()
    toward = max(
        ("#000000", "#ffffff"),
        key=lambda pole: get_contrast_ratio(pole, ground),
    )
    return step_toward(start, toward, _reads(ground, floor))


def _visibly_differ(one_hex: str, two_hex: str) -> bool:
    """Return whether two fills read as two states of one control."""
    # Channels as well as luminance: dracula's purple and pink sit at the
    # same luminance, and nobody mistakes one for the other.
    one, two = QColor(one_hex), QColor(two_hex)
    delta = max(
        abs(one.red() - two.red()),
        abs(one.green() - two.green()),
        abs(one.blue() - two.blue()),
    )
    return get_contrast_ratio(one_hex, two_hex) >= 1.1 or delta >= 48


def _away_from(ink_hex: str, fill_hex: str) -> str:
    """Return the pole a fill moves to for more contrast with `ink_hex`."""
    light_ink = get_luminance(ink_hex) > get_luminance(fill_hex)
    return "#000000" if light_ink else "#ffffff"


def _primary_button_fills(
    accent_primary: str,
    accent_secondary: str,
    text_on_primary: str,
    text_on_secondary: str,
) -> Tuple[str, str, str]:
    """Return the rest, hover and pressed fills of a primary button.

    Several themes' accents miss WCAG AA against their own on-accent text,
    so each fill is shifted until the text drawn on it reads at 4.5:1. Rest
    and pressed carry `text_on_primary`, hover `text_on_secondary`; where
    the secondary accent lands on the rest fill, hover steps off it instead.
    """

    def shifted(fill, ink, *apart):
        reads = _reads(ink, 4.5)
        return step_toward(fill, _away_from(ink, fill), lambda color: (
            reads(color) and all(_visibly_differ(color, o) for o in apart)
        ))

    rest = shifted(accent_primary, text_on_primary)
    hover = shifted(accent_secondary, text_on_secondary)
    if not _visibly_differ(rest, hover):
        hover = shifted(rest, text_on_secondary, rest)
    pressed = shifted(rest, text_on_primary, rest, hover)
    return rest, hover, pressed


def mix(one_hex, two_hex, amount: float) -> str:
    """Return the hex colour `amount` (0 to 1) of the way from one to two.

    Either colour may be anything QColor reads, a QColor included.
    """
    one, two = QColor(one_hex), QColor(two_hex)
    return QColor(
        round(one.red() + (two.red() - one.red()) * amount),
        round(one.green() + (two.green() - one.green()) * amount),
        round(one.blue() + (two.blue() - one.blue()) * amount),
    ).name()


def step_toward(start, toward, done) -> str:
    """Return the first hex colour from `start` to `toward` that is `done`.

    Args:
        start: The colour to begin at, tried first.
        toward: The colour to move to, in 40 steps.
        done: Takes a hex colour; True stops the walk there.

    Returns:
        The first colour `done` accepts, else `toward` itself.

    Examples:
        >>> fxstyle.step_toward("#202020", "#ffffff",
        ...     lambda c: fxstyle.get_contrast_ratio(c, "#202020") >= 4.5)
    """
    for step in range(41):
        color = mix(start, toward, step / 40)
        if done(color):
            return color
    return color


def _reads(against: str, minimum: float):
    """Return a test: does a color differ from `against` by `minimum`?"""
    return lambda color: get_contrast_ratio(color, against) >= minimum


def _depth_colors(theme_data: dict) -> Dict[str, str]:
    """Return a theme's frame, well, pane border and splitter mark colors.

    Each is the theme's own value when it states one. Otherwise:

    - ``frame``: ``surface_sunken`` when that is darker than ``surface`` by
      `FRAME_MIN_CONTRAST`, else ``surface`` darkened toward black until
      it is, else, for a pane too dark to darken, lightened toward white.
      The pane's hue stays; no accent comes in.
    - ``well``: half-way from ``surface`` to the frame, stepped on toward
      the frame until it differs from ``surface`` by `WELL_MIN_CONTRAST`.
    - ``pane_border``: ``border`` pushed away from the frame until they
      differ by `PANE_BORDER_MIN_CONTRAST`.
    - ``splitter_mark``: ``border``, else ``border_light``, else
      ``border_light`` stepped toward ``text``, whichever first differs
      from the frame by `SPLITTER_MARK_MIN_CONTRAST`.
    """
    surface = theme_data["surface"]
    sunken = theme_data.get("surface_sunken", surface)
    deep = _reads(surface, FRAME_MIN_CONTRAST)

    frame = theme_data.get("frame")
    if not frame:
        if get_luminance(sunken) < get_luminance(surface) and deep(sunken):
            frame = sunken
        else:
            frame = step_toward(surface, "#000000", deep)
            if not deep(frame):
                frame = step_toward(surface, "#ffffff", deep)

    well = theme_data.get("well") or step_toward(
        mix(surface, frame, 0.5), frame, _reads(surface, WELL_MIN_CONTRAST))

    border = theme_data.get("border", frame)
    edge = theme_data.get("pane_border")
    if not edge:
        away = (
            "#000000"
            if get_luminance(border) <= get_luminance(frame)
            else "#ffffff"
        )
        edge = step_toward(
            border, away, _reads(frame, PANE_BORDER_MIN_CONTRAST))

    mark = theme_data.get("splitter_mark")
    if not mark:
        visible = _reads(frame, SPLITTER_MARK_MIN_CONTRAST)
        quiet = theme_data.get("border_light", border)
        mark = next(
            (color for color in (border, quiet) if visible(color)), None
        ) or step_toward(quiet, theme_data.get("text", border), visible)

    return {
        "frame": frame,
        "well": well,
        "pane_border": edge,
        "splitter_mark": mark,
    }


# The splitter mark: this many square dots, each this many pixels a side,
# one dot apart. Short on purpose: a full-length line reads as a border.
_MARK_DOTS = 5
_MARK_DOT = 2


class _SplitterMark(QObject):
    """Paint a marked splitter's handles: the frame, and a short dot mark.

    Painted rather than drawn from a stylesheet image, so it needs no file
    and lands on whole device pixels at every screen scale.
    """

    def __init__(self, splitter: QSplitter):
        super().__init__(splitter)
        splitter.installEventFilter(self)
        self._watch()

    def _handles(self):
        splitter = self.parent()
        return [splitter.handle(index) for index in range(splitter.count())]

    def _watch(self) -> None:
        # Qt keeps one entry per filter, so installing again is harmless.
        for handle in self._handles():
            handle.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Watch handles as they appear; paint the ones of a marked splitter."""
        if isinstance(watched, QSplitter):
            # A handle is polished before its first paint, never after.
            if event.type() == QEvent.ChildPolished:
                self._watch()
            return False
        splitter = self.parent()
        if event.type() != QEvent.Paint or not splitter.property(
            FRAME_PROPERTY
        ):
            return False
        self._paint(watched, splitter.orientation() == Qt.Vertical)
        return True

    def _paint(self, handle: QWidget, across: bool) -> None:
        colors = _get_theme_namespace()
        painter = QPainter(handle)
        painter.fillRect(handle.rect(), QColor(colors.frame))
        # Device pixels from here on, so every dot is whole at any scale.
        ratio = painter.device().devicePixelRatioF()
        painter.setWorldTransform(QTransform.fromScale(1 / ratio, 1 / ratio))
        width = round(handle.width() * ratio)
        height = round(handle.height() * ratio)
        length, thickness = (width, height) if across else (height, width)
        dot = max(1, round(_MARK_DOT * ratio))
        start = (length - (_MARK_DOTS * 2 - 1) * dot) // 2
        cross = (thickness - dot) // 2
        ink = QColor(colors.splitter_mark)
        for index in range(_MARK_DOTS):
            along = start + index * dot * 2
            if across:
                painter.fillRect(along, cross, dot, dot, ink)
            else:
                painter.fillRect(cross, along, dot, dot, ink)
        painter.end()


def _token_map(theme_name: str) -> Dict[str, str]:
    """Build the ``@token`` -> value map for a theme.

    Single source of truth for stylesheet token resolution. Includes:
    flat theme color roles, flattened feedback colors
    (``@feedback_<level>_<part>``), computed on-accent colors, and the
    ``~icons`` folder path.

    Args:
        theme_name: Theme to resolve. Keys it omits come from the file's
            dark theme, then the built-in one.

    Returns:
        Mapping of placeholder (including the ``@``/``~`` prefix) to value.
    """
    theme_data = _theme_data(theme_name)

    tokens: Dict[str, str] = {
        f"@{key}": value
        for key, value in theme_data.items()
        if isinstance(value, str)
    }
    for key, value in _depth_colors(theme_data).items():
        tokens[f"@{key}"] = value

    # Feedback colors flatten to @feedback_<level>_<part>.
    for level, pair in _feedback(theme_name).items():
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

    (
        tokens["@primary_button"],
        tokens["@primary_button_hover"],
        tokens["@primary_button_pressed"],
    ) = _primary_button_fills(
        accent_primary, accent_secondary, text_on_primary, text_on_secondary
    )

    # Font roles flatten to @font_<role>, resolved against the families
    # Qt actually has so the sheet never names one it cannot honour.
    for role, entries in _font_config(theme_name).items():
        tokens[f"@font_{role}"] = _resolve_font_stack(entries)

    tokens["@button_radius"] = f"{BUTTON_RADIUS}px"
    # A bare number, for a sheet that writes its own unit: `@radiuspx`.
    tokens["@radius"] = str(BUTTON_RADIUS)

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


def _substitute(qss: str, tokens: Dict[str, str]) -> str:
    """Replace each placeholder, longest first so @border spares @border_light."""
    for key in sorted(tokens, key=len, reverse=True):
        qss = qss.replace(key, tokens[key])
    return qss


def resolve(qss: str, theme: Optional[str] = None) -> str:
    """Replace every ``@token`` and ``~icons`` placeholder in a stylesheet.

    Args:
        qss: Stylesheet text containing placeholders.
        theme: Theme whose values to substitute. Defaults to the current.

    Returns:
        The stylesheet with every known placeholder replaced.

    Examples:
        >>> fxstyle.resolve("QFrame { border-radius: @button_radius; }")
    """
    return _substitute(qss, _token_map(theme or get_theme()))


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
    return QColor(colors().surface).lightness() > 128


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

    available_themes = get_available_themes()

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


def apply_theme(theme: str) -> str:
    """Apply a theme to every themed root and emit ``theme_changed``.

    Args:
        theme: The theme name to apply (e.g., "dark", "light").

    Returns:
        The theme that was applied.

    Raises:
        ValueError: If the theme does not exist.
        TypeError: If `theme` is not a theme name.

    Examples:
        >>> fxstyle.apply_theme("dracula")
    """
    global _theme

    if not isinstance(theme, str):
        raise TypeError("apply_theme() takes a theme name")
    available_themes = get_available_themes()
    if theme not in available_themes:
        raise ValueError(
            f"Theme '{theme}' not found. Available themes: {available_themes}"
        )

    _theme = theme
    save_theme(theme)
    _colors_changed()
    return theme


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
        QStyle.SP_MessageBoxCritical: fxicons.get_icon("error", color="feedback_error_foreground"),
        QStyle.SP_MessageBoxInformation: fxicons.get_icon("info", color="feedback_info_foreground"),
        QStyle.SP_MessageBoxQuestion: fxicons.get_icon("help", color="feedback_success_foreground"),
        QStyle.SP_MessageBoxWarning: fxicons.get_icon("warning", color="feedback_warning_foreground"),
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

    def polish(self, widget):
        """Lay an item view's rows out again once the sheet has styled them."""
        super().polish(widget)
        # A view sized before its first polish keeps rows measured without
        # the sheet's item box; nothing else tells it to measure again.
        if isinstance(widget, QAbstractItemView):
            widget.scheduleDelayedItemsLayout()


###### Stylesheet Functions


def replace_colors(stylesheet: str, colors_dict: Optional[dict] = None) -> str:
    """Replace color placeholders in a stylesheet with actual color values.

    Placeholders are `@key`; the longest key is replaced first.

    Args:
        stylesheet: The stylesheet string containing color placeholders.
        colors_dict: Dictionary containing color definitions. Only top-level
            non-dict values are used. Defaults to every token of the
            current theme, as `resolve` substitutes them.

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
        return resolve(stylesheet)
    return _substitute(stylesheet, {
        f"@{key}": str(value)
        for key, value in colors_dict.items()
        if not isinstance(value, dict)
    })


def _font_stylesheet() -> str:
    """Return the title rule: a marked title takes the title family.

    The body family and size are the root font (:func:`font`), which a
    widget's own ``setFont`` overrides; the title rule outranks it.
    """
    return (
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
    return _build(STYLE_FILE, theme)


def _build(style_file, theme: Optional[str]) -> str:
    """Resolve the font block, `style_file` and every registered fragment."""
    parts = [_font_stylesheet()]
    if os.path.exists(style_file):
        with open(style_file, "r", encoding="utf-8") as in_file:
            parts.append(in_file.read())
    parts.extend(_widget_fragments.values())
    return resolve("\n".join(parts), theme)


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
    _themed_roots.add(root)
    if isinstance(root, QWidget):
        root.setProperty(ROOT_PROPERTY, True)
    _apply_to_root(root, build_stylesheet(), palette(), font())


def _reapply_to_roots() -> None:
    """Re-apply the current theme palette, font and sheet to all live roots."""
    if not _themed_roots:
        return
    sheet = build_stylesheet()
    theme_palette = palette()
    theme_font = font()
    for root in list(_themed_roots):
        if _compat.is_valid(root):
            _apply_to_root(root, sheet, theme_palette, theme_font)


# Inside a host, Qt hands a widget made or moved under a styled parent the
# host's palette and font, never the root's; only a sheet rule reaches it.
# Put before the base sheet, so every class rule there still wins.
_HOST_RULES = f"""
QWidget {{
    background-color: transparent;
    font-family: @font_body;
    font-size: {FONT_SIZE}px;@weight
}}
[{ROOT_PROPERTY}="true"], QMainWindow, QDialog {{
    background-color: @surface;
}}
"""


def _host_rules(theme: Optional[str] = None) -> str:
    """Return the host rules resolved, with the body weight if one is set."""
    theme = theme or get_theme()
    weight, _hinting = _shape(theme, "body")
    extra = f" font-weight: {weight};" if weight is not None else ""
    return resolve(_HOST_RULES.replace("@weight", extra), theme)


def _in_host(root: QObject) -> bool:
    """Return whether `root` is a widget in an application fxgui does not theme."""
    app = QApplication.instance()
    return isinstance(root, QWidget) and app not in _themed_roots


def _apply_to_root(root, sheet: str, theme_palette, theme_font) -> None:
    root.setPalette(theme_palette)
    root.setFont(theme_font)
    if _in_host(root):
        sheet = _host_rules() + sheet
    root.setStyleSheet(sheet)


# Palette role -> token, for every colour group; then the Disabled group.
_PALETTE_ROLES = {
    "Window": "surface",
    "WindowText": "text",
    "Base": "surface_sunken",
    "AlternateBase": "surface_alt",
    "Text": "text",
    "Button": "surface",
    "ButtonText": "text",
    "BrightText": "text_on_accent_primary",
    "Highlight": "accent_primary",
    "HighlightedText": "text_on_accent_primary",
    "ToolTipBase": "tooltip",
    "ToolTipText": "text",
    "PlaceholderText": "text_muted",
    "Link": "accent_primary",
    "LinkVisited": "accent_secondary",
    "Accent": "accent_primary",
}
_DISABLED_ROLES = {
    "WindowText": "text_disabled",
    "Text": "text_disabled",
    "ButtonText": "text_disabled",
    "PlaceholderText": "text_disabled",
    "HighlightedText": "text_disabled",
}


def palette(theme: Optional[str] = None) -> QPalette:
    """Build a QPalette from a theme's resolved colours.

    Roles a binding lacks (``Accent`` before Qt 6.6) are skipped.

    Args:
        theme: Theme name. Defaults to the current theme.

    Returns:
        The palette every themed root wears alongside the sheet.
    """
    if theme is None or theme == get_theme():
        tokens = vars(_get_theme_namespace())
    else:
        tokens = {
            name[1:]: value for name, value in _token_map(theme).items()
            if name.startswith("@")
        }
    result = QPalette()
    for roles, group in (
        (_PALETTE_ROLES, QPalette.All),
        (_DISABLED_ROLES, QPalette.Disabled),
    ):
        for role_name, token in roles.items():
            role = getattr(QPalette, role_name, None)
            if role is not None:
                result.setColor(group, role, QColor(tokens[token]))
    return result


def font(theme: Optional[str] = None, role: str = "body") -> QFont:
    """Build a role's font: its installed families, weight and hinting.

    The body role is the root font, set on every themed root with the
    palette; a child's own ``setFont`` wins over it, which a sheet
    ``font`` rule would not allow. Another role is for code that takes a
    QFont, such as a QGraphicsTextItem.

    Args:
        theme: Theme name. Defaults to the current theme.
        role: A role of the ``fonts:`` block. Defaults to "body".

    Raises:
        ValueError: If the role names a weight or hinting fxgui lacks.

    Examples:
        >>> item.setFont(fxstyle.font(role="mono"))
    """
    theme = theme or get_theme()
    families = [
        name.strip().strip('"')
        for name in get_font_family(role, theme).split(",")
    ]
    result = QFont()
    named = [name for name in families if name not in _GENERIC_FONT_FAMILIES]
    result.setFamilies(named)
    if named:
        result.setFamily(named[0])
    result.setPixelSize(FONT_SIZE)
    weight, hinting = _shape(theme, role)
    if weight is not None:
        result.setWeight(_WEIGHTS[weight])
    if hinting is not None:
        result.setHintingPreference(_HINTING[hinting])
    return result


def load_stylesheet(
    style_file: str = STYLE_FILE,
    extra: Optional[str] = None,
    theme: Optional[str] = None,
) -> str:
    """Return `build_stylesheet` over another QSS file; changes nothing.

    For styling a DCC window by hand: it carries the host rules a widget
    root needs, and the window wants `palette()` and `font()` set too.

    Args:
        style_file: The path to the QSS file. Defaults to `STYLE_FILE`.
        extra: Extra stylesheet content to append. Defaults to None.
        theme: The theme to use. Defaults to the current theme.

    Returns:
        The resolved stylesheet, or "" when `style_file` does not exist.
    """
    if not os.path.exists(style_file):
        return ""
    host = _host_rules(theme)
    return host + _build(style_file, theme) + (extra or "")
