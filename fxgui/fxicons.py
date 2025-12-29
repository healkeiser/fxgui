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
from typing import Dict, List, Optional

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


def set_icon_defaults(apply_to: Optional[str] = None, **kwargs):
    """Set the default values for the icons.

    Args:
        apply_to: The library to apply the defaults to. If set to `None`, the
            defaults will be applied to all libraries. Defaults to `None`.
        **kwargs: The default values to set.

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
    size = mask.size()
    return any(
        image.pixelIndex(x, y) == 0
        for x in range(size.width())
        for y in range(size.height())
    )


def change_pixmap_color(pixmap: QPixmap, color: str) -> QPixmap:
    """Change the color of a pixmap.

    Args:
        pixmap (QPixmap): The pixmap to change the color of.
        color (str): The color to apply.

    Returns:
        QPixmap: The pixmap with the new color applied.
    """

    mask = pixmap.createMaskFromColor(Qt.transparent)
    if not has_transparency(mask):
        return pixmap

    qcolor = QColor(color)
    qpixmap = pixmap.toImage()

    for y in range(qpixmap.height()):
        for x in range(qpixmap.width()):
            alpha = qpixmap.pixelColor(x, y).alpha()
            qcolor.setAlpha(alpha)
            qpixmap.setPixelColor(x, y, qcolor)

    return QPixmap.fromImage(qpixmap)


@lru_cache(maxsize=128)
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

    if width is None:
        width = defaults["width"]
    if height is None:
        height = defaults["height"]
    if color is None:
        color = defaults["color"]

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


@lru_cache(maxsize=128)
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

    # Get the `QPixmap` of the icon
    qpixmap = get_pixmap(
        icon_name, width, height, color, library, style, extension
    )

    # Create a `QIcon` and add the normal state pixmap
    icon = QIcon(qpixmap)

    # `QPixmap` for disabled state - use semi-transparent grey overlay
    disabled_pixmap = qpixmap.copy()
    painter = QPainter(disabled_pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    # Use a consistent disabled grey color with reduced opacity effect
    disabled_color = QColor(128, 128, 128, 180)
    painter.fillRect(disabled_pixmap.rect(), disabled_color)
    painter.end()

    # Add disabled state pixmap to the `QIcon`
    icon.addPixmap(disabled_pixmap, QIcon.Disabled)

    return icon


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

    get_icon.cache_clear()
    get_pixmap.cache_clear()
