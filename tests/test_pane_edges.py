"""A flush row view runs to its pane's border; the rest keeps the gap."""

# Third-party
import pytest

ads = pytest.importorskip("PySide6QtAds")

from qtpy.QtCore import QPoint, QRect  # noqa: E402
from qtpy.QtGui import QColor  # noqa: E402
from qtpy.QtWidgets import (  # noqa: E402
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxdocking, fxstyle  # noqa: E402
from fxgui.fxwidgets import (  # noqa: E402
    FXFilteredTree,
    FXKeyboardTree,
    FXMainWindow,
    FXSearchBar,
)

GAP = fxstyle.PANE_GAP


def _tree():
    view = QTreeWidget()
    view.setHeaderLabels(["Name"])
    for n in range(4):
        QTreeWidgetItem(view, [f"sh00{n}0"])
    return view


def _docked(qtbot, body):
    window = FXMainWindow(title="Panes", framed=True)
    docks = fxdocking.FXDockArea()
    window.setCentralWidget(docks)
    docks.set_central(QLabel("centre"))
    docks.add_dock("pane", "Pane", body, "left")
    qtbot.addWidget(window)
    window.resize(800, 500)
    window.show()
    qtbot.waitExposed(window)
    for _ in range(3):
        QApplication.processEvents()
    return window, docks


def _edges(docks, widget):
    """Return the pane's inner rect and `widget`'s rect, in the pane."""
    area = docks.manager().findDockWidget("pane").dockAreaWidget()
    box = QRect(widget.mapTo(area, QPoint(0, 0)), widget.size())
    return area.contentsRect(), box


def test_a_view_that_is_the_pane_runs_to_its_border(qtbot):
    view = _tree()
    _window, docks = _docked(qtbot, view)
    inner, box = _edges(docks, view)
    assert (box.left(), box.right(), box.bottom()) == (
        inner.left(), inner.right(), inner.bottom())


def test_a_flush_view_runs_to_the_sides_and_its_neighbours_keep_the_gap(qtbot):
    body = QWidget()
    column = QVBoxLayout(body)
    column.setContentsMargins(0, 0, 0, 0)
    search = FXSearchBar()
    view = _tree()
    fxstyle.mark_flush(view)
    publish = QPushButton("Publish")
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(publish)
    for item in (search, view):
        column.addWidget(item)
    column.addLayout(row)
    _window, docks = _docked(qtbot, body)
    inner, box = _edges(docks, view)
    assert (box.left(), box.right()) == (inner.left(), inner.right())
    # Not the last widget: the buttons under it stand above the bottom.
    assert box.bottom() < inner.bottom() - GAP
    _inner, bar = _edges(docks, search)
    assert bar.left() == inner.left() + GAP
    _inner, button = _edges(docks, publish)
    assert inner.right() - button.right() == GAP
    assert inner.bottom() - button.bottom() == GAP


def test_a_filtered_tree_runs_its_tree_to_the_border(qtbot):
    tree = FXKeyboardTree()
    for n in range(4):
        QTreeWidgetItem(tree, [f"seq0{n}0"])
    filtered = FXFilteredTree(tree)
    _window, docks = _docked(qtbot, filtered)
    inner, box = _edges(docks, tree)
    assert (box.left(), box.right(), box.bottom()) == (
        inner.left(), inner.right(), inner.bottom())
    _inner, bar = _edges(docks, filtered.filter_bar)
    assert bar.left() == inner.left() + GAP


@pytest.mark.parametrize("kind", ["form", "log"])
def test_a_pane_without_a_row_view_keeps_the_gap(qtbot, kind):
    if kind == "form":
        body = QWidget()
        fields = QVBoxLayout(body)
        fields.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit("sh0010")
        fields.addWidget(field)
        fields.addStretch()
    else:
        body = field = QPlainTextEdit("12:00 INFO started")
    _window, docks = _docked(qtbot, body)
    inner, box = _edges(docks, field)
    assert box.left() - inner.left() == GAP
    assert inner.right() - box.right() == GAP


def test_a_view_marked_flush_after_docking_runs_to_the_border(qtbot):
    body = QWidget()
    column = QVBoxLayout(body)
    column.setContentsMargins(0, 0, 0, 0)
    view = _tree()
    column.addWidget(view)
    _window, docks = _docked(qtbot, body)
    inner, box = _edges(docks, view)
    assert box.left() == inner.left() + GAP
    fxstyle.mark_flush(view)
    QApplication.processEvents()
    inner, box = _edges(docks, view)
    assert (box.left(), box.right(), box.bottom()) == (
        inner.left(), inner.right(), inner.bottom())


def test_a_floating_pane_keeps_its_view_at_the_border(qtbot):
    view = _tree()
    _window, docks = _docked(qtbot, view)
    held = docks.manager().findDockWidget("pane")
    held.setFloating()
    qtbot.waitUntil(lambda: held.floatingDockContainer() is not None)
    for _ in range(3):
        QApplication.processEvents()
    inner, box = _edges(docks, view)
    assert (box.left(), box.right(), box.bottom()) == (
        inner.left(), inner.right(), inner.bottom())


def test_the_pane_s_bottom_corners_stay_round_over_a_flush_view(qtbot):
    view = _tree()
    window, docks = _docked(qtbot, view)
    area = docks.manager().findDockWidget("pane").dockAreaWidget()
    image = area.grab().toImage()
    ground = fxstyle._ground(area.parentWidget()).name()
    bottom = area.height() - 1
    # The pane's own corner pixels, outside its arc, show what is behind it.
    for x in (0, area.width() - 1):
        assert QColor(image.pixel(x, bottom)).name() == ground


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_skeleton_over_a_plain_pane_hides_it_on_the_pane_s_ground(
    qtbot, theme
):
    from fxgui.fxwidgets import FXSkeleton

    fxstyle.apply_theme(theme, save=False)
    pane = QWidget()
    lines = QVBoxLayout(pane)
    words = [QLabel("OLD CONTENT " * 3) for _ in range(6)]
    for label in words:
        lines.addWidget(label)
    lines.addStretch()
    window, _docks = _docked(qtbot, pane)
    ground = fxstyle._ground(pane)
    before = window.grab().toImage()

    def inked(image):
        """Pixels of the old words: where the text differs from the ground."""
        spots = []
        for label in words:
            corner = label.mapTo(window, QPoint(0, 0))
            for x in range(corner.x(), corner.x() + label.width(), 3):
                for y in range(corner.y(), corner.y() + label.height(), 2):
                    if QColor(image.pixel(x, y)) != ground:
                        spots.append((x, y))
        return spots

    text = inked(before)
    assert text, "no old content drawn"
    skeleton = FXSkeleton.cover(pane, "lines")
    skeleton._animation.stop()
    QApplication.processEvents()
    after = window.grab().toImage()
    # Every old ink pixel is now the ground or a bar, never the old text.
    leftover = [
        (x, y) for x, y in text
        if QColor(after.pixel(x, y)) == QColor(before.pixel(x, y))
    ]
    assert not leftover, leftover[:5]
    corner = pane.mapTo(window, pane.rect().bottomRight())
    assert QColor(after.pixel(corner.x() - 3, corner.y() - 3)) == ground


def _nested(depth):
    """Return a pane body with a flush view `depth` containers deep."""
    view = _tree()
    fxstyle.mark_flush(view)
    holder, inner = None, view
    outer = None
    for level in range(depth):
        box = QWidget()
        stack = QVBoxLayout(box)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.addWidget(QLabel(f"level {level}"))
        stack.addWidget(inner)
        inner = box
        if outer is None:
            holder = stack
        outer = box
    return outer, view, holder


def test_a_view_three_containers_deep_reaches_the_border(qtbot):
    body, view, innermost = _nested(3)
    window, docks = _docked(qtbot, body)
    inner, box = _edges(docks, view)
    assert (box.left(), box.right(), box.bottom()) == (
        inner.left(), inner.right(), inner.bottom())
    # And stays there: a resize, a sibling hidden and shown, a re-layout.
    window.resize(900, 560)
    QApplication.processEvents()
    sibling = innermost.itemAt(0).widget()
    sibling.hide()
    QApplication.processEvents()
    sibling.show()
    QApplication.processEvents()
    innermost.invalidate()
    QApplication.processEvents()
    inner, box = _edges(docks, view)
    assert (box.left(), box.right(), box.bottom()) == (
        inner.left(), inner.right(), inner.bottom())


def test_a_deep_view_marked_flush_late_reaches_the_border(qtbot):
    body, view, _innermost = _nested(3)
    fxstyle.mark_flush(view, False)
    _window, docks = _docked(qtbot, body)
    fxstyle.mark_flush(view)
    QApplication.processEvents()
    inner, box = _edges(docks, view)
    assert (box.left(), box.right()) == (inner.left(), inner.right())
