"""Icons from the bundled libraries, drawn in the theme's colours.

Material, Font Awesome, Simple Icons, Beacon and the full-colour DCC marks.
An icon names theme tokens for its inks; `_ThemedIconEngine` resolves them
each time Qt draws it and keeps the drawings in `QPixmapCache`.

Examples:
    >>> from fxgui.fxicons import get_icon
    >>> icon = get_icon("home")
    >>> colored_icon = get_icon("settings", color="#FF5722")
    >>> dcc_icon = get_icon("houdini", library="dcc")
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
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
from fxgui import _compat, fxconstants


# Public API
__all__ = [
    "add_library",
    "badged",
    "get_icon_path",
    "get_icon",
    "get_pixmap",
    "rounded_pixmap",
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
    "disabled": "text_disabled",
}

# Opacity of a disabled full-colour icon.
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
_DEFAULT_LIBRARY = "material"


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

    valid_keys = _libraries_info[_DEFAULT_LIBRARY]["defaults"].keys()
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
    _libraries_info[library] = {
        "recolor": recolor,
        "pattern": pattern,
        "defaults": defaults,
        "root": root,
    }


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
        FileNotFoundError: If the icon does not exist.

    Returns:
        str: The path of the icon.

    Examples:
        >>> get_icon_path("add")
        >>> get_icon_path("lemon", library="fontawesome")
    """

    info = _libraries_info[library or _DEFAULT_LIBRARY]
    if style is None:
        style = info["defaults"].get("style")
    if extension is None:
        extension = info["defaults"].get("extension")

    path = info["pattern"].format(
        icon_name=icon_name,
        style=style,
        library=library or _DEFAULT_LIBRARY,
        extension=extension,
        root=info.get("root") or fxconstants.ICONS_ROOT,
    ).replace("\\", "/")

    if not Path(path).exists():
        raise FileNotFoundError(f"Icon path '{path}' does not exist.")

    return path


def _tint(pixmap: QPixmap, color: str) -> QPixmap:
    """Return a copy of `pixmap` in `color`, its alpha kept."""
    colored = pixmap.copy()
    painter = QPainter(colored)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(colored.rect(), QColor(color))
    painter.end()
    return colored


# TODO: shim; delete once _delegates.py:322 stops calling it.
change_pixmap_color = _tint


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
        qpixmap = _tint(qpixmap, color)
    qpixmap.setDevicePixelRatio(dpr)
    return qpixmap


def _resolved(library, width, height, color):
    """Fill a library, size and colour left unset from the library defaults.

    A full-colour library answers no colour, whatever was asked.
    """
    library = library or _DEFAULT_LIBRARY
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

    engine = _engine(icon_name, width, height, color, library, style,
                     extension, None)
    # A copy: one shares the pixels until written, so a caller changing it
    # leaves the cached one alone.
    return QPixmap(engine.scaledPixmap(
        QSize(engine._size), QIcon.Normal, QIcon.Off,
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
        # An icon drawn in its file's own colours keeps them, except disabled.
        if name != "disabled" and not self._inks.get("normal"):
            return None
        return _theme_ink(_DEFAULT_INKS[name])

    def scaledPixmap(self, size: QSize, mode, state, scale: float) -> QPixmap:
        """Return the icon drawn for `mode` at `size` and pixel ratio `scale`."""
        # An exception escaping a Qt virtual kills the process on PySide6.
        try:
            return self._drawn(size, mode, state, scale)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            return QPixmap()

    def _drawn(self, size: QSize, mode, state, scale: float) -> QPixmap:
        target = self.actualSize(size, mode, state)
        ink = self._ink(mode)
        key = (
            f"fxicon|{self._path}|{ink}|{mode}|"
            f"{target.width()}x{target.height()}@{scale}"
        )
        pixmap = _compat.find_pixmap(key)
        if pixmap is not None:
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


def _engine(icon_name, width, height, color, library, style, extension,
            inks) -> _ThemedIconEngine:
    """Return an engine drawing `icon_name` in the inks asked."""
    inks = dict(inks or {})
    unknown = set(inks) - set(_DEFAULT_INKS)
    if unknown:
        raise ValueError(f"No icon mode named {sorted(unknown)}.")
    library, width, height, inks["normal"] = _resolved(
        library, width, height, color)
    path = get_icon_path(
        icon_name, library=library, style=style, extension=extension
    )
    return _ThemedIconEngine(
        path, QSize(width, height), tuple(sorted(inks.items())),
        _libraries_info[library]["recolor"],
    )


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
            Selected take the on-accent tokens and Disabled text_disabled.
        fallback: What to answer with when `icon_name` is in no library
            this asked. A name is resolved in the DEFAULT library rather
            than in `library`, which is the point: a curated set is
            asked for a brand or a kind it may simply not carry, and the
            general-purpose set is where the stand-in lives. A `QIcon`
            is returned as it is, so `QIcon()` asks for a blank rather
            than a picture of something else. Defaults to `None`, which
            raises.

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

    try:
        engine = _engine(icon_name, width, height, color, library, style,
                         extension, inks)
    except FileNotFoundError:
        if fallback is None:
            raise
        if isinstance(fallback, QIcon):
            return fallback
        engine = _engine(fallback, width, height, color, None, None, None,
                         inks)
    return QIcon(engine)


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

    Scaled to cover the square and centred, so the long edge is cut, and
    outlined in the theme's `border_light`, read now.

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
    painter.setPen(QPen(QColor(fxstyle.colors().border_light), width))
    painter.setBrush(Qt.NoBrush)
    inside = QRectF(width / 2, width / 2, pixels - width, pixels - width)
    painter.drawRoundedRect(inside, corner, corner)
    painter.end()
    result.setDevicePixelRatio(ratio)
    return result


def set_icon(widget: Any, icon_name: str, **kwargs: Any) -> QIcon:
    """Set an icon on a widget; it takes its theme inks when drawn.

    A push button's Active ink is its normal one (see `_icon_for_widget`).

    Args:
        widget: Anything with `setIcon` (QAction, QPushButton, etc.).
        icon_name: The name of the icon.
        **kwargs: Passed to `get_icon` (width, height, color, inks,
            library, style, extension).

    Returns:
        The QIcon that was set on the widget.

    Raises:
        AttributeError: If `widget` has no `setIcon`.

    Examples:
        >>> fxicons.set_icon(my_button, "save")
        >>> fxicons.set_icon(indicator, "check", color="#00ff00")
    """
    icon = _icon_for_widget(widget, icon_name, kwargs)
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
