"""The row size scale: `fxstyle.apply_row_size` and the rows it shapes."""

# Third-party
import pytest
from qtpy.QtCore import QRect
from qtpy.QtGui import QColor, QIcon, QPixmap
from qtpy.QtWidgets import QStyleOptionViewItem, QTreeWidget, QTreeWidgetItem

# Internal
from fxgui import fxconfig, fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate

from _helpers import delegate_tree, near

DOT = QColor("#00ff00")
MARK = QColor("#ff00ff")
ICON = QColor("#4040ff")


@pytest.mark.parametrize("name", sorted(fxstyle.ROW_SIZES))
def test_apply_row_size_sets_the_height(set_row_size, name):
    assert set_row_size(name) == name
    assert fxstyle.row_size() == name
    assert fxstyle.row_height() == fxstyle.ROW_SIZES[name]


def test_the_row_size_is_saved_and_read_back(set_row_size):
    set_row_size("small")
    assert fxconfig.get_value("rows/size") == "small"
    # A fresh process reads it from the settings, not the cache.
    fxstyle._row_size = None
    assert fxstyle.row_size() == "small"


def test_an_unknown_row_size_is_refused(set_row_size):
    set_row_size("big")
    with pytest.raises(ValueError):
        fxstyle.apply_row_size("huge")
    assert fxstyle.row_size() == "big"


def test_the_default_row_size_is_normal():
    assert fxstyle.row_size() == "normal"
    assert fxstyle.row_height() == fxstyle.ROW_SIZES["normal"]


def test_a_live_tree_follows_the_row_size(qtbot, app_root, set_row_size):
    tree = QTreeWidget(app_root)
    app_root.layout().addWidget(tree)
    item = QTreeWidgetItem(tree, ["Row"])
    app_root.resize(300, 300)
    app_root.show()
    qtbot.waitExposed(app_root)
    for name in ("small", "big", "normal"):
        set_row_size(name)
        qtbot.waitUntil(
            lambda: tree.visualItemRect(item).height() == fxstyle.row_height()
        )


@pytest.mark.parametrize("name", sorted(fxstyle.ROW_SIZES))
def test_the_thumbnail_is_16_9_and_fits_the_row(qtbot, set_row_size, name):
    set_row_size(name)
    tree, delegate, item = delegate_tree(qtbot, ["Asset"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
    width, height = delegate._THUMBNAIL_WIDTH, delegate._THUMBNAIL_HEIGHT
    assert abs(width - height * 16 / 9) <= 0.5
    outer = height + delegate._THUMBNAIL_BORDER
    assert outer + delegate._THUMBNAIL_MARGIN * 2 <= fxstyle.row_height()
    index = tree.model().index(0, 0)
    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    assert delegate.sizeHint(option, index).height() == fxstyle.row_height()


@pytest.mark.parametrize("name, shown", [("small", False), ("normal", True)])
def test_the_description_hides_in_a_small_row(
    qtbot, set_row_size, name, shown
):
    set_row_size(name)
    tree, delegate, item = delegate_tree(qtbot, ["Asset"])
    item.setData(0, FXThumbnailDelegate.DESCRIPTION_ROLE, "A character")
    index = tree.model().index(0, 0)
    assert (delegate._description(index) == "A character") is shown


def _hit_rows(image, rect: QRect, color: QColor) -> list:
    """Every y in `rect` holding a pixel of `color`."""
    return sorted(
        {
            y
            for y in range(rect.top(), rect.bottom() + 1)
            for x in range(rect.left(), rect.right() + 1)
            if near(image.pixelColor(x, y), color, 40)
        }
    )


def _plain_tree(qtbot, **roles):
    tree, delegate, item = delegate_tree(qtbot, ["Asset"], height=160)
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    for role, value in roles.items():
        item.setData(0, getattr(FXThumbnailDelegate, role), value)
    return tree, item


def _centre(ys: list) -> float:
    return (ys[0] + ys[-1]) / 2


def test_a_big_row_without_thumbnail_centres_its_status(qtbot, set_row_size):
    set_row_size("big")
    tree, item = _plain_tree(
        qtbot,
        STATUS_DOT_COLOR_ROLE=DOT,
        STATUS_LABEL_COLOR_ROLE=MARK,
        STATUS_LABEL_TEXT_ROLE="Ready",
    )
    row = tree.visualItemRect(item)
    assert row.height() == fxstyle.ROW_SIZES["big"]
    image = tree.viewport().grab().toImage()
    middle = row.top() + row.height() / 2
    for color in (DOT, MARK):
        ys = _hit_rows(image, row, color)
        assert ys, color.name()
        assert abs(_centre(ys) - middle) <= 1.5, (color.name(), ys, middle)


def test_a_big_row_without_thumbnail_centres_its_child_count(
    qtbot, set_row_size
):
    set_row_size("big")
    counted, parent = _plain_tree(qtbot)
    QTreeWidgetItem(parent, ["child"])
    bare, _ = _plain_tree(qtbot)
    row = counted.visualItemRect(parent)
    strip = QRect(row.right() - 40, row.top(), 40, row.height())
    shown = counted.viewport().grab().toImage()
    plain = bare.viewport().grab().toImage()
    ys = sorted(
        {
            y
            for y in range(strip.top(), strip.bottom() + 1)
            for x in range(strip.left(), strip.right() + 1)
            if shown.pixel(x, y) != plain.pixel(x, y)
        }
    )
    # The digits' ink sits inside the centred text box, not the bottom one.
    box = FXThumbnailDelegate._CHILD_COUNT_HEIGHT
    top = row.top() + (row.height() - box) // 2
    assert ys and top <= ys[0] and ys[-1] < top + box, (ys, top)


def test_the_overlay_stays_inside_a_small_thumbnail(qtbot, set_row_size):
    set_row_size("small")
    tree, delegate, item = delegate_tree(qtbot, ["Asset"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
    pixmap = QPixmap(16, 16)
    pixmap.fill(ICON)
    item.setIcon(0, QIcon(pixmap))
    row = tree.visualItemRect(item)
    image = tree.viewport().grab().toImage()
    outer_w = delegate._THUMBNAIL_WIDTH + delegate._THUMBNAIL_BORDER
    outer_h = delegate._THUMBNAIL_HEIGHT + delegate._THUMBNAIL_BORDER
    thumb = QRect(
        row.left() + delegate._THUMBNAIL_MARGIN,
        row.top() + (row.height() - outer_h) // 2,
        outer_w,
        outer_h,
    )
    hits = [
        (x, y)
        for y in range(row.top(), row.bottom() + 1)
        for x in range(row.left(), row.right() + 1)
        if near(image.pixelColor(x, y), ICON, 40)
    ]
    assert hits
    assert all(thumb.contains(x, y) for x, y in hits), (thumb, hits[:5])


@pytest.mark.parametrize("name", ["normal", "big"])
def test_a_described_row_is_as_tall_as_a_plain_one(qtbot, set_row_size, name):
    """Two lines that fit the size keep every row of it one height."""
    set_row_size(name)
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    delegate = FXThumbnailDelegate(tree)
    tree.setItemDelegate(delegate)
    plain = QTreeWidgetItem(["shot_010"])
    described = QTreeWidgetItem(["shot_020"])
    described.setData(0, FXThumbnailDelegate.DESCRIPTION_ROLE, "a note")
    tree.addTopLevelItems([plain, described])
    option = QStyleOptionViewItem()
    option.initFrom(tree)
    heights = {
        delegate.sizeHint(option, tree.indexFromItem(item)).height()
        for item in (plain, described)
    }
    assert heights == {fxstyle.ROW_SIZES[name]}
