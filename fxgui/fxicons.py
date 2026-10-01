"""Icon management functionality for `fxgui`.

This module provides utilities for loading, caching, and manipulating icons
from multiple icon libraries including Material Icons, Font Awesome, Simple
Icons, and custom DCC (Digital Content Creation) icons.

The module supports:
    - Multiple icon libraries with configurable defaults
    - Icon color customization
    - Icons that take the theme's colours when drawn, cached in QPixmapCache
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
import glob
from pathlib import Path
import re
import traceback
from typing import Any, Dict, List, Optional, Union

# Third-party
from qtpy.QtGui import (
    QIcon,
    QIconEngine,
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPixmapCache,
)
from qtpy.QtCore import Qt, QRect, QRectF, QSize

# Internal
from fxgui import fxconstants


# Public API
__all__ = [
    "set_default_icon_library",
    "set_icon_defaults",
    "add_library",
    "get_available_icons_in_library",
    "get_icon_path",
    "get_icon",
    "get_icon_color",
    "get_pixmap",
    "change_pixmap_color",
    "superpose_icons",
    "rounded_pixmap",
    "clear_icon_cache",
    "set_icon",
]


# The modes an icon names an ink for, and each one's default ink.
_MODES = {
    "normal": QIcon.Normal,
    "active": QIcon.Active,
    "selected": QIcon.Selected,
    "disabled": QIcon.Disabled,
}
_DEFAULT_INKS = {
    "active": "icon_on_accent_secondary",
    "selected": "icon_on_accent_primary",
}

# Opacity of a disabled icon, monochrome or full-colour.
_DISABLED_ALPHA = 0.35

# Globals
_libraries_info = {
    "beacon": {
        "recolor": True,
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
        "recolor": False,
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
        "recolor": True,
        "pattern": "{root}/{library}/{extension}/{icon_name}/{style}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "round",
            "color": "icon",
            "width": 48,
            "height": 48,
        },
    },
    "fontawesome": {
        "recolor": True,
        "pattern": "{root}/{library}/{extension}s/{style}/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "solid",
            "color": "icon",
            "width": 48,
            "height": 48,
        },
    },
    "simple": {
        "recolor": True,
        "pattern": "{root}/{library}/icons/{icon_name}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "solid",
            "color": "icon",
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
    library: str,
    pattern: str,
    defaults: Dict,
    root: Optional[Path] = None,
    recolor: bool = True,
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
        recolor: Whether the icons are monochrome and take a colour. A
            full-colour library (logos) passes False; a colour asked of
            it is ignored.

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
        "recolor": recolor,
        "pattern": pattern,
        "defaults": defaults,
        "root": root,
    }


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

    if library not in _libraries_info:
        raise ValueError(f"Library '{library}' does not exist.")
    info = _libraries_info[library]
    defaults = info["defaults"]
    fields = {
        "root": str(info.get("root", fxconstants.ICONS_ROOT)),
        "library": library,
        "style": defaults.get("style") or "*",
        "extension": defaults.get("extension") or "*",
    }
    template = info["pattern"].format(icon_name="\0", **fields)
    template = template.replace("\\", "/")
    name = re.compile(
        re.escape(template).replace(r"\*", "[^/]*").replace("\0", "([^/]+)")
    )
    matches = (
        name.fullmatch(path.replace("\\", "/"))
        for path in glob.glob(template.replace("\0", "*"))
    )
    icon_names = sorted({match.group(1) for match in matches if match})

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


def change_pixmap_color(pixmap: QPixmap, color: str) -> QPixmap:
    """Return a copy of `pixmap` in `color`, its alpha kept.

    Args:
        pixmap (QPixmap): The pixmap to change the color of.
        color (str): The color to apply.

    Returns:
        QPixmap: The pixmap with the new color applied.
    """
    colored = pixmap.copy()
    painter = QPainter(colored)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(colored.rect(), QColor(color))
    painter.end()
    return colored


def _theme_ink(ink: Optional[str]) -> Optional[str]:
    """Return the colour `ink` names: a theme token's, or `ink` itself."""
    if not ink:
        return None
    from fxgui import fxstyle

    return vars(fxstyle.colors()).get(ink, ink)


def _faded(pixmap: QPixmap) -> QPixmap:
    """Return `pixmap` at the opacity a disabled icon is drawn with."""
    faded = QPixmap(pixmap.size())
    faded.setDevicePixelRatio(pixmap.devicePixelRatio())
    faded.fill(Qt.transparent)
    painter = QPainter(faded)
    painter.setOpacity(_DISABLED_ALPHA)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return faded


def _screen_dpr() -> float:
    """Return the primary screen's device pixel ratio (1.0 when headless).

    Icons rasterized at logical size look blurry on scaled displays (125% to
    200% is the norm on 4K monitors); rendering at physical resolution and
    tagging the pixmap with the ratio keeps them crisp.
    """
    from qtpy.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is not None:
        screen = app.primaryScreen()
        if screen is not None:
            return float(screen.devicePixelRatio())
    return 1.0


def _render_svg_to_pixmap(path: str, width: int, height: int) -> QPixmap:
    """Rasterize an SVG to a QPixmap using ``QSvgRenderer``.

    This deliberately bypasses ``QIcon(path).pixmap()`` / the ``qsvg``
    imageformat plugin: that plugin fails to load inside some embedded DCC
    interpreters (notably Cinema 4D), where it silently yields a blank pixmap.
    ``QSvgRenderer`` lives in the ``QtSvg`` module rather than the imageformat
    plugin chain, so it renders reliably in those hosts as well as standalone.

    Aspect ratio is preserved and the result centered, mirroring ``QIcon``.

    Args:
        path: Path to the SVG file.
        width: Target pixmap width.
        height: Target pixmap height.

    Returns:
        QPixmap: The rasterized icon.
    """
    # Lazy import so environments without QtSvg only fail when an SVG is needed.
    from qtpy.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(path)
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    default_size = renderer.defaultSize()
    if default_size.width() > 0 and default_size.height() > 0:
        # Scale the SVG's intrinsic size into the target box, keeping aspect.
        scaled = default_size.scaled(width, height, Qt.KeepAspectRatio)
        target = QRectF(
            (width - scaled.width()) / 2.0,
            (height - scaled.height()) / 2.0,
            scaled.width(),
            scaled.height(),
        )
        renderer.render(painter, target)
    else:
        renderer.render(painter)
    painter.end()

    return QPixmap.fromImage(image)


def _get_pixmap_internal(
    icon_name: str,
    width: int,
    height: int,
    color: Optional[str],
    library: str,
    style: Optional[str],
    extension: Optional[str],
    dpr: float = 1.0,
) -> QPixmap:
    """Internal function to get a QPixmap with resolved parameters.

    This is the cached version that takes fully resolved parameters.
    ``width``/``height`` are logical sizes; the pixmap is rendered at
    ``dpr`` times that and tagged with the ratio for crisp high-DPI display.
    """
    path = get_icon_path(
        icon_name,
        library=library,
        style=style,
        extension=extension,
    )
    return _raster(path, width, height, dpr, color)


def _raster(
    path: str, width: int, height: int, dpr: float, color: Optional[str]
) -> QPixmap:
    """Rasterize an icon file at `dpr` times its logical size, recoloured."""
    physical_width = max(1, int(round(width * dpr)))
    physical_height = max(1, int(round(height * dpr)))
    if path.lower().endswith(".svg"):
        qpixmap = _render_svg_to_pixmap(path, physical_width, physical_height)
    else:
        qpixmap = QIcon(path).pixmap(physical_width, physical_height)
    if color:
        qpixmap = change_pixmap_color(qpixmap, color)
    qpixmap.setDevicePixelRatio(dpr)
    return qpixmap


# Apply LRU cache to the internal function
_get_pixmap_cached = lru_cache(maxsize=512)(_get_pixmap_internal)


def _resolved(library, width, height, color):
    """Fill a library, size and colour left unset from the library defaults.

    A full-colour library answers no colour, whatever was asked.
    """
    library = library or _default_library
    info = _libraries_info[library]
    defaults = info["defaults"]
    if not info["recolor"]:
        color = None
    elif color is None:
        color = defaults["color"]
    return (
        library,
        defaults["width"] if width is None else width,
        defaults["height"] if height is None else height,
        color,
    )


def get_pixmap(
    icon_name: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    color: Optional[str] = None,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
    dpr: Optional[float] = None,
) -> QPixmap:
    """Get a QPixmap of the specified icon.

    Args:
        icon_name: The name of the icon.
        width: The width of the pixmap. Defaults to `None`.
        height: The height of the pixmap. Defaults to `None`.
        color: A theme token such as "text_muted", read now, or a colour.
            Defaults to the library's.
        library: The library of the icon. Defaults to `None`.
        style: The style of the icon. Defaults to `None`.
        extension: The extension of the icon. Defaults to `None`.
        dpr: The device pixel ratio to render at, such as a widget's
            `devicePixelRatioF()` on a denser second screen. Defaults to
            the primary screen's.

    Returns:
        QPixmap: The caller's own pixmap; changing it touches no other.

    Examples:
        >>> get_pixmap("add", color="red")
        >>> get_pixmap("lemon", library="fontawesome")
    """

    library, width, height, color = _resolved(library, width, height, color)
    # A copy: one shares the pixels until written, so a caller changing it
    # leaves the cached one alone.
    return QPixmap(_get_pixmap_cached(
        icon_name, width, height, _theme_ink(color), library, style, extension,
        _screen_dpr() if dpr is None else float(dpr),
    ))


class _ThemedIconEngine(QIconEngine):
    """Draw an icon file in the theme's colours of the moment.

    Nothing is baked: each draw resolves the mode's ink token through
    `fxstyle.colors()`, so a theme switch reaches every icon without a
    signal. Pixmaps land in QPixmapCache keyed by file, ink, size and ratio.
    """

    def __init__(self, path: str, size: QSize, inks: tuple, recolor: bool):
        super().__init__()
        self._path = path
        self._size = QSize(size)
        self._inks = dict(inks)
        self._recolor = recolor

    def clone(self) -> QIconEngine:
        """Return a copy of this engine, for a QIcon that detaches."""
        from fxgui._compat import is_valid

        copy = _ThemedIconEngine(
            self._path, self._size, tuple(self._inks.items()), self._recolor)
        # PySide gives Qt no ownership of a clone() result and has no API to
        # transfer it; this list is its only owner until the QIcon deletes it.
        _clones[:] = [engine for engine in _clones if is_valid(engine)]
        _clones.append(copy)
        return copy

    def availableSizes(self, mode=QIcon.Normal, state=QIcon.Off):
        """Return the size the icon was asked for."""
        return [QSize(self._size)]

    def actualSize(self, size: QSize, mode=QIcon.Normal, state=QIcon.Off):
        """Return the icon's size, shrunk to fit `size`, never grown."""
        if (
            self._size.width() <= size.width()
            and self._size.height() <= size.height()
        ):
            return QSize(self._size)
        return self._size.scaled(size, Qt.KeepAspectRatio)

    def _ink(self, mode) -> Optional[str]:
        if not self._recolor:
            return None
        name = next(key for key, value in _MODES.items() if value == mode)
        if name in self._inks:
            return _theme_ink(self._inks[name])
        if name == "disabled":
            return _get_disabled_icon_color()
        # An icon drawn in its file's own colours keeps them in every mode.
        if not self._inks.get("normal"):
            return None
        return _theme_ink(_DEFAULT_INKS[name])

    def scaledPixmap(self, size: QSize, mode, state, scale: float) -> QPixmap:
        """Return the icon drawn for `mode` at `size` and pixel ratio `scale`."""
        # An exception escaping a Qt virtual kills the process on PySide6.
        try:
            return self._drawn(size, mode, state, scale)
        except Exception:
            traceback.print_exc()
            return QPixmap()

    def _drawn(self, size: QSize, mode, state, scale: float) -> QPixmap:
        target = self.actualSize(size, mode, state)
        ink = self._ink(mode)
        key = (
            f"fxicon|{self._path}|{ink}|{mode}|"
            f"{target.width()}x{target.height()}@{scale}"
        )
        pixmap = QPixmapCache.find(key)
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            return pixmap
        pixmap = _raster(
            self._path, target.width(), target.height(), scale, ink
        )
        if not self._recolor and mode == QIcon.Disabled:
            pixmap = _faded(pixmap)
        QPixmapCache.insert(key, pixmap)
        return pixmap

    def pixmap(self, size: QSize, mode, state) -> QPixmap:
        """Return the icon drawn for `mode` at the screen's pixel ratio."""
        return self.scaledPixmap(size, mode, state, _screen_dpr())

    def paint(self, painter: QPainter, rect: QRect, mode, state) -> None:
        """Draw the icon centred in `rect`."""
        device = painter.device()
        scale = device.devicePixelRatioF() if device is not None else 1.0
        pixmap = self.scaledPixmap(rect.size(), mode, state, scale)
        logical = pixmap.size() / pixmap.devicePixelRatio()
        x = rect.x() + (rect.width() - logical.width()) // 2
        y = rect.y() + (rect.height() - logical.height()) // 2
        painter.drawPixmap(x, y, pixmap)


# Engines handed to Qt by clone(), held until Qt deletes them.
_clones: List[QIconEngine] = []


@lru_cache(maxsize=512)
def _get_icon_cached(
    path: str, width: int, height: int, inks: tuple, recolor: bool,
) -> QIcon:
    return QIcon(_ThemedIconEngine(path, QSize(width, height), inks, recolor))


def get_icon(
    icon_name: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    color: Optional[str] = None,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
    inks: Optional[Dict[str, str]] = None,
    fallback: Optional[Union[str, QIcon]] = None,
) -> QIcon:
    """Get a QIcon of the specified icon.

    Args:
        icon_name: The name of the icon.
        width: The width of the pixmap. Defaults to `None`.
        height: The height of the pixmap. Defaults to `None`.
        color: The normal ink: a theme token such as "text_muted", read
            each time the icon is drawn, or a fixed colour. Defaults to the
            library's ("icon" for the monochrome ones).
        library: The library of the icon. Defaults to `None`.
        style: The style of the icon. Defaults to `None`.
        extension: The extension of the icon. Defaults to `None`.
        inks: Inks for the other modes, keyed "active", "selected" or
            "disabled", each a token or a colour. Unset, Active and
            Selected take the on-accent tokens and Disabled a muted grey.
        fallback: What to answer with when `icon_name` is in no library
            this asked. A name is resolved in the DEFAULT library rather
            than in `library`, which is the point: a curated set is
            asked for a brand or a kind it may simply not carry, and the
            general-purpose set is where the stand-in lives. A `QIcon`
            is returned as it is, so `QIcon()` asks for a blank rather
            than a picture of something else. Defaults to `None`, which
            raises as before.

    Raises:
        ValueError: If `inks` names a mode other than the three above.
        FileNotFoundError: If `icon_name` is in no such library and no
            `fallback` was given -- or if the fallback name is not in
            the default library either, which is a mistake worth
            hearing about rather than a second silent stand-in.

    Returns:
        QIcon: The caller's own icon; deleting it touches no other.

    Examples:
        >>> get_icon("add", color="red")
        >>> get_icon("send", color="icon_on_accent_primary",
        ...          inks={"active": "icon_on_accent_secondary"})
        >>> get_icon("lemon", library="fontawesome")

        Mapping open-ended studio data onto a curated set, where a name
        that is not in it is ordinary rather than exceptional:

        >>> get_icon("houdini", library="dcc", fallback="apps")
        >>> get_icon(whatever_the_tracker_said, fallback=QIcon())
    """

    if library is None:
        library = _default_library

    if fallback is not None:
        try:
            return get_icon(
                icon_name,
                width,
                height,
                color,
                library,
                style,
                extension,
                inks,
            )
        except FileNotFoundError:
            if isinstance(fallback, QIcon):
                return fallback
            return get_icon(
                fallback,
                width,
                height,
                color,
                None,
                None,
                None,
                inks,
            )

    inks = dict(inks or {})
    unknown = set(inks) - set(_DEFAULT_INKS) - {"disabled"}
    if unknown:
        raise ValueError(f"No icon mode named {sorted(unknown)}.")
    library, width, height, inks["normal"] = _resolved(
        library, width, height, color)
    path = get_icon_path(
        icon_name, library=library, style=style, extension=extension
    )
    # A copy, which shares the engine: a binding that deletes the icon it
    # is handed (QtAds' icon provider) must not delete the cached one.
    return QIcon(_get_icon_cached(
        path, width, height, tuple(sorted(inks.items())),
        _libraries_info[library]["recolor"],
    ))


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


# Painted at 32: Windows asks a tray 16 at 100% and 32 at 200%, and the
# dot stays round at both.
_BADGE_PIXELS = 32
# Of the side: smaller vanishes at 16 px, larger eats the mark.
_BADGE_DOT = 0.4
_BADGE_GAP = 0.07


def badged(icon: QIcon, color: str = "accent_primary") -> QIcon:
    """Return `icon` with a filled dot at its lower right, for work in flight.

    A ring round the dot is cleared first, so the dot never reads as part
    of the mark under it.

    Args:
        icon: The icon to badge; it is left unchanged.
        color: A theme token or any colour QColor reads.

    Examples:
        >>> tray.setIcon(fxicons.badged(icon) if busy else icon)
    """
    side = _BADGE_PIXELS
    size = max(2, round(side * _BADGE_DOT))
    gap = max(1, round(side * _BADGE_GAP))
    # Drawn onto a transparent page: an opaque source has no alpha to clear.
    painted = QPixmap(side, side)
    painted.fill(Qt.transparent)
    painter = QPainter(painted)
    painter.drawPixmap(0, 0, icon.pixmap(side, side))
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setCompositionMode(QPainter.CompositionMode_Clear)
    painter.setBrush(Qt.black)
    painter.drawEllipse(
        side - size - gap, side - size - gap, size + gap * 2, size + gap * 2
    )
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    painter.setBrush(QColor(_theme_ink(color)))
    painter.drawEllipse(side - size, side - size, size, size)
    painter.end()
    return QIcon(painted)


def rounded_pixmap(
    image: Union[str, Path, QPixmap],
    side: int,
    ratio: float,
    radius: Optional[float] = None,
) -> Optional[QPixmap]:
    """Return an image cropped to a rounded square, for a thumbnail.

    Scaled to cover the square and centred, so the long edge is cut.
    Outlined as `FXThumbnailDelegate` outlines its thumbnails.

    Args:
        image: An image file Qt can read, or a pixmap.
        side: The square's side, in logical pixels.
        ratio: The device pixel ratio to draw at, a widget's
            `devicePixelRatioF()`; a wrong one looks right and is soft.
        radius: The corner radius in logical pixels. Defaults to
            `fxstyle.BUTTON_RADIUS`.

    Returns:
        The thumbnail, or None when `image` is no readable image.

    Examples:
        >>> label.setPixmap(fxicons.rounded_pixmap(
        ...     path, 48, ratio=label.devicePixelRatioF()))
    """
    from fxgui import fxstyle

    source = image if isinstance(image, QPixmap) else QPixmap(str(image))
    if source.isNull():
        return None
    corner = (fxstyle.BUTTON_RADIUS if radius is None else radius) * ratio
    pixels = round(side * ratio)
    covered = source.scaled(
        pixels, pixels, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    result = QPixmap(pixels, pixels)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing, True)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, pixels, pixels), corner, corner)
    painter.setClipPath(clip)
    painter.drawPixmap(
        (pixels - covered.width()) // 2,
        (pixels - covered.height()) // 2,
        covered,
    )
    # Unclipped and inset half its width, or the ring is cut at the edge.
    painter.setClipping(False)
    width = ratio
    painter.setPen(QPen(QColor(255, 255, 255, 127), width))
    painter.setBrush(Qt.NoBrush)
    inside = QRectF(width / 2, width / 2, pixels - width, pixels - width)
    painter.drawRoundedRect(inside, corner, corner)
    painter.end()
    result.setDevicePixelRatio(ratio)
    return result


def clear_icon_cache() -> None:
    """Clear the icon and pixmap LRU caches.

    A theme switch needs none of this: icons read the theme when drawn.

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


def _get_disabled_icon_color(icon_color: Optional[str] = None) -> str:
    """Get the disabled icon color derived from the main icon color.

    Creates a muted version of the icon color by significantly reducing
    opacity and shifting toward neutral gray for clear visual distinction.

    Args:
        icon_color: The icon color to mute. Defaults to the theme's.

    Returns:
        The disabled icon color as a hex string (with alpha).
    """
    if icon_color is None:
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

    color.setHslF(h, new_s, new_l, _DISABLED_ALPHA)
    return color.name(QColor.HexArgb)


def set_icon(
    widget: Any, icon_name: str, theme_color: bool = True, **kwargs: Any
) -> QIcon:
    """Set an icon on a widget; it takes its theme inks when drawn.

    A push button's Active ink is its normal one (see `_icon_for_widget`).

    Args:
        widget (Any): The widget to set the icon on (QAction, QPushButton, etc.).
        icon_name (str): The name of the icon.
        theme_color (bool): Ignored: a token `color` follows the theme and
            a fixed colour keeps it.
        **kwargs (Any): Passed to `get_icon` (width, height, color, inks,
            library, style, extension).

    Returns:
        The QIcon that was set on the widget.

    Examples:
        >>> from fxgui import fxicons
        >>> # Icon follows theme color
        >>> fxicons.set_icon(my_button, "save")
        >>> # Icon keeps explicit color across theme changes
        >>> fxicons.set_icon(indicator, "check", theme_color=False, color="#00ff00")
    """
    icon = _icon_for_widget(widget, icon_name, kwargs)

    if hasattr(widget, "setIcon"):
        widget.setIcon(icon)
    return icon


def _icon_for_widget(widget: Any, icon_name: str, kwargs: Dict) -> QIcon:
    """Build the icon for a widget; a push button's Active ink is its normal.

    Qt draws a focused QPushButton's icon in Active mode on no accent
    fill, so the on-accent Active ink would clash there. A hovered
    QToolButton, a menu row and an item-view row sit on the accent.
    """
    from qtpy.QtWidgets import QAbstractButton, QToolButton

    if isinstance(widget, QAbstractButton) and not isinstance(
        widget, QToolButton
    ):
        inks = dict(kwargs.pop("inks", None) or {})
        library = kwargs.get("library")
        inks.setdefault(
            "active", _resolved(library, None, None, kwargs.get("color"))[3])
        kwargs["inks"] = inks
    return get_icon(icon_name, **kwargs)
