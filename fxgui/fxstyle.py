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
import re
import sys
import tempfile
import weakref
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple, Union

# Third-party
import yaml
from qtpy.QtCore import QEvent, QObject, QRectF, QSize, Qt, Signal
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
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QFrame,
    QHeaderView,
    QProxyStyle,
    QSplitter,
    QStyle,
    QStyleFactory,
    QStyleOption,
    QTreeView,
    QWidget,
)

# Internal
from fxgui import _compat, fxconfig, fxconstants, fxicons, fxutils


###### Theme Management


class FXThemeColors:
    """A theme's resolved colours, one attribute per role; `colors` returns it.

    Examples:
        >>> fxstyle.colors().surface  # "#302f2f"
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


class _Signals(QObject):
    """Hold the `theme_changed(str)` signal `apply_theme` emits."""

    theme_changed = Signal(str)


_signals = _Signals()

# Emitted with the theme's name after every switch.
theme_changed = _signals.theme_changed


###### Public API

__all__ = [
    # Classes
    "FXProxyStyle",
    "FXThemeColors",
    # Signal
    "theme_changed",
    # Constants
    "STYLE_FILE",
    "DEFAULT_COLOR_FILE",
    "TITLE_PROPERTY",
    "BUTTON_RADIUS",
    "FONT_SIZE",
    "ROOT_PROPERTY",
    "THIN_SCROLL_PROPERTY",
    "THIN_SCROLL_WIDTH",
    "PANE_GAP",
    # Color configuration
    "colors",
    "qcolor",
    "get_colors",
    "set_color_file",
    "overlay_color_file",
    # Font configuration
    "register_fonts",
    "mark_as_title",
    "mark_as_frame",
    "mark_as_thin_scroll",
    # Theme functions
    "get_available_themes",
    "get_theme",
    "is_light_theme",
    "apply_theme",
    "save_theme",
    "load_saved_theme",
    # Style functions
    "set_style",
    # Stylesheet functions
    "resolve",
    "register_widget_style",
    "set_default_theme",
    "get_default_theme",
    "register_themed_root",
    "palette",
    "font",
    "control_height",
    "focus_visible",
    # Utility functions
    "get_luminance",
    "get_contrast_ratio",
    "readable_ink",
    "mix",
    "step_toward",
    "depth_shade",
    "DEPTH_STEP",
    "DEPTH_CAP",
]


###### Constants

STYLE_FILE = fxconstants.PACKAGE_ROOT / "qss" / "style.qss"
DEFAULT_COLOR_FILE = fxconstants.PACKAGE_ROOT / "style.yaml"

# Theme persistence keys
_SETTINGS_THEME_KEY = "theme/current"
_DEFAULT_THEME = "dark"

# Dynamic property routing a widget to the title font role. Set it
# through mark_as_title() rather than by hand.
TITLE_PROPERTY = "fxTitle"

# Dynamic property painting a widget in the frame colour. Set it through
# mark_as_frame() rather than by hand.
FRAME_PROPERTY = "fxFrame"

# Dynamic property drawing a scroll area as a card's thin scroll. Set it
# through mark_as_thin_scroll() rather than by hand.
THIN_SCROLL_PROPERTY = "fxThinScroll"

# The width, in pixels, of every scroll bar: `@thin_scroll` in QSS.
THIN_SCROLL_WIDTH = 8

# A tab pill's gap to its strip's edges and to the next pill, and a docked
# pane's content's gap to the pane's edges: `@pane_gap` in QSS.
PANE_GAP = 4

# Per tree level, toward `border_light`; the cap's 48% stays short of a border.
DEPTH_STEP = 0.12

# ponytail: rows deeper than this shade like this level; raise it for a
# tree that nests deeper and needs telling apart.
DEPTH_CAP = 4

# Styles QPushButton through @button_radius; widgets that draw a button
# shape of their own read it here.
BUTTON_RADIUS = 4

# The corners of a floating card: a tooltip, a banner, a dialog.
CARD_RADIUS = 8

# The side of an on/off mark: a check box or radio indicator, and the
# height of a switch's track. It centres in a row of control_height.
INDICATOR_SIZE = 18

# WCAG's least contrast for the parts of a control: an edge on its
# surface, a thumb on its track. `@control_edge` is held to it.
CONTROL_CONTRAST = 3.0

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

# Least contrast between a hovered fill and what it sits on (a pane, a view,
# a row's own card), and between it and a pressed or checked one: each state
# reads as a step of its own.
STATE_MIN_CONTRAST = 1.2

# WCAG AA for body text: every text ink reaches it on each ground it sits on.
TEXT_CONTRAST = 4.5

# Least contrast between text and muted text, so the two read as two ranks.
MUTED_STEP = 1.5

# A spin box's padding that makes it a line edit's height: PySide6 6.5 sizes
# one 3 px shorter than later Qt for the same padding.
# ponytail: measured on 6.5.3 and 6.11.2 only; move the bound if a version
# between them measures otherwise.
_SPIN_PADDING = (
    "4px 0px" if _compat.QT_VERSION < (6, 6) else "3px 0px 2px 0px"
)

# The body text size, in pixels, of every themed root.
FONT_SIZE = 12

# The dynamic property a widget registered as a themed root carries.
ROOT_PROPERTY = "fxThemedRoot"

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

# Title ranks when the color file's `fonts: ranks:` names none: pixel size
# and weight of a heading marked with `mark_as_title(widget, rank=...)`.
# "card" is bold: the splash title is one, and Qt 6.5 on Windows takes 0.4 s
# to load a first 600 face, which a bold one does not cost.
_DEFAULT_RANKS = {
    "section": {"size": 15, "weight": 600},
    "card": {"size": 16, "weight": 700},
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
_widget_fragments: "OrderedDict[str, str]" = OrderedDict()
_themed_roots: "weakref.WeakSet" = weakref.WeakSet()


def _invalidate_theme_namespace() -> None:
    """Drop the cached colours; every change of theme, file or font calls it."""
    global _theme_namespace
    _theme_namespace = None


def _get_theme_namespace() -> "FXThemeColors":
    """Return the cached resolved colours of the current theme."""
    global _theme_namespace
    _ensure_theme_loaded()
    if _theme_namespace is None:
        _theme_namespace = FXThemeColors(_colour_tokens(_theme))
    return _theme_namespace


def _colour_tokens(theme_name: str) -> Dict[str, str]:
    """Return a theme's ``@`` tokens without the ``@``."""
    return {
        name[1:]: value
        for name, value in _token_map(theme_name).items()
        if name.startswith("@")
    }


###### Private Helper Functions


def _read_yaml(path) -> dict:
    """Return a YAML file's mapping, empty for an empty file."""
    with open(path, "r", encoding="utf-8") as in_file:
        return yaml.safe_load(in_file) or {}


def _load_colors_from_yaml() -> dict:
    """Return the loaded colour file, reading it on first use."""
    global _colors
    if _colors is None:
        _colors = _read_yaml(_color_file or DEFAULT_COLOR_FILE)
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
    theme_changed.emit(get_theme())


###### Color Configuration


def set_color_file(color_file: str) -> None:
    """Replace the whole colour file, then re-apply the theme everywhere.

    A file setting only a few keys belongs in `overlay_color_file`.

    Args:
        color_file: Path to the YAML color configuration file.

    Raises:
        OSError: If the file cannot be read; the loaded one stays.
        yaml.YAMLError: If it is no YAML; the loaded one stays.
    """
    global _colors, _color_file
    _colors = _read_yaml(color_file)
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
    _colors = _deep_merge(get_colors(), _read_yaml(color_file))
    _colors_changed()


def get_colors() -> dict:
    """Return the loaded colour file as written, before any token is derived.

    For the file's own sections (``dcc``, ``fonts``, each theme's raw
    values); a theme's resolved colours are `colors`.

    Examples:
        >>> fxstyle.get_colors()["dcc"]["houdini"]
        '#ff6600'
    """
    return _load_colors_from_yaml()


def _feedback(theme_name: str) -> dict:
    """Return a theme's feedback block: its own, the file's dark, built-in."""
    themes = get_colors().get("themes", {})
    for source in (
        themes.get(theme_name, {}),
        themes.get(_DEFAULT_THEME, {}),
        _builtin_theme(),
    ):
        if isinstance(source.get("feedback"), dict):
            return source["feedback"]
    return {}


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


###### Font Configuration


def _platform_default_font() -> str:
    """Return the platform's default UI font family."""
    if sys.platform == "win32":
        return "Segoe UI"
    return QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()


def register_fonts(
    paths: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]],
) -> Dict[str, list]:
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
        _invalidate_theme_namespace()
        _reapply_to_roots()
    return results


def _fonts_block(theme_name: str) -> dict:
    """Return a theme's ``fonts:`` block, merged role by role and rank by rank.

    Lowest first: the built-in defaults, the colour file's top-level block,
    then the theme's own.
    """
    fonts = {**_DEFAULT_FONTS, "ranks": dict(_DEFAULT_RANKS)}
    theme_fonts = _theme_data(theme_name).get("fonts")
    for source in (get_colors().get("fonts"), theme_fonts):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if key == "ranks":
                if isinstance(value, dict):
                    fonts["ranks"].update(value)
            else:
                fonts[key] = value
    return fonts


def _font_config(theme_name: str) -> dict:
    """Return a theme's font roles, each a family list or a mapping."""
    fonts = _fonts_block(theme_name)
    del fonts["ranks"]
    return fonts


def _ranks(theme_name: str) -> Dict[str, dict]:
    """Return a theme's title ranks, each a size and a weight."""
    return _fonts_block(theme_name)["ranks"]


def _check_weight(weight, what: str) -> None:
    """Raise ValueError unless `weight` is None or on the CSS scale."""
    if weight is not None and weight not in _WEIGHTS:
        raise ValueError(
            f"Font weight {weight!r} for {what} is not one of "
            f"{sorted(_WEIGHTS)}")


def _shape(theme_name: str, role: str) -> Tuple[Optional[int], Optional[str]]:
    """Return a role's configured weight and hinting, each None when unset."""
    entry = _font_config(theme_name).get(role)
    if not isinstance(entry, dict):
        return None, None
    weight, hinting = entry.get("weight"), entry.get("hinting")
    _check_weight(weight, f"'{role}'")
    if hinting is not None and hinting not in _HINTING:
        raise ValueError(
            f"Font hinting {hinting!r} for '{role}' is not one of "
            f"{sorted(_HINTING)}")
    return weight, hinting


def _font_family(entries) -> str:
    """Return one role's family: the first the running Qt has, or a generic.

    One family, never a list: Qt on Windows takes about 0.4 s to resolve
    the first font that names two. A family Qt lacks is skipped, since Qt
    would draw whichever family sorts first instead. A CSS generic stands
    for itself, lowercased; with nothing found, the platform default.

    Args:
        entries: A family name, a list of them, a mapping with a ``family``
            key, or an empty value.
    """
    if isinstance(entries, dict):
        entries = entries.get("family")
    if not entries:
        entries = []
    elif isinstance(entries, str):
        entries = [entries]

    # QFontDatabase needs a QGuiApplication; before one, only the default.
    available = (
        set(QFontDatabase.families()) if QGuiApplication.instance() else set()
    )
    for entry in entries:
        name = str(entry).strip()
        if name.lower() in _GENERIC_FONT_FAMILIES:
            return name.lower()
        if name in available:
            return name
    return _platform_default_font()


def _qss_family(entries) -> str:
    """Return one role's family as a QSS ``font-family``, a generic unquoted."""
    name = _font_family(entries)
    return name if name in _GENERIC_FONT_FAMILIES else f'"{name}"'


def mark_as_title(
    widget: QWidget, is_title: bool = True, rank: Optional[str] = None
) -> None:
    """Draw a widget's text in the theme's title font role.

    Without a rank only the family changes. A rank ("section", "card",
    or one the color file's ``fonts: ranks:`` adds) also sets the size
    and weight, from the stylesheet, so it holds inside a host too,
    where a font set in code loses to the host rules.

    Args:
        widget: The widget whose text is a title.
        is_title: False removes the mark and returns the widget to the
            body role. Defaults to True.
        rank: The heading's rank. Defaults to None, the family alone.

    Raises:
        ValueError: If `rank` is not a rank of the current theme.

    Examples:
        >>> fxstyle.mark_as_title(heading, rank="section")
    """
    value = bool(is_title)
    if rank is not None:
        ranks = _ranks(get_theme())
        if rank not in ranks:
            raise ValueError(
                f"No title rank {rank!r}. Ranks: {sorted(ranks)}")
        value = rank if is_title else False
    widget.setProperty(TITLE_PROPERTY, value)
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
    for child in widget.findChildren(QWidget, "", Qt.FindDirectChildrenOnly):
        fxutils.repolish(child)


def mark_as_thin_scroll(area: QAbstractScrollArea, is_thin: bool = True) -> None:
    """Draw a scroll area as part of the card it sits on.

    No fill and no border of its own.

    Args:
        area: The scroll area, or any QAbstractScrollArea.
        is_thin: False gives it the theme's own look back. Defaults to True.

    Examples:
        >>> fxstyle.mark_as_thin_scroll(runs_area)
    """
    area.setProperty(THIN_SCROLL_PROPERTY, bool(is_thin))
    # Child selectors are matched when the child polishes, not the parent.
    for part in (area, area.viewport()):
        fxutils.repolish(part)


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
    color = QColor(hex_color)
    if not color.isValid():
        color = QColor(f"#{hex_color}")

    def gamma(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = color.redF(), color.greenF(), color.blueF()
    return 0.2126 * gamma(r) + 0.7152 * gamma(g) + 0.0722 * gamma(b)


def get_contrast_ratio(one_hex: str, two_hex: str) -> float:
    """Return the WCAG contrast ratio between two colors, 1.0 to 21.0."""
    low, high = sorted([get_luminance(one_hex), get_luminance(two_hex)])
    return (high + 0.05) / (low + 0.05)


def readable_ink(
    background: Union[str, QColor],
    preferred: Union[str, QColor, None] = None,
    floor: float = 4.5,
) -> str:
    """Return an ink that reads on `background` at `floor`:1 or better.

    Args:
        background: The color the ink is drawn on, anything QColor reads.
        preferred: The ink to keep if it reads. Defaults to white.
        floor: The minimum WCAG contrast ratio.

    Returns:
        `preferred` when it reads, else the first color from it toward
        black or white, whichever stands further from `background`, that
        does. The pole itself when none does.
    """
    return _readable_ink(
        QColor(background).name(), QColor(preferred or "#ffffff").name(),
        floor)


# Keyed on names: a QColor is unhashable.
@lru_cache(maxsize=512)
def _readable_ink(ground: str, start: str, floor: float) -> str:
    return step_toward(start, _pole_from(ground), _reads(ground, floor))


def _pole_from(ground: str) -> str:
    """Return black or white, whichever stands further from `ground`."""
    return max(
        ("#000000", "#ffffff"),
        key=lambda pole: get_contrast_ratio(pole, ground),
    )


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
        return step_toward(fill, _pole_from(ink), lambda color: (
            reads(color) and all(_visibly_differ(color, o) for o in apart)
        ))

    rest = shifted(accent_primary, text_on_primary)
    hover = shifted(accent_secondary, text_on_secondary)
    if not _visibly_differ(rest, hover):
        hover = shifted(rest, text_on_secondary, rest)
    pressed = shifted(rest, text_on_primary, rest, hover)
    return rest, hover, pressed


def control_height(widget: QWidget) -> int:
    """Return the height a push button comes to in `widget`'s font."""
    # QPushButton in style.qss: 5 px of padding and a 1 px border each side.
    return widget.fontMetrics().height() + 12


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


def step_toward(
    start: str, toward: str, done: Callable[[str], bool]
) -> str:
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


def depth_shade(base: Union[str, QColor], depth: int) -> str:
    """Return a tree row's `base` colour tinted for its `depth`.

    Each level steps `DEPTH_STEP` toward the theme's ``border_light``,
    its mid-tone rather than its text, which washes a dark blue to grey.
    The step is held back where the text would fall under 4.5:1.

    Args:
        base: The row's colour at depth 0, anything QColor reads.
        depth: How many rows sit above it; 0 is a top-level row.

    Examples:
        >>> fxstyle.depth_shade(fxstyle.colors().surface, 2)
    """
    base = QColor(base).name()
    if depth <= 0:
        return base
    theme = colors()
    text = theme.text
    floor = min(TEXT_CONTRAST, get_contrast_ratio(text, base))
    deepest = mix(
        base, theme.border_light, min(depth, DEPTH_CAP) * DEPTH_STEP)
    return step_toward(deepest, base, _reads(text, floor))


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


def _readable_states(theme_data: dict) -> Dict[str, str]:
    """Return a theme's pressed fill and text inks, each held to its floor.

    - ``state_hover``: stepped away from ``surface`` until it differs by
      `STATE_MIN_CONTRAST` from it and from the ``surface_sunken`` and
      ``well`` a view fills, so a hovered row reads as a hovered tab does.
    - ``state_pressed``: stepped on until it differs from ``state_hover``
      by the same.
    - ``text``: stepped toward black or white until it reads at
      `TEXT_CONTRAST` on every ground it sits on, the hover and pressed
      fills included.
    - ``text_muted``: the same on every ground but a pressed fill, which
      carries ``text``.
    - ``text`` then steps on until it stands `MUTED_STEP` off ``text_muted``;
      a ``text`` already at black or white leaves ``text_muted`` to step
      back toward ``surface`` instead, as far as it still reads.
    """
    surface = theme_data["surface"]
    pole = _pole_from(surface)
    rows_on = [theme_data.get(key, surface)
               for key in ("surface", "surface_sunken", "well")]
    hover = step_toward(
        theme_data.get("state_hover", surface), pole,
        lambda color: all(
            _reads(ground, STATE_MIN_CONTRAST)(color) for ground in rows_on))
    pressed = step_toward(
        theme_data.get("state_pressed", hover), pole,
        _reads(hover, STATE_MIN_CONTRAST))
    grounds = [
        theme_data.get(key, surface)
        for key in ("surface", "surface_sunken", "surface_alt", "well",
                    "frame", "tooltip")
    ] + [hover]

    def reading(ink: str, on: list) -> str:
        return step_toward(QColor(ink).name(), pole, lambda color: all(
            get_contrast_ratio(color, ground) >= TEXT_CONTRAST
            for ground in on))

    muted = reading(theme_data["text_muted"], grounds)
    text = reading(theme_data["text"], grounds + [pressed])
    # Then on, until muted text reads as a step below it; where text meets
    # the pole first, muted steps back toward the surface while it reads.
    text = step_toward(text, pole, _reads(muted, MUTED_STEP))
    if not _reads(muted, MUTED_STEP)(text):
        quieter = step_toward(muted, surface, _reads(text, MUTED_STEP))
        if all(get_contrast_ratio(quieter, ground) >= TEXT_CONTRAST
               for ground in grounds):
            muted = quieter
    return {
        "state_hover": hover,
        "state_pressed": pressed,
        "text": text,
        "text_muted": muted,
    }


def _is_light(surface: str) -> bool:
    """Return whether a theme whose pane is `surface` is a light one."""
    return QColor(surface).lightness() > 128


def _token_map(theme_name: str) -> Dict[str, str]:
    """Build the ``@token`` -> value map for a theme.

    The one token resolver: the theme's roles, the derived ones (depth,
    states, text inks, on-accent, primary fills, control edge), the
    flattened feedback colours, font families, sizes and the ``~icons`` path.

    Args:
        theme_name: Theme to resolve. Keys it omits come from the file's
            dark theme, then the built-in one.

    Returns:
        Mapping of placeholder (including the ``@``/``~`` prefix) to value.
    """
    theme_data = _theme_data(theme_name)
    theme_data.update(_depth_colors(theme_data))
    theme_data.update(_readable_states(theme_data))

    tokens: Dict[str, str] = {
        f"@{key}": str(value)
        for key, value in theme_data.items()
        if isinstance(value, (str, int)) and not isinstance(value, bool)
    }

    # Feedback colors flatten to @feedback_<level>_<part>, plus
    # @feedback_<level>_ink, a text colour that reads on the background.
    for level, pair in _feedback(theme_name).items():
        if isinstance(pair, dict):
            for part, value in pair.items():
                tokens[f"@feedback_{level}_{part}"] = value
            if "background" in pair:
                tokens[f"@feedback_{level}_ink"] = readable_ink(
                    pair["background"]
                )

    # On-accent inks: the theme's, else the pole that reads best.
    accent_primary = theme_data["accent_primary"]
    accent_secondary = theme_data["accent_secondary"]
    text_on_primary = theme_data.get(
        "text_on_accent_primary") or _pole_from(accent_primary)
    text_on_secondary = theme_data.get(
        "text_on_accent_secondary") or _pole_from(accent_secondary)
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
        tokens[f"@font_{role}"] = _qss_family(entries)

    # No bundled border reads at 3:1 on its surface; a control whose edge
    # is its only shape (a switch, a slider handle) wears this one.
    tokens["@control_edge"] = readable_ink(
        theme_data["surface"],
        theme_data.get("border_strong", "#808080"),
        CONTROL_CONTRAST,
    )
    tokens["@button_radius"] = f"{BUTTON_RADIUS}px"
    tokens["@card_radius"] = f"{CARD_RADIUS}px"
    tokens["@indicator_size"] = f"{INDICATOR_SIZE}px"
    tokens["@thin_scroll_radius"] = f"{THIN_SCROLL_WIDTH // 2}px"
    tokens["@thin_scroll"] = f"{THIN_SCROLL_WIDTH}px"
    tokens["@pane_gap_half"] = f"{PANE_GAP // 2}px"
    tokens["@pane_gap"] = f"{PANE_GAP}px"
    tokens["@spin_padding"] = _SPIN_PADDING

    # url(~icons/...) in QSS: the folder of the theme being resolved, which
    # need not be the current one.
    icon_folder = (
        "stylesheet_light" if _is_light(theme_data["surface"])
        else "stylesheet_dark"
    )
    tokens["~icons"] = (fxconstants.ICONS_ROOT / icon_folder).as_posix()
    return tokens


# `~icon(name, token)`: the icon library's `name`, filled with a token.
_SHEET_ICON = re.compile(r"~icon\((\w+),\s*(\w+)\)")


def _sheet_icon(name: str, color: str) -> str:
    """Return a sheet `url()` of icon `name` filled with `color`.

    A sheet loads an image only from a file, so each colour gets a copy.
    """
    folder = Path(tempfile.gettempdir()) / "fxgui" / "sheet_icons"
    path = folder / f"{name}_{color.lstrip('#')}.svg"
    if not path.exists():
        svg = Path(fxicons.get_icon_path(name)).read_text(encoding="utf-8")
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(
            svg.replace("<svg ", f'<svg fill="{color}" ', 1), encoding="utf-8"
        )
    return f"url({path.as_posix()})"


def _substitute(qss: str, tokens: Dict[str, str]) -> str:
    """Replace each placeholder, longest first so @border spares @border_light."""

    def icon(match: "re.Match") -> str:
        color = tokens.get(f"@{match.group(2)}")
        return _sheet_icon(match.group(1), color) if color else match.group(0)

    qss = _SHEET_ICON.sub(icon, qss)
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
    """Return whether the current theme is light, judged by its surface."""
    return _is_light(colors().surface)


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


def qcolor(value) -> QColor:
    """Return a QColor for a theme token name, a colour or a QColor, now.

    A token is read from the current theme, so a caller that keeps the name
    follows every switch. Anything QColor cannot read is an invalid QColor,
    which a paint can skip rather than raise.

    Examples:
        >>> fxstyle.qcolor("accent_primary")
        >>> fxstyle.qcolor("#ff5722")
    """
    if isinstance(value, QColor):
        return QColor(value)
    if not isinstance(value, str):
        return QColor()
    return QColor(getattr(colors(), value, value))


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
    """Give Qt's standard icons (dialogs, message boxes) fxgui's themed icons.

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

    def drawPrimitive(self, element, option, painter, widget=None):
        """Draw `element`, except Qt's focus rectangle.

        PySide6 6.5's Fusion and Windows 11 draw it on an item view's current
        cell whatever the sheet's ``outline`` says, tinting its
        BackgroundRole; every fxgui control shows focus in its own edge.
        """
        if element != QStyle.PE_FrameFocusRect:
            super().drawPrimitive(element, option, painter, widget)

    def pixelMetric(self, metric, option=None, widget=None):
        """Return `metric`; a list view's icons take a tree's 16 px box."""
        if metric == QStyle.PM_ListViewIconSize:
            metric = QStyle.PM_SmallIconSize
        return super().pixelMetric(metric, option, widget)

    def polish(self, widget):
        """Lay an item view's rows out again once the sheet has styled them."""
        super().polish(widget)
        # A view sized before its first polish keeps rows measured without
        # the sheet's item box; nothing else tells it to measure again.
        if isinstance(widget, QAbstractItemView):
            widget.scheduleDelayedItemsLayout()


###### Stylesheet Functions


def _font_stylesheet(theme: Optional[str] = None) -> str:
    """Return the title rules: the title family, then each rank's size.

    The body family and size are the root font (:func:`font`), which a
    widget's own ``setFont`` overrides; the title rules outrank it.
    """
    ranks = _ranks(theme or get_theme())
    selectors = [f'[{TITLE_PROPERTY}="true"]'] + [
        f'[{TITLE_PROPERTY}="{rank}"]' for rank in ranks
    ]
    rules = [f"{', '.join(selectors)} {{ font-family: @font_title; }}"]
    for rank, shape in ranks.items():
        declarations = []
        if shape.get("size") is not None:
            declarations.append(f"font-size: {int(shape['size'])}px;")
        weight = shape.get("weight")
        _check_weight(weight, f"rank '{rank}'")
        if weight is not None:
            declarations.append(f"font-weight: {weight};")
        if declarations:
            rules.append(
                f'[{TITLE_PROPERTY}="{rank}"] {{ {" ".join(declarations)} }}')
    return "\n".join(rules) + "\n"


def _build_stylesheet(theme: Optional[str] = None) -> str:
    """Return the title rules, `STYLE_FILE` and every fragment, resolved."""
    parts = [_font_stylesheet(theme), STYLE_FILE.read_text(encoding="utf-8")]
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

    A widget is not registered while the QApplication is a root: the
    application's sheet already reaches it, and the next switch of that
    sheet would hand the widget back the palette of the theme before.

    Roots are held weakly; destroyed widgets drop out automatically.

    Args:
        root: Any object with ``setStyleSheet`` (QWidget or QApplication).
    """
    _ensure_theme_loaded()
    if isinstance(root, QWidget) and not _in_host(root):
        return
    _themed_roots.add(root)
    if isinstance(root, QWidget):
        root.setProperty(ROOT_PROPERTY, True)
    _watch_focus()
    _apply_to_root(root, _build_stylesheet(), palette(), font())


def _reapply_to_roots() -> None:
    """Re-apply the current theme palette, font and sheet to all live roots."""
    if not _themed_roots:
        return
    sheet = _build_stylesheet()
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
/* Undo what a host's sheet on the parent (Houdini's base.qss) sets and
   the base sheet leaves open; -1px is Qt's own unset size. */
QWidget {{ margin: 0px; }}
QToolButton {{ width: -1px; height: -1px; }}
QLineEdit {{ height: -1px; }}
QMenu::separator {{ margin: 0px; }}
QMenu::indicator {{ margin-left: 0px; border: none; }}
QMenu::icon {{ position: relative; top: 0px; left: 0px; bottom: 0px; right: 0px; }}
/* Native, not none: any other ::item border makes the sheet paint the cell
   and hide its BackgroundRole. */
QTableView::item {{ border: native; }}
/* A native border grows a list row 1px each side; the margin takes it back. */
QListView::item {{ border: native; margin: -1px 0px; }}
QMenuBar {{ border: none; padding: 0px; }}
QSpinBox {{ padding-left: 0px; padding-right: 0px; }}
QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {{ background: none; border: none; }}
QScrollBar::add-line, QScrollBar::sub-line {{ border: none; background: none; }}
QScrollBar::left-arrow, QScrollBar::right-arrow,
QScrollBar::up-arrow, QScrollBar::down-arrow {{ border: none; width: -1px; height: -1px; }}
QHeaderView::section {{ height: -1px; }}
QHeaderView::up-arrow, QHeaderView::down-arrow {{ border: none; }}
QSlider::horizontal {{ height: -1px; }}
QSlider::vertical {{ width: -1px; }}
QSlider::add-page:vertical {{ border: none; background: none; width: -1px; margin: 0px; }}
QTabWidget, QTabWidget::pane {{ background: none; }}
QTabBar::tab {{ height: -1px; }}
QGroupBox {{ padding: 0px; }}
QGroupBox::title {{ position: relative; left: 0px; }}
QPushButton::menu-indicator {{ left: 0px; }}
"""


def _host_rules(theme: Optional[str] = None) -> str:
    """Return the host rules resolved, with the body weight if one is set."""
    theme = theme or get_theme()
    weight, _hinting = _shape(theme, "body")
    extra = f" font-weight: {weight};" if weight is not None else ""
    return resolve(_HOST_RULES.replace("@weight", extra), theme)


# Set on a parentless list Qt shows as a popup (a completer's), which no
# type selector tells from a view in a window.
POPUP_PROPERTY = "fxPopup"

# Set on the focused widget while its focus came by keyboard, as a
# browser's :focus-visible; every focus look in fxgui keys off it.
FOCUS_VISIBLE_PROPERTY = "fxFocusVisible"

_KEYBOARD_REASONS = (
    Qt.TabFocusReason,
    Qt.BacktabFocusReason,
    Qt.ShortcutFocusReason,
)


def _drop_focus_rect(view: QAbstractItemView) -> None:
    """Give an item view in a themed host window a style with no focus rect.

    A host's own style draws it on the focused current cell, over the cell's
    BackgroundRole, on PySide6 6.5; a themed application's FXProxyStyle
    already skips it. Done once, at the view's first show, after the sheet
    has polished it; a popup's list is left alone.
    """
    if (
        QApplication.instance() in _themed_roots
        or isinstance(view, QHeaderView)
        or view.window().windowType() == Qt.Popup
        or not _is_themed(view)
        # Any proxy already on it (a delegate's) has its own say.
        or view.findChild(QProxyStyle, "", Qt.FindDirectChildrenOnly)
        is not None
    ):
        return
    # No base: it takes the application's style. Parented, since a style
    # freed before its view crashes.
    style = FXProxyStyle()
    style.setParent(view)
    view.setStyle(style)


_FOCUS_EVENTS = frozenset((
    QEvent.KeyPress,
    QEvent.MouseButtonPress,
    QEvent.MouseButtonDblClick,
    QEvent.FocusIn,
    QEvent.FocusOut,
    QEvent.Polish,
    QEvent.Show,
    QEvent.ShowToParent,
    QEvent.HideToParent,
))


class _FocusVisibility(QObject):
    """Mark a themed widget's focus visible when it came by keyboard.

    It also gives every themed popup and tooltip, Qt's own included,
    flyout corners, an item view in a host window a style without the
    focus rect, and a tree whose header hides or shows its padding again.
    """

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self._by_keyboard = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Note the last input, and set the property on focus in and out."""
        kind = event.type()
        # Every event of the application passes here: most leave at once.
        if kind not in _FOCUS_EVENTS:
            return False
        if kind == QEvent.KeyPress:
            self._by_keyboard = True
        elif kind in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            self._by_keyboard = False
        elif kind in (QEvent.FocusIn, QEvent.FocusOut) and isinstance(
            watched, QWidget
        ):
            self._mark(watched, kind == QEvent.FocusIn and self._visible(event))
        elif kind == QEvent.Polish:
            # Qt measures a completer's rows before it shows the list.
            if (
                isinstance(watched, QAbstractItemView)
                and watched.windowType() == Qt.Popup
            ):
                self._adopt(watched)
        elif kind in (QEvent.ShowToParent, QEvent.HideToParent):
            # The sheet pads a tree by its headerHidden property.
            view = _compat.parent_widget(watched) if isinstance(
                watched, QHeaderView) else None
            if isinstance(view, QTreeView) and _is_themed(view):
                fxutils.repolish(view)
        elif kind == QEvent.Show and isinstance(watched, QWidget):
            if watched.windowType() in (Qt.Popup, Qt.ToolTip):
                self._dress_popup(watched)
            elif isinstance(watched, QAbstractItemView):
                _drop_focus_rect(watched)
        return False

    @staticmethod
    def _adopt(popup: QWidget) -> None:
        """Theme a parentless popup as its owner is: a completer's line edit."""
        if popup.property(POPUP_PROPERTY) or _compat.parent_widget(popup):
            return
        # A completer makes its line edit the list's focus proxy.
        focus = popup.focusProxy() or QApplication.focusWidget()
        if focus is None or not _is_themed(focus):
            return
        popup.setProperty(POPUP_PROPERTY, True)
        if isinstance(popup, QAbstractItemView):
            # A host's style gives a list 24 px icons; a size set stays.
            if not popup.iconSize().isValid():
                side = popup.style().pixelMetric(QStyle.PM_SmallIconSize)
                popup.setIconSize(QSize(side, side))
            fxutils.repolish(popup)
        register_themed_root(popup)

    @staticmethod
    def _dress_popup(popup: QWidget) -> None:
        """Theme a popup Qt shows and round its corners."""
        # Not a tooltip: Qt keeps one for the whole application, a host's too.
        if popup.windowType() == Qt.Popup:
            _FocusVisibility._adopt(popup)
        if not _is_themed(popup):
            return
        if isinstance(_compat.parent_widget(popup), QComboBox):
            _ComboCard.dress(popup)
        fxutils.round_window_corners(popup)

    def _visible(self, event) -> bool:
        reason = event.reason()
        if reason in _KEYBOARD_REASONS:
            return True
        if reason == Qt.MouseFocusReason:
            return False
        # A popup closing, a window coming back, a setFocus() call: as the
        # last input was.
        return self._by_keyboard

    @staticmethod
    def _mark(widget: QWidget, visible: bool) -> None:
        if bool(widget.property(FOCUS_VISIBLE_PROPERTY)) == visible:
            return
        widget.setProperty(FOCUS_VISIBLE_PROPERTY, visible)
        # Only fxgui's own sheet reads it; a host's widgets keep their polish.
        if _is_themed(widget):
            fxutils.repolish(widget)


_focus_visibility: Optional[_FocusVisibility] = None


class _ComboCard(QObject):
    """Paint a combo box's popup frame as the popup card a menu is.

    Qt's sheet never styles that frame, so it is painted here: `@surface`,
    edged in `@border` at `CARD_RADIUS`, under a list with no fill.
    """

    @classmethod
    def dress(cls, frame: QFrame) -> None:
        """Give `frame` its painter once, and a 1 px edge for the list."""
        if frame.findChild(cls, "", Qt.FindDirectChildrenOnly) is None:
            frame.installEventFilter(cls(frame))
        if frame.frameStyle() != _POPUP_FRAME:
            # The list was sized before the edge took its pixels.
            frame.setFrameStyle(_POPUP_FRAME)
            frame.setLineWidth(1)
            frame.resize(frame.width(), frame.height() + 2 * frame.frameWidth())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Paint the card instead of Qt's frame."""
        if event.type() != QEvent.Paint:
            return False
        colors = _get_theme_namespace()
        painter = QPainter(watched)
        painter.fillRect(watched.rect(), QColor(colors.surface))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(colors.border))
        painter.drawRoundedRect(
            QRectF(watched.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            CARD_RADIUS, CARD_RADIUS)
        painter.end()
        return True


_POPUP_FRAME = QFrame.Box | QFrame.Plain


def _watch_focus() -> None:
    """Install the one focus watcher on the running application."""
    global _focus_visibility
    app = QApplication.instance()
    if app is None:
        return
    if _focus_visibility is not None and _compat.is_valid(_focus_visibility):
        if _focus_visibility.parent() is app:
            return
    _focus_visibility = _FocusVisibility(app)
    app.installEventFilter(_focus_visibility)


def _is_themed(widget: QWidget) -> bool:
    """Return whether fxgui themes `widget`: the app, or a root above it."""
    if QApplication.instance() in _themed_roots:
        return True
    while widget is not None:
        if widget.property(ROOT_PROPERTY):
            return True
        widget = _compat.parent_widget(widget)
    return False


def focus_visible(widget: QWidget) -> bool:
    """Return whether `widget` has focus that came by keyboard.

    The first call starts the focus watch, so a widget that draws its own
    focus look asks once before its first focus: when it is built or paints.
    """
    _watch_focus()
    return widget.hasFocus() and bool(widget.property(FOCUS_VISIBLE_PROPERTY))


def _in_host(root: QObject) -> bool:
    """Return whether `root` is a widget in an application fxgui does not theme."""
    app = QApplication.instance()
    return isinstance(root, QWidget) and app not in _themed_roots


def _apply_to_root(root, sheet: str, theme_palette, theme_font) -> None:
    """Put a theme's sheet, palette and font on `root`."""
    if isinstance(root, QApplication):
        # The application's sheet restores, on every widget, the palette
        # in force when it is set, so that palette goes first.
        root.setPalette(theme_palette)
        root.setFont(theme_font)
        root.setStyleSheet(sheet)
        return
    # A widget's sheet change restores the palette its stylesheet style
    # saved at an earlier polish; the palette set after it wins.
    if _in_host(root):
        sheet = _host_rules() + sheet
    root.setStyleSheet(sheet)
    root.setPalette(theme_palette)
    root.setFont(theme_font)


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
        tokens = _colour_tokens(theme)
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
    """Build a role's font: its installed family, weight and hinting.

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
    roles = _font_config(theme)
    family = _font_family(roles.get(role, roles["body"]))
    result = QFont()
    result.setFamilies([] if family in _GENERIC_FONT_FAMILIES else [family])
    result.setPixelSize(FONT_SIZE)
    weight, hinting = _shape(theme, role)
    if weight is not None:
        result.setWeight(_WEIGHTS[weight])
    if hinting is not None:
        result.setHintingPreference(_HINTING[hinting])
    return result

