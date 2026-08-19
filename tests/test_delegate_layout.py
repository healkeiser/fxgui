"""Layout tests for FXThumbnailDelegate's column 0.

Regression: the status label pill and the status dot are anchored to the row's
right edge, so they walk left as the column narrows. Nothing stopped column 0
from shrinking past the point where they reach the thumbnail, and they were
painted on top of the image.

The anchoring is not the bug and is unchanged. What these tests pin is the
floor under column 0: the thumbnail's full span plus the space the row's own
indicators take. `sizeHint` reports it, `apply_minimum_thumbnail_width`
enforces it against a hand-dragged header, and the paint helpers skip an
indicator rather than draw it on the image when a view has neither.

Set the ``FXGUI_SCREENSHOT_DIR`` environment variable to also dump the
grabbed rows as PNGs for human inspection.
"""

# Built-in
import os

# Third-party
import pytest
from qtpy.QtCore import QRect
from qtpy.QtGui import QColor, QFont, QFontMetrics
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
    title: str = "Asset 001",
    description: str = "A character asset, shading",
    children: int = 0,
    starred: bool = False,
    pill_color=PILL_COLOR,
    dot_color=DOT_COLOR,
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
        title: The item's display text.
        description: The item's description, or None for a one-line row.
        children: How many child rows to add, which draws the count badge.
        starred: Whether the item is starred.
        pill_color: What to store in the status label color role.
        dot_color: What to store in the status dot color role.
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
    # The style's own minimum would clamp the narrow widths the scans below
    # ask for, which is the very thing under test
    tree.header().setMinimumSectionSize(10)
    tree.setColumnWidth(0, width)
    tree.resize(width + 40, 160)

    delegate = FXThumbnailDelegate()
    for name, value in flags.items():
        setattr(delegate, name, value)
    tree.setItemDelegate(delegate)

    item = QTreeWidgetItem(tree, [title])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, thumbnail)
    if description:
        item.setData(0, FXThumbnailDelegate.DESCRIPTION_ROLE, description)
    if pill:
        item.setData(
            0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, pill_color
        )
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, "Ready")
    if dot:
        item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, dot_color)
    if starred:
        item.setData(0, FXThumbnailDelegate.STARRED_ROLE, True)
    for number in range(children):
        QTreeWidgetItem(item, [f"Child {number}"])
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


def _icon_rect(row_rect: QRect) -> QRect:
    """The decoration icon rect, as `_draw_icon_and_text` paints it."""

    size = 16
    return QRect(
        row_rect.left() + 6,
        row_rect.top() + (row_rect.height() - size) // 2,
        size,
        size,
    )


def _prefix_indicator_rects(row_rect: QRect, label_width: int, dot: bool):
    """The pill and dot rects as cb76d019 placed them, in literals.

    This is the pre-fix geometry the owner's screenshots were taken of, copied
    out of `_draw_status_dot` and `_draw_status_label` at that commit: an 8px
    dot 4px in from the row's right edge, at 4px from its top, and the pill
    6px to the left of the dot's slot whether or not the dot is shown, 14px
    tall from the same top.

    The dot's y here is cb76d019's, which the delegate no longer matches: the
    dot is centered in the pill's band now. Callers compare against the dot's
    x and size only.

    Args:
        row_rect: The rectangle of the entire row.
        label_width: The pill width, or 0 when it is not shown.
        dot: Whether the dot is shown.

    Returns:
        Tuple of (pill_rect, dot_rect), either None when not shown.
    """

    dot_size, dot_margin, label_margin, label_height = 8, 4, 6, 14
    dot_x = row_rect.right() - dot_size - dot_margin
    top = row_rect.top() + dot_margin

    pill_rect = None
    if label_width:
        pill_rect = QRect(
            dot_x - label_width - label_margin, top, label_width, label_height
        )

    dot_rect = None
    if dot:
        dot_rect = QRect(dot_x, top, dot_size, dot_size)

    return pill_rect, dot_rect


def _indicator_rects(delegate, option, index):
    """The pill and dot rects, as the paint helpers place them."""

    label_width, dot_width, _ = delegate._indicator_metrics(index)
    label_x, dot_x = delegate._indicator_left(
        option.rect, label_width, dot_width
    )
    band_top = option.rect.top() + delegate._INDICATOR_BAND_TOP

    pill_rect = None
    if label_width:
        pill_rect = QRect(
            label_x, band_top, label_width, delegate._INDICATOR_BAND_HEIGHT
        )

    dot_rect = None
    if dot_width:
        dot_rect = QRect(
            dot_x,
            band_top
            + (delegate._INDICATOR_BAND_HEIGHT - delegate._DOT_SIZE) // 2,
            dot_width,
            dot_width,
        )

    return pill_rect, dot_rect


def _is_near(color: QColor, reference: QColor, tolerance: int = 40) -> bool:
    """Whether a pixel is the reference color, allowing for antialiasing."""

    return (
        abs(color.red() - reference.red()) < tolerance
        and abs(color.green() - reference.green()) < tolerance
        and abs(color.blue() - reference.blue()) < tolerance
    )


def _indicator_hits(image, rect: QRect):
    """Every pill or dot pixel found inside a rect."""

    hits = []
    for y in range(rect.top(), rect.bottom() + 1):
        for x in range(rect.left(), rect.right() + 1):
            pixel = image.pixelColor(x, y)
            if _is_near(pixel, PILL_COLOR):
                hits.append(("pill", x, y))
            elif _is_near(pixel, DOT_COLOR):
                hits.append(("dot", x, y))
    return hits


###### The restored anchoring


@pytest.mark.parametrize(
    "pill, dot",
    [(True, True), (True, False), (False, True)],
)
@pytest.mark.parametrize("width", [420, 300, 220, 180])
def test_indicator_placement_matches_the_pre_fix_geometry(
    qtbot, pill, dot, width
):
    """The horizontal anchoring is cb76d019's, to the pixel.

    An intermediate round read the owner's screenshot as a request to move the
    indicators into a gutter between the thumbnail and the text. It was not:
    the screenshot showed this same right-anchored layout at its minimum
    column width. The rects compared against here are the pre-fix ones,
    written out in literals.

    The dot's vertical placement is the one deliberate departure, see
    `test_the_dot_is_centered_against_the_pill`, so only its x and its size
    are held to cb76d019 here.
    """

    tree, delegate, index = _tree_with_item(
        qtbot, pill=pill, dot=dot, width=width
    )
    option = _option_for(tree, index)
    label_width, _, _ = delegate._indicator_metrics(index)

    pill_rect, dot_rect = _indicator_rects(delegate, option, index)
    prefix_pill, prefix_dot = _prefix_indicator_rects(
        option.rect, label_width, dot
    )

    assert pill_rect == prefix_pill
    if dot:
        assert dot_rect.left() == prefix_dot.left()
        assert dot_rect.width() == prefix_dot.width()
        assert dot_rect.height() == prefix_dot.height()
    else:
        assert dot_rect is prefix_dot is None


def test_the_pill_sits_left_of_the_dot_at_the_rows_right_edge(qtbot):
    """Reading order is thumbnail, text, pill, dot."""

    tree, delegate, index = _tree_with_item(qtbot)
    option = _option_for(tree, index)
    pill_rect, dot_rect = _indicator_rects(delegate, option, index)

    assert pill_rect.right() < dot_rect.left()
    # An 8px dot, 4px in from the row's right edge
    assert dot_rect.left() == option.rect.right() - 8 - 4
    assert pill_rect.top() == option.rect.top() + 4
    # The text stops short of the pill, so nothing runs under it
    assert (
        delegate._content_right_limit(
            option, index, delegate._TEXT_RIGHT_MARGIN
        )
        <= pill_rect.left()
    )


def test_the_dot_is_centered_against_the_pill(qtbot):
    """The dot lines up with the middle of the pill rather than with its top.

    This is the one axis on which the pre-fix geometry is deliberately not
    restored: cb76d019 put an 8px dot and a 14px pill at the same y, leaving
    their centers 3px apart.
    """

    tree, delegate, index = _tree_with_item(qtbot)
    option = _option_for(tree, index)
    pill_rect, dot_rect = _indicator_rects(delegate, option, index)

    assert dot_rect.center().y() == pill_rect.center().y()
    # And it is no longer where cb76d019 put it
    _, prefix_dot = _prefix_indicator_rects(
        option.rect, delegate._indicator_metrics(index)[0], True
    )
    assert dot_rect.top() != prefix_dot.top()


def test_a_dot_sits_at_the_same_height_with_or_without_a_pill(qtbot):
    """The band is fixed geometry, so hiding the pill must not move the dot
    up or down. A column of rows, some with pills and some without, has to
    read as one straight line of dots."""

    with_pill, delegate, index = _tree_with_item(qtbot)
    without_pill, other_delegate, other_index = _tree_with_item(
        qtbot, pill=False
    )

    first = _indicator_rects(delegate, _option_for(with_pill, index), index)[1]
    second = _indicator_rects(
        other_delegate, _option_for(without_pill, other_index), other_index
    )[1]
    assert first == second


def test_the_pill_holds_its_slot_when_the_dot_is_hidden(qtbot):
    """The pill is placed against the dot's slot, occupied or not, so hiding
    the dot must not slide the pill right."""

    with_dot, delegate, index = _tree_with_item(qtbot)
    without_dot, other_delegate, other_index = _tree_with_item(
        qtbot, dot=False
    )

    first = _indicator_rects(delegate, _option_for(with_dot, index), index)[0]
    second = _indicator_rects(
        other_delegate, _option_for(without_dot, other_index), other_index
    )[0]
    assert first == second


###### What each row reserves


@pytest.mark.parametrize(
    "pill, dot, expect_pill, expect_dot",
    [
        (True, True, True, True),
        (True, False, True, False),
        (False, True, False, True),
        (False, False, False, False),
    ],
)
def test_reserved_footprint_matches_what_the_item_shows(
    qtbot, pill, dot, expect_pill, expect_dot
):
    """The footprint is how far in from the right edge the indicators reach,
    and zero when the item shows neither."""

    tree, delegate, index = _tree_with_item(qtbot, pill=pill, dot=dot)
    option = _option_for(tree, index)
    label_width, dot_width, footprint = delegate._indicator_metrics(index)

    assert bool(label_width) is expect_pill
    assert bool(dot_width) is expect_dot

    if not expect_pill and not expect_dot:
        assert footprint == 0
        return

    # The footprint has to reach the leftmost indicator pixel, measured from
    # the rect's exclusive right edge
    pill_rect, dot_rect = _indicator_rects(delegate, option, index)
    leftmost = (pill_rect or dot_rect).left()
    assert option.rect.left() + option.rect.width() - footprint == leftmost


def test_wider_pill_text_reserves_more_room(qtbot):
    """The pill grows with its text, so the footprint must grow with it too."""

    tree, delegate, index = _tree_with_item(qtbot)
    narrow = delegate._indicator_metrics(index)[2]

    tree.topLevelItem(0).setData(
        0,
        FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE,
        "Waiting for approval, second pass",
    )
    assert delegate._indicator_metrics(index)[2] > narrow


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
    label_width, dot_width, footprint = delegate._indicator_metrics(index)

    assert bool(label_width) is expect_pill
    assert bool(dot_width) is expect_dot
    if not expect_pill and not expect_dot:
        assert footprint == 0


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


###### The floor under column 0


def test_the_floor_is_the_thumbnail_plus_the_indicators(qtbot):
    """The owner's rule, in arithmetic: column 0 cannot go below the
    thumbnail's span plus the gap plus what the indicators take."""

    tree, delegate, index = _tree_with_item(qtbot)
    option = _option_for(tree, index)
    footprint = delegate._indicator_metrics(index)[2]

    # Bordered thumbnail (68 + 2) inside its 5px margins, then the 5px gutter
    assert delegate._row_minimum_width(option, index, True) == (
        85 + footprint
    )


@pytest.mark.parametrize(
    "pill, dot",
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_the_floor_follows_the_indicators_the_row_shows(qtbot, pill, dot):
    """A row showing neither indicator asks only for its thumbnail, a row
    showing both asks for the most. The owner's words: the minimum depends on
    the presence of the dot and/or the status pill."""

    tree, delegate, index = _tree_with_item(qtbot, pill=pill, dot=dot)
    option = _option_for(tree, index)
    floor = delegate._row_minimum_width(option, index, True)

    if not pill and not dot:
        assert floor == 80
        return

    assert floor > 85
    # At exactly the floor the leftmost indicator comes to rest on the text
    # origin, which is what the owner's screenshot showed
    row = QRect(option.rect.left(), option.rect.top(), floor, 50)
    label_width, dot_width, _ = delegate._indicator_metrics(index)
    label_x, dot_x = delegate._indicator_left(row, label_width, dot_width)
    leftmost = label_x if label_width else dot_x
    assert leftmost == delegate._text_left(option, index, True)


@pytest.mark.parametrize("thumbnail", [True, False])
@pytest.mark.parametrize(
    "pill, dot",
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_size_hint_never_reports_less_than_the_floor(
    qtbot, thumbnail, pill, dot
):
    """Whatever the text measures, the hint carries the floor, so anything
    sizing to contents lands at or above it."""

    tree, delegate, index = _tree_with_item(
        qtbot, thumbnail=thumbnail, pill=pill, dot=dot, title="A"
    )
    option = _option_for(tree, index)

    assert delegate.sizeHint(option, index).width() >= (
        delegate._row_minimum_width(option, index, thumbnail)
    )


def test_resize_to_contents_lands_at_or_above_the_floor(qtbot):
    """The path an artist actually takes: double-click the header divider."""

    tree, delegate, index = _tree_with_item(qtbot, title="A", description=None)
    tree.resizeColumnToContents(0)
    option = _option_for(tree, index)

    assert tree.columnWidth(0) >= delegate._row_minimum_width(
        option, index, True
    )


def test_measured_floor_is_the_widest_row_in_the_model(qtbot):
    """One column has to satisfy every row, so the widest pill wins."""

    tree, delegate, index = _tree_with_item(qtbot)
    narrow = FXThumbnailDelegate._measure_minimum_width(tree, 0)

    wide = QTreeWidgetItem(tree, ["Asset 002"])
    wide.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
    wide.setData(0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, PILL_COLOR)
    wide.setData(
        0,
        FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE,
        "Waiting for approval, second pass",
    )
    wide.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, DOT_COLOR)

    grown = FXThumbnailDelegate._measure_minimum_width(tree, 0)
    option = _option_for(tree, index)
    assert grown > narrow
    assert grown == delegate._row_minimum_width(
        option, tree.model().index(1, 0), True
    )


def test_a_column_can_be_dragged_under_the_floor_without_the_opt_in(qtbot):
    """The floor is opt-in, so this is what a view gets by default. It is
    also the proof that the test below measures the installed guard and not
    some clamp Qt applies on its own."""

    tree, delegate, index = _tree_with_item(qtbot)
    floor = FXThumbnailDelegate._measure_minimum_width(tree, 0)

    tree.header().resizeSection(0, floor - 40)
    assert tree.columnWidth(0) == floor - 40


def test_installed_floor_snaps_a_narrower_resize_back(qtbot):
    """`apply_minimum_thumbnail_width` is what stops a hand-dragged header,
    which no size hint can do."""

    tree, delegate, index = _tree_with_item(qtbot)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    floor = FXThumbnailDelegate._measure_minimum_width(tree, 0)

    for attempt in (floor - 1, floor - 40, 20):
        tree.header().resizeSection(0, attempt)
        assert tree.columnWidth(0) == floor

    # Wider than the floor is nobody's business but the user's
    tree.header().resizeSection(0, floor + 40)
    assert tree.columnWidth(0) == floor + 40


def test_installing_the_floor_lifts_an_already_narrow_column(qtbot):
    """A view narrower than its floor when the guard goes in is fixed then and
    there, rather than waiting for the next resize."""

    tree, delegate, index = _tree_with_item(qtbot, width=100)
    floor = FXThumbnailDelegate._measure_minimum_width(tree, 0)
    assert tree.columnWidth(0) < floor

    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    assert tree.columnWidth(0) == floor


def test_installing_the_floor_twice_leaves_one_handler(qtbot):
    """A widget rebuilt by a consumer must not stack duplicate handlers on
    the header's signal."""

    tree, delegate, index = _tree_with_item(qtbot)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    floor = FXThumbnailDelegate._measure_minimum_width(tree, 0)

    assert len(tree._fxgui_minimum_section_guards) == 1
    tree.header().resizeSection(0, floor - 30)
    assert tree.columnWidth(0) == floor


def test_the_floor_leaves_the_other_columns_alone(qtbot):
    """Why the header's own minimum could not serve: it is header-wide, so
    column 0's floor would be forced on every narrow column beside it."""

    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Status"])
    tree.header().setStretchLastSection(False)
    tree.header().setMinimumSectionSize(10)
    delegate = FXThumbnailDelegate()
    tree.setItemDelegate(delegate)
    item = QTreeWidgetItem(tree, ["Asset 001", "wip"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, PILL_COLOR)
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, "Ready")
    item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, DOT_COLOR)
    qtbot.addWidget(tree)
    tree.show()
    qtbot.waitExposed(tree)

    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    floor = FXThumbnailDelegate._measure_minimum_width(tree, 0)

    tree.header().resizeSection(1, 30)
    assert tree.columnWidth(1) == 30
    assert tree.columnWidth(0) == floor


def test_the_floor_survives_a_view_without_this_delegate(qtbot):
    """Installing it on a view that does not use the delegate does nothing
    rather than raising."""

    tree = QTreeWidget()
    tree.setHeaderLabels(["Name"])
    tree.header().setStretchLastSection(False)
    tree.header().setMinimumSectionSize(10)
    QTreeWidgetItem(tree, ["Plain"])
    qtbot.addWidget(tree)

    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    assert FXThumbnailDelegate._measure_minimum_width(tree, 0) == 0
    tree.header().resizeSection(0, 30)
    assert tree.columnWidth(0) == 30


###### The proof in pixels


def _scan_widths(floor: int):
    """Widths from generous, through the floor, to well under it."""

    return [floor + 80, floor + 1, floor, floor - 1, floor - 20, 40]


@pytest.mark.parametrize(
    "pill, dot, name",
    [
        (True, True, "pill_and_dot"),
        (True, False, "pill_only"),
        (False, True, "dot_only"),
        (False, False, "neither"),
    ],
)
@pytest.mark.parametrize("thumbnail", [True, False])
def test_no_indicator_pixel_lands_on_the_image(
    qtbot, pill, dot, name, thumbnail
):
    """Scan the thumbnail (or the decoration icon) of a rendered row and
    assert neither the pill color nor the dot color appears in it, at every
    width from generous through the floor and below.

    Above the floor the arithmetic keeps them apart. Below it, which is only
    reachable without the opt-in, the paint helpers skip an indicator rather
    than draw it on the image.
    """

    tree, delegate, index = _tree_with_item(
        qtbot,
        pill=pill,
        dot=dot,
        thumbnail=thumbnail,
        decoration=not thumbnail,
    )
    floor = delegate._row_minimum_width(
        _option_for(tree, index), index, thumbnail
    )

    for width in _scan_widths(floor):
        tree.setColumnWidth(0, width)
        tree.resize(width + 40, 160)
        qtbot.waitExposed(tree)
        image = tree.viewport().grab().toImage()
        kind = "thumb" if thumbnail else "icon"
        _save(image, f"delegate_{name}_{kind}_{width}.png")

        row = tree.visualRect(index)
        target = _thumbnail_rect(row) if thumbnail else _icon_rect(row)
        hits = _indicator_hits(image, target)
        assert not hits, (
            f"indicator pixels on the image at width {width}: {hits[:5]}"
        )


def test_the_pill_is_painted_at_the_floor_and_skipped_below_it(qtbot):
    """At the floor the pill is still there, immediately right of the
    thumbnail. That is the state the owner's screenshot showed."""

    tree, delegate, index = _tree_with_item(qtbot, dot=False)
    option = _option_for(tree, index)
    floor = delegate._row_minimum_width(option, index, True)

    tree.setColumnWidth(0, floor)
    tree.resize(floor + 40, 160)
    at_floor = tree.viewport().grab().toImage()
    row = tree.visualRect(index)
    assert _indicator_hits(at_floor, row), "the pill vanished at the floor"

    # The pill's left edge lands on the text origin, hard against the gutter
    pill_rect, _ = _indicator_rects(delegate, _option_for(tree, index), index)
    assert pill_rect.left() == delegate._text_left(
        _option_for(tree, index), index, True
    )

    # Far below the floor it is dropped rather than drawn on the image
    tree.setColumnWidth(0, floor - 40)
    tree.resize(floor, 160)
    below = tree.viewport().grab().toImage()
    assert not _indicator_hits(below, tree.visualRect(index))


###### The text clips, it does not elide


LONG_TITLE = "Asset 001 hero character with a very long name indeed"


def _title_band(tree, delegate, index, has_thumbnail: bool):
    """The x range and y range the title is painted in."""

    option = _option_for(tree, index)
    text_x = delegate._text_left(option, index, has_thumbnail)
    right_margin = (
        delegate._TEXT_RIGHT_MARGIN if has_thumbnail else delegate._ICON_MARGIN
    )
    right = delegate._content_right_limit(option, index, right_margin)
    return text_x, right, option.rect.top(), option.rect.bottom()


@pytest.mark.parametrize("thumbnail", [True, False])
def test_the_title_clips_instead_of_eliding(qtbot, thumbnail):
    """A narrowing column must reveal less of the title, not replace its tail
    with an ellipsis.

    The check is a comparison rather than a hunt for three dots: rendered at a
    narrow width, the title's pixels must be exactly the wide render's pixels
    cropped to the narrow text width. Clipping gives that by construction.
    Eliding cannot: it swaps the tail for an ellipsis, so the pixels differ.
    """

    wide_tree, wide_delegate, wide_index = _tree_with_item(
        qtbot,
        thumbnail=thumbnail,
        title=LONG_TITLE,
        description=None,
        width=600,
    )
    narrow_tree, narrow_delegate, narrow_index = _tree_with_item(
        qtbot,
        thumbnail=thumbnail,
        title=LONG_TITLE,
        description=None,
        width=300,
    )

    wide_image = wide_tree.viewport().grab().toImage()
    narrow_image = narrow_tree.viewport().grab().toImage()
    _save(narrow_image, f"delegate_clipped_title_{thumbnail}.png")

    wide_x, _, wide_top, _ = _title_band(
        wide_tree, wide_delegate, wide_index, thumbnail
    )
    narrow_x, narrow_right, narrow_top, narrow_bottom = _title_band(
        narrow_tree, narrow_delegate, narrow_index, thumbnail
    )
    assert wide_x == narrow_x, "the two rows must share a text origin"
    assert wide_top == narrow_top

    differences = 0
    ink = 0
    for y in range(narrow_top, narrow_bottom + 1):
        for x in range(narrow_x, narrow_right):
            narrow_pixel = narrow_image.pixelColor(x, y)
            if narrow_pixel != wide_image.pixelColor(x, y):
                differences += 1
            if not _is_near(narrow_pixel, QColor("#1e1e1e"), 30):
                ink += 1

    assert ink, "no title was painted, so the comparison proves nothing"
    assert not differences, (
        f"{differences} title pixels differ from the wide render, so the "
        "narrow row is not the same text clipped"
    )


@pytest.mark.parametrize("thumbnail", [True, False])
def test_the_title_reveals_more_as_the_column_widens(qtbot, thumbnail):
    """Step by step, which is what the owner asked for: more of the title
    with every pixel of column, no ellipsis eating the tail."""

    tree, delegate, index = _tree_with_item(
        qtbot, thumbnail=thumbnail, title=LONG_TITLE, description=None
    )

    seen = []
    for width in (200, 260, 320, 380):
        tree.setColumnWidth(0, width)
        tree.resize(width + 40, 160)
        image = tree.viewport().grab().toImage()
        text_x, right, top, bottom = _title_band(
            tree, delegate, index, thumbnail
        )
        ink = sum(
            1
            for y in range(top, bottom + 1)
            for x in range(text_x, right)
            if not _is_near(image.pixelColor(x, y), QColor("#1e1e1e"), 30)
        )
        seen.append(ink)

    assert seen == sorted(
        seen
    ), f"the title did not grow with the column: {seen}"
    assert seen[-1] > seen[0]


###### Sizing


def _available_text_width(tree, delegate, index, has_thumbnail: bool) -> int:
    """The width the paint path gives the title, for the current column."""

    option = _option_for(tree, index)
    text_x = delegate._text_left(option, index, has_thumbnail)
    right_margin = (
        delegate._TEXT_RIGHT_MARGIN if has_thumbnail else delegate._ICON_MARGIN
    )
    return delegate._content_right_limit(option, index, right_margin) - text_x


@pytest.mark.parametrize("thumbnail", [True, False])
def test_size_hint_grows_with_the_title_width(qtbot, thumbnail):
    """The hint has to carry the text, not just the furniture around it."""

    long_tree, delegate, long_index = _tree_with_item(
        qtbot, thumbnail=thumbnail, title=LONG_TITLE, description=None
    )
    short_tree, short_delegate, short_index = _tree_with_item(
        qtbot, thumbnail=thumbnail, title="Short", description=None
    )

    option = _option_for(long_tree, long_index)
    title_font = (
        delegate._title_font(option)
        if thumbnail
        else QFont(option.font)  # One-line rows paint the title unbolded
    )
    metrics = QFontMetrics(title_font)
    text_delta = metrics.horizontalAdvance(
        LONG_TITLE
    ) - metrics.horizontalAdvance("Short")

    hint_delta = (
        delegate.sizeHint(option, long_index).width()
        - short_delegate.sizeHint(
            _option_for(short_tree, short_index), short_index
        ).width()
    )
    assert hint_delta == text_delta


@pytest.mark.parametrize(
    "thumbnail, description, children, starred",
    [
        (True, None, 0, False),
        (True, "A character asset, shading in progress, pass two", 0, False),
        (True, None, 12, True),
        (False, None, 0, False),
        (False, "Two lines, because a description is set", 0, False),
        (False, None, 12, True),
    ],
)
def test_resize_to_contents_fits_the_whole_title(
    qtbot, thumbnail, description, children, starred
):
    """Regression: an artist sized the thumbnail column to contents and the
    title still came out short. `sizeHint` summed its parts while the paint
    path measured from `QRect.right()`, which is one pixel inside the rect,
    so the row was always a pixel short of the title it had just asked for.
    """

    tree, delegate, index = _tree_with_item(
        qtbot,
        thumbnail=thumbnail,
        title=LONG_TITLE,
        description=description,
        children=children,
        starred=starred,
    )
    tree.resizeColumnToContents(0)

    available = _available_text_width(tree, delegate, index, thumbnail)
    option = _option_for(tree, index)
    title_font = (
        delegate._title_font(option)
        if (thumbnail or description)
        else QFont(option.font)
    )
    assert available >= QFontMetrics(title_font).horizontalAdvance(LONG_TITLE)

    if description:
        # The description stacks under the title and shares its width
        plain = delegate.markdown_to_plain_text(description)
        description_metrics = QFontMetrics(delegate._description_font(option))
        assert available >= description_metrics.horizontalAdvance(plain)


def test_size_hint_covers_the_indicators_and_the_badge(qtbot):
    """Widening the pill or adding a badge must widen the hint by as much,
    or the text loses the room instead."""

    tree, delegate, index = _tree_with_item(
        qtbot, title=LONG_TITLE, description=None
    )
    option = _option_for(tree, index)
    base = delegate.sizeHint(option, index).width()
    base_footprint = delegate._indicator_metrics(index)[2]

    tree.topLevelItem(0).setData(
        0,
        FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE,
        "Waiting for approval, second pass",
    )
    grown = delegate.sizeHint(option, index).width()
    assert grown - base == (
        delegate._indicator_metrics(index)[2] - base_footprint
    )

    badge_tree, badge_delegate, badge_index = _tree_with_item(
        qtbot, title=LONG_TITLE, description=None, children=3
    )
    badge_option = _option_for(badge_tree, badge_index)
    assert badge_delegate.sizeHint(
        badge_option, badge_index
    ).width() - base == badge_delegate._child_count_width(badge_index)


###### Layout of thumbnail-less rows


@pytest.mark.parametrize("decoration", [True, False])
def test_thumbnail_less_rows_start_from_the_left_edge(qtbot, decoration):
    """Without a thumbnail there is no thumbnail gap to leave: the text
    follows the decoration icon, or the row's left edge when there is none."""

    tree, delegate, index = _tree_with_item(
        qtbot, thumbnail=False, decoration=decoration
    )
    option = _option_for(tree, index)

    expected = option.rect.left() + delegate._ICON_MARGIN
    if decoration:
        expected += delegate._ICON_SIZE + delegate._ICON_MARGIN
    assert delegate._text_left(option, index, False) == expected
    assert delegate._content_left(option, index, False) == expected


def test_global_thumbnail_flag_off_keeps_the_left_edge_layout(qtbot):
    """`show_thumbnail = False` must not leave room for an image nobody
    paints."""

    tree, delegate, index = _tree_with_item(qtbot, show_thumbnail=False)
    option = _option_for(tree, index)

    assert delegate._has_thumbnail(index) is False
    assert delegate._text_left(option, index, False) == (
        option.rect.left() + delegate._ICON_MARGIN
    )


###### Color roles


@pytest.mark.parametrize("role_value", ["#00ff00", DOT_COLOR])
def test_color_roles_accept_a_string(qtbot, role_value):
    """A hex string in a color role is the obvious thing for a consumer to
    store, so it renders rather than raising."""

    tree, delegate, index = _tree_with_item(
        qtbot, pill=False, dot_color=role_value
    )
    assert delegate._indicator_metrics(index)[1] == delegate._DOT_SIZE

    image = tree.viewport().grab().toImage()
    _save(image, "delegate_string_color.png")
    assert _indicator_hits(image, tree.visualRect(index))


@pytest.mark.parametrize(
    "role_value", ["not a color", "", 42, object(), QRect()]
)
def test_unusable_color_roles_hide_without_raising(qtbot, role_value):
    """Anything a QColor cannot be made of hides its indicator. It used to
    raise mid-paint, and it would raise in sizeHint too now that the hint
    measures the indicators."""

    tree, delegate, index = _tree_with_item(
        qtbot, pill_color=role_value, dot_color=role_value
    )
    label_width, dot_width, footprint = delegate._indicator_metrics(index)

    assert (label_width, dot_width, footprint) == (0, 0, 0)
    # Neither painting nor sizing may raise on the way through
    assert not tree.viewport().grab().toImage().isNull()
    assert delegate.sizeHint(_option_for(tree, index), index).height() == 50
