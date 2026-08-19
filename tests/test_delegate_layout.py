"""Layout tests for FXThumbnailDelegate's column 0.

Regression: the status label pill and the status dot were anchored to the
row's right edge, so on a narrow column 0 they were painted on top of the
thumbnail (pill over its left half, dot over its top-right corner). The
space reserved for them lived on the other side of the text, so no amount of
reserving could keep them off the image.

They are now laid out in a region reserved between the thumbnail (or the
decoration icon, on thumbnail-less rows) and the text, and the region's width
comes from what the item actually shows. These tests pin both halves: the
rects the paint code uses must never touch the thumbnail, and the reserved
width must match what is drawn.

Set the ``FXGUI_SCREENSHOT_DIR`` environment variable to also dump the
grabbed rows as PNGs for human inspection.
"""

# Built-in
import os

# Third-party
import pytest
from qtpy.QtCore import QRect
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui.fxwidgets import FXThumbnailDelegate


# Colors no theme uses, so a pixel of either one is unambiguous
PILL_COLOR = QColor("#ff00ff")
DOT_COLOR = QColor("#00ff00")


def _save(image, name: str) -> None:
    directory = os.environ.get("FXGUI_SCREENSHOT_DIR")
    if directory:
        os.makedirs(directory, exist_ok=True)
        image.save(os.path.join(directory, name))


def _tree_with_item(
    qtbot,
    thumbnail: bool = True,
    pill: bool = True,
    dot: bool = True,
    decoration: bool = False,
    width: int = 420,
    **flags,
):
    """Build a one-row tree using the delegate.

    Args:
        qtbot: The pytest-qt bot.
        thumbnail: Whether the item enables its thumbnail.
        pill: Whether the item carries status label color and text.
        dot: Whether the item carries a status dot color.
        decoration: Whether the item carries a decoration icon.
        width: The width of column 0.
        **flags: Delegate-global overrides, keyed by property name.

    Returns:
        Tuple of (tree, delegate, index).
    """

    tree = QTreeWidget()
    tree.setHeaderLabels(["Name"])
    tree.setRootIsDecorated(False)
    # Without this the single column stretches to the viewport and the width
    # asked for here is ignored
    tree.header().setStretchLastSection(False)
    tree.setColumnWidth(0, width)
    tree.resize(width + 40, 160)

    delegate = FXThumbnailDelegate()
    for name, value in flags.items():
        setattr(delegate, name, value)
    tree.setItemDelegate(delegate)

    item = QTreeWidgetItem(tree, ["Asset 001"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, thumbnail)
    item.setData(
        0, FXThumbnailDelegate.DESCRIPTION_ROLE, "A character asset, shading"
    )
    if pill:
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, PILL_COLOR)
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, "Ready")
    if dot:
        item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, DOT_COLOR)
    if decoration:
        # A pixmap-backed icon, so the test does not need the icons submodule
        from qtpy.QtGui import QIcon, QPixmap

        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor("#4040ff"))
        item.setIcon(0, QIcon(pixmap))

    qtbot.addWidget(tree)
    tree.show()
    qtbot.waitExposed(tree)

    return tree, delegate, tree.model().index(0, 0)


def _option_for(tree, index) -> QStyleOptionViewItem:
    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    return option


def _thumbnail_rect(row_rect: QRect) -> QRect:
    """The bordered thumbnail rect, as `_draw_thumbnail_content` paints it.

    Spelled out in literals rather than read off the delegate, so the pixel
    scans below stay a black-box check of the documented geometry: a 68x38
    thumbnail plus a 1px border, inset by a 5px margin, centered vertically.
    """

    width, height = 68 + 2, 38 + 2
    return QRect(
        row_rect.left() + 5,
        row_rect.top() + (row_rect.height() - height) // 2,
        width,
        height,
    )


def _indicator_rects(delegate, option, index, has_thumbnail: bool):
    """The pill and dot rects, as the paint helpers place them."""

    label_width, dot_width, _ = delegate._indicator_metrics(index)
    x = delegate._indicator_region_left(option, index, has_thumbnail)
    band_top = option.rect.top() + delegate._INDICATOR_BAND_TOP

    pill_rect = None
    if label_width:
        pill_rect = QRect(
            x, band_top, label_width, delegate._INDICATOR_BAND_HEIGHT
        )
        x += label_width + delegate._INDICATOR_SPACING

    dot_rect = None
    if dot_width:
        dot_rect = QRect(
            x,
            band_top
            + (delegate._INDICATOR_BAND_HEIGHT - delegate._DOT_SIZE) // 2,
            dot_width,
            dot_width,
        )

    return pill_rect, dot_rect


@pytest.mark.parametrize(
    "pill, dot",
    [(True, True), (True, False), (False, True)],
)
def test_indicators_never_touch_the_thumbnail(qtbot, pill, dot):
    """The thumbnail keeps its full space: no indicator may overlap it."""

    tree, delegate, index = _tree_with_item(qtbot, pill=pill, dot=dot)
    option = _option_for(tree, index)
    thumbnail = _thumbnail_rect(option.rect)
    pill_rect, dot_rect = _indicator_rects(delegate, option, index, True)

    for name, rect in (("pill", pill_rect), ("dot", dot_rect)):
        if rect is None:
            continue
        assert not thumbnail.intersects(rect), f"{name} overlaps the thumbnail"
        assert rect.left() >= thumbnail.right(), f"{name} is not to its right"


def test_pill_comes_first_and_the_dot_follows_it(qtbot):
    """Reading order is thumbnail, pill, dot, text."""

    tree, delegate, index = _tree_with_item(qtbot)
    option = _option_for(tree, index)
    pill_rect, dot_rect = _indicator_rects(delegate, option, index, True)

    assert dot_rect.left() >= pill_rect.right()
    # Both sit in one band near the row's top, the dot centered against
    # the pill
    assert pill_rect.top() == option.rect.top() + 4
    assert dot_rect.center().y() == pill_rect.center().y()


@pytest.mark.parametrize(
    "pill, dot, expect_pill, expect_dot",
    [
        (True, True, True, True),
        (True, False, True, False),
        (False, True, False, True),
        (False, False, False, False),
    ],
)
def test_reserved_width_matches_what_the_item_shows(
    qtbot, pill, dot, expect_pill, expect_dot
):
    """The region is as wide as the indicators actually drawn, and zero when
    the item shows neither."""

    tree, delegate, index = _tree_with_item(qtbot, pill=pill, dot=dot)
    label_width, dot_width, region_width = delegate._indicator_metrics(index)

    assert bool(label_width) is expect_pill
    assert bool(dot_width) is expect_dot

    if not expect_pill and not expect_dot:
        assert region_width == 0
        return

    expected = label_width + dot_width + delegate._INDICATOR_SPACING
    if label_width and dot_width:
        expected += delegate._INDICATOR_SPACING
    assert region_width == expected


def test_wider_pill_text_reserves_more_room(qtbot):
    """The pill grows with its text, so the region must grow with it too."""

    tree, delegate, index = _tree_with_item(qtbot)
    narrow = delegate._indicator_metrics(index)[2]

    tree.topLevelItem(0).setData(
        0,
        FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE,
        "Waiting for approval, second pass",
    )
    assert delegate._indicator_metrics(index)[2] > narrow


def test_text_origin_is_unchanged_when_no_indicator_is_shown(qtbot):
    """A row with neither indicator must lay out exactly as it did before the
    region existed: text right after the thumbnail, no phantom gap."""

    tree, delegate, index = _tree_with_item(qtbot, pill=False, dot=False)
    option = _option_for(tree, index)

    region_left = delegate._indicator_region_left(option, index, True)
    # Bordered thumbnail (68 + 2) inside its 5px margins, plus the 5px gutter
    assert region_left == option.rect.left() + 85
    assert delegate._indicator_metrics(index)[2] == 0


@pytest.mark.parametrize(
    "flags, expect_pill, expect_dot",
    [
        ({"show_status_dot": False}, True, False),
        ({"show_status_label": False}, False, True),
        ({"show_status_dot": False, "show_status_label": False}, False, False),
    ],
)
def test_delegate_global_flags_gate_the_reservation(
    qtbot, flags, expect_pill, expect_dot
):
    """A globally hidden indicator reserves nothing, exactly as it draws
    nothing. Both display modes that exist in production live here."""

    tree, delegate, index = _tree_with_item(qtbot, **flags)
    label_width, dot_width, region_width = delegate._indicator_metrics(index)

    assert bool(label_width) is expect_pill
    assert bool(dot_width) is expect_dot
    if not expect_pill and not expect_dot:
        assert region_width == 0


@pytest.mark.parametrize(
    "role, expect_pill, expect_dot",
    [
        (FXThumbnailDelegate.STATUS_DOT_VISIBLE_ROLE, True, False),
        (FXThumbnailDelegate.STATUS_LABEL_VISIBLE_ROLE, False, True),
    ],
)
def test_per_item_roles_gate_the_reservation(
    qtbot, role, expect_pill, expect_dot
):
    """Setting a per-item visibility role to False also frees its room."""

    tree, delegate, index = _tree_with_item(qtbot)
    tree.topLevelItem(0).setData(0, role, False)
    label_width, dot_width, _ = delegate._indicator_metrics(index)

    assert bool(label_width) is expect_pill
    assert bool(dot_width) is expect_dot


@pytest.mark.parametrize("decoration", [True, False])
def test_thumbnail_less_rows_start_from_the_left_edge(qtbot, decoration):
    """Without a thumbnail there is no thumbnail gap to leave: indicators
    follow the decoration icon, or the row's left edge when there is none."""

    tree, delegate, index = _tree_with_item(
        qtbot, thumbnail=False, decoration=decoration
    )
    option = _option_for(tree, index)
    region_left = delegate._indicator_region_left(option, index, False)

    expected = option.rect.left() + delegate._ICON_MARGIN
    if decoration:
        expected += delegate._ICON_SIZE + delegate._ICON_MARGIN
    assert region_left == expected


def test_global_thumbnail_flag_off_keeps_the_left_edge_layout(qtbot):
    """`show_thumbnail = False` must not leave room for an image nobody
    paints."""

    tree, delegate, index = _tree_with_item(qtbot, show_thumbnail=False)
    option = _option_for(tree, index)

    assert delegate._has_thumbnail(index) is False
    assert delegate._indicator_region_left(
        option, index, False
    ) == option.rect.left() + delegate._ICON_MARGIN


@pytest.mark.parametrize("width", [420, 200, 130, 110, 90])
@pytest.mark.parametrize(
    "pill, dot, name",
    [
        (True, True, "pill_and_dot"),
        (True, False, "pill_only"),
        (False, True, "dot_only"),
    ],
)
def test_no_indicator_pixel_lands_on_the_thumbnail(
    qtbot, pill, dot, name, width
):
    """The proof in pixels: scan the thumbnail rect of a rendered row and
    assert neither the pill color nor the dot color appears in it.

    The narrow widths are the ones that used to fail. Right-anchored
    indicators walked left into the image as the column shrank, so anything
    under roughly 140px painted the pill on the thumbnail.
    """

    tree, delegate, index = _tree_with_item(
        qtbot, pill=pill, dot=dot, width=width
    )
    image = tree.grab().toImage()
    _save(image, f"delegate_{name}_{width}.png")

    thumbnail = _thumbnail_rect(tree.visualRect(index))
    hits = []
    for y in range(thumbnail.top(), thumbnail.bottom() + 1):
        for x in range(thumbnail.left(), thumbnail.right() + 1):
            pixel = image.pixelColor(x, y)
            if _is_near(pixel, PILL_COLOR):
                hits.append(("pill", x, y))
            elif _is_near(pixel, DOT_COLOR):
                hits.append(("dot", x, y))

    assert not hits, f"indicator pixels inside the thumbnail: {hits[:5]}"


def _is_near(color: QColor, reference: QColor, tolerance: int = 40) -> bool:
    """Whether a pixel is the reference color, allowing for antialiasing."""

    return (
        abs(color.red() - reference.red()) < tolerance
        and abs(color.green() - reference.green()) < tolerance
        and abs(color.blue() - reference.blue()) < tolerance
    )


def test_narrow_column_drops_indicators_instead_of_drawing_on_the_image(qtbot):
    """When the row is too narrow for the region, an indicator is skipped
    rather than painted over the thumbnail. `sizeHint` reserves the region, so
    a view that sizes to contents has the room."""

    tree, delegate, index = _tree_with_item(qtbot, width=110)
    option = _option_for(tree, index)
    label_width, _, region_width = delegate._indicator_metrics(index)
    region_left = delegate._indicator_region_left(option, index, True)

    # The row cannot fit the region the item asks for
    assert region_left + region_width > option.rect.right()
    assert delegate.sizeHint(option, index).width() >= (
        region_left - option.rect.left() + region_width
    )

    # The pill is the wide one, so it is the one that cannot fit here
    assert region_left + label_width > option.rect.right()
