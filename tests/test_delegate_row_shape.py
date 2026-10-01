"""The row's rounded card, its column separators and the focus ring's ends."""

# Third-party
import pytest
from qtpy.QtCore import QModelIndex, QRect
from qtpy.QtGui import QColor, QPainter, QPixmap
from qtpy.QtWidgets import QStyle, QStyleOptionViewItem

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate

from _helpers import delegate_tree

from _helpers import near

_FILL = QColor("#1a3a5c")
_BLANK = QColor("#ff00ff")


def _paint(qtbot, draw, position):
    delegate = FXThumbnailDelegate()
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 60, 30)
    option.state = QStyle.State_Enabled | QStyle.State_HasFocus
    option.widget = None
    canvas = QPixmap(60, 30)
    canvas.fill(_BLANK)
    painter = QPainter(canvas)
    try:
        if draw == "card":
            delegate._draw_background_and_border(
                painter, option, _FILL, position
            )
        else:
            delegate._draw_focus_indicator(
                painter, option.rect, option, QModelIndex(), position
            )
    finally:
        painter.end()
    return canvas.toImage()


def test_the_first_cell_rounds_its_outer_corners_only(qtbot):
    image = _paint(qtbot, "card", (True, False))
    assert not near(image.pixelColor(1, 1), _FILL, 40)
    assert near(image.pixelColor(30, 15), _FILL, 40)
    # The inner edge is square and carries the column separator
    assert image.pixelColor(59, 2) != _BLANK


def test_a_middle_cell_draws_both_separators(qtbot):
    image = _paint(qtbot, "card", (False, False))
    border = QColor(fxstyle.colors().border_light)
    assert image.pixelColor(0, 15) == border
    assert image.pixelColor(59, 15) == border
    assert image.pixelColor(0, 1) != _BLANK


@pytest.mark.parametrize(
    "position, left, right",
    [
        ((True, False), True, False),
        ((False, False), False, False),
        ((False, True), False, True),
        ((True, True), True, True),
    ],
)
def test_the_focus_ring_closes_only_at_the_row_ends(
    qtbot, position, left, right
):
    image = _paint(qtbot, "ring", position)
    accent = QColor(fxstyle.colors().accent_primary)
    assert near(image.pixelColor(30, 0), accent, 40)
    assert near(image.pixelColor(0, 15), accent, 40) is left
    assert near(image.pixelColor(59, 15), accent, 40) is right


def _tree_row(qtbot, text="Row"):
    return delegate_tree(qtbot, [text])


def test_size_and_paint_agree_on_a_falsy_thumbnail_role(qtbot):
    tree, delegate, item = _tree_row(qtbot)
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, 0)
    index = tree.model().index(0, 0)
    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    assert delegate._has_thumbnail(index)
    assert delegate.sizeHint(option, index).height() == 50


def test_a_selected_title_is_painted_in_the_highlighted_text_color(qtbot):
    tree, delegate, item = _tree_row(qtbot, "WWWWWWWW")
    delegate.show_thumbnail = False
    item.setSelected(True)
    rect = tree.visualItemRect(item)
    image = tree.viewport().grab().toImage()
    ink = tree.palette().highlightedText().color()
    colors = {
        image.pixelColor(x, y).name()
        for x in range(rect.left(), rect.left() + 120)
        for y in range(rect.top(), rect.bottom())
    }
    assert any(near(QColor(c), ink, 30) for c in colors)


def test_a_hidden_child_count_paints_no_badge(qtbot):
    from qtpy.QtWidgets import QTreeWidgetItem

    shown, _, parent = _tree_row(qtbot)
    QTreeWidgetItem(parent, ["child"])
    hidden, _, other = _tree_row(qtbot)
    QTreeWidgetItem(other, ["child"])
    other.setData(0, FXThumbnailDelegate.CHILD_COUNT_VISIBLE_ROLE, False)
    bare, _, _ = _tree_row(qtbot)
    rect = shown.visualItemRect(parent)
    corner = QRect(rect.right() - 30, rect.bottom() - 20, 30, 20)

    def region(tree):
        image = tree.viewport().grab().toImage()
        return [
            image.pixel(x, y)
            for x in range(corner.left(), corner.right())
            for y in range(corner.top(), corner.bottom())
        ]

    assert region(hidden) == region(bare)
    assert region(shown) != region(bare)
