"""A hovered row reads off whatever it sits on, as a hovered tab does."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate

from _helpers import hover, themed_window


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_hover_fill_reads_on_every_ground_a_row_sits_on(theme):
    fxstyle.apply_theme(theme)
    colors = fxstyle.colors()
    for ground in ("surface", "surface_sunken", "well"):
        ratio = fxstyle.get_contrast_ratio(
            colors.state_hover, getattr(colors, ground))
        assert ratio >= fxstyle.STATE_MIN_CONTRAST, (ground, round(ratio, 3))


def _hovered_fill(qtbot, window, tree, item):
    rect = tree.visualItemRect(item)
    hover(qtbot, tree.viewport(), rect.center())
    # Between the text and the child count badge, inside the row's fill.
    point = tree.viewport().mapTo(
        window, QPoint(rect.right() - 40, rect.center().y()))
    return window.grab().toImage().pixelColor(point).name()


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_hovered_card_row_reads_off_its_own_card_at_every_depth(
        qtbot, theme):
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    FXThumbnailDelegate.apply_transparent_selection(tree)
    fxstyle.apply_theme(theme)
    parent, items = tree, []
    for depth in range(fxstyle.DEPTH_CAP + 1):
        item = QTreeWidgetItem(parent, [f"depth {depth}"])
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
        item.setBackground(0, QColor(
            fxstyle.depth_shade(fxstyle.colors().surface, depth)))
        items.append(item)
        parent = item
    tree.expandAll()
    window = themed_window(qtbot, theme, tree, size=(320, 260))
    colors = fxstyle.colors()
    for depth, item in enumerate(items):
        card = item.background(0).color().name()
        fill = _hovered_fill(qtbot, window, tree, item)
        ratio = fxstyle.get_contrast_ratio(fill, card)
        assert ratio >= fxstyle.STATE_MIN_CONTRAST, (depth, card, fill)
        assert fill != colors.accent_primary.lower()
        assert fxstyle.get_contrast_ratio(colors.text, fill) >= (
            fxstyle.TEXT_CONTRAST), (depth, fill)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_hovered_plain_row_reads_off_the_view(qtbot, theme):
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    items = [QTreeWidgetItem(tree, [f"Row {index}"]) for index in range(3)]
    window = themed_window(qtbot, theme, tree)
    ground = fxstyle.colors().surface_sunken
    fill = _hovered_fill(qtbot, window, tree, items[1])
    assert fill == fxstyle.colors().state_hover.lower()
    assert fxstyle.get_contrast_ratio(fill, ground) >= (
        fxstyle.STATE_MIN_CONTRAST)
