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
import os
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
from qtpy.QtUiTools import QUiLoader
from qtpy.QtGui import QIcon, QKeySequence
from qtpy.QtCore import QFile


def load_ui(parent: QWidget, ui_file: str) -> QWidget:
    """Load a UI file and return the loaded UI as a QWidget.

    Args:
        parent (QWidget): Parent object.
        ui_file (str): Path to the UI file.

    Returns:
        QWidget: The loaded UI.

    Raises:
        FileNotFoundError: If the specified UI file doesn't exist.

    Examples:
        To load a UI file located in the same directory as the Python script
        >>> from pathlib import Path
        >>> ui_path = Path(__file__).with_suffix('.ui')
        >>> loaded_ui = load_ui(self, ui_path)
    """

    if os.path.isfile(ui_file):
        ui_file = QFile(ui_file)
        loaded_ui = QUiLoader().load(ui_file, parent)
        ui_file.close()
        return loaded_ui
    else:
        raise FileNotFoundError(f"UI file not found: {ui_file}")


def create_action(
    parent: QWidget,
    name: str,
    icon: Union[str, QIcon],
    trigger: Optional[Callable] = None,
    enable: bool = True,
    visible: bool = True,
    shortcut: Optional[str] = None,
) -> QAction:
    """Create a QAction with common settings.

    Args:
        parent: Parent widget for the action.
        name: Display name for the action.
        icon: Icon for the action. Can be a path string or a QIcon object.
        trigger: Callback function to execute when triggered. Defaults to None.
        enable: Whether the action is enabled. Defaults to True.
        visible: Whether the action is visible. Defaults to True.
        shortcut: Keyboard shortcut (e.g., "Ctrl+S"). Defaults to None.

    Returns:
        The created QAction.

    Examples:
        >>> action = create_action(
        ...     parent=window,
        ...     name="Save",
        ...     icon=get_icon("save"),
        ...     trigger=lambda: print("Saved!"),
        ...     shortcut="Ctrl+S"
        ... )
    """

    action = QAction(name, parent or None)
    if isinstance(icon, QIcon):
        action.setIcon(icon)
    else:
        action.setIcon(QIcon(icon))
    if trigger is not None:
        action.triggered.connect(trigger)
    action.setEnabled(enable)
    action.setVisible(visible)
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
