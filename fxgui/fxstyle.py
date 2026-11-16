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
import contextlib
import hashlib
import math
import os
import re
import sys
import tempfile  # noqa: F401 - patched by callers' tests; FXGUI_CACHE_DIR replaces that
import weakref
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from qtpy.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QFontInfo,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QTransform,
)
from qtpy.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractScrollArea,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QFrame,
    QGraphicsView,
    QHeaderView,
    QLineEdit,
    QListView,
    QMenu,
    QPlainTextEdit,
    QProxyStyle,
    QPushButton,
    QSplitter,
    QStackedLayout,
    QStyle,
    QStyleFactory,
    QStyleOption,
    QStyleOptionHeader,
    QStyleOptionTab,
    QTabBar,
    QTableView,
    QTabWidget,
    QTextEdit,
    QToolButton,
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
        """Hold each role of `colors_dict` as an attribute."""
        self.__dict__.update(colors_dict)

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
    "CARD_RADIUS",
    "SMALL_RADIUS",
    "FONT_SIZE",
    "BODY_WEIGHT",
    "CARD_STEP",
    "COMPACT_HEIGHT",
    "COMPACT_PROPERTY",
    "DENSE_PROPERTY",
    "READING_INSET",
    "FLUSH_PROPERTY",
    "FILTER_DROP",
    "EMPHASIS_WEIGHT",
    "STRONG_WEIGHT",
    "drawn_weight",
    "DIALOG_GUTTER",
    "DIALOG_EDGE",
    "DIALOG_GAP",
    "font_rank",
    "ROW_SIZES",
    "ROOT_PROPERTY",
    "THIN_SCROLL_PROPERTY",
    "NAV_PROPERTY",
    "INK_PROPERTY",
    "INKS",
    "THIN_SCROLL_WIDTH",
    "PANE_GAP",
    "FRAME_GAP",
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
    "mark_compact",
    "mark_dense",
    "mark_flush",
    "ink_section",
    "SECTION_INK_PROPERTY",
    "column_lines",
    "apply_column_lines",
    "draw_column_rule",
    "mark_as_thin_scroll",
    "mark_as_nav",
    "mark_as_segmented",
    "set_tab_count",
    "ink",
    # Theme functions
    "get_available_themes",
    "get_theme",
    "is_light_theme",
    "apply_theme",
    "motion",
    "REDUCED_MOTION_VAR",
    "MOTION_INSTANT",
    "MOTION_FAST",
    "MOTION_BASE",
    "MOTION_SLOW",
    "MOTION_SPRING",
    "ease_out",
    "ease_spring",
    "apply_row_size",
    "row_size",
    "row_height",
    "state_contrast",
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
    "unregister_themed_root",
    "palette",
    "font",
    "control_height",
    "focus_visible",
    # Utility functions
    "get_luminance",
    "get_contrast_ratio",
    "readable_ink",
    "mix",
    "mix_oklab",
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
_SETTINGS_ROW_SIZE_KEY = "rows/size"
_SETTINGS_COLUMN_LINES_KEY = "rows/column_lines"
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

# Dynamic property drawing an item view as a navigation list. Set it
# through mark_as_nav() rather than by hand.
NAV_PROPERTY = "fxNav"
_NAV_END_GAP = 3

# Dynamic property writing a widget's text in one theme colour. Set it
# through ink() rather than by hand.
INK_PROPERTY = "fxInk"
# Closed on purpose: each token is one rule; a new ink is one line here.
INKS = (
    "text",
    "text_muted",
    "text_strong",
    "text_toned",
    "text_dimmed",
    "text_disabled",
    "accent_primary",
    *(
        f"feedback_{level}_foreground"
        for level in ("debug", "info", "success", "warning", "error")
    ),
)
# An inked label shows what it sits on, even under a sheet rule that fills
# labels.
_INK_RULES = "".join(
    f'QWidget[{INK_PROPERTY}="{token}"] {{ color: @{token}; }}\n'
    f'QLabel[{INK_PROPERTY}="{token}"] {{ background-color: transparent; }}\n'
    for token in INKS
)

# The width, in pixels, of every scroll bar: `@thin_scroll` in QSS.
THIN_SCROLL_WIDTH = 8

# The one gap between widgets: a layout's default spacing, a tab pill's gap
# to its strip's edges, a pane's content's to its edges: `@pane_gap` in QSS.
PANE_GAP = 6

# The frame's gap: between docked panes, and from them to the window's
# edges, as a raised page stands off its backdrop.
FRAME_GAP = 8

# A tab pill's side padding, its text's lead off the pill: `@tab_padding`.
TAB_PADDING = 8

# A tab's close glyph inks 2 px inside its button; the pill edge is 1 px.
_CLOSE_INSET = PANE_GAP // 2 + 1 + TAB_PADDING - 2

# Per tree level, toward `border_light`; the cap's 48% stays short of a border.
DEPTH_STEP = 0.12

# ponytail: rows deeper than this shade like this level; raise it for a
# tree that nests deeper and needs telling apart.
DEPTH_CAP = 4

# A tree's indentation per level, and the chevron centred in it.
_TREE_INDENT = 22
_CHEVRON = 14
# Names a tree's indentation, so the sheet pads its chevron to 14 px.
INDENT_PROPERTY = "fxIndent"
# ponytail: indentations 0-64 px have a rule; a wider tree's chevron grows.
_BRANCH_RULES = "".join(
    f'QTreeView[{INDENT_PROPERTY}="{indent}"]::branch:has-children '
    f"{{ padding: 2px {max(0, (indent - _CHEVRON) // 2)}px; }}\n"
    for indent in range(65)
)

# One scale of corners, each step nesting inside the one above. Qt draws a
# corner square when its radius passes half the box's height, so a box under
# 18 px tall takes SMALL_RADIUS.
# What floats or holds panes' content: a pane, a menu, a popup, a dialog.
CARD_RADIUS = 12

# What sits inside one: a control, a list, a card in a pane, a menu item.
BUTTON_RADIUS = 9

# Something small: a badge, a key hint, a chip, a tooltip, a check's box.
SMALL_RADIUS = 6

# The side of an on/off mark: a check box or radio indicator, and the
# height of a switch's track. It centres in a row of control_height.
INDICATOR_SIZE = 16

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

# Least contrast between `splitter_mark` and the frame. fxgui no longer
# draws that token (a handle is blank until lit); themes and callers keep it.
SPLITTER_MARK_MIN_CONTRAST = 1.3

# Least contrast between a hovered fill and what it sits on (a pane, a view,
# a row's own card), and between it and a pressed or checked one: each state
# reads as a step of its own.
STATE_MIN_CONTRAST = 1.2

# WCAG AA for body text: every text ink reaches it on each ground it sits on.
TEXT_CONTRAST = 4.5

# Least contrast between text and muted text, so the two read as two ranks.
MUTED_STEP = 1.5

# Lumen's tints, in OKLab, for the keys a theme leaves out: a selected row is
# the accent over the pane, a notice its own colour; hover starts from text
# over the pane and is held to `STATE_MIN_CONTRAST`.
SELECTION_TINT = 0.15
FEEDBACK_TINT = 0.12
HOVER_TINT = 0.05
PRESSED_TINT = 0.10
# How far a row's name stands past `text`, toward black or white.
STRONG_STEP = 0.6

# A spin box's height with no vertical padding, over its line of text (Qt
# holds that line to 14 px at least): PySide6 6.5 sizes one 3 px shorter.
# ponytail: measured on 6.5.3, 6.11.1 and 6.12.0 only; move the bound if a
# version between them measures otherwise.
_SPIN_BASE = 4 if _compat.QT_VERSION < (6, 6) else 7
# A popup row's side padding: Qt 6.8 and older paint a resting row without
# it and a highlighted one with it, so there both keep Qt's own position.
_POPUP_ITEM_PAD = 8 if _compat.QT_VERSION >= (6, 9) else 0
_SPIN_LINE_FLOOR = 14
# A field's padding and border, top and bottom together, in style.qss.
_FIELD_BOX = 10
# A control's line box over its font's pixel size, as CSS's 1.5 line
# height; and the 6 px around it each side, its 1 px edge included. At the
# 13 px body font: a 20 px line box, a 32 px control.
_LINE_BOX = 1.5
_CONTROL_BOX = 12

# A cell's text lead from its edges: a header's padding, and an item's
# padding with Qt's own 3 px text margin inside it.
_CELL_LEAD = 12
_CELL_PADDING = _CELL_LEAD - 3
# A header section's height under its 1 px rule: 36 px in all.
_HEADER_HEIGHT = 35

# The body text size, in pixels, of every themed root.
FONT_SIZE = 13
# The weights text takes, on the CSS scale, as the web look names them:
# body text (unless a theme's `fonts: body` names another), emphasis
# (names, titles, headers, a current segment, a tab's label) and strong
# (a group's title). Qt draws them through `drawn_weight`, which reads the
# theme: light text on a dark ground needs a step more to read as dark as a
# browser draws it.
BODY_WEIGHT = 400
EMPHASIS_WEIGHT = 500
STRONG_WEIGHT = 600

# A dialog's layout: title, body and buttons start `DIALOG_GUTTER` in from
# the sides, the card's top and bottom stand `DIALOG_EDGE` off, and
# `DIALOG_GAP` parts title, body and buttons.
# How far a dark theme's card steps from its pane toward its text, in
# OKLab: the web look's #16171A on #101113.
CARD_STEP = 0.035

# A reading pane's inset (a task's details, a comment thread): its content
# stands this far from the pane's edges, and its blocks this far apart, as
# the web look's. Tool panes keep `PANE_GAP`.
READING_INSET = 24

# Set on a view that fills its pane and draws no frame (mark_flush).
FLUSH_PROPERTY = "fxFlush"

# Set on a view whose rows are a size denser (mark_dense).
DENSE_PROPERTY = "fxDense"

# A compact button's height (mark_compact), and the property it sets.
COMPACT_HEIGHT = 24
COMPACT_PROPERTY = "fxCompact"

# How much shorter a filter field (FXSearchBar) is than a control: 28 px
# beside a 32 px button.
FILTER_DROP = 4

DIALOG_GUTTER = 20
DIALOG_EDGE = 16
DIALOG_GAP = 12

# The five durations every animation picks from, in ms: a state flick, a
# hover or a leave, a control or a fold, a page arriving, a spring settling.
MOTION_INSTANT = 100
MOTION_FAST = 150
MOTION_BASE = 200
MOTION_SLOW = 300
MOTION_SPRING = 400

# A critically damped spring per unit mass, from rest to its place: settled
# within `MOTION_SPRING`, under 1 % overshoot.
_SPRING_STIFFNESS = 520.0
_SPRING_DAMPING = 40.0
# Qt corrupts its heap copying a bezier spline of more than 10 segments.
_SPRING_SEGMENTS = 8


def ease_out() -> QEasingCurve:
    """Return the curve every fade and slide eases out on.

    Fast off the mark, long and gentle into place: the cubic bezier
    (0.2, 0) (0, 1).

    Returns:
        A new `QEasingCurve`.

    Examples:
        >>> animation.setEasingCurve(fxstyle.ease_out())
    """
    curve = QEasingCurve(QEasingCurve.BezierSpline)
    curve.addCubicBezierSegment(
        QPointF(0.2, 0.0), QPointF(0.0, 1.0), QPointF(1.0, 1.0))
    return curve


def ease_spring() -> QEasingCurve:
    """Return the curve anything that travels rides: a spring settling.

    Run it over `MOTION_SPRING`. The spring's closed form, sampled with its
    slope at `_SPRING_SEGMENTS` points, as a bezier spline: Qt keeps no
    Python easing function safely once it copies the curve.

    Returns:
        A new `QEasingCurve`.

    Examples:
        >>> animation.setDuration(fxstyle.MOTION_SPRING)
        >>> animation.setEasingCurve(fxstyle.ease_spring())
    """
    omega = math.sqrt(_SPRING_STIFFNESS)
    zeta = _SPRING_DAMPING / (2.0 * omega)
    damped = omega * math.sqrt(1.0 - zeta * zeta)
    span = MOTION_SPRING / 1000.0

    def place(progress: float) -> float:
        t = progress * span
        return 1.0 - math.exp(-zeta * omega * t) * (
            math.cos(damped * t)
            + zeta * omega / damped * math.sin(damped * t))

    def slope(progress: float) -> float:
        t = progress * span
        return span * math.exp(-zeta * omega * t) * (
            omega * omega / damped * math.sin(damped * t))

    curve = QEasingCurve(QEasingCurve.BezierSpline)
    step = 1.0 / _SPRING_SEGMENTS
    for index in range(_SPRING_SEGMENTS):
        start, end = index * step, (index + 1) * step
        # Settled: the last point sits exactly in place.
        arrival = 1.0 if index == _SPRING_SEGMENTS - 1 else place(end)
        curve.addCubicBezierSegment(
            QPointF(start + step / 3, place(start) + step / 3 * slope(start)),
            QPointF(end - step / 3, arrival - step / 3 * slope(end)),
            QPointF(end, arrival),
        )
    return curve


# How long a popup, a menu or a tooltip takes to fade in, in ms: short
# enough never to hold the pointer up; a window, a little longer.
POPUP_FADE_MS = MOTION_INSTANT
WINDOW_FADE_MS = MOTION_BASE
# How far a popup drops into place as it fades in, in px: a top-level
# window cannot scale in, so it only fades.
POPUP_DROP = 0

# How long a panel takes to fade in as it comes to the front, in ms: a dock
# pane opened or picked by its tab, a page of a stacked widget.
PANEL_FADE_MS = MOTION_SLOW
# How far a page rises into place as it fades in, in px; a pane opening
# grows open on the spring over `PANEL_OPEN_MS` instead.
PANEL_RISE = 4
PANEL_OPEN_MS = MOTION_SPRING

# Set to "1", every animation lands at once, as a reduced-motion setting
# asks; tests that read pixels set it.
REDUCED_MOTION_VAR = "FXGUI_REDUCED_MOTION"


def motion() -> bool:
    """Whether animations play: not under `REDUCED_MOTION_VAR`."""
    return os.environ.get(REDUCED_MOTION_VAR) != "1"


# One scale of row heights for every list and tree, in even steps so each
# choice reads as different; `apply_row_size` picks one.
ROW_SIZES = {"small": 28, "normal": 36, "big": 52}
_DEFAULT_ROW_SIZE = "normal"

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
# default UI font.
# No hinting: grid-fitting rounds Inter's x-height up a pixel at 13 px,
# so text reads larger and narrower than the same face in a browser.
_DEFAULT_FONTS = {
    "title": {"family": ["Inter"], "hinting": "none"},
    "body": {"family": ["Inter"], "hinting": "none"},
    "mono": {
        "family": ["JetBrains Mono", "Consolas", "Courier New", "monospace"],
        "hinting": "none",
    },
}

# Title ranks when the color file's `fonts: ranks:` names none: pixel size
# and weight of a heading marked with `mark_as_title(widget, rank=...)`.
# Emphasis, never past it: a rank is told by its size.
_DEFAULT_RANKS = {
    "section": {"size": 15, "weight": EMPHASIS_WEIGHT},
    "card": {"size": 18, "weight": EMPHASIS_WEIGHT},
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
_row_size = None  # Likewise
_default_theme = _DEFAULT_THEME  # What load_saved_theme() falls back to
_theme_namespace = None  # Cached FXThemeColors for the current theme
_widget_fragments: "OrderedDict[str, str]" = OrderedDict()
_themed_roots: "weakref.WeakSet" = weakref.WeakSet()
# Built sheets and host rules: key -> (the colour file read, the text).
_sheet_cache: Dict[tuple, Tuple[dict, str]] = {}


def _invalidate_theme_namespace() -> None:
    """Drop the cached colours; every change of theme, file or font calls it."""
    global _theme_namespace
    _theme_namespace = None
    _sheet_cache.clear()


def _cached_sheet(key: tuple, build: Callable[[], str]) -> str:
    """Return the text `build` makes for `key`, built once per colour file."""
    _watch_fonts()
    # The entry holds the colour mapping itself, so its id is never reused.
    source = get_colors()
    entry = _sheet_cache.get(key)
    if entry is None or entry[0] is not source or not _images_exist(entry[1]):
        entry = _sheet_cache[key] = (source, build())
    return entry[1]


def _watch_fonts() -> None:
    """Drop the built sheets whenever Qt's fonts change, watched once per app."""
    # A font added straight through Qt changes which family a token names.
    app = QGuiApplication.instance()
    if app is not None and not app.property("_fxgui_watches_fonts"):
        app.setProperty("_fxgui_watches_fonts", True)
        app.fontDatabaseChanged.connect(_invalidate_theme_namespace)


_SHEET_URL = re.compile(r'url\("([^"]+/fxgui/sheet_icons/[^"]+)"\)')


def _images_exist(sheet: str) -> bool:
    """Return whether every image `_sheet_icon` drew for a sheet is on disk."""
    # The temp folder may be cleaned while the application runs.
    return all(os.path.exists(path) for path in _SHEET_URL.findall(sheet))


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
    # Imported here and parsed by libyaml when built with it: the pure
    # Python loader takes ten times as long on style.yaml.
    import yaml

    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    with open(path, "r", encoding="utf-8") as in_file:
        return yaml.load(in_file, Loader=loader) or {}


# Inks worked out from a theme's own accents when it omits them.
_ON_ACCENT_KEYS = ("text_on_accent", "icon_on_accent")


@lru_cache(maxsize=1)
def _builtin_theme() -> dict:
    """Return the default file's dark theme, the baseline for every key.

    Keys computed from others are left out, so a file whose accent differs
    gets them computed from its own accent.
    """
    theme = _read_yaml(DEFAULT_COLOR_FILE)["themes"][_DEFAULT_THEME]
    return {
        key: value for key, value in theme.items()
        if not key.startswith(_ON_ACCENT_KEYS)
    }


def state_contrast(theme_name: Optional[str] = None) -> float:
    """Return the least contrast a theme holds its hover and pressed fills to.

    `STATE_MIN_CONTRAST` unless the theme's ``state_contrast`` says less, as
    a brand's own fills may.
    """
    data = _theme_data(theme_name or get_theme())
    return float(data.get("state_contrast", STATE_MIN_CONTRAST))


def _theme_data(theme_name: str) -> dict:
    """Return a theme's raw values over the file's dark and the built-in dark.

    A theme of the file other than dark takes no on-accent ink from dark:
    dark's white was chosen for dark's accent, and an omitted ink is
    computed from the theme's own. An unknown name is dark itself.
    """
    themes = get_colors().get("themes", {})
    dark = themes.get(_DEFAULT_THEME, {})
    if theme_name != _DEFAULT_THEME and theme_name in themes:
        dark = {
            key: value for key, value in dark.items()
            if not key.startswith(_ON_ACCENT_KEYS)
        }
    return {**_builtin_theme(), **dark, **themes.get(theme_name, {})}


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
    global _colors
    if _colors is None:
        _colors = _read_yaml(_color_file or DEFAULT_COLOR_FILE)
    return _colors


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


# Faces fxgui ships, each SIL OFL 1.1 (its notice beside it): Inter for body
# and titles, JetBrains Mono for code, grid-fitted for screens; vertical
# hinting is what uses that grid-fitting (see fonts/README.md).
_BUNDLED_FONTS = fxconstants.PACKAGE_ROOT / "fonts"
_bundled_registered = False


def _register_bundled_fonts() -> None:
    """Put fxgui's own faces in Qt's font database, once a GUI app exists."""
    global _bundled_registered
    if _bundled_registered or QGuiApplication.instance() is None:
        return
    _bundled_registered = True
    for path in sorted(_BUNDLED_FONTS.glob("*/*.ttf")):
        QFontDatabase.addApplicationFont(str(path))


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
    if isinstance(paths, (str, os.PathLike)):
        paths = [paths]

    results: Dict[str, list] = {}
    for path in paths:
        key = os.fspath(path)
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


def font_rank(name: str, theme: Optional[str] = None) -> Tuple[int, int]:
    """Return a text rank's pixel size and the weight Qt draws it at.

    The weight is `drawn_weight` of the rank's CSS weight, so a QFont built
    from it matches the sheet's own text in that theme.

    "body" is the root font's; a title rank ("section", "card", or one the
    color file's ``fonts: ranks:`` adds) is what
    ``mark_as_title(widget, rank=name)`` sets.

    Args:
        name: "body" or a title rank.
        theme: Theme name. Defaults to the current theme.

    Returns:
        The size in pixels and the weight, e.g. ``(15, 600)`` for
        "section" in a dark theme, ``(15, 500)`` in a light one.

    Raises:
        ValueError: If `name` is not "body" nor a rank of the theme.

    Examples:
        >>> size, weight = fxstyle.font_rank("section")
    """
    theme = theme or get_theme()
    if name == "body":
        weight, _hinting = _shape(theme, "body")
        return FONT_SIZE, drawn_weight(
            BODY_WEIGHT if weight is None else weight, theme)
    ranks = _ranks(theme)
    if name not in ranks:
        raise ValueError(
            f"No text rank {name!r}: 'body' or one of {sorted(ranks)}")
    shape = ranks[name]
    size = shape.get("size")
    weight = shape.get("weight")
    return (
        FONT_SIZE if size is None else int(size),
        drawn_weight(BODY_WEIGHT if weight is None else int(weight), theme),
    )


def drawn_weight(weight: int, theme: Optional[str] = None) -> int:
    """Return the weight Qt draws for a CSS `weight` in `theme`.

    Chromium draws light text on a dark ground darker than Qt does (Qt
    blends DirectWrite's coverage with the system's ClearType gamma and no
    contrast boost): measured on Windows, Inter at 13 px in a dark theme
    needs one step more in Qt to lay down the ink a browser does. Dark text
    on a light ground draws alike in both, so it keeps its weight.

    Args:
        weight: A weight on the CSS scale, such as `EMPHASIS_WEIGHT`.
        theme: Theme name. Defaults to the current theme.

    Returns:
        The weight to give a QFont or a sheet, at most 900.

    Raises:
        ValueError: If `weight` is not a multiple of 100 from 100 to 900.

    Examples:
        >>> font.setWeight(QFont.Weight(fxstyle.drawn_weight(fxstyle.EMPHASIS_WEIGHT)))
    """
    _check_weight(weight, "drawn_weight")
    return min(weight + 100, 900) if _light_on_dark(theme or get_theme()) else weight


# (theme, colour file) -> whether its text is lighter than its surface; a
# delegate asks on every paint.
_LIGHT_ON_DARK: Dict[Tuple[str, int], bool] = {}


def _light_on_dark(theme: str) -> bool:
    """Return whether `theme` sets light text on a dark surface."""
    key = (theme, id(get_colors()))
    if key not in _LIGHT_ON_DARK:
        data = _theme_data(theme)
        text, ground = data.get("text"), data.get("surface")
        _LIGHT_ON_DARK[key] = bool(
            text and ground and get_luminance(text) > get_luminance(ground))
    return _LIGHT_ON_DARK[key]


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
    _register_bundled_fonts()
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


def mark_compact(widget: QWidget, compact: bool = True) -> None:
    """Make a push or tool button the compact size: `COMPACT_HEIGHT` tall.

    For a button in a row or a panel, as the web look's extra-small one:
    24 px, small text, a 16 px icon. A round `FXIconButton` takes its own
    ``size`` argument instead.

    Args:
        widget: The button.
        compact: False gives it the control height back. Defaults to True.

    Examples:
        >>> fxstyle.mark_compact(reply_button)
    """
    widget.setProperty(COMPACT_PROPERTY, bool(compact))
    fxutils.repolish(widget)
    widget.updateGeometry()


def mark_as_frame(widget: QWidget, is_frame: bool = True) -> None:
    """Paint a widget in the theme's ``frame`` color, as window chrome.

    Labels, check boxes, radio buttons and disabled tool buttons placed
    directly in it lose their own fill, so they sit on the frame. A
    `QSplitter` so marked draws its handles as frame-colored gaps, blank
    until the pointer finds one: then a 1 px accent line lights down its
    middle. Its width stays whatever `setHandleWidth` says.

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


def mark_as_nav(view: QAbstractItemView, is_nav: bool = True) -> None:
    """Draw an item view as a navigation list, as a sidebar's.

    Rows are 28 px chips at the small radius; the current one is a neutral
    chip with its text in the accent, so it reads as a place, not a
    selection.

    Args:
        view: The list or tree of places to go to.
        is_nav: False gives it the theme's own look back. Defaults to True.

    Examples:
        >>> fxstyle.mark_as_nav(pages)
    """
    view.setProperty(NAV_PROPERTY, bool(is_nav))
    # Chips sit 1 px apart; 3 px more at the ends gives the first and last
    # the 4 px to the frame they have at the sides. Not sheet padding: Qt
    # then paints a rounded frame's corners as thick wedges.
    end = _NAV_END_GAP if is_nav else 0
    view.setViewportMargins(0, end, 0, end)
    fxutils.repolish(view)


def mark_as_segmented(
    tabs: Union[QTabBar, QTabWidget], is_segmented: bool = True
) -> None:
    """Draw a tab bar as a segmented switch, as for Table | Gantt views.

    The tabs sit side by side on a ``state_pressed`` track; the picked one
    is a raised chip in the page colour with a 1 px ``border`` ring, its
    text in ``text_strong``. The chip slides to a newly picked tab on the
    spring over `MOTION_SPRING`, or jumps under reduced motion. Keyboard
    and signals are the tab bar's own.

    Args:
        tabs: The `QTabBar`, or the `QTabWidget` whose bar to mark.
        is_segmented: False gives the bar the plain tab look back.
            Defaults to True.

    Examples:
        >>> views = QTabBar()
        >>> views.addTab("Table")
        >>> views.addTab("Gantt")
        >>> fxstyle.mark_as_segmented(views)
    """
    from fxgui import _tabs

    _tabs.mark_as_segmented(tabs, is_segmented)


def set_tab_count(
    tabs: Union[QTabBar, QTabWidget], index: int, count: Optional[int]
) -> None:
    """Show a count after a tab's label, as a small ringed badge.

    Works on a plain or a segmented bar. A screen reader reads the tab as
    "Label, N". On a closable bar whose close buttons stand on the right,
    the count stands before the label. Call it again after renaming the
    tab, so the name read follows.

    Args:
        tabs: The `QTabBar`, or the `QTabWidget` whose bar to count on.
        index: The tab's index.
        count: The number to show; None removes the badge.

    Raises:
        IndexError: If the bar has no tab `index`.

    Examples:
        >>> fxstyle.set_tab_count(views, 0, 26)
        >>> fxstyle.set_tab_count(views, 0, None)
    """
    from fxgui import _tabs

    _tabs.set_tab_count(tabs, index, count)


def ink(widget: QWidget, token: Optional[str]) -> None:
    """Write a widget's text in one theme colour, through the stylesheet.

    The rule is the theme's, so the colour follows every theme switch. An
    inked label also loses its own fill, so it shows what it sits on.

    Args:
        widget: The widget whose text to ink.
        token: One of `INKS`, e.g. ``"text_muted"``; None returns the
            widget to its default ink.

    Raises:
        ValueError: If `token` is not one of `INKS`.

    Examples:
        >>> fxstyle.ink(hint_label, "text_muted")
        >>> fxstyle.ink(hint_label, None)
    """
    if token is not None and token not in INKS:
        raise ValueError(f"No ink {token!r}. Inks: {list(INKS)}")
    widget.setProperty(INK_PROPERTY, token or "")
    fxutils.repolish(widget)


# Prefixes a header's property naming one section's ink (ink_section).
SECTION_INK_PROPERTY = "fxSectionInk"


def ink_section(header: QHeaderView, section: int, token: Optional[str]) -> None:
    """Write one header section's label in one theme colour.

    Over the sheet's muted header ink and a sorted section's strong one:
    a weekend's day dimmed, today's in the accent.

    Args:
        header: The header view.
        section: The logical section.
        token: One of `INKS`, e.g. ``"text_dimmed"`` or ``"accent_primary"``;
            None gives the section the header's own ink back.

    Raises:
        ValueError: If `token` is not one of `INKS`.

    Examples:
        >>> fxstyle.ink_section(table.horizontalHeader(), 5, "text_dimmed")
    """
    if token is not None and token not in INKS:
        raise ValueError(f"No ink {token!r}. Inks: {list(INKS)}")
    header.setProperty(f"{SECTION_INK_PROPERTY}{section}", token or "")
    header.viewport().update()


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


def _overlay(
    ink: str, grounds: List[str], fill: str, floor: float = 1.0
) -> str:
    """Return `ink`, see-through, standing off its grounds as `fill` does.

    The least alpha, in hundredths up to a half, whose blend over the first
    ground reaches the contrast `fill` has with it, and over every ground
    at least `floor`. For a control with no ground of its own: it shows on
    a band, a card or a tooltip alike, where an opaque fill may equal the
    ground.

    Args:
        ink: The colour to see through, as hex.
        grounds: The colours it is drawn over, as hex; the first is the
            one `fill` is measured against.
        fill: The opaque fill whose contrast with the first ground to reach.
        floor: The least contrast over every ground. Defaults to 1.0.

    Returns:
        The colour as ``#AARRGGBB``, which QSS and QColor both read.
    """
    target = get_contrast_ratio(fill, grounds[0])
    color = QColor(ink)
    for step in range(1, 51):
        # Test the 8-bit alpha Qt paints, so rounding never leaves it short.
        color.setAlpha(round(255 * step / 100))
        alpha = color.alphaF()
        if get_contrast_ratio(
            mix(grounds[0], ink, alpha), grounds[0]
        ) >= target and all(
            get_contrast_ratio(mix(ground, ink, alpha), ground) >= floor
            for ground in grounds
        ):
            break
    return color.name(QColor.NameFormat.HexArgb)


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


def _control_line(text_line: int, shape: QFont) -> int:
    """Return a control's line box: 1.5 x `shape`'s pixel size, or the
    measured `text_line` where its face draws taller."""
    # Asked in pixels, as the theme's font is; else as matched, in points.
    pixel_size = shape.pixelSize()
    if pixel_size <= 0:
        pixel_size = QFontInfo(shape).pixelSize()
    return max(text_line, int(pixel_size * _LINE_BOX + 0.5))


def control_height(widget: QWidget) -> int:
    """Return the height a push button comes to in `widget`'s font."""
    # A line measured as a push button measures its text: rounded up from
    # the font's real line, where `height()` rounds it to nearest.
    line = widget.fontMetrics().size(Qt.TextShowMnemonic, "Ag").height()
    return _control_line(line, widget.font()) + _CONTROL_BOX


def _to_oklab(color: QColor) -> Tuple[float, float, float]:
    """Return `color` in OKLab, from sRGB."""

    def linear(channel: float) -> float:
        return (
            channel / 12.92 if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )

    r, g, b = (linear(c) for c in (
        color.redF(), color.greenF(), color.blueF()))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _from_oklab(lab: Tuple[float, float, float]) -> QColor:
    """Return the sRGB colour of an OKLab triple, clamped to the gamut."""
    L, a, b = lab
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3

    def encoded(channel: float) -> int:
        channel = max(0.0, min(1.0, channel))
        value = (
            12.92 * channel if channel <= 0.0031308
            else 1.055 * channel ** (1 / 2.4) - 0.055
        )
        return round(value * 255)

    return QColor(*(encoded(c) for c in (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )))


def mix_oklab(one_hex, two_hex, amount: float) -> str:
    """Return the hex colour `amount` of the way from one to two, in OKLab.

    As CSS ``color-mix(in oklab, ...)`` mixes: even in lightness, so a
    little white in a dark grey lightens it as little as the eye expects.

    Examples:
        >>> fxstyle.mix_oklab("#101113", "#f7f8f8", 0.1)
        '#222325'
    """
    one, two = _to_oklab(QColor(one_hex)), _to_oklab(QColor(two_hex))
    return _from_oklab(tuple(
        x + (y - x) * amount for x, y in zip(one, two))).name()


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


# A lit splitter handle's line, in px, and the dynamic properties a handle
# keeps its light in: how lit (0 to 1) and whether a drag holds it.
_HANDLE_LINE = 1
_GLOW_PROPERTY = "fxSplitterGlow"
_DRAG_PROPERTY = "fxSplitterDrag"


class _SplitterMark(QObject):
    """Paint a themed splitter's handles: nothing at rest, a line when lit.

    The handle is the hit area, as wide as `setHandleWidth` or the sheet
    says (8 px). A marked one fills the frame. Under the pointer, or while
    dragged, a 1 px `accent_primary` line down its middle fades in over
    `MOTION_FAST`, as a pane's edge does on the web. Painted in device
    pixels, so the line is whole at every screen scale.
    """

    @classmethod
    def watch(cls, splitter: QSplitter) -> None:
        """Give a themed `splitter` its painter, once."""
        if _is_themed(splitter) and splitter.findChild(
            cls, "", Qt.FindDirectChildrenOnly
        ) is None:
            cls(splitter)

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
        """Watch handles as they appear; light and paint them."""
        if isinstance(watched, QSplitter):
            # A handle is polished before its first paint, never after.
            if event.type() == QEvent.ChildPolished:
                self._watch()
            return False
        kind = event.type()
        if kind == QEvent.Paint:
            return self._paint(watched)
        if kind == QEvent.MouseButtonPress:
            watched.setProperty(_DRAG_PROPERTY, True)
            self._light(watched, True)
        elif kind == QEvent.MouseButtonRelease:
            watched.setProperty(_DRAG_PROPERTY, False)
            self._light(
                watched, watched.rect().contains(event.position().toPoint()))
        elif kind == QEvent.Enter:
            self._light(watched, True)
        elif kind == QEvent.Leave and not watched.property(_DRAG_PROPERTY):
            self._light(watched, False)
        return False

    @staticmethod
    def _light(handle: QWidget, lit: bool) -> None:
        """Fade `handle`'s line in or out; at once under reduced motion."""
        fade = handle.findChild(
            QVariantAnimation, _GLOW_PROPERTY, Qt.FindDirectChildrenOnly)
        if fade is not None:
            fade.stop()
        level = float(handle.property(_GLOW_PROPERTY) or 0.0)
        target = 1.0 if lit else 0.0
        if not motion() or level == target:
            handle.setProperty(_GLOW_PROPERTY, target)
            handle.update()
            return
        if fade is None:
            fade = QVariantAnimation(handle)
            fade.setObjectName(_GLOW_PROPERTY)
            fade.setDuration(MOTION_FAST)
            fade.setEasingCurve(ease_out())

            def step(value, handle=handle):
                handle.setProperty(_GLOW_PROPERTY, value)
                handle.update()

            fade.valueChanged.connect(step)
        fade.setStartValue(level)
        fade.setEndValue(target)
        fade.start()

    def _paint(self, handle: QWidget) -> bool:
        splitter = self.parent()
        framed = bool(splitter.property(FRAME_PROPERTY))
        level = float(handle.property(_GLOW_PROPERTY) or 0.0)
        if not framed and not level:
            return False
        theme = colors()
        painter = QPainter(handle)
        if framed:
            painter.fillRect(handle.rect(), QColor(theme.frame))
        if level:
            # Device pixels from here on, so the line is whole at any scale.
            ratio = painter.device().devicePixelRatioF()
            painter.setWorldTransform(
                QTransform.fromScale(1 / ratio, 1 / ratio))
            width = round(handle.width() * ratio)
            height = round(handle.height() * ratio)
            line = max(1, round(_HANDLE_LINE * ratio))
            ink = QColor(theme.accent_primary)
            ink.setAlphaF(ink.alphaF() * min(1.0, level))
            if splitter.orientation() == Qt.Vertical:
                painter.fillRect(0, (height - line) // 2, width, line, ink)
            else:
                painter.fillRect((width - line) // 2, 0, line, height, ink)
        painter.end()
        return True


def _readable_states(theme_data: dict) -> Dict[str, str]:
    """Return a theme's pressed fill and text inks, each held to its floor.

    - ``state_hover``: stepped away from ``surface`` until it differs by
      `STATE_MIN_CONTRAST` from ``surface``, ``surface_sunken``,
      ``surface_alt``, ``well`` and ``frame``, every ground it is drawn on,
      so a hovered row reads as a hovered tab does.
    - ``state_pressed``: stepped on until it differs by the same from
      ``state_hover`` and from those grounds and, when derived rather than
      stated, until it sits past ``state_hover`` toward black or white.
    - ``state_checked_hover``: stepped on from ``state_pressed`` until it
      differs from it (and every state ground) by the floor; ``text`` reads
      at 4.5:1 on it.
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
    # Every ground a state fill is drawn on: a pane, a view, a list set in a
    # pane, an alternate row, and the frame's bands, where icon buttons are
    # flat.
    state_grounds = [
        theme_data.get(key, surface)
        for key in ("surface", "surface_sunken", "surface_alt", "well",
                    "frame")
    ]
    # A theme may hold its states closer, as a brand's own fills do.
    floor = float(theme_data.get("state_contrast", STATE_MIN_CONTRAST))

    def stands_off(*others: str) -> Callable[[str], bool]:
        return lambda color: all(
            _reads(ground, floor)(color)
            for ground in (*state_grounds, *others))

    hover = step_toward(
        theme_data.get("state_hover")
        or mix_oklab(surface, theme_data["text"], HOVER_TINT), pole,
        stands_off())
    stated = theme_data.get("state_pressed")
    off_hover = stands_off(hover)

    def past_hover(color: str) -> bool:
        # The derived start can sit on the surface's side of a hover pushed
        # far, as catppuccin_latte's did: a pressed fill lighter than hover.
        return get_contrast_ratio(color, pole) < get_contrast_ratio(
            hover, pole)

    pressed = step_toward(
        stated or mix_oklab(surface, theme_data["text"], PRESSED_TINT),
        pole,
        lambda color: off_hover(color) and (bool(stated) or past_hover(color)))
    # A checked button under the pointer: a step past pressed, so the click
    # that unchecks it shows. One step at least, for a brand's floor of 1.
    checked_hover = step_toward(
        pressed, pole,
        lambda color: color != pressed and stands_off(pressed)(color))
    # A raised card: a step off a dark pane toward its text; on a light
    # pane, the pane itself (white is as raised as it gets).
    card = theme_data.get("card") or (
        surface if _is_light(surface)
        else mix_oklab(surface, theme_data["text"], CARD_STEP))
    grounds = [
        theme_data.get(key, surface)
        for key in ("surface", "surface_sunken", "surface_alt", "well",
                    "frame", "tooltip")
    ] + [hover, card]

    def reading(ink: str, on: list) -> str:
        return step_toward(QColor(ink).name(), pole, lambda color: all(
            get_contrast_ratio(color, ground) >= TEXT_CONTRAST
            for ground in on))

    muted = reading(theme_data["text_muted"], grounds)
    text = reading(theme_data["text"], grounds + [pressed, checked_hover])
    # Then on, until muted text reads as a step below it; where text meets
    # the pole first, muted steps back toward the surface while it reads.
    text = step_toward(text, pole, _reads(muted, MUTED_STEP))
    if not _reads(muted, MUTED_STEP)(text):
        quieter = step_toward(muted, surface, _reads(text, MUTED_STEP))
        if all(get_contrast_ratio(quieter, ground) >= TEXT_CONTRAST
               for ground in grounds):
            muted = quieter
    # Dimmed reads at 4.5:1 too, so where muted already sits at that floor it
    # comes to muted, never past it.
    dimmed = reading(
        theme_data.get("text_dimmed") or mix_oklab(text, muted, 1.5), grounds)
    if get_contrast_ratio(dimmed, surface) > get_contrast_ratio(muted, surface):
        dimmed = muted
    return {
        "card": card,
        "state_hover": hover,
        "state_pressed": pressed,
        "state_checked_hover": checked_hover,
        "text": text,
        "text_muted": muted,
        # What a row's name is drawn in: past text, toward black or white.
        "text_strong": theme_data.get("text_strong")
        or mix_oklab(text, pole, STRONG_STEP),
        # Halfway from text to muted: a task's name, a pane's values.
        "text_toned": reading(
            theme_data.get("text_toned") or mix_oklab(text, muted, 0.5),
            grounds),
        # Half that step again past muted, still read at 4.5:1: chevrons,
        # separators, dates, an empty cell's dash.
        "text_dimmed": dimmed,
    }


def _is_light(surface: str) -> bool:
    """Return whether a theme whose pane is `surface` is a light one."""
    return QColor(surface).lightness() > 128


def _line_tokens(theme_name: str) -> Dict[str, str]:
    """Return the sizes that line controls and rows up in the theme's font.

    Each control rounds its own line, so no padding alone lines them up for
    every font: a line edit, a combo box and a spin box come to a push
    button's height, and a menu row to a list popup's.
    """
    if QGuiApplication.instance() is None:
        # No font to measure yet: a root registers later, and rebuilds.
        line = text_line = FONT_SIZE + 3
        theme_font = QFont()
        theme_font.setPixelSize(FONT_SIZE)
    else:
        theme_font = font(theme_name)
        metrics = QFontMetrics(theme_font)
        line = metrics.height()
        text_line = metrics.size(Qt.TextShowMnemonic, "Ag").height()
    line_box = _control_line(text_line, theme_font)
    height = line_box + _CONTROL_BOX
    spare = height - max(line, _SPIN_LINE_FLOOR) - _SPIN_BASE
    top, bottom = (spare + 1) // 2, spare // 2
    # A push button's padding is what its 1 px edges and text line leave.
    room = height - 2 - text_line
    return {
        "@field_inner": f"{height - _FIELD_BOX}px",
        # A filter field: 4 px under a control, as the web look's.
        "@filter_inner": f"{height - FILTER_DROP - _FIELD_BOX}px",
        "@spin_padding": f"{top}px 10px {bottom}px 10px",
        "@button_padding": f"{(room + 1) // 2}px 10px {room // 2}px 10px",
        # An on/off mark's label line, the mark centred in it.
        "@line_box": f"{line_box}px",
        # A tab's line as a dock tab's title label measures it.
        "@text_line": f"{text_line}px",
    }


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
    # A level that names no background gets its colour over the pane, and
    # that colour stepped until it reads as text on it.
    for level, pair in theme_data.get("feedback", {}).items():
        if isinstance(pair, dict):
            pair = dict(pair)
            if "background" not in pair and "foreground" in pair:
                ground = mix_oklab(
                    theme_data["surface"], pair["foreground"], FEEDBACK_TINT)
                pair["background"] = ground
                pair["foreground"] = step_toward(
                    QColor(pair["foreground"]).name(), _pole_from(ground),
                    _reads(ground, TEXT_CONTRAST))
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

    # A selected item's fill is the accent unless the theme names a softer
    # one, whose inks are the theme's own text and icon made to read on it.
    # A derived one steps toward the accent until a selected row shows on
    # every view it fills: catppuccin_latte's 15% vanished on its lists.
    selection = theme_data.get("selection")
    if not selection:
        views = [
            theme_data.get(key, theme_data["surface"])
            for key in ("surface", "surface_sunken", "well")
        ]
        selection = step_toward(
            mix_oklab(theme_data["surface"], accent_primary, SELECTION_TINT),
            accent_primary,
            lambda color: all(_visibly_differ(color, view) for view in views))
    tokens["@selection"] = selection
    tokens["@popup_item_pad"] = f"{_POPUP_ITEM_PAD}px"
    tokens["@body_weight"] = str(drawn_weight(BODY_WEIGHT, theme_name))
    tokens["@emphasis_weight"] = str(drawn_weight(EMPHASIS_WEIGHT, theme_name))
    tokens["@strong_weight"] = str(drawn_weight(STRONG_WEIGHT, theme_name))
    # A tree's row rule under its branches: the cells' rule, see-through as
    # theirs is. Qt paints a cell's panel twice, so the cells' 60 % lands
    # twice; the branches' one stroke carries the same total.
    branch_rule = QColor(theme_data.get("border", theme_data["surface"]))
    branch_rule.setAlphaF(1 - (1 - _TABLE_RULE_ALPHA) ** 2)
    tokens["@branch_rule"] = branch_rule.name(QColor.NameFormat.HexArgb)
    tokens["@selection_border"] = (
        theme_data.get("selection_border") or accent_primary)
    if selection == accent_primary:
        tokens["@text_on_selection"] = text_on_primary
        tokens["@icon_on_selection"] = tokens["@icon_on_accent_primary"]
    else:
        tokens["@text_on_selection"] = readable_ink(
            selection, theme_data["text"])
        tokens["@icon_on_selection"] = readable_ink(
            selection, theme_data.get("icon", theme_data["text"]))

    # A flat button has no ground of its own (a band, a card, a tooltip),
    # where an opaque fill can equal the ground: its fills are the text,
    # see-through, standing off `surface` as the opaque ones do. A 24 px
    # icon cannot carry the faint fill a wide row can, so each also holds
    # fxgui's floor on every ground, a floor further per state, whatever
    # the theme's `state_contrast`; the opaque fills stay as stated.
    surface = theme_data["surface"]
    flat_grounds = [surface] + [
        theme_data.get(key, surface)
        for key in ("tooltip", "frame", "surface_sunken", "surface_alt", "well")
    ]
    for steps, state in enumerate(
        ("state_hover", "state_pressed", "state_checked_hover"), start=1
    ):
        tokens[f"@{state}_overlay"] = _overlay(
            theme_data["text"], flat_grounds, theme_data[state],
            STATE_MIN_CONTRAST ** steps)

    (
        tokens["@primary_button"],
        tokens["@primary_button_hover"],
        tokens["@primary_button_pressed"],
    ) = _primary_button_fills(
        accent_primary, accent_secondary, text_on_primary, text_on_secondary
    )
    # A destructive verb's button: the error colour, filled as a primary
    # button is, with the pole that reads on it.
    danger = tokens.get("@feedback_error_foreground", "#e5484d")
    tokens["@text_on_danger"] = _pole_from(danger)
    (
        tokens["@danger_button"],
        tokens["@danger_button_hover"],
        tokens["@danger_button_pressed"],
    ) = _primary_button_fills(
        danger, danger, tokens["@text_on_danger"], tokens["@text_on_danger"])
    # The veil a modal dialog drops over its window (ls-ui's gallery).
    tokens["@modal_scrim"] = theme_data.get("modal_scrim") or (
        "#bff3f3f5" if _is_light(theme_data["surface"]) else "#99000000")

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
    # A meter's empty track: the text at 8 % over the pane (9 % on a light
    # one), as the web look's; the filled span carries the value.
    # Held back toward the pane where the fill would read under 3:1 on it.
    tokens["@meter_track"] = step_toward(
        mix(theme_data["surface"], theme_data["text"],
            0.09 if _is_light(theme_data["surface"]) else 0.08),
        theme_data["surface"],
        _reads(accent_primary, CONTROL_CONTRAST))
    tokens["@compact_inner"] = f"{COMPACT_HEIGHT - 2}px"
    tokens["@button_radius"] = f"{BUTTON_RADIUS}px"
    tokens["@card_radius"] = f"{CARD_RADIUS}px"
    tokens["@small_radius"] = f"{SMALL_RADIUS}px"
    tokens["@row_height"] = f"{row_height()}px"
    names = list(ROW_SIZES)
    tokens["@dense_row_height"] = (
        f"{ROW_SIZES[names[max(names.index(row_size()) - 1, 0)]]}px")
    # A navigation list's current row: the accent, stepped until it reads
    # on the pressed chip behind it.
    tokens["@nav_ink"] = readable_ink(
        theme_data.get("state_pressed", theme_data["surface"]),
        theme_data["accent_primary"],
    )
    tokens["@indicator_size"] = f"{INDICATOR_SIZE}px"
    # Text a step and two below the body: a header's labels, a keycap's.
    tokens["@font_size_small"] = f"{FONT_SIZE - 1}px"
    tokens["@font_size_tiny"] = f"{FONT_SIZE - 2}px"
    # A drawn mark's box less its 1 px edge, and the corner that makes it round.
    tokens["@indicator_inner"] = f"{INDICATOR_SIZE - 2}px"
    tokens["@indicator_round"] = f"{INDICATOR_SIZE // 2}px"
    tokens["@thin_scroll_radius"] = f"{THIN_SCROLL_WIDTH // 2}px"
    tokens["@thin_scroll"] = f"{THIN_SCROLL_WIDTH}px"
    tokens["@pane_gap_half"] = f"{PANE_GAP // 2}px"
    tokens["@pane_gap"] = f"{PANE_GAP}px"
    tokens["@tab_padding"] = f"{TAB_PADDING}px"
    tokens.update(_line_tokens(theme_name))
    tokens["@cell_lead"] = f"{_CELL_LEAD}px"
    tokens["@cell_padding"] = f"{_CELL_PADDING}px"
    tokens["@header_height"] = f"{_HEADER_HEIGHT}px"

    # url(~icons/...) in QSS: the folder of the theme being resolved, which
    # need not be the current one.
    icon_folder = (
        "stylesheet_light" if _is_light(theme_data["surface"])
        else "stylesheet_dark"
    )
    tokens["~icons"] = (fxconstants.ICONS_ROOT / icon_folder).as_posix()
    return tokens


# `~icon(name, token[, px])`: the icon library's `name`, filled with a token,
# 16 px unless sized.
_SHEET_ICON = re.compile(r"~icon\(([\w-]+),\s*(\w+)(?:,\s*(\d+))?\)")
# `url(~icons/name.svg[, px])`: an image of the theme's light or dark sheet
# set, `_SHEET_ICON_SIZE` unless sized.
_SHEET_ICON_SIZE = 18
_SHEET_SVG = re.compile(r"url\(~icons/(\w+)\.svg(?:,\s*(\d+))?\)")


# Qt loads `name@2x.png` beside `name.png` on a screen scaled past 100%.
_SHEET_SCALES = (3, 2, 1)


def _sheet_icon(
    svg: str, stem: str, size: int, color: Optional[str] = None
) -> str:
    """Return a sheet `url()` of `svg` as a `size` px PNG, filled `color`.

    A sheet reads an SVG through the qsvg plugin, which Cinema 4D fails to
    load, so its images go blank; a PNG needs no plugin. `size` is the size
    the rule draws it at: Qt blurs a PNG it scales down.
    """
    folder = fxicons._cache_dir() / "sheet_icons"
    # The temp folder is shared by every fxgui install: the name carries
    # which file, at which size and version, it was drawn from.
    source = f"{os.path.abspath(svg)}|{size}|{os.stat(svg).st_mtime_ns}"
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
    stem = f"{stem}_{size}_{digest}"
    path = folder / f"{stem}.png"
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        # The plain file goes last: its presence says the set is whole.
        for scale in _SHEET_SCALES:
            target = path.with_name(
                f"{stem}@{scale}x.png" if scale > 1 else path.name
            )
            pixmap = fxicons._raster(svg, size, size, scale, color)
            # Written aside, then renamed: another app starting at once must
            # never load a half-written file.
            part = target.with_name(f"{target.name}.{os.getpid()}.part")
            if not pixmap.save(str(part), "PNG"):
                raise OSError(f"Cannot write {part}")
            try:
                os.replace(part, target)
            except OSError:
                # Windows refuses while another app holds the target open;
                # by its name, that file is this same image.
                if not target.exists():
                    raise
                with contextlib.suppress(OSError):
                    os.remove(part)
    # Quoted: Qt drops the whole sheet over a `$` in a bare url, and the
    # temp folder of a Windows service account ends in one.
    return f'url("{path.as_posix()}")'


def _substitute(qss: str, tokens: Dict[str, str]) -> str:
    """Replace each placeholder, longest first so @border spares @border_light."""

    def icon(match: "re.Match") -> str:
        name, color = match.group(1), tokens.get(f"@{match.group(2)}")
        if not color:
            return match.group(0)
        svg = fxicons.get_icon_path(name)
        # From the file, so one name in two libraries keeps two images.
        stem = f"{Path(svg).parent.name}_{Path(svg).stem}_{color.lstrip('#')}"
        size = int(match.group(3) or 16)
        return _sheet_icon(svg, stem, size, color)

    def sheet_svg(match: "re.Match") -> str:
        folder = Path(tokens["~icons"])
        svg = str(folder / f"{match.group(1)}.svg")
        stem = f"{folder.name}_{match.group(1)}"
        return _sheet_icon(svg, stem, int(match.group(2) or _SHEET_ICON_SIZE))

    qss = _SHEET_ICON.sub(icon, qss)
    qss = _SHEET_SVG.sub(sheet_svg, qss)
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


# Qt platforms that draw on no screen: nobody there chose a theme.
_HEADLESS_PLATFORMS = frozenset({"offscreen", "minimal"})


def _interactive() -> bool:
    """Return whether Qt draws on a real screen, so a person is choosing."""
    if QGuiApplication.instance() is not None:
        name = QGuiApplication.platformName()
    else:
        # Without an application, platformName() names the default platform.
        name = os.environ.get("QT_QPA_PLATFORM", "")
    # QT_QPA_PLATFORM may carry fallbacks ("a;b") and options ("a:x=1").
    return name.split(";")[0].split(":")[0] not in _HEADLESS_PLATFORMS


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
        >>> fxstyle.apply_theme(fxstyle.load_saved_theme(), save=False)
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


def get_theme() -> str:
    """Get the current theme name.

    On first access, the theme is loaded from persistent storage.
    If no theme was previously saved, defaults to "dark".

    Returns:
        The current theme name (e.g., "dark", "light").
    """
    global _theme
    if _theme is None:
        _theme = load_saved_theme()
    return _theme


def row_size() -> str:
    """Return the `ROW_SIZES` name in force, the saved one on first access."""
    global _row_size
    if _row_size is None:
        saved = fxconfig.get_value(_SETTINGS_ROW_SIZE_KEY, _DEFAULT_ROW_SIZE)
        _row_size = saved if saved in ROW_SIZES else _DEFAULT_ROW_SIZE
    return _row_size


def _forget_saved_settings() -> None:
    """Re-read the theme and row size from the settings file, re-styling."""
    global _theme, _row_size
    before = (_theme, _row_size)
    _theme = None
    _row_size = None
    _invalidate_theme_namespace()
    # Live roots wear the old file's theme: re-apply when the new one differs.
    if _themed_roots and any(
        old is not None and old != new
        for old, new in zip(before, (get_theme(), row_size()))
    ):
        _colors_changed()


def row_height(view: Optional[QWidget] = None) -> int:
    """Return the height, in pixels, of a list or tree row.

    Args:
        view: The view the row is in. A view marked dense (`mark_dense`)
            takes one row size under the one in force.
    """
    names = list(ROW_SIZES)
    size = row_size()
    if view is not None and view.property(DENSE_PROPERTY):
        size = names[max(names.index(size) - 1, 0)]
    return ROW_SIZES[size]


def column_lines() -> bool:
    """Return whether tables and trees rule every column, the saved choice.

    Off unless chosen (`apply_column_lines`): the first column is ruled
    either way, as the web look's pinned name column.
    """
    if _column_lines_now is not None:
        return _column_lines_now
    return _truthy(fxconfig.get_value(_SETTINGS_COLUMN_LINES_KEY, False))


def apply_column_lines(on: bool, *, save: Optional[bool] = None) -> bool:
    """Rule every column of tables and trees, or only the first; re-paint.

    Args:
        on: True rules every column; False only the first.
        save: Whether to save it as the person's choice. None (the default)
            saves unless Qt runs headless, as `apply_row_size`.

    Examples:
        >>> fxstyle.apply_column_lines(True)
    """
    global _column_lines_now
    _column_lines_now = bool(on)
    if save is None:
        save = _interactive()
    if save:
        fxconfig.set_value(_SETTINGS_COLUMN_LINES_KEY, bool(on))
    _colors_changed()
    return bool(on)


def _truthy(value) -> bool:
    """Return a saved setting read back as a bool (an INI keeps strings)."""
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


# The column lines chosen in this session, before or without a save.
_column_lines_now: Optional[bool] = None


def _column_ruled(view: Optional[QWidget], column: int) -> bool:
    """Whether a cell of `column` in `view` draws a rule at its right edge.

    The first visible column always does, past one column; every other
    but the last only with `column_lines` on.
    """
    if isinstance(view, QTreeView):
        header = view.header()
    elif isinstance(view, QTableView):
        header = view.horizontalHeader()
    else:
        return False
    shown = [
        header.logicalIndex(visual) for visual in range(header.count())
        if not header.isSectionHidden(header.logicalIndex(visual))
    ]
    if len(shown) < 2 or column not in shown[:-1]:
        return False
    return column == shown[0] or column_lines()


def draw_column_rule(
    painter: QPainter, rect: QRect, view: Optional[QWidget], column: int
) -> None:
    """Draw a cell's column rule at its right edge, if it has one.

    For an item delegate that paints its own cells; fxgui's own views and
    `FXThumbnailDelegate` draw it already.

    Args:
        painter: The painter on the view's viewport.
        rect: The cell's rect.
        view: The view the cell is in.
        column: The cell's logical column.
    """
    if not _column_ruled(view, column):
        return
    ink = QColor(colors().border)
    ink.setAlphaF(_TABLE_RULE_ALPHA)
    painter.fillRect(QRect(rect.right(), rect.top(), 1, rect.height()), ink)


def mark_flush(view: QWidget, flush: bool = True) -> None:
    """Draw a view that fills its pane with no frame of its own.

    The pane's edge is its frame, as the web look's tables and trees sit
    flush in their card; a small table inside a section keeps its frame.
    `FXDockArea` marks a pane whose body is a view itself.

    Args:
        view: A list, tree, table or other scroll area.
        flush: False gives it its frame back.

    Examples:
        >>> fxstyle.mark_flush(browse_tree)
    """
    view.setProperty(FLUSH_PROPERTY, bool(flush))
    fxutils.repolish(view)


def mark_dense(view: QWidget, dense: bool = True) -> None:
    """Make a view's rows one row size under the one in force.

    For a navigation tree, as the web look's Hierarchy: small rows while
    the person's row height is normal, normal ones when it is big, small
    still when it is small. Lists keep the row height in force.

    Args:
        view: A tree or list view.
        dense: False gives it the row height in force back.

    Examples:
        >>> fxstyle.mark_dense(browse_tree)
    """
    view.setProperty(DENSE_PROPERTY, bool(dense))
    fxutils.repolish(view)
    if isinstance(view, QAbstractItemView):
        view.scheduleDelayedItemsLayout()


def apply_row_size(size: str, *, save: Optional[bool] = None) -> str:
    """Make every list and tree row `size` tall, save it when chosen, re-style.

    Args:
        size: A `ROW_SIZES` name.
        save: Whether to save the row size as the person's choice. None (the
            default) saves unless Qt runs headless (the "offscreen" or
            "minimal" platform), so a script or a test never overwrites it.

    Raises:
        ValueError: If `size` is not a `ROW_SIZES` name.

    Examples:
        >>> fxstyle.apply_row_size("small")
    """
    global _row_size
    if size not in ROW_SIZES:
        raise ValueError(f"Row size '{size}' not found: {sorted(ROW_SIZES)}")
    _row_size = size
    if save is None:
        save = _interactive()
    if save:
        fxconfig.set_value(_SETTINGS_ROW_SIZE_KEY, size)
    _colors_changed()
    return size


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
    global _theme_namespace
    if _theme_namespace is None:
        _theme_namespace = FXThemeColors(_colour_tokens(get_theme()))
    return _theme_namespace


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


def apply_theme(theme: str, *, save: Optional[bool] = None) -> str:
    """Apply a theme to every themed root and emit ``theme_changed``.

    Args:
        theme: The theme name to apply (e.g., "dark", "light").
        save: Whether to save the theme as the person's choice. None (the
            default) saves unless Qt runs headless (the "offscreen" or
            "minimal" platform), so a script or a test never overwrites it.

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
    if save is None:
        save = _interactive()
    if save:
        save_theme(theme)
    _colors_changed()
    return theme


def set_style(widget: QWidget, style: str = None) -> "FXProxyStyle":
    """Give `widget` (or the application) FXProxyStyle over a Qt style.

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


@lru_cache(maxsize=2)
def _sort_arrow(name: str) -> QIcon:
    """Return a header's sort arrow, in the sorted label's strong ink."""
    return fxicons.get_icon(name, color="text_strong")


@lru_cache(maxsize=1)
def _standard_icons() -> dict:
    """Return the themed icon standing in for each Qt standard pixmap."""
    # fmt: off
    return {
        QStyle.SP_ArrowBack: fxicons.get_icon("arrow-left"),
        QStyle.SP_ArrowDown: fxicons.get_icon("arrow-down"),
        QStyle.SP_ArrowForward: fxicons.get_icon("arrow-right"),
        QStyle.SP_ArrowLeft: fxicons.get_icon("chevron-left"),
        QStyle.SP_ArrowRight: fxicons.get_icon("chevron-right"),
        QStyle.SP_ArrowUp: fxicons.get_icon("arrow-up"),
        QStyle.SP_BrowserReload: fxicons.get_icon("refresh-cw"),
        QStyle.SP_BrowserStop: fxicons.get_icon("ban"),
        QStyle.SP_CommandLink: fxicons.get_icon("arrow-right"),
        QStyle.SP_ComputerIcon: fxicons.get_icon("monitor"),
        QStyle.SP_CustomBase: fxicons.get_icon("sliders-horizontal"),
        QStyle.SP_DesktopIcon: fxicons.get_icon("monitor"),
        QStyle.SP_DialogAbortButton: fxicons.get_icon("circle-x"),
        QStyle.SP_DialogApplyButton: fxicons.get_icon("check"),
        QStyle.SP_DialogCancelButton: fxicons.get_icon("circle-x"),
        QStyle.SP_DialogCloseButton: fxicons.get_icon("x"),
        QStyle.SP_DialogDiscardButton: fxicons.get_icon("trash"),
        QStyle.SP_DialogHelpButton: fxicons.get_icon("circle-question-mark"),
        QStyle.SP_DialogIgnoreButton: fxicons.get_icon("bell-off"),
        QStyle.SP_DialogNoButton: fxicons.get_icon("circle-x"),
        QStyle.SP_DialogNoToAllButton: fxicons.get_icon("circle-minus"),
        QStyle.SP_DialogOkButton: fxicons.get_icon("check"),
        QStyle.SP_DialogOpenButton: fxicons.get_icon("external-link"),
        QStyle.SP_DialogResetButton: fxicons.get_icon("brush-cleaning"),
        QStyle.SP_DialogRetryButton: fxicons.get_icon("rotate-ccw"),
        QStyle.SP_DialogSaveAllButton: fxicons.get_icon("save-all"),
        QStyle.SP_DialogSaveButton: fxicons.get_icon("save"),
        QStyle.SP_DialogYesButton: fxicons.get_icon("check"),
        QStyle.SP_DialogYesToAllButton: fxicons.get_icon("check-check"),
        QStyle.SP_DirClosedIcon: fxicons.get_icon("folder"),
        QStyle.SP_DirHomeIcon: fxicons.get_icon("house"),
        QStyle.SP_DirIcon: fxicons.get_icon("folder-open"),
        QStyle.SP_DirLinkIcon: fxicons.get_icon("link"),
        QStyle.SP_DirLinkOpenIcon: fxicons.get_icon("folder-open"),
        QStyle.SP_DockWidgetCloseButton: fxicons.get_icon("x"),
        QStyle.SP_DirOpenIcon: fxicons.get_icon("folder-open"),
        QStyle.SP_DriveCDIcon: fxicons.get_icon("disc-3"),
        QStyle.SP_DriveDVDIcon: fxicons.get_icon("disc-3"),
        QStyle.SP_DriveFDIcon: fxicons.get_icon("usb"),
        QStyle.SP_DriveHDIcon: fxicons.get_icon("usb"),
        QStyle.SP_DriveNetIcon: fxicons.get_icon("cloud"),
        QStyle.SP_FileDialogBack: fxicons.get_icon("arrow-left"),
        QStyle.SP_FileDialogContentsView: fxicons.get_icon("file-search"),
        QStyle.SP_FileDialogDetailedView: fxicons.get_icon("file-text"),
        QStyle.SP_FileDialogEnd: fxicons.get_icon("circle-check"),
        QStyle.SP_FileDialogInfoView: fxicons.get_icon("info"),
        QStyle.SP_FileDialogListView: fxicons.get_icon("list"),
        QStyle.SP_FileDialogNewFolder: fxicons.get_icon("folder-plus"),
        QStyle.SP_FileDialogStart: fxicons.get_icon("file"),
        QStyle.SP_FileDialogToParent: fxicons.get_icon("folder-up"),
        QStyle.SP_FileIcon: fxicons.get_icon("file"),
        QStyle.SP_FileLinkIcon: fxicons.get_icon("link"),
        QStyle.SP_LineEditClearButton: fxicons.get_icon("x"),
        QStyle.SP_MediaPause: fxicons.get_icon("pause"),
        QStyle.SP_MediaPlay: fxicons.get_icon("play"),
        QStyle.SP_MediaSeekBackward: fxicons.get_icon("rewind"),
        QStyle.SP_MediaSeekForward: fxicons.get_icon("fast-forward"),
        QStyle.SP_MediaSkipBackward: fxicons.get_icon("skip-back"),
        QStyle.SP_MediaSkipForward: fxicons.get_icon("skip-forward"),
        QStyle.SP_MediaStop: fxicons.get_icon("square"),
        QStyle.SP_MediaVolume: fxicons.get_icon("volume-2"),
        QStyle.SP_MediaVolumeMuted: fxicons.get_icon("volume-x"),
        QStyle.SP_MessageBoxCritical: fxicons.get_icon("circle-alert", color="feedback_error_foreground"),
        QStyle.SP_MessageBoxInformation: fxicons.get_icon("info", color="feedback_info_foreground"),
        QStyle.SP_MessageBoxQuestion: fxicons.get_icon("circle-question-mark", color="feedback_success_foreground"),
        QStyle.SP_MessageBoxWarning: fxicons.get_icon("triangle-alert", color="feedback_warning_foreground"),
        QStyle.SP_RestoreDefaultsButton: fxicons.get_icon("rotate-ccw"),
        QStyle.SP_TitleBarCloseButton: fxicons.get_icon("x"),
        QStyle.SP_TitleBarContextHelpButton: fxicons.get_icon("circle-question-mark"),
        QStyle.SP_TitleBarMaxButton: fxicons.get_icon("square"),
        QStyle.SP_TitleBarMenuButton: fxicons.get_icon("menu"),
        QStyle.SP_TitleBarMinButton: fxicons.get_icon("minus"),
        QStyle.SP_TitleBarNormalButton: fxicons.get_icon("copy"),
        QStyle.SP_TitleBarShadeButton: fxicons.get_icon("chevron-down"),
        QStyle.SP_TitleBarUnshadeButton: fxicons.get_icon("chevron-up"),
        QStyle.SP_ToolBarHorizontalExtensionButton: fxicons.get_icon("chevron-right"),
        QStyle.SP_ToolBarVerticalExtensionButton: fxicons.get_icon("arrow-down"),
        QStyle.SP_TrashIcon: fxicons.get_icon("trash"),
        QStyle.SP_VistaShield: fxicons.get_icon("shield"),
    }
    # fmt: on


# Read once: pixelMetric runs thousands of times per restyle, and each
# enum attribute read goes through Python's enum machinery.
_LAYOUT_GAPS = (
    QStyle.PM_LayoutHorizontalSpacing,
    QStyle.PM_LayoutVerticalSpacing,
)
_LIST_ICON = QStyle.PM_ListViewIconSize
_TREE_INDENTATION = QStyle.PM_TreeViewIndentation
# A row's hairline, Lumen's border at 60%.
_TABLE_RULE_ALPHA = 0.6
# A header's sort arrow: its side, its gap after the label, and the label's
# lead in the section (the sheet's ::section padding).
_SORT_ARROW = 12
_SORT_GAP = 4
_HEADER_LEAD = _CELL_LEAD
# A cell's parts, which a row Qt paints natively asks this style for.
_ITEM_PARTS = (
    QStyle.SE_ItemViewItemText,
    QStyle.SE_ItemViewItemDecoration,
    QStyle.SE_ItemViewItemCheckIndicator,
    QStyle.SE_ItemViewItemFocusRect,
)
# A header label's icon, which sits before its words.
_HEADER_ICON = 16
_SMALL_ICON = QStyle.PM_SmallIconSize
_CLOSE_WIDTH = QStyle.PM_TabCloseIndicatorWidth
# How long after a tooltip shows the next target's shows at once, in ms.
_TIP_AWAKE = QStyle.SH_ToolTip_FallAsleepDelay
_TIP_AWAKE_MS = 300


def _mark_self_ruled(view: QAbstractItemView) -> None:
    """Mark a view whose delegate rules its own rows, before it paints.

    The sheet's branch rule then stands down there; a delegate set after
    the view shows marks the view itself on its first paint.
    """
    if getattr(view.itemDelegate(), "_FX_RULES_ITS_ROWS", False) and not (
        view.property("fxRulesRows")
    ):
        view.setProperty("fxRulesRows", True)
        fxutils.repolish(view)


def _ruled(view: Optional[QWidget]) -> bool:
    """Whether `view` draws a hairline under each row.

    A table, and a tree or list that is no navigation list, icon grid or
    popup's list (a combo box's, a completer's, a menu-like list's).
    """
    if isinstance(view, QTableView):
        return True
    if isinstance(view, QListView):
        if view.viewMode() == QListView.IconMode:
            return False
    elif not isinstance(view, QTreeView):
        return False
    return not (
        view.property(NAV_PROPERTY)
        or view.property(POPUP_PROPERTY)
        or view.window().windowType() == Qt.Popup
    )


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
        icon = _standard_icons().get(standardIcon)
        if icon is not None:
            return icon
        return super().standardIcon(standardIcon, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        """Draw `element`, except Qt's focus rectangle; rule a view's rows.

        PySide6 6.5's Fusion and Windows 11 draw it on an item view's current
        cell whatever the sheet's ``outline`` says, tinting its
        BackgroundRole; every fxgui control shows focus in its own edge.
        A table, tree or list cell gets Lumen's hairline under it here, over
        its own BackgroundRole: a sheet ``::item`` border would hide that
        colour.
        """
        if element == QStyle.PE_FrameFocusRect:
            return
        if element == QStyle.PE_IndicatorHeaderArrow and isinstance(
            option, QStyleOptionHeader
        ):
            # Qt names an ascending sort SortDown; Lumen marks it arrow-up.
            up = option.sortIndicator == QStyleOptionHeader.SortDown
            _sort_arrow("arrow-up" if up else "arrow-down").paint(
                painter, option.rect
            )
            return
        super().drawPrimitive(element, option, painter, widget)
        if element == QStyle.PE_PanelItemViewItem and _ruled(widget):
            index = getattr(option, "index", None)
            if index is not None and index.isValid():
                draw_column_rule(painter, option.rect, widget, index.column())
            rule = QColor(colors().border)
            rule.setAlphaF(_TABLE_RULE_ALPHA)
            painter.save()
            painter.setPen(QPen(rule, 1))
            bottom = option.rect.bottom()
            painter.drawLine(
                option.rect.left(), bottom, option.rect.right(), bottom
            )
            painter.restore()

    def drawControl(self, element, option, painter, widget=None):
        """Draw `element`; a header section's label in its own ink.

        A section given one by `ink_section` wears it, a sorted one the
        strong ink. No sheet pseudo-state tells either, so the label is
        recoloured here, under the sheet's own colour for the section.
        """
        if (
            element == QStyle.CE_HeaderLabel
            and isinstance(option, QStyleOptionHeader)
            and _is_themed(widget)
        ):
            token = widget.property(f"{SECTION_INK_PROPERTY}{option.section}")
            if not token and (
                option.sortIndicator != QStyleOptionHeader.SortIndicator.None_
            ):
                token = "text_strong"
            if token:
                option = QStyleOptionHeader(option)
                option.palette.setColor(
                    QPalette.ColorRole.ButtonText,
                    QColor(getattr(colors(), token)))
        super().drawControl(element, option, painter, widget)

    # Set while the sheet is asked for a cell's rects, which it may ask back.
    _asking_sheet = False

    def subElementRect(self, element, option, widget=None):
        """Return `element`'s rect; a header's sort arrow follows its label.

        A cell's text, icon and check box take the sheet's rects: Qt 6.8
        and older paint a resting row natively, here, without the item's
        padding, and a highlighted one through the sheet, with it.
        """
        if (
            element in _ITEM_PARTS
            and widget is not None
            and not self._asking_sheet
        ):
            sheet = widget.style()
            if sheet is not self and sheet.inherits("QStyleSheetStyle"):
                self._asking_sheet = True
                try:
                    return sheet.subElementRect(element, option, widget)
                finally:
                    self._asking_sheet = False
        rect = super().subElementRect(element, option, widget)
        if (
            element != QStyle.SE_HeaderArrow
            or not isinstance(option, QStyleOptionHeader)
            # A label set right or centred keeps the arrow at the end.
            or not option.textAlignment & Qt.AlignLeft
        ):
            return rect
        font = QFont(
            widget.font() if widget is not None else QApplication.font()
        )
        # The sheet's ::section size and weight, which the option's font
        # does not carry.
        font.setPixelSize(FONT_SIZE - 1)
        font.setWeight(_WEIGHTS[drawn_weight(EMPHASIS_WEIGHT)])
        label = QFontMetrics(font).horizontalAdvance(option.text)
        if not option.icon.isNull():
            label += _HEADER_ICON + _SORT_GAP
        section = option.rect
        left = section.left() + _HEADER_LEAD + label + _SORT_GAP
        return QRect(
            min(left, section.right() - _SORT_ARROW),
            section.center().y() - _SORT_ARROW // 2 + 1,
            _SORT_ARROW,
            _SORT_ARROW,
        )

    def pixelMetric(self, metric, option=None, widget=None):
        """Return `metric`; layouts space one pane gap, list and toolbar icons
        16 px, a tree's levels 22 px.

        A themed tab's close button widens to the left by the room its glyph
        needs to stand as far in from the pill's edge as the text does.
        """
        if metric in _LAYOUT_GAPS:
            return PANE_GAP
        if metric == _TREE_INDENTATION:
            return _TREE_INDENT
        if metric in (_LIST_ICON, QStyle.PM_ToolBarIconSize):
            # Toolbar icons too: a toolbar's tool button is a 28 px square.
            metric = _SMALL_ICON
        size = super().pixelMetric(metric, option, widget)
        if metric != _CLOSE_WIDTH or widget is None:
            return size
        bar = widget.parentWidget()
        if isinstance(bar, QTabBar) and _is_themed(bar):
            size += _close_room(bar)
        return size

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        """Return `hint`; a tooltip keeps the next one quick for 300 ms.

        Qt's window is 2 s from the moment a tip shows: within it, the
        next target's tip shows at once instead of after the 700 ms wait.
        """
        if hint == _TIP_AWAKE:
            return _TIP_AWAKE_MS
        return super().styleHint(hint, option, widget, returnData)

    def polish(self, widget):
        """Lay an item view's rows out again once the sheet has styled them."""
        super().polish(widget)
        # A view sized before its first polish keeps rows measured without
        # the sheet's item box; nothing else tells it to measure again.
        if isinstance(widget, QAbstractItemView):
            widget.scheduleDelayedItemsLayout()
        # The sheet's chevron fills its branch box: a rule per indentation
        # pads that box in to the 14 px chevron.
        # ponytail: read at polish; a later setIndentation needs a repolish.
        if isinstance(widget, QTreeView):
            widget.setProperty(INDENT_PROPERTY, widget.indentation())
        # A tab widget wears the pane card around its tabs too, as a dock
        # pane does; Qt draws a sheet box on it only with this.
        if isinstance(widget, QTabWidget):
            widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if isinstance(widget, QMenu):
            widget.installEventFilter(_menu_badges())


#: Set on a menu action by `set_menu_badge`: the text of its pill.
BADGE_PROPERTY = "fxBadge"

# The pill's height and side padding; the QMenu::item rule's right padding.
_BADGE_HEIGHT = 18
_BADGE_PADDING = 7
_MENU_ITEM_PADDING = 8

# Reserves the pill's width in the key-hint column without drawing a glyph.
_BADGE_ROOM = " "


def _badge_font() -> QFont:
    """Return a badge's font: a step under the body size, emphasised."""
    shape = font()
    shape.setPixelSize(FONT_SIZE - 1)
    shape.setWeight(_WEIGHTS[drawn_weight(EMPHASIS_WEIGHT)])
    return shape


def _badge_width(text: str) -> int:
    """Return how wide `text`'s pill stands."""
    return QFontMetrics(_badge_font()).horizontalAdvance(text) + (
        2 * _BADGE_PADDING)


def set_menu_badge(action: QAction, text: str) -> None:
    """Show `text` as a pill at the right of `action`'s menu item.

    The pill stands in the key-hint column, so the item shows no shortcut
    text; the action keeps its shortcut.

    Examples:
        >>> fxstyle.set_menu_badge(delete_action, "Admin")
    """
    label = action.text().split("\t", 1)[0]
    space = max(QFontMetrics(font()).horizontalAdvance(_BADGE_ROOM), 1)
    room = -(-_badge_width(text) // space)
    action.setText(f"{label}\t{_BADGE_ROOM * room}")
    action.setProperty(BADGE_PROPERTY, text)


class _MenuBadges(QObject):
    """Paints every badged item's pill over a menu Qt has just drawn."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Draw the menu, then its pills, on a menu holding a badge."""
        if event.type() != QEvent.Paint or not isinstance(watched, QMenu):
            return False
        badged = [
            (action, action.property(BADGE_PROPERTY))
            for action in watched.actions()
            if action.isVisible() and action.property(BADGE_PROPERTY)
        ]
        if not badged:
            return False
        QMenu.paintEvent(watched, event)
        theme = colors()
        painter = QPainter(watched)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(_badge_font())
        for action, text in badged:
            item = watched.actionGeometry(action)
            width = _badge_width(str(text))
            pill = QRectF(
                # Its right edge on the item's padding, as the key hint's.
                item.right() + 1 - _MENU_ITEM_PADDING - width,
                item.center().y() + 1 - _BADGE_HEIGHT / 2,
                width, _BADGE_HEIGHT)
            painter.setOpacity(1.0 if action.isEnabled() else 0.6)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.feedback_warning_background))
            painter.drawRoundedRect(pill, _BADGE_HEIGHT / 2, _BADGE_HEIGHT / 2)
            painter.setPen(QColor(theme.feedback_warning_foreground))
            painter.drawText(pill, Qt.AlignCenter, str(text))
        painter.end()
        return True


@lru_cache(maxsize=1)
def _menu_badges() -> _MenuBadges:
    """Return the one badge painter every menu shares."""
    return _MenuBadges()


def _close_room(bar: QTabBar) -> int:
    """Return how far `bar`'s close glyphs must move in off the tab's edge.

    The sheet's style sets the button a Qt-version-dependent gap off the
    tab's edge, past the pill's margin and padding.
    """
    probe = QStyleOptionTab()
    probe.rect = QRect(0, 0, 100, 30)
    probe.rightButtonSize = QSize(1, 1)
    probe.shape = bar.shape()
    button = bar.style().subElementRect(
        QStyle.SE_TabBarTabRightButton, probe, bar)
    return max(0, _CLOSE_INSET - (probe.rect.right() - button.right()))


###### Stylesheet Functions


def _font_stylesheet(theme: Optional[str] = None) -> str:
    """Return the title rules: the title family, then each rank's size.

    The body family and size are the root font (:func:`font`), which a
    widget's own ``setFont`` overrides; the title rules outrank it.
    """
    theme = theme or get_theme()
    ranks = _ranks(theme)
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
            declarations.append(
                f"font-weight: {drawn_weight(weight, theme)};")
        if declarations:
            rules.append(
                f'[{TITLE_PROPERTY}="{rank}"] {{ {" ".join(declarations)} }}')
    return "\n".join(rules) + "\n"


def _build_stylesheet(theme: Optional[str] = None) -> str:
    """Return the title rules, `STYLE_FILE` and every fragment, resolved."""
    theme = theme or get_theme()

    def build() -> str:
        parts = [
            _font_stylesheet(theme),
            STYLE_FILE.read_text(encoding="utf-8"),
            _BRANCH_RULES,
            _INK_RULES,
        ]
        parts.extend(_widget_fragments.values())
        return resolve("\n".join(parts), theme)

    # The sheet's images live in the cache folder, so it is part of the key.
    key = ("sheet", theme, row_size(), str(fxicons._cache_dir()))
    return _cached_sheet(key, build)


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
    _sheet_cache.clear()
    _reapply_to_roots()


def register_themed_root(root: QObject) -> None:
    """Register a widget (or QApplication) as a themed root.

    The current theme stylesheet is applied to it immediately and
    re-applied on every subsequent :func:`apply_theme` call. Qt cascades
    the sheet to all descendants, so children need no registration.

    A widget is not registered while the QApplication is a root: the
    application's sheet already reaches it, and the next switch of that
    sheet would hand the widget back the palette of the theme before.
    It is still marked as a themed window, so it fades in as it shows,
    as in a host.

    Roots are held weakly; destroyed widgets drop out automatically.

    Args:
        root: Any object with ``setStyleSheet`` (QWidget or QApplication).
    """
    # fxgui's faces in the database before anything is laid out, so the
    # first layout measures with the face the first paint draws.
    _register_bundled_fonts()
    if isinstance(root, QWidget):
        # Marked in both modes: a themed window fades in as it shows.
        root.setProperty(ROOT_PROPERTY, True)
        if not _in_host(root):
            return
    _themed_roots.add(root)
    _watch_focus()
    _apply_to_root(root, _build_stylesheet(), palette(), font())


def unregister_themed_root(root: QObject) -> None:
    """Forget `root`: later theme switches no longer restyle it.

    Restores nothing: `root` keeps the sheet, palette and font it wears
    until you set others. Forgetting a root never registered does nothing.

    Args:
        root: A widget or QApplication given to `register_themed_root`.
    """
    _themed_roots.discard(root)


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
/* A host's sort arrow (Houdini's margin-right) reserves room in every
   section under Qt 6.5; FXProxyStyle draws the arrow itself. */
QHeaderView::up-arrow, QHeaderView::down-arrow {{
    width: -1px; height: -1px; margin: 0px; border: none;
}}
QMenu::separator {{ margin: 0px; }}
QMenu::indicator {{ margin-left: 0px; border: none; }}
QMenu::icon {{ position: relative; top: 0px; left: 0px; bottom: 0px; right: 0px; }}
/* Native, not none: any other ::item border makes the sheet paint the cell
   and hide its BackgroundRole. A native border sets a cell's text 1px
   further in; the margin takes it back. */
QTableView::item {{ border: native; margin: 0px -1px; }}
/* A native border grows a list row 1px each side; the margin takes it back. */
QListView::item {{ border: native; margin: -1px; }}
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

    def build() -> str:
        weight, _hinting = _shape(theme, "body")
        extra = f" font-weight: {drawn_weight(BODY_WEIGHT if weight is None else weight, theme)};"
        return resolve(_HOST_RULES.replace("@weight", extra), theme)

    return _cached_sheet(("host", theme), build)


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


def _is_stacked_page(widget: QWidget) -> bool:
    """Whether `widget` is a page a stacked layout brings to the front."""
    # PySide6 6.5 keeps a stale wrapper for a C++-made widget's parent, and
    # hands it back for a later widget at that address: pages are Python's.
    if _compat.created_by_python and not _compat.created_by_python(widget):
        return False
    parent = _compat.parent_widget(widget)
    return (
        parent is not None
        and isinstance(parent.layout(), QStackedLayout)
        and _is_themed(widget)
    )


def _ground(widget: Optional[QWidget]) -> QColor:
    """Return the colour `widget` is painted on: its sheet's, by its palette.

    A view may sit on the frame, a well or a card, not only the surface; a
    see-through widget shows its nearest painted parent's.
    """
    while widget is not None:
        color = widget.palette().color(widget.backgroundRole())
        if color.alpha() == 255:
            return color
        widget = _compat.parent_widget(widget)
    return QColor(colors().surface)


class _Reveal(QWidget):
    """Fade a page in as it rises `PANEL_RISE` px into place.

    A child of the page, above it and clear of the pointer: it paints the
    pane's colour, then a snapshot of the page, faded and lowered, while
    the page lays itself out and paints as ever underneath.
    """

    # Read before `__init__` has run: Qt may paint a child it adopts.
    _shown = 1.0
    _moving = False

    @classmethod
    def over(cls, page: QWidget, *, moving: bool = True) -> None:
        """Reveal `page`; not `moving`, it fades in where it stands.

        A page whose size is still changing, as a pane growing open, does
        not move: a snapshot of it would be the wrong size. A reveal
        already under way on it takes that on.
        """
        # A page coming up with its window rides the window's own fade.
        if not motion() or page.window().windowOpacity() < 1.0:
            return
        reveal = page.findChild(cls, "", Qt.FindDirectChildrenOnly)
        if reveal is None:
            reveal = cls(page)
        reveal._moving = reveal._moving and moving

    def __init__(self, page: QWidget):
        super().__init__(page)
        self._shown = 0.0
        self._moving = True
        self._shot = QPixmap()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setGeometry(page.rect())
        self.raise_()
        self.show()
        # Once the page has laid itself out, a step later.
        fxutils.later(0, self, self._start)

    def _start(self) -> None:
        page = self.parentWidget()
        if page is None:
            return
        # Qt shows a window's pages before the window itself: by now a page
        # shown with its window knows that window is fading in, and stands.
        if page.window().windowOpacity() < 1.0:
            self.setParent(None)
            self.deleteLater()
            return
        self.setGeometry(page.rect())
        if self._moving:
            self.hide()
            self._shot = page.grab()
            self.show()
        rise = QVariantAnimation(self)
        rise.setDuration(PANEL_FADE_MS)
        rise.setStartValue(0.0)
        rise.setEndValue(1.0)
        rise.setEasingCurve(ease_out())
        rise.valueChanged.connect(self._step)
        rise.finished.connect(self.deleteLater)
        rise.start(QVariantAnimation.DeleteWhenStopped)

    def _step(self, shown: float) -> None:
        self._shown = shown
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the pane over the page, less and less as it fades in.

        A moving page paints its snapshot, faded and lowered, over a pane.
        """
        painter = QPainter(self)
        fill = _ground(self.parentWidget())
        if self._moving and not self._shot.isNull():
            painter.fillRect(self.rect(), fill)
            painter.setOpacity(self._shown)
            painter.drawPixmap(
                QPointF(0, (1.0 - self._shown) * PANEL_RISE), self._shot)
        else:
            fill.setAlphaF(1.0 - self._shown)
            painter.fillRect(self.rect(), fill)
        painter.end()


class _ResizeMark(QWidget):
    """Light the edge a header column resizes by, under the pointer.

    An edge is found as Qt finds it, within the style's grip margin of a
    section the user may resize; this transparent child of the viewport
    draws a short accent bar there, held while the edge is dragged.
    """

    # The bar's width, and its height against the header's, in px.
    _WIDTH = 2
    _INSET = 6
    # Read before `__init__` has run, or after a closing window tore the
    # Python side down while Qt still sends events: each answers "nothing".
    _header: Optional[QHeaderView] = None
    _x: Optional[int] = None
    _edge: Optional[int] = None
    _dragging = False

    @classmethod
    def watch(cls, header: QHeaderView) -> None:
        """Give a themed horizontal `header` its mark, once."""
        # A header shown while its view is torn down may be half deleted.
        if not _compat.is_valid(header):
            return
        viewport = header.viewport()
        if (
            not _compat.is_valid(viewport)
            or header.orientation() != Qt.Horizontal
            or not _is_themed(header)
            or viewport.findChild(cls, "", Qt.FindDirectChildrenOnly)
        ):
            return
        cls(header)

    def __init__(self, header: QHeaderView):
        super().__init__(header.viewport())
        _compat.hold(self)
        self._header = header
        self._x: Optional[int] = None
        self._edge: Optional[int] = None
        self._dragging = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        for watched in (header, header.viewport()):
            watched.installEventFilter(self)
        self.setGeometry(header.viewport().rect())
        self.show()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Follow the pointer along the header and the drag of an edge."""
        if self._header is None or not _compat.is_valid(self._header):
            return False
        kind = event.type()
        if kind == QEvent.Resize and watched is self._header.viewport():
            self.setGeometry(watched.rect())
        elif kind in (QEvent.MouseMove, QEvent.HoverMove):
            self._follow(event.position().toPoint().x())
        elif kind == QEvent.MouseButtonPress:
            self._dragging = self._edge is not None
        elif kind == QEvent.MouseButtonRelease:
            self._dragging = False
            self._follow(event.position().toPoint().x())
        elif kind in (QEvent.Leave, QEvent.HoverLeave) and not self._dragging:
            self._show_at(None)
        return False

    def _follow(self, x: int) -> None:
        header = self._header
        if not self._dragging:
            self._edge = self._edge_at(x)
        if self._edge is None:
            self._show_at(None)
            return
        self._show_at(
            header.sectionViewportPosition(self._edge)
            + header.sectionSize(self._edge))

    def _edge_at(self, x: int) -> Optional[int]:
        """Return the section whose right edge `x` grips, as Qt reads it."""
        header = self._header
        index = header.logicalIndexAt(x)
        if index < 0:
            return None
        grip = header.style().pixelMetric(
            QStyle.PM_HeaderGripMargin, None, header)
        start = header.sectionViewportPosition(index)
        if start + header.sectionSize(index) - x <= grip:
            edge = index
        elif x - start <= grip and header.visualIndex(index) > 0:
            edge = header.logicalIndex(header.visualIndex(index) - 1)
        else:
            return None
        if header.sectionResizeMode(edge) != QHeaderView.Interactive:
            return None
        return edge

    def _show_at(self, x: Optional[int]) -> None:
        if x != self._x:
            self._x = x
            self.raise_()
            self.update()

    def paintEvent(self, event) -> None:
        """Draw the accent bar on the lit edge."""
        if self._x is None or self._header is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors().accent_primary))
        bar = QRectF(
            self._x - self._WIDTH / 2,
            self._INSET,
            self._WIDTH,
            self.height() - 2 * self._INSET,
        )
        painter.drawRoundedRect(bar, self._WIDTH / 2, self._WIDTH / 2)
        painter.end()


class _ViewportCorners(QWidget):
    """Redraw a framed view's round corners over what it paints.

    The sheet rounds the frame, but rows, or a canvas's grid, paint the
    viewport's square corners over it. This transparent child covers the
    whole view, so padding between frame and viewport moves nothing; at
    each corner it paints the pane outside the arc, then the arc.
    """

    @classmethod
    def round(cls, view: QAbstractScrollArea) -> None:
        """Give `view` its corners once, unless it draws no frame."""
        if (
            view.frameWidth() == 0
            or view.window().windowType() == Qt.Popup
            or not _is_themed(view)
            or view.findChild(cls, "", Qt.FindDirectChildrenOnly)
        ):
            return
        cls(view)

    # Read before `__init__` has run, or after a closing window tore the
    # Python side down while Qt still paints: it then paints nothing.
    _view: Optional[QAbstractScrollArea] = None

    def __init__(self, view: QAbstractScrollArea):
        super().__init__(view)
        self._view = view
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        view.installEventFilter(self)
        self.setGeometry(view.rect())
        self.raise_()
        self.show()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Follow the view's size; stay above its viewport and bars."""
        if event.type() in (QEvent.Resize, QEvent.Show):
            self.setGeometry(watched.rect())
            self.raise_()
        return False

    def paintEvent(self, event) -> None:
        """Paint the pane outside each rounded corner, then the arc."""
        view = self._view
        if view is None or not _compat.is_valid(view):
            return
        frame = view.frameWidth()
        outer = QRectF(self.rect())
        radius = BUTTON_RADIUS
        clip = QPainterPath()
        for x, y in (
            (outer.left(), outer.top()),
            (outer.right() - radius, outer.top()),
            (outer.left(), outer.bottom() - radius),
            (outer.right() - radius, outer.bottom() - radius),
        ):
            clip.addRect(QRectF(x, y, radius + 1, radius + 1))
        shape = QPainterPath()
        shape.addRoundedRect(outer, radius, radius)
        theme = colors()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipPath(clip)
        painter.fillPath(clip.subtracted(shape), _ground(view.parentWidget()))
        edge = QPainterPath()
        half = frame / 2
        edge.addRoundedRect(
            outer.adjusted(half, half, -half, -half),
            radius - half,
            radius - half,
        )
        painter.setPen(QPen(QColor(theme.border), frame))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(edge)
        painter.end()


def _adopt_proxy_style(view: QWidget) -> None:
    """Give an item view or tab bar in a themed host window FXProxyStyle.

    A host's own style draws a focus rect on a view's current cell, over its
    BackgroundRole, on PySide6 6.5, and sets a tab's close button on the
    pill's edge; a themed application's FXProxyStyle already fixes both.
    Done once, at the first show, after the sheet has polished it; a popup's
    list is left alone.
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


def _rank_dialog_buttons(box: QDialogButtonBox) -> None:
    """Make a dialog's one primary button: its named default, else its
    first accepting verb.

    Read as the box shows, before a click: Qt then makes the last clicked
    button the default. One only: "Yes" beside "Yes to All" stays plain.
    """
    accepting = (QDialogButtonBox.AcceptRole, QDialogButtonBox.YesRole)
    buttons = box.buttons()
    if any(button.property("fxRole") is not None for button in buttons):
        return
    # The button Enter presses is the one that should look pressable.
    named = [
        button for button in buttons
        if isinstance(button, QPushButton) and button.isDefault()
    ]
    chosen = named or [
        button for button in buttons if box.buttonRole(button) in accepting
    ]
    if chosen:
        chosen[0].setProperty("fxRole", "primary")
        fxutils.repolish(chosen[0])


def _fit_close_buttons(bar: QTabBar) -> None:
    """Size `bar`'s close buttons as FXProxyStyle does, then lay tabs out.

    Qt sizes a close button once, as it makes it: a bar built before it was
    themed, or under a host's style, keeps the narrow button.
    """
    _adopt_proxy_style(bar)
    changed = False
    for button in bar.findChildren(
            QAbstractButton, "", Qt.FindDirectChildrenOnly):
        hint = button.sizeHint()
        if (
            button.metaObject().className() == "CloseButton"
            and button.size() != hint
        ):
            button.resize(hint)
            changed = True
    if changed:
        QApplication.sendEvent(bar, QEvent(QEvent.StyleChange))


_FOCUS_EVENTS = frozenset((
    QEvent.KeyPress,
    QEvent.MouseButtonPress,
    QEvent.MouseButtonDblClick,
    QEvent.FocusIn,
    QEvent.FocusOut,
    QEvent.Polish,
    QEvent.Show,
))

class _FocusVisibility(QObject):
    """Mark a themed widget's focus visible when it came by keyboard.

    It also gives every themed popup and tooltip, Qt's own included,
    flyout corners, an item view or tab bar in a host window FXProxyStyle,
    and a tab's close button its room.
    """

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self._by_keyboard = False
        if isinstance(parent, QGuiApplication):
            parent.applicationStateChanged.connect(self._left_for)

    def _left_for(self, state: Qt.ApplicationState) -> None:
        """Forget the last key once another application takes the input.

        The input that brings a window back, a tray icon's click, is one
        Qt never sees.
        """
        if state != Qt.ApplicationActive:
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
        elif kind == QEvent.Show and isinstance(watched, QWidget):
            if watched.windowType() in (Qt.Popup, Qt.ToolTip):
                self._dress_popup(watched)
            elif (
                watched.isWindow()
                and watched.property(ROOT_PROPERTY)
                # Shown by the application, not restored by the system.
                and not event.spontaneous()
            ):
                _fade_in(watched, WINDOW_FADE_MS)
            elif isinstance(watched, QAbstractItemView):
                _adopt_proxy_style(watched)
                _mark_self_ruled(watched)
                _ViewportCorners.round(watched)
                if isinstance(watched, QHeaderView):
                    _ResizeMark.watch(watched)
            elif isinstance(watched, QTabBar):
                _fit_close_buttons(watched)
            elif isinstance(watched, QSplitter):
                _SplitterMark.watch(watched)
            elif isinstance(watched, QDialogButtonBox):
                _rank_dialog_buttons(watched)
            elif isinstance(watched, QGraphicsView):
                _ViewportCorners.round(watched)
            if not event.spontaneous() and _is_stacked_page(watched):
                _Reveal.over(watched)
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
        _fade_in(popup)
        if popup.windowType() == Qt.Popup:
            _drop_in(popup)

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
        # A focus event can reach a widget whose window is being deleted.
        if not _compat.is_valid(widget):
            return
        if bool(widget.property(FOCUS_VISIBLE_PROPERTY)) == visible:
            return
        widget.setProperty(FOCUS_VISIBLE_PROPERTY, visible)
        # Only fxgui's own sheet reads it; a host's widgets keep their polish.
        if _is_themed(widget):
            fxutils.repolish(widget)
            _FocusRing.show_on(widget, visible)


_focus_visibility: Optional[_FocusVisibility] = None

# What takes a focus ring: inputs ring in the accent, buttons in the text.
_RING_ACCENT_KINDS = (
    QLineEdit, QAbstractSpinBox, QComboBox, QPlainTextEdit, QTextEdit)
_RING_KINDS = _RING_ACCENT_KINDS + (QPushButton, QToolButton)

# The keyboard focus ring outside a control, as the web look's: this wide,
# at this share of its ink, round the control's own 1 px accent edge.
FOCUS_RING_WIDTH = 3
FOCUS_RING_ALPHA = 0.25


class _FocusRing(QWidget):
    """A ring drawn outside the control that has keyboard focus.

    A sibling over the control, grown by `FOCUS_RING_WIDTH` each side: a
    sheet cannot draw outside a widget. Inputs and primary buttons ring in
    the accent, other buttons in the text's ink, each at
    `FOCUS_RING_ALPHA`. The parent's edge clips it, as a web page's overflow
    does; the control's own accent edge still shows focus there.
    """

    _shown: "Optional[_FocusRing]" = None

    def __init__(self, target: QWidget):
        super().__init__(target.parentWidget())
        self._target = target
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        target.installEventFilter(self)
        # Gone with the control, never left standing over its place.
        target.destroyed.connect(self.deleteLater)
        self._follow()

    @classmethod
    def show_on(cls, widget: QWidget, visible: bool) -> None:
        """Ring `widget` when its focus came by keyboard; else drop the ring."""
        target = _ring_target(widget) if _compat.is_valid(widget) else None
        ring = cls._shown
        if ring is not None and _compat.is_valid(ring):
            if visible and ring._target is target:
                return
            if not visible and ring._target is not target:
                return
            ring.deleteLater()
            ring.hide()
        cls._shown = None
        if visible and target is not None:
            cls._shown = cls(target)
            cls._shown.show()

    def _follow(self) -> None:
        """Stand over the target, grown by the ring, above it."""
        grow = FOCUS_RING_WIDTH
        self.setGeometry(self._target.geometry().adjusted(-grow, -grow, grow, grow))
        self.raise_()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        kind = event.type()
        if kind in (QEvent.Move, QEvent.Resize):
            self._follow()
        elif kind == QEvent.Hide:
            self.hide()
        elif kind == QEvent.Show:
            self.show()
            self._follow()
        return False

    def paintEvent(self, event) -> None:
        theme = colors()
        target = self._target
        accent = isinstance(target, _RING_ACCENT_KINDS) or (
            target.property("fxRole") == "primary"
            or type(target).__name__ == "FXPrimaryButton")
        ink = QColor(theme.accent_primary if accent else theme.text)
        ink.setAlphaF(FOCUS_RING_ALPHA)
        height = target.height()
        radius = (
            height / 2 if target.property("fxSize") else
            min(BUTTON_RADIUS, height / 2))
        half = FOCUS_RING_WIDTH / 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(ink, FOCUS_RING_WIDTH))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(half, half, -half, -half),
            radius + half, radius + half)
        painter.end()


def _ring_target(widget: QWidget) -> Optional[QWidget]:
    """Return the control a focus ring goes round, or None for no ring.

    A combo box's or spin box's own line edit rings its box; a widget at a
    window's top level, or in an item view, a menu or a popup, has none.
    """
    parent = widget.parentWidget()
    if isinstance(parent, (QComboBox, QAbstractSpinBox)):
        widget, parent = parent, parent.parentWidget()
    if parent is None or widget.isWindow():
        return None
    if not isinstance(widget, _RING_KINDS):
        return None
    probe = parent
    while probe is not None:
        if isinstance(probe, (QAbstractItemView, QMenu)) or (
            probe.isWindow() and probe.windowType() == Qt.Popup
        ):
            return None
        if probe.isWindow():
            break
        probe = probe.parentWidget()
    return widget


def _drop_in(popup: QWidget) -> None:
    """Drop a popup `POPUP_DROP` px into the place Qt gave it."""
    if not motion() or not POPUP_DROP:
        return
    end = popup.pos()
    drop = QPropertyAnimation(popup, b"pos", popup)
    drop.setDuration(POPUP_FADE_MS)
    drop.setStartValue(end - QPoint(0, POPUP_DROP))
    drop.setEndValue(end)
    drop.setEasingCurve(ease_out())
    drop.start(QPropertyAnimation.DeleteWhenStopped)


def _fade_in(window: QWidget, duration: int = POPUP_FADE_MS) -> None:
    """Fade a window in from clear; it ends opaque however it ends."""
    if not motion():
        return
    fade = QPropertyAnimation(window, b"windowOpacity", window)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(ease_out())
    fade.start(QPropertyAnimation.DeleteWhenStopped)


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
        theme = colors()
        painter = QPainter(watched)
        painter.fillRect(watched.rect(), QColor(theme.surface))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(theme.border))
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
    "Highlight": "selection",
    "HighlightedText": "text_on_selection",
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
        tokens = vars(colors())
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
    QFont, such as a QGraphicsTextItem. A role that falls to the generic
    ``monospace`` names the platform's fixed-pitch family.

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
    if family == "monospace" and QGuiApplication.instance() is not None:
        # Qt draws no CSS generic, rich text included: name the platform's
        # fixed face, whatever it is called.
        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        result.setFamilies([fixed.family()])
    else:
        result.setFamilies(
            [] if family in _GENERIC_FONT_FAMILIES else [family])
    if family == "monospace":
        result.setStyleHint(QFont.StyleHint.Monospace)
    result.setPixelSize(FONT_SIZE)
    # An unknown role is the body's, its weight and hinting included.
    weight, hinting = _shape(theme, role if role in roles else "body")
    result.setWeight(_WEIGHTS[drawn_weight(
        BODY_WEIGHT if weight is None else weight, theme)])
    if hinting is not None:
        result.setHintingPreference(_HINTING[hinting])
    return result

