"""Helpers the test files share: pixels, colours, the pointer, windows."""

# Third-party
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor, QCursor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle


def near(a, b, step: int = 8) -> bool:
    """Return whether two colours sit within `step` on every channel."""
    one, two = QColor(a), QColor(b)
    return max(abs(one.red() - two.red()), abs(one.green() - two.green()),
               abs(one.blue() - two.blue())) <= step


def pixel(window: QWidget, widget: QWidget, x, y: int = None) -> str:
    """Return the colour name `window` paints at `widget`'s (x, y).

    `x` may be a QPoint, with no `y`.
    """
    point = widget.mapTo(window, x if y is None else QPoint(x, y))
    return window.grab().toImage().pixelColor(point).name()


def _image(source):
    return source.toImage() if hasattr(source, "toImage") else source


def inks(source) -> set:
    """Return every opaque colour name in an image or pixmap."""
    image = _image(source)
    return {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }


def first_ink(source) -> str:
    """Return the first opaque colour name, column by column, or ""."""
    image = _image(source)
    for x in range(image.width()):
        for y in range(image.height()):
            colour = image.pixelColor(x, y)
            if colour.alpha() == 255:
                return colour.name()
    return ""


def _clear_of_other_windows(window: QWidget) -> None:
    """Move `window` right of every other shown window it overlaps.

    The offscreen platform opens every window at one spot, and a window
    opened over another one never gets the pointer.
    """
    mine = window.frameGeometry()
    others = [
        other.frameGeometry() for other in QApplication.topLevelWidgets()
        if other is not window and other.isVisible()
        and other.frameGeometry().intersects(mine)
    ]
    if others:
        window.move(max(other.right() for other in others) + 20, window.y())


def hover(qtbot, widget: QWidget, point: QPoint = None) -> None:
    """Move the pointer onto `widget` from outside its window, like a mouse.

    The move goes through Qt's own mouse path, so the widget gets its enter
    and hover events and WA_UnderMouse the way a real pointer gives them.
    """
    _clear_of_other_windows(widget.window())
    unhover(qtbot, widget)
    if point is None:
        point = widget.rect().center()
    QTest.mouseMove(widget, point)
    qtbot.waitUntil(widget.underMouse)


def unhover(qtbot, widget: QWidget) -> None:
    """Move the pointer off `widget`, to just outside its window."""
    QTest.mouseMove(widget.window(), QPoint(-1, -1))
    qtbot.waitUntil(lambda: not widget.underMouse())


def shown(qtbot, widget: QWidget, size=None) -> QWidget:
    """Show `widget` at `size` and return it once it is on screen."""
    if widget.parentWidget() is None:
        qtbot.addWidget(widget)
    if size is not None:
        widget.resize(*size)
    # A window opened under the pointer marks a widget under it that no
    # later move clears, so the pointer goes off every screen first.
    QCursor.setPos(-1000, -1000)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def themed_window(qtbot, theme: str, *widgets, size=(320, 240)) -> QWidget:
    """Return a shown themed window holding `widgets`, focus on itself."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    layout = QVBoxLayout(window)
    for widget in widgets:
        layout.addWidget(widget)
    shown(qtbot, window, size)
    # The window holds focus, so no widget wears its focus look.
    window.setFocusPolicy(Qt.StrongFocus)
    window.setFocus()
    QApplication.processEvents()
    return window


def delegate_tree(qtbot, row=None, headers=None, widths=(300,), height=120,
                  **attrs):
    """Return a shown tree drawn by FXThumbnailDelegate, with one row or none.

    Args:
        row: The row's text per column, or None for no row.
        headers: The column titles, or None for no header.
        widths: Each column's width.
        height: The tree's height.
        **attrs: Delegate attributes to set, by name.

    Returns:
        Tuple of (tree, delegate, item or None).
    """
    from fxgui.fxwidgets import FXThumbnailDelegate

    tree = QTreeWidget()
    tree.setColumnCount(len(widths))
    if headers:
        tree.setHeaderLabels(list(headers))
    else:
        tree.setHeaderHidden(True)
    tree.setRootIsDecorated(False)
    tree.header().setStretchLastSection(False)
    for column, width in enumerate(widths):
        tree.setColumnWidth(column, width)
    delegate = FXThumbnailDelegate()
    for name, value in attrs.items():
        setattr(delegate, name, value)
    tree.setItemDelegate(delegate)
    item = QTreeWidgetItem(tree, list(row)) if row else None
    shown(qtbot, tree, (sum(widths) + 40, height))
    return tree, delegate, item
