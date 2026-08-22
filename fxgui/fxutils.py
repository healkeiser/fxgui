"""Utility functions for the `fxgui` package.

This module provides general-purpose utility functions for Qt-based
applications including UI loading, action creation, widget effects,
tree filtering, and tooltip formatting.

Functions:
    load_ui: Load a Qt Designer UI file.
    create_action: Create a QAction with common settings.
    add_shadows: Apply drop shadow effect to a widget.
    filter_tree: Filter QTreeWidget items by text.
    set_formatted_tooltip: Set a styled tooltip with title.
    get_formatted_time: Get current time as formatted string.
    deprecated: Decorator to mark functions as deprecated.
    repolish: Force re-evaluation of stylesheet rules for a widget.
    round_window_corners: Ask Windows 11 for a flyout's rounded corners.

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
from datetime import datetime
from functools import wraps
from typing import Callable, Optional, Union
import warnings

# Third-party
from qtpy.QtWidgets import (
    QAction,
    QWidget,
    QGraphicsDropShadowEffect,
    QLineEdit,
    QTreeWidget,
)
from qtpy.QtGui import QIcon, QKeySequence
from qtpy.QtCore import QFile


# Public API
__all__ = [
    "load_ui",
    "create_action",
    "add_shadows",
    "filter_tree",
    "set_formatted_tooltip",
    "get_formatted_time",
    "deprecated",
    "repolish",
    "round_window_corners",
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
        icon: Icon for the action. Can be a path string or a QIcon object.
            Deprecated: prefer using `icon_name` for automatic theme updates.
        trigger: Callback function to execute when triggered. Defaults to None.
        enable: Whether the action is enabled. Defaults to True.
        visible: Whether the action is visible. Defaults to True.
        shortcut: Keyboard shortcut (e.g., "Ctrl+S"). Defaults to None.
        checkable: Whether the action is checkable. Defaults to False.
        icon_name: Name of the icon from fxicons. When provided, the action
            will be registered for automatic icon updates on theme changes.

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

    # Prefer icon_name for automatic theme updates
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
    color: str = "#000000",
    blur: float = 10,
    offset: float = 0,
) -> QGraphicsDropShadowEffect:
    """Apply shadows to a widget.

    Args:
        parent (QWidget, optional): Parent object.
        shadow_object (QWidget): Object to receive shadows.
        color (str, optional): Color of the shadows. Defaults to `#000000`.
        blur (float, optional): Blur level of the shadows. Defaults to `10`.
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
    shadow.setColor(color)
    shadow_object.setGraphicsEffect(shadow)

    return shadow


def filter_tree(
    filter_bar_object: QLineEdit,
    tree_to_filter: QTreeWidget,
    column: int = 0,
) -> None:
    """Filters the items of a tree by displaying or hiding them based
    on whether they match the filter text. Both root and child items are
    considered.

    .. deprecated::
        Consider using :class:`fxgui.fxcore.FXSortFilterProxyModel` for
        more sophisticated filtering with fuzzy matching support.

    Args:
        filter_bar_object (QLineEdit): The QLineEdit widget representing the
            filter bar.
        tree_to_filter (QTreeWidget): The QTreeWidget to be filtered.
        column (int, optional): The column index to use for text filtering.
            Defaults to `0`.

    Examples:
        >>> filter_bar = QLineEdit()
        >>> tree_widget = QTreeWidget()
        >>> filter_tree(filter_bar, tree_widget, column=1)
    """
    warnings.warn(
        "filter_tree is deprecated. Consider using FXSortFilterProxyModel "
        "from fxgui.fxcore for more sophisticated fuzzy filtering.",
        DeprecationWarning,
        stacklevel=2,
    )

    filter_text = filter_bar_object.text().lower()
    root = tree_to_filter.invisibleRootItem()

    for child in range(root.childCount()):
        item = root.child(child)
        item_text = item.text(column).lower()
        item.setHidden(filter_text not in item_text)

        if item.childCount() > 0:
            should_hide_parent = all(
                filter_text not in item.child(grandchild).text(column).lower()
                for grandchild in range(item.childCount())
            )
            item.setHidden(item.isHidden() or should_hide_parent)


def set_formatted_tooltip(
    widget: QWidget, title: str, tooltip: str, duration: int = 5
) -> None:
    """Set a formatted tooltip. The tooltip will be displayed with a bold title,
    and a separator line between the title and the tooltip text.

    Args:
        widget (QWidget): The widget to set the tooltip.
        title (str): The title of the tooltip.
        tooltip (str): The tooltip text.
        duration (int): The duration in seconds to show the tooltip.
            Defaults to `5`.

    Examples:
        >>> set_formatted_tooltip(
        ...     self, "Tooltip", "This is a <b>formatted</b> tooltip."
        ... )

    Note:
        Superseded by `fxwidgets.apply_tip`, which is theme-aware, escapes
        the caller's strings, renders a keyboard shortcut as a keycap and
        also sets a status tip. Prefer it for new code.

        This function is kept as-is rather than reimplemented over
        `apply_tip` because the two have incompatible contracts: `tooltip`
        here is documented as accepting markup (see the example above), which
        `apply_tip` escapes on purpose so a path or a name cannot corrupt the
        layout. Rewriting it would turn a caller's `<b>` into literal text
        and drop `setToolTipDuration`.
    """

    tooltip = f"<b>{title}</b><hr>{tooltip}"
    widget.setToolTip(tooltip)
    widget.setToolTipDuration(duration * 1000)


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


def deprecated(func: Callable) -> Callable:
    """Decorator to mark functions as deprecated.

    When a decorated function is called, it emits a DeprecationWarning
    to alert users that the function will be removed in a future version.

    Args:
        func: The function to mark as deprecated.

    Returns:
        A wrapper function that emits a warning before calling the original.

    Examples:
        >>> @deprecated
        ... def old_function():
        ...     return "old behavior"
        >>> old_function()  # Emits DeprecationWarning
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} is deprecated and will be removed in a future version",
            DeprecationWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


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

    This is the one place in fxgui that reaches for `ctypes`. It is
    stdlib, it is loaded lazily by the platform guard below on every
    system that is not Windows, and there is no Qt API for the request.

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
