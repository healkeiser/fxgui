"""This module provides functionality for handling icons in a VFX
application.
"""

# Built-in
from typing import Optional, List
from pathlib import Path
from functools import lru_cache

# Third-party
from qtpy.QtGui import (
    QIcon,
    QColor,
    QPainter,
    QPixmap,
    QBitmap,
)
from qtpy.QtCore import Qt, qVersion


# Constants
_LIBRARIES_ROOT = Path(__file__).parent / "icons"
_DEFAULT_LIBRARY = "material"

# Globals
_LIBRARIES_INFO = {
    "dcc": {
        "pattern": "{root}/{library}/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": None,
        },
    },
    "material": {
        "pattern": "{root}/{library}/{extension}/{icon_name}/{style}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "round",
        },
    },
    "fontawesome": {
        "pattern": "{root}/{library}/{extension}s/{style}/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "regular",
        },
    },
}
_ICON_DEFAULTS = {
    # Attributes
    "color": "#b4b4b4",
    "width": 12,
    "height": 12,
    # Library
    "library": _DEFAULT_LIBRARY,
    "style": _LIBRARIES_INFO[_DEFAULT_LIBRARY]["defaults"]["style"],
    "extension": _LIBRARIES_INFO[_DEFAULT_LIBRARY]["defaults"]["extension"],
}


def set_icon_defaults(**kwargs):
    """Set the default values for the icons.

    Args:
        **kwargs: The default values to set.

    Examples:
        >>> set_icon_defaults(color="red", width=32, height=32)
    """

    valid_keys = _ICON_DEFAULTS.keys()
    if not all(key in valid_keys for key in kwargs.keys()):
        raise ValueError(f"Invalid key in {kwargs.keys()}.")

    for key, value in kwargs.items():
        if key in _ICON_DEFAULTS:
            _ICON_DEFAULTS[key] = value


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
    verify: bool = True,
) -> str:
    """Get the path of the specified icon.

    Args:
        icon_name: The name of the icon.
        library: The library of the icon. Defaults to `None`.
        style: The style of the icon. Defaults to `None`.
        extension: The extension of the icon. Defaults to `None`.
        verify: Whether to verify if the icon exists. Defaults to `True`.

    Raises:
        FileNotFoundError: If verify is `True` and the icon does not exist.

    Returns:
        str: The path of the icon.
    """

    if library is None:
        library = _DEFAULT_LIBRARY
    if style is None:
        style = _LIBRARIES_INFO[library]["defaults"].get("style")
    if extension is None:
        extension = _LIBRARIES_INFO[library]["defaults"].get("extension")

    pattern = _LIBRARIES_INFO[library]["pattern"]
    path = pattern.format(
        icon_name=icon_name,
        style=style,
        library=library,
        extension=extension,
        root=_LIBRARIES_ROOT,
    ).replace("\\", "/")

    if verify and not Path(path).exists():
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
    if qVersion() < "4.8.0":
        pixmap.fill(qcolor)
        pixmap.setMask(mask)
        return pixmap

    if qVersion() < "5.6.0":
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.setPen(qcolor)
        painter.drawPixmap(pixmap.rect(), mask, mask.rect())
        painter.end()
        return pixmap

    qpixmap = pixmap.toImage()
    for y in range(qpixmap.height()):
        for x in range(qpixmap.width()):
            alpha = qpixmap.pixelColor(x, y).alpha()
            qcolor.setAlpha(alpha)
            qpixmap.setPixelColor(x, y, qcolor)
    pixmap = QPixmap().fromImage(qpixmap)
    return pixmap


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
        library = _ICON_DEFAULTS["library"]
    if style is None:
        style = _ICON_DEFAULTS["style"]
    if extension is None:
        extension = _ICON_DEFAULTS["extension"]
    if width is None:
        width = _ICON_DEFAULTS["width"]
    if height is None:
        height = _ICON_DEFAULTS["height"]
    if color is None:
        color = _ICON_DEFAULTS["color"]

    path = get_icon_path(
        icon_name,
        library=library,
        style=style,
        extension=extension,
        verify=True,
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
