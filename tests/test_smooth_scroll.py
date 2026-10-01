"""Every list, tree and table under fxgui's sheet scrolls by the pixel.

Proved in both modes: an app fxgui themes, and a foreign app (a DCC host)
where only a registered root wears the sheet.
"""

# Third-party
import pytest
from qtpy.QtCore import QPoint, QPointF, Qt
from qtpy.QtGui import QWheelEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QListWidget,
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXDropZone, FXFuzzySearchTree

PIXEL = QAbstractItemView.ScrollMode.ScrollPerPixel
ITEM = QAbstractItemView.ScrollMode.ScrollPerItem


@pytest.fixture(params=["app", "host"])
def root(request, qapp, qtbot):
    """Return a window that wears the sheet: the app's, or its own."""
    window = QWidget()
    qtbot.addWidget(window)
    QVBoxLayout(window)
    if request.param == "host":
        fxstyle.register_themed_root(window)
        yield window
        return
    # What FXApplication does to the application.
    before = (qapp.styleSheet(), qapp.palette(), qapp.font(),
              qapp.style().name())
    fxstyle.set_style(qapp, "Fusion")
    fxstyle.register_themed_root(qapp)
    yield window
    qapp.setStyle(before[3])
    qapp.setStyleSheet(before[0])
    qapp.setPalette(before[1])
    qapp.setFont(before[2])


def _per_pixel(view: QAbstractItemView) -> bool:
    return (
        view.verticalScrollMode() == PIXEL
        and view.horizontalScrollMode() == PIXEL
    )


def _held(root, widget):
    root.layout().addWidget(widget)
    root.show()
    widget.ensurePolished()
    return widget


@pytest.mark.parametrize("build", [QTreeWidget, QListWidget, QTableWidget])
def test_any_item_view_scrolls_by_the_pixel(root, build):
    view = _held(root, build())

    assert _per_pixel(view), type(view).__name__


@pytest.mark.parametrize(
    "build", [FXFuzzySearchTree, FXDropZone]
)
def test_fxgui_views_scroll_by_the_pixel(root, build):
    widget = _held(root, build())

    views = [
        view
        for view in widget.findChildren(QAbstractItemView)
        if not isinstance(view, QHeaderView)
    ]
    if isinstance(widget, QAbstractItemView):
        views.append(widget)

    assert views
    for view in views:
        view.ensurePolished()
        assert _per_pixel(view), type(view).__name__


def test_views_built_after_the_window_scroll_by_the_pixel(root):
    root.show()
    tree = QTreeWidget()
    root.layout().addWidget(tree)
    tree.ensurePolished()

    assert _per_pixel(tree)


def test_a_view_named_in_a_rule_of_its_own_keeps_rows(root):
    fxstyle.register_widget_style(
        "QTreeWidget#fxTestRows { qproperty-verticalScrollMode: ScrollPerItem; }"
    )
    tree = QTreeWidget()
    tree.setObjectName("fxTestRows")

    _held(root, tree)

    assert tree.verticalScrollMode() == ITEM


def _notch(view: QAbstractItemView) -> int:
    """Turn the wheel one notch down over `view`; return the pixels moved."""
    viewport = view.viewport()
    centre = QPointF(viewport.rect().center())
    event = QWheelEvent(
        centre,
        QPointF(viewport.mapToGlobal(viewport.rect().center())),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    before = view.verticalScrollBar().value()
    QApplication.sendEvent(viewport, event)
    return int(view.verticalScrollBar().value() - before)


def test_one_wheel_notch_still_moves_about_three_rows(qtbot, root):
    tree = QTreeWidget()
    tree.setColumnCount(1)
    for index in range(200):
        QTreeWidgetItem(tree, [f"row {index}"])
    _held(root, tree)
    root.resize(300, 300)
    qtbot.waitExposed(root)
    row = tree.visualItemRect(tree.topLevelItem(0)).height()

    moved = _notch(tree)

    assert tree.verticalScrollMode() == PIXEL
    assert abs(moved - 3 * row) <= row, (moved, row)
