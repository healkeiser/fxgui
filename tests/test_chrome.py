"""The base sheet's chrome: branches, scroll bars, arrows, cards, tabs, popups."""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint, QPointF, Qt
from qtpy.QtGui import QColor, QHoverEvent
from qtpy.QtWidgets import (
    QApplication,
    QListWidget,
    QStyle,
    QStyleOptionSlider,
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


# (2) Scroll bars: a thin rounded thumb, no arrows, wider on hover.


def _hover(widget, point):
    widget.setAttribute(Qt.WA_UnderMouse, True)
    QApplication.sendEvent(
        widget,
        QHoverEvent(
            QEvent.HoverMove,
            QPointF(point),
            QPointF(widget.mapToGlobal(point)),
            QPointF(-1, -1),
        ),
    )
    QApplication.processEvents()


def _bar_rect(bar, control):
    option = QStyleOptionSlider()
    bar.initStyleOption(option)
    return bar.style().subControlRect(QStyle.CC_ScrollBar, option, control, bar)


def _thumb_width(bar):
    """Return how many pixels across the bar the thumb paints."""
    image = bar.window().grab().toImage()
    middle = _bar_rect(bar, QStyle.SC_ScrollBarSlider).center().y()
    row = [
        image.pixelColor(bar.mapTo(bar.window(), QPoint(x, middle))).name()
        for x in range(bar.width())
    ]
    thumb = fxstyle.colors().scrollbar_thumb.lower()
    hover = fxstyle.colors().scrollbar_thumb_hover.lower()
    return sum(ink in (thumb, hover) for ink in row)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_scroll_bar_is_a_thin_pill_with_no_arrows(qtbot, theme):
    view = QListWidget()
    view.addItems([f"row {index}" for index in range(60)])
    window = _shown(qtbot, theme, view)
    bar = view.verticalScrollBar()
    assert bar.isVisible()
    assert bar.width() == fxstyle.THIN_SCROLL_WIDTH
    for control in (QStyle.SC_ScrollBarAddLine, QStyle.SC_ScrollBarSubLine):
        assert _bar_rect(bar, control).isEmpty()
    # No track: below the thumb the bar shows the view's own fill.
    image = window.grab().toImage()
    groove = bar.mapTo(window, QPoint(bar.width() // 2, bar.height() * 3 // 4))
    assert image.pixelColor(groove).name() == fxstyle.colors().surface_sunken
    # A rounded thumb paints its corner pixel only in part.
    handle = _bar_rect(bar, QStyle.SC_ScrollBarSlider)
    corner = bar.mapTo(window, QPoint(2, handle.top()))
    middle = bar.mapTo(window, QPoint(bar.width() // 2, handle.center().y()))
    assert image.pixelColor(middle).name() == fxstyle.colors().scrollbar_thumb
    assert image.pixelColor(corner).name() != fxstyle.colors().scrollbar_thumb
    rest = _thumb_width(bar)
    _hover(bar, handle.center())
    hovered = _thumb_width(bar)
    assert 0 < rest < hovered <= bar.width(), (rest, hovered)
    assert bar.width() == fxstyle.THIN_SCROLL_WIDTH
