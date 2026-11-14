"""FXThumbnailDelegate's status label: a neutral tag, a kept case, a readable mark."""

# Third-party
from qtpy.QtCore import QRect, Qt
from qtpy.QtGui import QColor, QFontMetrics, QPalette
from qtpy.QtWidgets import QStyleOptionViewItem, QTreeWidget, QTreeWidgetItem

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate


# A colour no theme uses, so it reads 3.14:1 on white and is never stepped.
PILL_COLOR = QColor("#ff00ff")
LONG_TITLE = "Asset 001 hero character with a very long name indeed"


def _tree_with_item(
    qtbot,
    text: str = "Ready",
    color=None,
    title: str = "Asset 001",
    thumbnail: bool = False,
    width: int = 420,
    **roles,
):
    """Build a one-row tree whose item carries a status label and no dot.

    Args:
        qtbot: The pytest-qt bot.
        text: The status label's words.
        color: What to store in the label's colour role; None leaves it unset.
        title: The item's display text.
        thumbnail: Whether the item enables its thumbnail.
        width: The width of column 0.
        **roles: Extra item roles, keyed by the delegate's attribute name.

    Returns:
        Tuple of (tree, delegate, index).
    """
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name"])
    tree.setRootIsDecorated(False)
    tree.header().setStretchLastSection(False)
    tree.header().setMinimumSectionSize(10)
    tree.setColumnWidth(0, width)
    tree.resize(width + 40, 160)

    delegate = FXThumbnailDelegate()
    tree.setItemDelegate(delegate)

    item = QTreeWidgetItem(tree, [title])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, thumbnail)
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, text)
    if color is not None:
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, color)
    for name, value in roles.items():
        item.setData(0, getattr(FXThumbnailDelegate, name), value)

    qtbot.addWidget(tree)
    tree.show()
    qtbot.waitExposed(tree)
    return tree, delegate, tree.model().index(0, 0)


def _option_for(tree, index) -> QStyleOptionViewItem:
    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    return option


def _advance(delegate, option, text: str) -> int:
    return QFontMetrics(delegate._label_font(option)).horizontalAdvance(text)


def test_a_label_with_no_colour_role_is_a_neutral_tag(qtbot):
    tree, delegate, index = _tree_with_item(qtbot)
    option = _option_for(tree, index)

    m = delegate._indicator_metrics(index, option)

    assert m.label_width == (
        2 * delegate._LABEL_PADDING + _advance(delegate, option, "READY")
    )
    assert not m.label_color.isValid()
    assert m.footprint == delegate._INDICATOR_RIGHT_MARGIN + m.label_width + 1


def test_the_neutral_tag_is_an_outline_with_no_coloured_mark(qtbot):
    tree, delegate, index = _tree_with_item(qtbot)
    option = _option_for(tree, index)
    m = delegate._indicator_metrics(index, option, fit=True)
    assert m.label_width

    image = tree.viewport().grab().toImage()
    label_x, _dot_x = delegate._indicator_left(option.rect, m.label_width, 0)
    tall = delegate._is_tall(option.rect, delegate._has_thumbnail(index))
    top = delegate._band_top(option.rect, tall)
    rect = QRect(label_x, top, m.label_width, delegate._INDICATOR_BAND_HEIGHT)

    border = QColor(fxstyle.colors().border_light)
    # Two columns: the radius leaves the left edge a curve, antialiased.
    edge = [image.pixelColor(x, y)
            for y in range(rect.top(), rect.bottom() + 1)
            for x in (rect.left(), rect.left() + 1)]
    assert any(
        abs(p.red() - border.red()) <= 24
        and abs(p.green() - border.green()) <= 24
        and abs(p.blue() - border.blue()) <= 24
        for p in edge
    )
    saturations = [
        image.pixelColor(x, y).hslSaturation()
        for y in range(rect.top(), rect.bottom() + 1)
        for x in range(rect.left(), rect.right() + 1)
    ]
    assert max(saturations) <= 60


def test_the_uppercase_role_false_keeps_the_case(qtbot):
    tree, delegate, index = _tree_with_item(
        qtbot, text="v012", color=PILL_COLOR,
        STATUS_LABEL_UPPERCASE_ROLE=False,
    )
    option = _option_for(tree, index)
    m = delegate._indicator_metrics(index, option)
    assert m.label_width == (
        delegate._LABEL_MARK + delegate._LABEL_GAP
        + _advance(delegate, option, "v012")
    )
    assert m.label_upper is False

    tree, delegate, index = _tree_with_item(
        qtbot, text="v012", color=PILL_COLOR
    )
    option = _option_for(tree, index)
    m = delegate._indicator_metrics(index, option)
    assert m.label_width == (
        delegate._LABEL_MARK + delegate._LABEL_GAP
        + _advance(delegate, option, "V012")
    )
    assert m.label_upper is True


def test_a_pale_mark_is_stepped_to_read_on_the_row(qtbot):
    tree, delegate, index = _tree_with_item(qtbot, color=PILL_COLOR)
    option = _option_for(tree, index)
    option.palette.setColor(QPalette.Base, QColor("#ffffff"))

    pale = delegate._mark_ink(option, index, QColor("#f5f5f5"))
    assert fxstyle.get_contrast_ratio(pale.name(), "#ffffff") >= (
        fxstyle.CONTROL_CONTRAST
    )
    kept = delegate._mark_ink(option, index, PILL_COLOR)
    assert kept.name() == PILL_COLOR.name()

    tree.topLevelItem(0).setData(0, Qt.BackgroundRole, "#000000")
    dark = delegate._mark_ink(option, index, QColor("#101010"))
    assert dark.lightness() > QColor("#101010").lightness()
    assert fxstyle.get_contrast_ratio(dark.name(), "#000000") >= (
        fxstyle.CONTROL_CONTRAST
    )


def test_a_squeezed_neutral_tag_hides_and_frees_its_room(qtbot):
    # Narrow enough that the title squeezes the tag on any platform's font.
    tree, delegate, index = _tree_with_item(
        qtbot, title=LONG_TITLE, width=200
    )
    option = _option_for(tree, index)

    squeezed = delegate._indicator_metrics(index, option, fit=True)
    assert squeezed.label_width == 0
    assert squeezed.footprint == 0
    # Measuring never shrinks it, so a size hint never depends on the width.
    assert delegate._indicator_metrics(index, option).label_width > 0


def test_an_unusable_colour_still_hides_the_label(qtbot):
    tree, delegate, index = _tree_with_item(qtbot, color="not a color")
    option = _option_for(tree, index)
    assert delegate._indicator_metrics(index, option).label_width == 0
