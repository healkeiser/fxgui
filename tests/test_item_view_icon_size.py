"""Every item view draws its icons and branch chevrons in one 16 px box."""

# Third-party
import pytest
from qtpy.QtCore import QRect, QSize
from qtpy.QtGui import QImage, QPainter
from qtpy.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxicons, fxstyle, fxwidgets

from _helpers import near, themed_window

_BOX = 16


def _extent(image, ink: str):
    """Return the (width, height) of the pixels near `ink` in `image`."""
    xs, ys = [], []
    for x in range(image.width()):
        for y in range(image.height()):
            if near(image.pixelColor(x, y), ink, 24):
                xs.append(x)
                ys.append(y)
    return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) if xs else None


def _glyph(name: str, ground) -> tuple:
    """Return the ink extent of `name` drawn at the 16 px box on `ground`."""
    image = QImage(_BOX, _BOX, QImage.Format_ARGB32)
    image.fill(ground)
    painter = QPainter(image)
    painter.drawPixmap(0, 0, fxicons.get_icon(name).pixmap(QSize(_BOX, _BOX)))
    painter.end()
    return _extent(image, fxstyle.colors().icon)


def _same_box(drawn, glyph) -> bool:
    """Return whether two extents match to a pixel of antialiasing."""
    return drawn is not None and all(
        abs(one - two) <= 1 for one, two in zip(drawn, glyph))


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("kind", ["list", "tree"])
def test_an_item_icon_is_drawn_in_the_16_px_box(qtbot, theme, kind):
    if kind == "list":
        view = QListWidget()
        view.addItem(QListWidgetItem(fxicons.get_icon("folder"), ""))
    else:
        view = QTreeWidget()
        view.setHeaderHidden(True)
        view.setRootIsDecorated(False)
        QTreeWidgetItem(view, [""]).setIcon(0, fxicons.get_icon("folder"))
    window = themed_window(qtbot, theme, view)
    rect = view.visualRect(view.model().index(0, 0))

    image = view.viewport().grab(rect).toImage()
    drawn = _extent(image, fxstyle.colors().icon)
    glyph = _glyph("folder", image.pixelColor(image.width() - 2, 1))

    assert _same_box(drawn, glyph), (drawn, glyph)
    window.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("delegate", [False, True])
def test_a_branch_chevron_is_drawn_in_the_16_px_box(qtbot, theme, delegate):
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    if delegate:
        tree.setItemDelegate(fxwidgets.FXThumbnailDelegate(tree))
    parent = QTreeWidgetItem(tree, ["seq010"])
    QTreeWidgetItem(parent, ["sh0010"])
    tree.expandAll()
    window = themed_window(qtbot, theme, tree)
    row = tree.visualRect(tree.model().index(0, 0))
    branch = QRect(0, row.top(), row.left(), row.height())

    image = tree.viewport().grab(branch).toImage()
    drawn = _extent(image, fxstyle.colors().icon)
    glyph = _glyph("expand_more", image.pixelColor(1, 1))

    assert _same_box(drawn, glyph), (drawn, glyph)
    window.close()
