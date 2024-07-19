"""Utils related to QT objects."""

# Built-in
import os
from typing import Callable, Optional

# Thirs-party
from qtpy.QtUiTools import QUiLoader
from qtpy.QtCore import QFile, QSize
from qtpy.QtGui import QIcon, QPixmap, QKeySequence
from qtpy.QtWidgets import (
    QAction,
    QWidget,
    QGraphicsDropShadowEffect,
    QLineEdit,
    QTreeWidget,
)


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
    icon: str,
    trigger: Callable,
    enable: bool = True,
    visible: bool = True,
    shortcut: str = None,
) -> Optional[QAction]:
    """Creates a QACtion.

    Args:
        parent (QWidget): Parent object.
        name (str): Name to display.
        icon (str): Icon path.
        trigger (Callable): Function to trigger when clicked.
        enable (bool, optional): Enable/disable. Defaults to `True`.
        visible (bool, optional): Show/hide. Defaults to `True`.
        shortcut (str, optional): If not `None`, key sequence (hotkeys) to use.
            Defaults to `None`.

    Returns:
        Optional[QAction]:
    """

    action = QAction(name, parent or None)
    action.setIcon(QIcon(icon))
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


def convert_qicon_to_qpixmap(icon: QIcon, desired_size: Optional[QSize] = None) -> Optional[QPixmap]:
    """Converts a QIcon to a QPixmap.

    Args:
      icon: The QIcon to convert.
      desired_size: The desired size for the pixmap (QSize). If `None`,
        the "best" available size will be used.

    Returns:
      QPixmap: A QPixmap or `None` if no suitable pixmap is available.

    Examples:
        Let the size be decided
        >>> icon = hou.qt.Icon("MISC_python")
        >>> pixmap = convert_qicon_to_qpixmap(icon)

        Choose a size
        >>> icon = hou.qt.Icon("MISC_python")
        >>> pixmap = convert_qicon_to_qpixmap(icon, QSize(48, 48))
    """

    try:
        if desired_size:
            return icon.pixmap(desired_size)
        else:
            return icon.pixmap(QSize(48, 48))
    except:
        return None


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


def set_formatted_tooltip(widget: QWidget, title: str, tooltip: str, duration: int = 5) -> None:
    """Set a formatted tooltip. The tooltip will be displayed with a bold title, and a separator line
    between the title and the tooltip text.

    Args:
        widget (QWidget): The widget to set the tooltip.
        title (str): The title of the tooltip.
        tooltip (str): The tooltip text.
        duration (int): The duration in seconds to show the tooltip. Defaults to `5`.

    Examples:
        >>> set_formatted_tooltip(self, "Tooltip", "This is a <b>formatted</b> tooltip.")
    """

    tooltip = f"<b>{title}</b><hr>{tooltip}"
    widget.setToolTip(tooltip)
    widget.setToolTipDuration(duration * 1000)
