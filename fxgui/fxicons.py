"""This module provides functionality for handling icons."""

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
from qtpy.QtCore import Qt

# Internal
from fxgui import fxconstants

# Constants
_LIBRARIES_ROOT = fxconstants.ICONS_ROOT

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
}
_default_library = "material"


def set_default_icon_library(library: str):
    """Set the default icon library.

    Args:
        library: The name of the library to set as default.

    Raises:
        ValueError: If the library does not exist.
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
        root: The root path for the library. Defaults to `_LIBRARIES_ROOT`.

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
        ...    root=str(Path.home() / "OneDrive" / "Pictures" / "Icons"),
        ... )
    """

    valid_keys = _libraries_info[_default_library]["defaults"].keys()
    if not all(key in valid_keys for key in defaults.keys()):
        raise ValueError(f"Invalid key(s) in defaults: {defaults.keys()}")

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
        root = _LIBRARIES_ROOT

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
        ["beacon", "dcc", "material"]
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
    library_path = _LIBRARIES_ROOT / library
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
    """
    if library is None:
        library = _default_library
    if style is None:
        style = _libraries_info[library]["defaults"].get("style")
    if extension is None:
        extension = _libraries_info[library]["defaults"].get("extension")

    root = _libraries_info[library].get("root", _LIBRARIES_ROOT)
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
    """
    qpixmap = get_pixmap(
        icon_name, width, height, color, library, style, extension
    )
    return QIcon(qpixmap)


def superpose_icons(*icons: QIcon) -> QIcon:
    """Superpose multiple icons.

    Args:
        *icons: Icons to superpose. Add the icons in the order you want them
            to be superposed, from background to foreground.

    Returns:
        QIcon: The QIcon of the superposed icons.

    Notes:
        The size of the resulting icon is the size of the first icon.
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
