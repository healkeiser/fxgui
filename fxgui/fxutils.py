"""Utility functions for the `fxgui` package.

Qt helpers every widget and application shares: UI loading, actions,
shadows, menus, trees, window corners and wrapper lifetimes.

Examples:
    >>> from fxgui.fxutils import load_ui
    >>> ui = load_ui(parent_widget, "path/to/ui_file.ui")
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
import ctypes
import functools
import html
import os
import re
import sys
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, Optional, Tuple

# Third-party
from qtpy.QtWidgets import (
    QAction,
    QMenu,
    QStyleOptionViewItem,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QGraphicsDropShadowEffect,
)
from qtpy.QtGui import QColor, QKeySequence
from qtpy.QtCore import QModelIndex, QPoint, QTimer

# Internal
from fxgui._compat import created_by_python


# Public API
__all__ = [
    "load_ui",
    "create_action",
    "add_shadow",
    "markdown_to_plain_text",
    "repolish",
    "round_window_corners",
    "set_app_user_model_id",
    "popup_menu",
    "add_submenu",
    "children_of",
    "filter_tree",
    "fit_columns",
    "TreeState",
    "later",
    "rehome",
    "focus_step",
]

# `DWMWA_WINDOW_CORNER_PREFERENCE` from `dwmapi.h`: which rounding the
# compositor gives a window's corners. Windows 11 and up; an older build
# answers with a failure code.
_DWMWA_WINDOW_CORNER_PREFERENCE = 33

# `DWMWCP_ROUND`: the full radius the OS gives its own flyouts and menus.
_DWMWCP_ROUND = 2

_HTML_TAG = re.compile(r"<[^>]+>")


def load_ui(parent: QWidget, ui_file: str) -> QWidget:
    """Load a Qt Designer UI file as a new widget parented to `parent`.

    Raises:
        FileNotFoundError: If the specified UI file doesn't exist.

    Examples:
        >>> loaded_ui = load_ui(self, Path(__file__).with_suffix(".ui"))
    """

    if not os.path.isfile(ui_file):
        raise FileNotFoundError(f"UI file not found: {ui_file}")

    try:
        # Not shipped by the PyQt bindings, hence the deferred import.
        from qtpy.QtUiTools import QUiLoader
    except ImportError:
        from qtpy.uic import loadUi

        loaded_ui = loadUi(ui_file)
        loaded_ui.setParent(parent)
        return loaded_ui
    return QUiLoader().load(str(ui_file), parent)


def create_action(
    parent: QWidget,
    name: str,
    *_legacy,
    trigger: Optional[Callable] = None,
    enable: bool = True,
    shortcut: Optional[str] = None,
    checkable: bool = False,
    icon_name: Optional[str] = None,
    **_retired,
) -> QAction:
    """Create a QAction owned by `parent`.

    Args:
        parent: Parent widget for the action.
        name: Display name for the action.
        trigger: Called when the action is triggered.
        enable: Whether the action is enabled.
        shortcut: Keyboard shortcut (e.g., "Ctrl+S").
        checkable: Whether the action is checkable.
        icon_name: An fxicons name, drawn in the theme's colours.

    Examples:
        >>> action = create_action(
        ...     window, "Save", trigger=save, shortcut="Ctrl+S",
        ...     icon_name="save")
    """
    # TODO: shim; drop `_legacy` (icon, trigger) and `_retired` (visible)
    # once _system_tray.py:92 and _main_window.py:319-480 stop passing them.
    legacy_icon = _legacy[0] if _legacy else None
    if len(_legacy) > 1:
        trigger = _legacy[1]
    action = QAction(name, parent)
    if icon_name is not None:
        from fxgui import fxicons

        fxicons.set_icon(action, icon_name)
    elif legacy_icon is not None:
        action.setIcon(legacy_icon)
    if trigger is not None:
        action.triggered.connect(trigger)
    action.setEnabled(enable)
    action.setCheckable(checkable)
    if shortcut is not None:
        action.setShortcut(QKeySequence(shortcut))
    return action


def add_shadow(
    widget: QWidget,
    blur: float = 20,
    offset: Tuple[float, float] = (0, 0),
    alpha: int = 80,
) -> QGraphicsDropShadowEffect:
    """Cast a black drop shadow of `alpha` opacity (0-255) under `widget`.

    Black in every theme: a themed colour baked here would go stale on a
    theme switch.

    Examples:
        >>> fxutils.add_shadow(card, blur=24, offset=(0, 4), alpha=100)
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(*offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)
    return shadow


def add_shadows(parent, shadow_object):
    """Cast the splash screen's shadow; use `add_shadow` instead."""
    # TODO: shim; delete once _splash_screen.py:194 calls add_shadow.
    return add_shadow(shadow_object, blur=10, alpha=255)


@functools.lru_cache(maxsize=1024)
def markdown_to_plain_text(text: str) -> str:
    """Return `text` with its Markdown formatting removed.

    Without the optional `markdown` package the text is returned as is.
    """
    if not text or text == "-":
        return text
    try:
        import markdown
    except ImportError:
        return text
    rendered = markdown.markdown(text, extensions=["extra", "nl2br"])
    plain = html.unescape(_HTML_TAG.sub("", rendered))
    return " ".join(plain.split())


def repolish(widget: QWidget) -> None:
    """Force re-evaluation of the stylesheet rules for a widget.

    Call after changing a Qt dynamic property that a stylesheet
    attribute selector depends on, e.g.
    ``MyBanner[level="error"] { ... }``.

    Args:
        widget: The widget to unpolish/polish and repaint.

    Examples:
        >>> banner.setProperty("level", "error")
        >>> fxutils.repolish(banner)
    """

    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def round_window_corners(widget: QWidget) -> bool:
    """Give `widget`'s own window the corners and shadow of a flyout.

    One `DwmSetWindowAttribute` call on Windows 11: the compositor clips and
    shades the window, and its geometry does not change. Nothing raises.

    Args:
        widget: A window; asking a child for its handle would make it native.

    Returns:
        bool: Whether the compositor took the request; False off Windows 11.

    Examples:
        >>> fxutils.round_window_corners(panel)  # doctest: +SKIP
        True
    """

    if not sys.platform.startswith("win"):
        return False
    handle = int(widget.winId())
    if handle == 0:
        return False
    try:
        from ctypes import wintypes

        dwmapi = ctypes.WinDLL("dwmapi")
        # Declared rather than left to ctypes' own guesses: the third
        # argument is a pointer to the value and the fourth its size in
        # bytes, and getting either wrong is a call the compositor reads
        # past the end of.
        dwmapi.DwmSetWindowAttribute.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        # The raw result rather than `ctypes.HRESULT`, which raises on a
        # failure code. A build with no window rounding is not an error
        # here, it is the other answer.
        dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
        preference = ctypes.c_int(_DWMWCP_ROUND)
        result = dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(handle),
            wintypes.DWORD(_DWMWA_WINDOW_CORNER_PREFERENCE),
            ctypes.byref(preference),
            wintypes.DWORD(ctypes.sizeof(preference)),
        )
    except (AttributeError, ImportError, OSError, ValueError):
        return False
    return bool(result == 0)


def set_app_user_model_id(app_id: str) -> bool:
    """Tell Windows this process is its own application, `app_id`.

    Windows groups taskbar buttons and picks their icon by this id, so a
    Python-run application otherwise wears the Python icon. Call before
    the first window exists: Windows reads the id when a window is made.
    A pinned shortcut must carry the same id. Nothing here raises.

    Args:
        app_id: A machine-wide id, such as `"Studio.Launcher"`.

    Returns:
        bool: Whether Windows took it; always False off Windows.

    Examples:
        >>> fxutils.set_app_user_model_id("Studio.App")  # doctest: +SKIP
        True
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        shell32 = ctypes.windll.shell32
        result = shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        return False
    return result == 0


def popup_menu(menu: QMenu, at: QPoint) -> None:
    """Show `menu` at global position `at`, freeing it once it closes.

    `popup` rather than `exec`, whose own event loop no key-driven test can
    step through; a parented menu is never freed, so `aboutToHide` frees it.
    """
    menu.aboutToHide.connect(menu.deleteLater)
    menu.popup(at)


def add_submenu(menu: QMenu, label: str) -> QMenu:
    """Add and return a submenu titled `label`, owned by `menu` in C++.

    `menu.addMenu(label)` makes one that dies with the first dropped Python
    wrapper of its action.
    """
    sub = QMenu(label, menu)
    menu.addMenu(sub)
    return sub


def children_of(item: QTreeWidgetItem) -> Iterator[QTreeWidgetItem]:
    """Yield every child row of `item`."""
    for index in range(item.childCount()):
        child = item.child(index)
        if child is not None:
            yield child


def _hide_unless(item: QTreeWidgetItem, keep: bool) -> None:
    item.setHidden(not keep)


def filter_tree(
    tree: QTreeWidget,
    text: str,
    mark: Callable[[QTreeWidgetItem, bool], None] = _hide_unless,
) -> None:
    """Tell `mark` for every row of `tree` whether `text` keeps it.

    A row matches when any column holds `text`, ignoring case; empty text
    matches every row. A match keeps its whole subtree and its ancestors.

    Args:
        tree: The tree to walk, top level down.
        text: The text to find.
        mark: Called with each row and its verdict; the default hides the
            rows the text drops.
    """
    query = text.strip().lower()

    def walk(item: QTreeWidgetItem, ancestor_matched: bool) -> bool:
        matched = ancestor_matched or not query or any(
            query in item.text(column).lower()
            for column in range(item.columnCount())
        )
        # A list, so every child is walked and marked.
        below = [walk(child, matched) for child in children_of(item)]
        keep = matched or any(below)
        mark(item, keep)
        return keep

    for item in children_of(tree.invisibleRootItem()):
        walk(item, False)


def fit_columns(view: QTreeView) -> None:
    """Widen each column to its widest row, collapsed rows too; never narrow.

    `resizeColumnToContents` measures only the rows that are expanded.
    """
    model, header = view.model(), view.header()
    if hasattr(view, "initViewItemOption"):
        option = QStyleOptionViewItem()
        view.initViewItemOption(option)
    else:
        option = view.viewOptions()  # Qt 5
    columns = range(model.columnCount())
    wanted = [header.sectionSizeHint(column) for column in columns]
    decorated = int(view.rootIsDecorated())
    parents = [(QModelIndex(), 0)]
    while parents:
        parent, depth = parents.pop()
        for row in range(model.rowCount(parent)):
            for column in columns:
                index = model.index(row, column, parent)
                # Qt 5 names it `itemDelegate(index)`.
                delegate = getattr(
                    view, "itemDelegateForIndex", view.itemDelegate
                )(index)
                width = delegate.sizeHint(option, index).width()
                if column == 0:
                    width += view.indentation() * (depth + decorated)
                wanted[column] = max(wanted[column], width)
            parents.append((model.index(row, 0, parent), depth + 1))
    for column in columns:
        if wanted[column] > header.sectionSize(column):
            header.resizeSection(column, wanted[column])


# A unit separator, which no row's text holds.
_FIELD = "\x1f"

_RowPath = Tuple[str, ...]


def _every_item(tree: QTreeWidget) -> Iterator[QTreeWidgetItem]:
    stack = list(children_of(tree.invisibleRootItem()))
    while stack:
        item = stack.pop()
        yield item
        stack.extend(children_of(item))


def _name_path(item: Optional[QTreeWidgetItem]) -> _RowPath:
    """Name `item` and each ancestor by column 0 alone."""
    levels = []
    while item is not None:
        levels.append(item.text(0))
        item = item.parent()
    return tuple(reversed(levels))


def _row_path(item: QTreeWidgetItem, columns: int) -> _RowPath:
    """Name `item` by every column, its ancestors by column 0.

    Two rows of one name, such as versions, differ in their other columns.
    """
    return (
        *_name_path(item.parent()),
        _FIELD.join(item.text(column) for column in range(columns)),
    )


@dataclass(frozen=True)
class TreeState:
    """What is open, selected and current in a tree, named by row text.

    Text survives a tree that is cleared and refilled; items do not.

    Examples:
        >>> state = fxutils.TreeState.of(tree)  # doctest: +SKIP
        >>> refill(tree)  # doctest: +SKIP
        >>> state.restore(tree)  # doctest: +SKIP
    """

    expanded: Tuple[_RowPath, ...] = ()
    selected: Tuple[_RowPath, ...] = ()
    current: Optional[_RowPath] = None
    scroll: int = 0

    @classmethod
    def of(cls, tree: QTreeWidget) -> "TreeState":
        """Return what is open, selected and current in `tree` now."""
        columns = tree.columnCount()
        current = tree.currentItem()
        return cls(
            expanded=tuple(
                _name_path(item)
                for item in _every_item(tree)
                if item.isExpanded()
            ),
            selected=tuple(
                _row_path(item, columns) for item in tree.selectedItems()
            ),
            current=None if current is None else _row_path(current, columns),
            scroll=tree.verticalScrollBar().value(),
        )

    def restore(self, tree: QTreeWidget) -> None:
        """Put this state back on `tree`, skipping rows it no longer has.

        Focus goes before selection, since Qt selects what it focuses, and
        scroll goes last, since focusing scrolls.
        """
        columns = tree.columnCount()
        by_name: Dict[_RowPath, QTreeWidgetItem] = {}
        by_row: Dict[_RowPath, QTreeWidgetItem] = {}
        for item in _every_item(tree):
            by_name.setdefault(_name_path(item), item)
            by_row.setdefault(_row_path(item, columns), item)
        for path in self.expanded:
            if path in by_name:
                by_name[path].setExpanded(True)
        if self.current in by_row:
            tree.setCurrentItem(by_row[self.current])
        for path in self.selected:
            if path in by_row:
                by_row[path].setSelected(True)
        # The view lays out lazily; the scrollbar still has the old range.
        tree.doItemsLayout()
        tree.verticalScrollBar().setValue(self.scroll)


def later(ms: int, owner, call) -> None:
    """Run `call` once after `ms` milliseconds, unless `owner` died first.

    Stands in for `QTimer.singleShot(ms, owner, call)`, which Houdini 21's
    PySide6 6.5 lacks. Call it on `owner`'s thread: the timer is its child.
    """
    timer = QTimer(owner)
    timer.setSingleShot(True)
    timer.timeout.connect(call)
    timer.timeout.connect(timer.deleteLater)
    timer.start(ms)


def rehome(widget):
    """Give `widget`'s Python wrapper back to its own parent's; return it.

    PySide files a widget a getter returns under the widget asked, and
    kills that one's wrapped children when it dies. Qt skips a `setParent`
    to the same parent; the binding files the wrapper back. A parent only
    C++ made is filed first, up to one Python made.
    """
    if widget is not None and created_by_python is not None:
        _file_back(widget)
    return widget


def _file_back(widget) -> bool:
    """File `widget` under its parent's lasting wrapper; say if one lasts."""
    parent = widget.parentWidget()
    if parent is None:
        if not created_by_python(widget):
            # Python taking a host's window would delete it with the name.
            return False
        widget.setParent(None)
        return True
    if not (created_by_python(parent) or _file_back(parent)):
        return False
    widget.setParent(parent)
    return True


def focus_step(widget, forward: bool = True):
    """Return the widget after `widget` in the focus chain, or before it."""
    return rehome(
        widget.nextInFocusChain() if forward
        else widget.previousInFocusChain()
    )
