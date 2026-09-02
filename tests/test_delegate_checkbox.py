"""A tickable row drawn through FXThumbnailDelegate shows and takes its tick.

Regression: the delegate painted column 0 itself -- icon, title, description,
indicators -- and never the check box a `Qt.ItemIsUserCheckable` item
carries. The base class's `editorEvent` went on toggling the check state
under a click, so a tickable tree given this delegate had ticks nobody
could see and a box nobody could aim at.

What these tests pin: the box is painted where the style puts it, the text
starts to its right, a click on it toggles the item, and `sizeHint` makes
room for it.
"""

# Third-party
from qtpy.QtCore import QRect, Qt
from qtpy.QtGui import QImage
from qtpy.QtWidgets import (
    QStyle,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui.fxwidgets import FXThumbnailDelegate


def _tree(qtbot, *, checkable: bool):
    """A one-row tree drawn through the delegate, ticked or not tickable."""

    tree = QTreeWidget()
    tree.setHeaderLabels(["Name"])
    tree.setRootIsDecorated(False)
    tree.header().setStretchLastSection(False)
    tree.setColumnWidth(0, 300)
    tree.resize(340, 120)
    delegate = FXThumbnailDelegate()
    delegate.show_thumbnail = False
    tree.setItemDelegate(delegate)
    item = QTreeWidgetItem(tree, ["Beauty"])
    if checkable:
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
    qtbot.addWidget(tree)
    tree.show()
    qtbot.waitExposed(tree)
    return tree, delegate, item


def _check_rect(tree, index) -> QRect:
    """Where the style puts the box, asked the way `editorEvent` asks."""

    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    tree.itemDelegate().initStyleOption(option, index)
    return tree.style().subElementRect(
        QStyle.SE_ItemViewItemCheckIndicator, option, tree
    )


def _painted(tree, rect: QRect) -> set:
    """The distinct colours the viewport shows inside `rect`."""

    image: QImage = tree.viewport().grab().toImage()
    return {
        image.pixel(x, y)
        for x in range(rect.left(), rect.right() + 1)
        for y in range(rect.top(), rect.bottom() + 1)
    }


def test_a_tickable_row_paints_its_box(qtbot):
    """The box region carries more than the row's own painting does: a
    border and a fill at the least. The same region on an untickable
    row holds only what the row paints there, which is the background
    and its edge."""

    ticked_tree, _, _ = _tree(qtbot, checkable=True)
    plain_tree, _, _ = _tree(qtbot, checkable=False)
    index = ticked_tree.model().index(0, 0)
    rect = _check_rect(ticked_tree, index)
    assert rect.isValid() and rect.width() > 4

    assert len(_painted(ticked_tree, rect)) > len(_painted(plain_tree, rect))


def test_the_title_starts_right_of_the_box(qtbot):
    """Text drawn under the box is text nobody can read and a box nobody
    can see. The first painted column of the title is past the box."""

    ticked_tree, _, _ = _tree(qtbot, checkable=True)
    index = ticked_tree.model().index(0, 0)
    row = ticked_tree.visualRect(index)
    box = _check_rect(ticked_tree, index)
    image: QImage = ticked_tree.viewport().grab().toImage()
    background = image.pixel(row.right() - 2, row.center().y())

    # A margin past the box before the text is looked for, so the box's
    # own antialiased right edge is not read as the start of the title.
    gap = 3
    # Scan the strip between the box and the right edge for the first
    # column holding a non-background pixel: that is where the text is.
    text_left = None
    for x in range(box.right() + gap, row.right()):
        if any(
            image.pixel(x, y) != background
            for y in range(row.top() + 2, row.bottom() - 1)
        ):
            text_left = x
            break
    assert text_left is not None
    # And the title starts clear of the box, not on top of it.
    assert text_left > box.right() + gap


def test_a_click_on_the_box_toggles_the_tick(qtbot):
    """The base class's `editorEvent` decides a click's target from the
    same rect this delegate paints in, so what the artist sees is what
    the artist toggles."""

    tree, _, item = _tree(qtbot, checkable=True)
    index = tree.model().index(0, 0)
    box = _check_rect(tree, index)

    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=box.center())
    assert item.checkState(0) == Qt.Checked

    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=box.center())
    assert item.checkState(0) == Qt.Unchecked


def test_size_hint_makes_room_for_the_box(qtbot):
    """A row sized as if it had no box lays its title out under it the
    moment the column is narrowed to the hint."""

    ticked_tree, ticked_delegate, _ = _tree(qtbot, checkable=True)
    plain_tree, plain_delegate, _ = _tree(qtbot, checkable=False)
    ticked_index = ticked_tree.model().index(0, 0)
    plain_index = plain_tree.model().index(0, 0)

    option = QStyleOptionViewItem()
    option.rect = ticked_tree.visualRect(ticked_index)
    with_box = ticked_delegate.sizeHint(option, ticked_index).width()
    option.rect = plain_tree.visualRect(plain_index)
    without = plain_delegate.sizeHint(option, plain_index).width()

    box = _check_rect(ticked_tree, ticked_index)
    assert with_box - without >= box.width()
