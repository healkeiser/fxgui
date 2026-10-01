"""The base sheet's chrome: branches, scroll bars, arrows, cards, tabs, popups."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle

THEMES = pytest.mark.parametrize("theme", fxstyle.get_available_themes())


def _shown(qtbot, theme, widget, size=(320, 240)):
    """Show `widget` alone in a themed window and return the window."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    QVBoxLayout(window).addWidget(widget)
    window.resize(*size)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    return window


def _distance(first, second):
    a, b = QColor(first), QColor(second)
    return max(
        abs(a.red() - b.red()),
        abs(a.green() - b.green()),
        abs(a.blue() - b.blue()),
    )


def _pixels(image, rect):
    return {
        image.pixelColor(x, y).name()
        for x in range(rect.left(), rect.right() + 1)
        for y in range(rect.top(), rect.bottom() + 1)
    }


# (1) Trees: no branch lines, the accordion's chevrons in the icon token.


def _tree():
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setIndentation(20)
    opened = QTreeWidgetItem(tree, ["opened"])
    for name in ("first", "second", "third"):
        QTreeWidgetItem(opened, [name])
    closed = QTreeWidgetItem(tree, ["closed"])
    QTreeWidgetItem(closed, ["hidden"])
    QTreeWidgetItem(tree, ["leaf"])
    opened.setExpanded(True)
    return tree


def _branch(tree, item):
    """Return the branch area left of `item`, in window coordinates."""
    rect = tree.visualItemRect(item)
    rect.setLeft(rect.left() - tree.indentation())
    rect.setRight(rect.left() + tree.indentation() - 1)
    return rect.translated(tree.viewport().mapTo(tree.window(), QPoint()))


@THEMES
def test_a_tree_draws_chevrons_and_no_branch_lines(qtbot, theme):
    tree = _tree()
    window = _shown(qtbot, theme, tree)
    image = window.grab().toImage()
    colors = fxstyle.colors()
    opened, closed, leaf = (tree.topLevelItem(row) for row in range(3))
    for item in (opened, closed):
        inks = _pixels(image, _branch(tree, item))
        assert min(_distance(ink, colors.icon) for ink in inks) <= 24, inks
    # A leaf, a child and the column under an open parent are bare.
    sunken = colors.surface_sunken.lower()
    for item in (leaf, opened.child(0), opened.child(2)):
        assert _pixels(image, _branch(tree, item)) == {sunken}, item.text(0)
    # Open and closed are different marks.
    assert image.copy(_branch(tree, opened)) != image.copy(
        _branch(tree, closed)
    )
