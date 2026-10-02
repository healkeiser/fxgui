"""Every item view draws its icons and branch chevrons in one 16 px box."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect, QSize
from qtpy.QtGui import QImage, QPainter, QRegion
from qtpy.QtWidgets import (
    QListWidget,
    QProxyStyle,
    QStyle,
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


def test_a_completer_list_in_a_host_window_takes_the_16_px_box(qtbot, host_root):
    from qtpy.QtWidgets import QCompleter, QLineEdit

    field = QLineEdit(host_root)
    host_root.layout().addWidget(field)
    completer = QCompleter(["sh0010", "sh0020"], field)
    field.setCompleter(completer)
    host_root.show()
    qtbot.waitExposed(host_root)
    field.setFocus()
    completer.complete()
    popup = completer.popup()
    qtbot.waitUntil(popup.isVisible)
    assert popup.iconSize() == QSize(_BOX, _BOX)
    popup.hide()


class _TallRows(fxwidgets.FXThumbnailDelegate):
    """A thumbnail delegate whose rows are `height` pixels tall."""

    height = 50

    def sizeHint(self, option, index):
        return QSize(super().sizeHint(option, index).width(), self.height)


class _WideIndent(QProxyStyle):
    """A platform style that indents a tree 30 px, as Windows 11's does."""

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PM_TreeViewIndentation:
            return 30
        return super().pixelMetric(metric, option, widget)


def _chevron(qtbot, theme, ratio, height=None, wide=False):
    """Return the ink extent and centre offset of a parent row's chevron.

    `height` gives the tree thumbnail rows that tall; `wide` puts it under a
    platform style indenting 30 px, under fxgui's own, as a host window does.
    """
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    if wide:
        style = fxstyle.FXProxyStyle(_WideIndent())
        style.setParent(tree)
        tree.setStyle(style)
    if height is not None:
        delegate = _TallRows(tree)
        delegate.height = height
        tree.setItemDelegate(delegate)
    parent = QTreeWidgetItem(tree, ["houdini"])
    QTreeWidgetItem(parent, ["test"])
    tree.expandAll()
    window = themed_window(qtbot, theme, tree, size=(400, 300))
    row = tree.visualRect(tree.model().index(0, 0))
    if height is not None:
        assert row.height() == height
    branch = QRect(0, row.top(), row.left(), row.height())
    image = QImage(branch.size() * ratio, QImage.Format_ARGB32)
    image.setDevicePixelRatio(ratio)
    image.fill(0)
    tree.viewport().render(image, QPoint(), QRegion(branch))
    window.close()
    ink = fxstyle.colors().icon
    ys = [y for x in range(image.width()) for y in range(image.height())
          if near(image.pixelColor(x, y), ink, 24)]
    offset = (min(ys) + max(ys)) / 2 - (image.height() - 1) / 2
    return _extent(image, ink), offset


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("height", [24, 50, 80])
@pytest.mark.parametrize("wide", [False, True])
@pytest.mark.parametrize("ratio", [1.0, 1.5])
def test_a_branch_chevron_stays_16_px_in_a_tall_thumbnail_row(
        qtbot, theme, height, wide, ratio):
    browse, _offset = _chevron(qtbot, theme, ratio)
    drawn, offset = _chevron(qtbot, theme, ratio, height, wide)
    assert _same_box(drawn, browse), (drawn, browse)
    # Centred down the row, to a device pixel.
    assert abs(offset) <= 1, offset
