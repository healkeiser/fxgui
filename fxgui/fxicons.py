"""Icon management functionality for `fxgui`.

This module provides utilities for loading, caching, and manipulating icons
from multiple icon libraries including Material Icons, Font Awesome, Simple
Icons, and custom DCC (Digital Content Creation) icons.

The module supports:
    - Multiple icon libraries with configurable defaults
    - Icon color customization
    - Automatic caching using LRU cache for performance
    - Icon superposition for composite icons
    - Pixmap and QIcon conversion utilities

Functions:
    get_icon: Get a QIcon from an icon library.
    get_pixmap: Get a QPixmap from an icon library.
    get_icon_path: Get the file path of an icon.
    clear_icon_cache: Clear the icon LRU cache.
    set_default_icon_library: Set the default icon library.
    set_icon_defaults: Configure default icon parameters.
    add_library: Add a custom icon library.

Examples:
    Basic icon usage:

    >>> from fxgui.fxicons import get_icon
    >>> icon = get_icon("home")
    >>> colored_icon = get_icon("settings", color="#FF5722")

    Using different libraries:

    >>> fa_icon = get_icon("lemon", library="fontawesome")
    >>> dcc_icon = get_icon("houdini", library="dcc")
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from functools import lru_cache
from pathlib import Path
import re
import weakref
from typing import Any, Dict, List, Optional

# Third-party
from qtpy.QtGui import (
    QIcon,
    QColor,
    QPainter,
    QPixmap,
    QBitmap,
)
from qtpy.QtCore import Qt, QSize

# Internal
from fxgui import fxconstants


# Public API
__all__ = [
    "set_default_icon_library",
    "set_icon_defaults",
    "add_library",
    "get_available_libraries",
    "get_available_icons_in_library",
    "get_icon_path",
    "get_icon",
    "get_icon_color",
    "get_pixmap",
    "change_pixmap_color",
    "convert_icon_to_pixmap",
    "superpose_icons",
    "clear_icon_cache",
    "sync_colors_with_theme",
    "set_icon",
    "refresh_all_icons",
]


# Globals
_libraries_info = {
    "beacon": {
        "pattern": "{root}/{library}/{extension}/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": None,
            "color": None,
            "width": 48,
            "height": 48,
        },
    },
    "dcc": {
        "pattern": "{root}/{library}/{extension}/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": None,
            "color": None,
            "width": 48,
            "height": 48,
        },
    },
    "material": {
        "pattern": "{root}/{library}/{extension}/{icon_name}/{style}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "round",
            "color": "#B4B4B4",
            "width": 48,
            "height": 48,
        },
    },
    "fontawesome": {
        "pattern": "{root}/{library}/{extension}s/{style}/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "solid",
            "color": "#B4B4B4",
            "width": 48,
            "height": 48,
        },
    },
    "simple": {
        "pattern": "{root}/{library}/icons/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "solid",
            "color": "#B4B4B4",
            "width": 48,
            "height": 48,
        },
    },
}
_default_library = "material"

# Widget registry for automatic icon refresh
# Uses WeakSet to avoid preventing garbage collection of widgets
_icon_widgets = weakref.WeakSet()


def set_default_icon_library(library: str):
    """Set the default icon library.

    Args:
        library: The name of the library to set as default.

    Raises:
        ValueError: If the library does not exist.

    Examples:
        >>> set_default_icon_library("fontawesome")
    """

    global _default_library
    if library not in _libraries_info:
        raise ValueError(f"Library '{library}' does not exist.")
    _default_library = library


def set_icon_defaults(apply_to: Optional[str] = None, **kwargs: Any) -> None:
    """Set the default values for the icons.

    Args:
        apply_to: The library to apply the defaults to. If set to `None`, the
            defaults will be applied to all libraries. Defaults to `None`.
        **kwargs (Any): The default values to set.

    Examples:
        >>> set_icon_defaults(color="red", width=32, height=32)
        >>> set_icon_defaults(apply_to="material", color="blue")
    """

    valid_keys = _libraries_info[_default_library]["defaults"].keys()
    if not all(key in valid_keys for key in kwargs.keys()):
        raise ValueError(f"Invalid key in {kwargs.keys()}.")

    if apply_to is None:
        # Apply to all libraries
        for library_info in _libraries_info.values():
            for key, value in kwargs.items():
                library_info["defaults"][key] = value
    else:
        # Apply to specific library
        if apply_to not in _libraries_info:
            raise ValueError(f"Library '{apply_to}' does not exist.")
        for key, value in kwargs.items():
            _libraries_info[apply_to]["defaults"][key] = value


def add_library(
    library: str, pattern: str, defaults: Dict, root: Optional[Path] = None
):
    """Add a new icon library to the available libraries.

    Args:
        library: The name of the library.
        pattern: The pattern to use for the library. Valid placeholders are:
            - `{root}`: The root path for the library.
            - `{library}`: The name of the library.
            - `{style}`: The style of the icon.
            - `{icon_name}`: The name of the icon.
            - `{extension}`: The extension of the icon.
        defaults: The default values for the library.
        root: The root path for the library. Defaults to
            `fxconstants.ICONS_ROOT`.

    Examples:
        >>> add_library(
        ...    library="houdini",
        ...    pattern="{root}/{library}/{style}/{icon_name}.{extension}",
        ...    defaults={
        ...        "extension": "svg",
        ...        "style": "CROWDS",
        ...        "color": None,
        ...        "width": 48,
        ...        "height": 48,
        ...    },
        ...    root=str(Path.home() / "Pictures" / "Icons"),
        ... )
    """

    # Check for valid keys in `defaults`
    valid_keys = _libraries_info[_default_library]["defaults"].keys()
    if not all(key in valid_keys for key in defaults.keys()):
        raise ValueError(f"Invalid key(s) in defaults: {defaults.keys()}")

    # Check for valid placeholders in `pattern`
    valid_placeholders = {
        "{root}",
        "{library}",
        "{style}",
        "{icon_name}",
        "{extension}",
    }
    placeholders = set(re.findall(r"\{[a-zA-Z_]+\}", pattern))
    if not placeholders.issubset(valid_placeholders):
        raise ValueError(f"Invalid placeholder(s) in pattern: {placeholders}")
    if root is None:
        root = fxconstants.ICONS_ROOT

    # Add the library
    _libraries_info[library] = {
        "pattern": pattern,
        "defaults": defaults,
        "root": root,
    }


def get_available_libraries() -> List[str]:
    """Get all available icon libraries.

    Returns:
        List[str]: The available icon libraries.

    Examples:
        >>> print(get_available_libraries())
        ["beacon", "dcc", "material", "fontawesome"]
    """
    return list(_libraries_info.keys())


def get_available_icons_in_library(library: str) -> List[str]:
    """Get all available icon names in the specified library.

    Args:
        library (str): The name of the library.

    Returns:
        List[str]: The available icon names in the library.

    Raises:
        ValueError: If the library does not exist.
        FileNotFoundError: If no icons are found in the library.

    Examples:
        >>> print(get_available_icons_in_library("dcc"))
        ["3d_equalizer", "adobe_photoshop", "blender", "hiero"]
    """

    library_path = fxconstants.ICONS_ROOT / library
    if not library_path.exists():
        raise ValueError(f"Library '{library}' does not exist.")

    icon_files = library_path.glob("**/*.*")
    icon_names = sorted(icon_file.stem for icon_file in icon_files)

    if not icon_names:
        raise FileNotFoundError(f"No icons found in library '{library}'.")

    return icon_names


def get_icon_path(
    icon_name: str,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
) -> str:
    """Get the path of the specified icon.

    Args:
        icon_name: The name of the icon.
        library: The library of the icon. Defaults to `None`.
        style: The style of the icon. Defaults to `None`.
        extension: The extension of the icon. Defaults to `None`.

    Raises:
        FileNotFoundError: If verify is `True` and the icon does not exist.

    Returns:
        str: The path of the icon.

    Examples:
        >>> get_icon_path("add")
        >>> get_icon_path("lemon", library="fontawesome")
    """

    if library is None:
        library = _default_library
    if style is None:
        style = _libraries_info[library]["defaults"].get("style")
    if extension is None:
        extension = _libraries_info[library]["defaults"].get("extension")

    root = _libraries_info[library].get("root", fxconstants.ICONS_ROOT)
    pattern = _libraries_info[library]["pattern"]
    path = pattern.format(
        icon_name=icon_name,
        style=style,
        library=library,
        extension=extension,
        root=root,
    ).replace("\\", "/")

    if not Path(path).exists():
        raise FileNotFoundError(f"Icon path '{path}' does not exist.")

    return path


def has_transparency(mask: QBitmap) -> bool:
    """Check if a mask has any transparency.

    Args:
        mask: The mask to check.

    Returns:
        bool: `True` if the mask has transparency, `False` otherwise.
    """
    image = mask.toImage()
    width = mask.width()
    height = mask.height()

    # Early exit: scan row by row for better cache locality
    for y in range(height):
        for x in range(width):
            if image.pixelIndex(x, y) == 0:
                return True
    return False


def change_pixmap_color(pixmap: QPixmap, color: str) -> QPixmap:
    """Change the color of a pixmap.

    Uses QPainter with composition mode for efficient colorization
    while preserving the original alpha channel.

    Args:
        pixmap (QPixmap): The pixmap to change the color of.
        color (str): The color to apply.

    Returns:
        QPixmap: The pixmap with the new color applied.
    """
    mask = pixmap.createMaskFromColor(Qt.transparent)
    if not has_transparency(mask):
        return pixmap

    # Create a copy to avoid modifying the original
    colored_pixmap = pixmap.copy()

    # Use QPainter with SourceIn composition to colorize while preserving alpha
    painter = QPainter(colored_pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(colored_pixmap.rect(), QColor(color))
    painter.end()

    return colored_pixmap


def _get_pixmap_internal(
    icon_name: str,
    width: int,
    height: int,
    color: Optional[str],
    library: str,
    style: Optional[str],
    extension: Optional[str],
) -> QPixmap:
    """Internal function to get a QPixmap with resolved parameters.

    This is the cached version that takes fully resolved parameters.
    """
    path = get_icon_path(
        icon_name,
        library=library,
        style=style,
        extension=extension,
    )
    qpixmap = QIcon(path).pixmap(width, height)
    if color is not None:
        qpixmap = change_pixmap_color(qpixmap, color)
    return qpixmap


# Apply LRU cache to the internal function
_get_pixmap_cached = lru_cache(maxsize=512)(_get_pixmap_internal)


def get_pixmap(
    icon_name: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    color: Optional[str] = None,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
) -> QPixmap:
    """Get a QPixmap of the specified icon.

    Args:
        icon_name: The name of the icon.
        width: The width of the pixmap. Defaults to `None`.
        height: The height of the pixmap. Defaults to `None`.
        color: The color to convert the pixmap to. Defaults to `None`.
        library: The library of the icon. Defaults to `None`.
        style: The style of the icon. Defaults to `None`.
        extension: The extension of the icon. Defaults to `None`.

    Returns:
        QPixmap: The QPixmap of the icon.

    Examples:
        >>> get_pixmap("add", color="red")
        >>> get_pixmap("lemon", library="fontawesome")
    """

    if library is None:
        library = _default_library

    defaults = _libraries_info[library]["defaults"]

    # Resolve defaults BEFORE caching - these become part of the cache key
    if width is None:
        width = defaults["width"]
    if height is None:
        height = defaults["height"]
    if color is None:
        color = defaults["color"]

    return _get_pixmap_cached(
        icon_name, width, height, color, library, style, extension
    )


def _get_icon_internal(
    icon_name: str,
    width: int,
    height: int,
    color: Optional[str],
    disabled_color: str,
    library: str,
    style: Optional[str],
    extension: Optional[str],
) -> QIcon:
    """Internal function to get a QIcon with resolved parameters.

    This is the cached version that takes fully resolved parameters.
    """
    # Get the `QPixmap` of the icon
    qpixmap = _get_pixmap_cached(
        icon_name, width, height, color, library, style, extension
    )

    # Create a `QIcon` and add the normal state pixmap
    icon = QIcon(qpixmap)

    # `QPixmap` for disabled state - use derived muted color
    disabled_pixmap = qpixmap.copy()
    painter = QPainter(disabled_pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(disabled_pixmap.rect(), QColor(disabled_color))
    painter.end()
    icon.addPixmap(disabled_pixmap, QIcon.Disabled)

    return icon


# Apply LRU cache to the internal function
_get_icon_cached = lru_cache(maxsize=512)(_get_icon_internal)


def get_icon(
    icon_name: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    color: Optional[str] = None,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
) -> QIcon:
    """Get a QIcon of the specified icon.

    Args:
        icon_name: The name of the icon.
        width: The width of the pixmap. Defaults to `None`.
        height: The height of the pixmap. Defaults to `None`.
        color: The color to convert the pixmap to. Defaults to `None`.
        library: The library of the icon. Defaults to `None`.
        style: The style of the icon. Defaults to `None`.
        extension: The extension of the icon. Defaults to `None`.

    Returns:
        QIcon: The QIcon of the icon.

    Examples:
        >>> get_icon("add", color="red")
        >>> get_icon("lemon", library="fontawesome")
    """

    if library is None:
        library = _default_library

    defaults = _libraries_info[library]["defaults"]

    # Resolve defaults BEFORE caching - these become part of the cache key
    if width is None:
        width = defaults["width"]
    if height is None:
        height = defaults["height"]
    if color is None:
        color = defaults["color"]

    # Get disabled icon color from theme
    disabled_color = _get_disabled_icon_color()

    return _get_icon_cached(
        icon_name,
        width,
        height,
        color,
        disabled_color,
        library,
        style,
        extension,
    )


def convert_icon_to_pixmap(
    icon: QIcon, desired_size: Optional[QSize] = None
) -> Optional[QPixmap]:
    """Converts a QIcon to a QPixmap.

    Args:
        icon: The QIcon to convert.
        desired_size: The desired size for the pixmap (QSize). If `None`,
            the default size is 48x48.

    Returns:
        A QPixmap or `None` if no suitable pixmap is available.

    Examples:
        Let the size be decided
        >>> icon = hou.qt.Icon("MISC_python")
        >>> pixmap = convert_icon_to_pixmap(icon)

        Choose a size
        >>> icon = hou.qt.Icon("MISC_python")
        >>> pixmap = convert_icon_to_pixmap(icon, QSize(48, 48))
    """

    if desired_size:
        return icon.pixmap(desired_size)
    return icon.pixmap(QSize(48, 48))


def superpose_icons(*icons: QIcon) -> QIcon:
    """Superpose multiple icons.

    Args:
        *icons: Icons to superpose. Add the icons in the order you want them
            to be superposed, from background to foreground.

    Returns:
        QIcon: The QIcon of the superposed icons.

    Notes:
        The size of the resulting icon is the size of the first icon.

    Examples:
        >>> icon_a = get_icon("add")
        >>> icon_b = get_icon("lemon", library="fontawesome")
        >>> superposed_icon = superpose_icons(icon_a, icon_b)
    """

    if not icons:
        return QIcon()

    # Use the size of the first icon
    size = icons[0].availableSizes()[0]
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    for icon in icons:
        icon_pixmap = icon.pixmap(size)
        painter.drawPixmap(0, 0, icon_pixmap)
    painter.end()

    return QIcon(pixmap)


def clear_icon_cache() -> None:
    """Clear the icon and pixmap LRU caches.

    This should be called when changing themes to ensure icons are
    regenerated with the new color scheme.

    Examples:
        >>> clear_icon_cache()
    """

    _get_icon_cached.cache_clear()
    _get_pixmap_cached.cache_clear()


def get_icon_color() -> str:
    """Get the current default icon color.

    Returns the icon color from the current theme. This is the canonical
    source for icon color and is synchronized with the theme.

    Returns:
        The current default icon color as a hex string.

    Examples:
        >>> color = get_icon_color()
        >>> print(color)  # "#b4b4b4" for dark theme
    """
    # Import here to avoid circular imports
    from fxgui import fxstyle

    return fxstyle.get_icon_color()


def _get_disabled_icon_color() -> str:
    """Get the disabled icon color derived from the main icon color.

    Creates a muted version of the icon color by significantly reducing
    opacity and shifting toward neutral gray for clear visual distinction.

    Returns:
        The disabled icon color as a hex string (with alpha).
    """
    icon_color = get_icon_color()
    if not icon_color:
        return "#80808060"

    # Parse the color
    color = QColor(icon_color)
    h, s, l, a = color.getHslF()

    # Completely desaturate and move toward middle gray
    # This ensures disabled icons are clearly distinguishable regardless
    # of the original icon color
    new_s = 0  # Fully desaturated (grayscale)
    new_l = 0.5  # Middle gray lightness

    # Use low alpha for the "faded out" disabled look
    color.setHslF(h, new_s, new_l, 0.35)
    return color.name(QColor.HexArgb)


def sync_colors_with_theme() -> None:
    """Synchronize icon colors with the current theme from fxstyle.

    This function reads the icon color from the current theme's JSONC
    configuration and updates all icon library defaults accordingly.
    It also clears the icon cache and refreshes all registered widget icons.

    This is automatically called by `fxstyle.apply_theme()`, but can
    also be called manually when needed.

    Examples:
        >>> from fxgui import fxicons
        >>> fxicons.sync_colors_with_theme()
    """
    # Import here to avoid circular imports
    from fxgui import fxstyle

    # Get the icon color from the current theme
    theme_colors = fxstyle.get_theme_colors()
    icon_color = theme_colors.get("icon", "#b4b4b4")

    # Update all libraries that support colorization
    for library_name, library_info in _libraries_info.items():
        # Only update libraries that have a default color set
        # (beacon and dcc don't colorize by default)
        if library_info["defaults"].get("color") is not None:
            library_info["defaults"]["color"] = icon_color

    # Clear the cache so icons regenerate with new colors
    clear_icon_cache()

    # Refresh all registered widget icons
    refresh_all_icons()


def set_icon(
    widget: Any, icon_name: str, theme_color: bool = True, **kwargs: Any
) -> QIcon:
    """Set an icon on a widget and register it for automatic theme updates.

    This is the recommended way to set icons on widgets. The icon will
    automatically refresh when the theme changes.

    Args:
        widget (Any): The widget to set the icon on (QAction, QPushButton, etc.).
        icon_name (str): The name of the icon.
        theme_color (bool): If True (default), the icon color will update to
            match the theme on theme changes. If False, the explicit color
            passed in kwargs will be preserved across theme changes.
        **kwargs (Any): Optional parameters passed to get_icon (width, height,
            color, library, style, extension).

    Returns:
        The QIcon that was set on the widget.

    Examples:
        >>> from fxgui import fxicons
        >>> # Icon follows theme color
        >>> fxicons.set_icon(my_button, "save")
        >>> # Icon keeps explicit color across theme changes
        >>> fxicons.set_icon(indicator, "check", theme_color=False, color="#00ff00")
    """
    icon = get_icon(icon_name, **kwargs)

    if hasattr(widget, "setIcon"):
        widget.setIcon(icon)

    # Store icon name and settings for refresh
    widget.setProperty("_fxicon_name", icon_name)
    widget.setProperty("_fxicon_theme_color", theme_color)
    if kwargs:
        widget.setProperty("_fxicon_kwargs", kwargs)

    _icon_widgets.add(widget)
    return icon


def refresh_all_icons() -> None:
    """Refresh icons on all registered widgets.

    This is automatically called by `sync_colors_with_theme()`, but can
    be called manually if needed.
    """
    from qtpy.QtWidgets import QWidget
    from qtpy.shiboken import isValid as is_valid

    for widget in list(_icon_widgets):
        # Skip widgets whose C++ object has been deleted
        if not is_valid(widget):
            continue

        try:
            icon_name = widget.property("_fxicon_name")
            if icon_name:
                kwargs = widget.property("_fxicon_kwargs") or {}
                theme_color = widget.property("_fxicon_theme_color")

                # Only reset color if theme_color is True (or not set, for backwards compat)
                if theme_color is not False:
                    kwargs.pop("color", None)

                icon = get_icon(icon_name, **kwargs)

                if hasattr(widget, "setIcon"):
                    widget.setIcon(icon)

                    # Force visual update for QActions
                    if hasattr(widget, "associatedWidgets"):
                        for assoc_widget in widget.associatedWidgets():
                            if isinstance(assoc_widget, QWidget):
                                assoc_widget.update()
        except RuntimeError:
            # Widget was deleted between validity check and access
            pass
