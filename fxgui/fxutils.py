"""Utility functions for the `fxgui` package.

This module provides general-purpose utility functions for Qt-based
applications including UI loading, action creation, widget effects
and window corners.

Functions:
    load_ui: Load a Qt Designer UI file.
    create_action: Create a QAction with common settings.
    add_shadows: Apply drop shadow effect to a widget.
    get_formatted_time: Get current time as formatted string.
    repolish: Force re-evaluation of stylesheet rules for a widget.
    round_window_corners: Ask Windows 11 for a flyout's rounded corners.
    popup_menu: Show a menu without blocking, freed once it closes.
    add_submenu: Add a submenu that outlives its Python wrapper.
    children_of: Yield a tree item's children.
    filter_tree: Hide the rows of a tree a text does not match.
    fit_columns: Widen a tree's columns to every row, collapsed ones too.
    TreeState: What is open, selected and current in a tree, by row text.
    later: Run a call after a delay unless its owner died (PySide 6.5 safe).
    rehome: Give a widget's PySide wrapper back to its own parent's.
    focus_step: Step the focus chain without leaving wrappers to die.

Examples:
    Loading a UI file:

    >>> from fxgui.fxutils import load_ui
    >>> ui = load_ui(parent_widget, "path/to/ui_file.ui")

    Creating an action:

    >>> action = create_action(
    ...     parent=window,
    ...     name="Save",
    ...     icon=get_icon("save"),
    ...     trigger=save_callback,
    ...     shortcut="Ctrl+S"
    ... )
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
import ctypes
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterator, Optional, Tuple, Union

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
from qtpy.QtGui import QColor, QIcon, QKeySequence
from qtpy.QtCore import QFile, QModelIndex, QPoint

# Internal
from fxgui._compat import focus_step, later, rehome


# Public API
__all__ = [
    "load_ui",
    "create_action",
    "add_shadows",
    "get_formatted_time",
    "repolish",
    "round_window_corners",
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
# compositor gives a window's corners. Windows 11 and up. An older build
# does not ignore the attribute, it answers with a failure code, which is
# the same answer `round_window_corners` hands back.
_DWMWA_WINDOW_CORNER_PREFERENCE = 33

# `DWMWCP_ROUND`: the full radius the OS gives its own flyouts and
# context menus, rather than `DWMWCP_ROUNDSMALL`'s tighter one, which is
# drawn for controls inside a window rather than for a window.
_DWMWCP_ROUND = 2


def load_ui(parent: QWidget, ui_file: str) -> QWidget:
    """Load a UI file and return the loaded UI as a QWidget.

    Args:
        parent (QWidget): Parent object.
        ui_file (str): Path to the UI file.

    Returns:
        QWidget: The loaded UI.

    Raises:
        FileNotFoundError: If the specified UI file doesn't exist.

    Note:
        `QUiLoader` lives in `QtUiTools`, which the PyQt bindings do not
        ship. The import is therefore deferred to call time (a module-level
        one made `import fxgui` fail outright under PyQt5/PyQt6) and falls
        back to `qtpy.uic.loadUi`, which qtpy provides for every binding.

    Examples:
        To load a UI file located in the same directory as the Python script
        >>> from pathlib import Path
        >>> ui_path = Path(__file__).with_suffix('.ui')
        >>> loaded_ui = load_ui(self, ui_path)
    """

    if not os.path.isfile(ui_file):
        raise FileNotFoundError(f"UI file not found: {ui_file}")

    try:
        from qtpy.QtUiTools import QUiLoader
    except ImportError:
        # PyQt: load without a base instance so a *new* widget comes back,
        # then parent it, matching the QUiLoader behavior below.
        from qtpy.uic import loadUi

        loaded_ui = loadUi(ui_file)
        loaded_ui.setParent(parent)
        return loaded_ui

    handle = QFile(ui_file)
    loaded_ui = QUiLoader().load(handle, parent)
    handle.close()
    return loaded_ui


def create_action(
    parent: QWidget,
    name: str,
    icon: Union[str, QIcon] = None,
    trigger: Optional[Callable] = None,
    enable: bool = True,
    visible: bool = True,
    shortcut: Optional[str] = None,
    checkable: bool = False,
    icon_name: Optional[str] = None,
) -> QAction:
    """Create a QAction with common settings.

    Args:
        parent: Parent widget for the action.
        name: Display name for the action.
        icon: A QIcon, or the path of an icon file.
        trigger: Callback function to execute when triggered. Defaults to None.
        enable: Whether the action is enabled. Defaults to True.
        visible: Whether the action is visible. Defaults to True.
        shortcut: Keyboard shortcut (e.g., "Ctrl+S"). Defaults to None.
        checkable: Whether the action is checkable. Defaults to False.
        icon_name: An fxicons name, drawn in the theme's colours; wins over
            `icon`.

    Returns:
        The created QAction.

    Examples:
        >>> action = create_action(
        ...     parent=window,
        ...     name="Save",
        ...     icon_name="save",
        ...     trigger=lambda: print("Saved!"),
        ...     shortcut="Ctrl+S"
        ... )
    """
    from fxgui import fxicons

    action = QAction(name, parent or None)

    if icon_name is not None:
        fxicons.set_icon(action, icon_name)
    elif icon is not None:
        if isinstance(icon, QIcon):
            action.setIcon(icon)
        else:
            action.setIcon(QIcon(icon))

    if trigger is not None:
        action.triggered.connect(trigger)
    action.setEnabled(enable)
    action.setVisible(visible)
    action.setCheckable(checkable)
    if shortcut is not None:
        action.setShortcut(QKeySequence(shortcut))

    return action


def add_shadows(
    parent: QWidget,
    shadow_object: QWidget,
    color: str = "#50000000",
    blur: float = 20,
    offset: float = 0,
) -> QGraphicsDropShadowEffect:
    """Apply shadows to a widget; the defaults are every floating card's.

    Args:
        parent (QWidget, optional): Parent object.
        shadow_object (QWidget): Object to receive shadows.
        color (str, optional): Color of the shadows, `#AARRGGBB` for an
            alpha. Defaults to black at 80 of 255.
        blur (float, optional): Blur level of the shadows. Defaults to `20`.
        offset (float, optional): Offset of the shadow from the
            `shadow_object`. Defaults to `0`.

    Returns:
        QGraphicsDropShadowEffect: The shadow object.

    Examples:
        >>> # Apply shadows to `self.top_toolbar` widget
        >>> add_shadows(self, self.top_toolbar, "#212121")
    """

    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(blur)
    shadow.setOffset(offset)
    shadow.setColor(QColor(color))
    shadow_object.setGraphicsEffect(shadow)

    return shadow


# ' Misc
def get_formatted_time(
    display_seconds: bool = False, display_date: bool = False
) -> str:
    """Returns the current time as a formatted string.

    Args:
        display_seconds (bool, optional): Whether to display the seconds.
            Defaults to `False`.
        display_date (bool, optional): Whether to display the date.
            Defaults to `False`.

    Returns:
        str: The formatted current time.

    Examples:
        >>> get_formatted_time()
        '14:30'
        >>> get_formatted_time(display_seconds=True)
        '14:30:45'
        >>> get_formatted_time(display_date=True)
        '2025-12-29 14:30'
    """

    format_string = "%H:%M:%S" if display_seconds else "%H:%M"
    if display_date:
        format_string = "%Y-%m-%d " + format_string
    return datetime.now().strftime(format_string)


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

    A tray flyout or a context menu on Windows 11 is a rounded rectangle
    with the compositor's own shadow under it, and the platform draws
    both for any window that asks. Asking is one
    `DwmSetWindowAttribute` call, which is the whole reason this exists
    rather than a paint event: rounding a window by hand needs a
    translucent frameless widget and a paint event that agrees with it,
    the shadow under that needs a transparent margin on every edge, and
    a window seated by its own edges then has to subtract those margins
    from every position it computes. The compositor's answer changes no
    geometry at all -- the window keeps the rectangle it was given, and
    the OS clips and shades it.

    Nothing here raises. Off Windows 11 -- an older build, another
    platform, the offscreen platform a test runs under -- the answer is
    `False` and the window keeps its square corners, because a square
    panel is still a panel and an application that refuses to open
    because a compositor declined is not.

    `ctypes` is stdlib, the platform guard below keeps it unused on
    every system that is not Windows, and there is no Qt API for the
    request.

    Args:
        widget: The window to round. Must already BE a window: this
            reads its native handle, and asking a widget for one creates
            it, so a child widget would be made native for nothing.

    Returns:
        bool: Whether the compositor took the request. `False` is an
        ordinary answer rather than a failure -- it is what every
        platform without Windows 11's window rounding says.

    Examples:
        >>> panel.show()  # doctest: +SKIP
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
    option = QStyleOptionViewItem()
    option.font = view.font()
    option.widget = view
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
