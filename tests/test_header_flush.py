"""A view's header sits flush with its frame; rows keep their text still."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtWidgets import (
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle

from _helpers import hover, themed_window

# The sheet's 1 px edge around every item view.
_EDGE = 1


def _tree(header=True):
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Version"])
    tree.setHeaderHidden(not header)
    tree.setRootIsDecorated(False)
    for index in range(3):
        QTreeWidgetItem(tree, [f"Row{index}", "v001"])
    return tree


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_tree_header_touches_the_frame_on_three_sides(qtbot, theme):
    tree = _tree()
    _window = themed_window(qtbot, theme, tree)
    header = tree.header().geometry()
    assert (header.left(), header.top()) == (_EDGE, _EDGE)
    assert header.width() == tree.width() - 2 * _EDGE


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_table_header_touches_the_frame(qtbot, theme):
    table = QTableWidget(3, 2)
    _window = themed_window(qtbot, theme, table)
    top = table.horizontalHeader().geometry()
    side = table.verticalHeader().geometry()
    assert top.top() == _EDGE
    assert side.left() == _EDGE


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_tree_with_no_header_keeps_its_rows_off_the_top(qtbot, theme):
    tree = _tree(header=False)
    _window = themed_window(qtbot, theme, tree)
    viewport = tree.viewport().geometry()
    assert viewport.top() > _EDGE


def _text_left(image, origin, y, right):
    """Return the first column right of `origin` that is ink on the row.

    The row's fill is read at `right`, past its text.
    """
    fill = image.pixelColor(right, y).name()
    return next(
        x for x in range(origin.x() + _EDGE, right)
        if fxstyle.get_contrast_ratio(image.pixelColor(x, y).name(), fill)
        >= 3
    ) - origin.x()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_row_text_stays_put_in_every_state(qtbot, theme):
    tree = _tree()
    window = themed_window(qtbot, theme, tree)
    rows = [tree.topLevelItem(index) for index in range(3)]
    rows[2].setSelected(True)
    hover(qtbot, tree.viewport(), tree.visualItemRect(rows[1]).center())
    image = window.grab().toImage()
    origin = tree.mapTo(window, QPoint())
    right = origin.x() + tree.columnWidth(0) - 10
    starts = [
        _text_left(image, origin, tree.viewport().mapTo(
            window, tree.visualItemRect(row).center()).y(), right)
        for row in rows
    ]
    assert len(set(starts)) == 1, starts


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_inset_follows_a_header_hidden_or_shown_after_the_show(
        qtbot, theme):
    tree = _tree()
    _window = themed_window(qtbot, theme, tree)
    assert tree.viewport().geometry().left() == _EDGE
    tree.setHeaderHidden(True)
    qtbot.waitUntil(lambda: tree.viewport().geometry().top() > _EDGE)
    tree.setHeaderHidden(False)
    qtbot.waitUntil(lambda: tree.header().geometry().top() == _EDGE)
