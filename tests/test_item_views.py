"""Item views: the thumbnail delegate, the fuzzy proxy, trees, sorting."""

# Built-in
import os

# Third-party
from qtpy.QtCore import QRect, Qt
from qtpy.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QPainter,
    QStandardItem,
    QStandardItemModel,
)
from qtpy.QtWidgets import (
    QStyle,
    QStyleOptionViewItem,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxcore, fxstyle, fxwidgets
from fxgui.fxcore import FXSortFilterProxyModel
from fxgui.fxwidgets import FXThumbnailDelegate
from fxgui.fxwidgets import _delegates


def _tree(qtbot, columns=1, width=420):
    tree = QTreeWidget()
    tree.setColumnCount(columns)
    tree.setRootIsDecorated(False)
    delegate = FXThumbnailDelegate(tree)
    tree.setItemDelegate(delegate)
    tree.resize(width, 200)
    qtbot.addWidget(tree)
    return tree, delegate


def _card_row(tree, columns):
    item = QTreeWidgetItem(tree, [f"cell {n}" for n in range(columns)])
    item.setData(0, Qt.BackgroundRole, "surface")
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    return item


# FXThumbnailDelegate ------------------------------------------------------


def test_row_ends_follow_the_visual_column_order(qtbot, monkeypatch):
    tree, delegate = _tree(qtbot, columns=3)
    _card_row(tree, 3)
    tree.header().moveSection(2, 0)
    tree.show()
    qtbot.waitExposed(tree)

    seen = {}
    real = delegate.paint

    def spy(painter, option, index):
        seen[index.column()] = delegate._row_ends(option, index)
        real(painter, option, index)

    monkeypatch.setattr(delegate, "paint", spy)
    tree.viewport().grab()
    # Logical column 2 is drawn first now, and logical 1 last.
    assert seen[2] == (True, False)
    assert seen[0] == (False, False)
    assert seen[1] == (False, True)


def test_size_hint_measures_the_items_own_font(qtbot):
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, ["A rather long asset title"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    big = QFont(tree.font())
    big.setPixelSize(40)
    item.setFont(0, big)
    index = tree.model().index(0, 0)
    option = QStyleOptionViewItem()
    option.font = tree.font()
    option.widget = tree
    hint = delegate.sizeHint(option, index)
    assert hint.width() >= QFontMetrics(big).horizontalAdvance(item.text(0))
    assert hint.height() >= QFontMetrics(big).height()


def test_row_height_grows_with_the_font(qtbot):
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, ["Asset"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    item.setData(0, FXThumbnailDelegate.DESCRIPTION_ROLE, "shading")
    index = tree.model().index(0, 0)
    option = QStyleOptionViewItem()
    option.widget = tree
    option.font = tree.font()
    small = delegate.sizeHint(option, index).height()
    big = QFont(tree.font())
    big.setPixelSize(30)
    option.font = big
    assert delegate.sizeHint(option, index).height() > small + 20


def test_the_description_font_is_one_step_smaller_in_pixels(qtbot):
    delegate = FXThumbnailDelegate()
    option = QStyleOptionViewItem()
    font = QFont()
    font.setPixelSize(20)
    option.font = font
    assert delegate._description_font(option).pixelSize() == 19



def test_the_delegate_s_type_is_the_body_weight_and_600_only(qtbot):
    """Title 600; metadata one step, 11 px at 12; badge 10 px at 12, 600."""
    option = QStyleOptionViewItem()
    font = QFont()
    font.setPixelSize(12)
    option.font = font
    FXThumbnailDelegate._badge_fonts.clear()
    assert FXThumbnailDelegate._title_font(option).weight() == QFont.DemiBold
    assert FXThumbnailDelegate._description_font(option).pixelSize() == 11
    badge = FXThumbnailDelegate._badge_font(option)
    assert (badge.pixelSize(), badge.weight()) == (10, QFont.DemiBold)
def test_every_role_is_claimed_once_from_one_table():
    from fxgui.fxwidgets import _roles

    claimed = [
        value for name, value in vars(_roles).items() if name.isupper()
    ]
    assert len(claimed) == len(set(claimed))
    assert fxwidgets.FXSortedTreeWidgetItem.SORT_ROLE == _roles.SORT
    assert FXThumbnailDelegate.FIRST_FREE_ROLE == _roles.FIRST_FREE
    assert _roles.FIRST_FREE == max(claimed)


def test_a_thumbnail_is_stat_once_per_window(qtbot, monkeypatch, tmp_path):
    calls = []
    real = os.path.getmtime

    def counting(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(_delegates.os.path, "getmtime", counting)
    image = tmp_path / "a.png"
    QImage(8, 8, QImage.Format_RGB32).save(str(image))
    delegate = FXThumbnailDelegate()
    for _ in range(5):
        delegate._bordered_thumbnail(str(image), 1.0)
    assert len(calls) == 1


def test_the_thumbnail_frame_is_the_border_light_token(qtbot, tmp_path):
    fxstyle.apply_theme("light")
    image = tmp_path / "b.png"
    source = QImage(68, 38, QImage.Format_RGB32)
    source.fill(QColor("#336699"))
    source.save(str(image))
    framed = FXThumbnailDelegate()._bordered_thumbnail(str(image), 2.0)
    assert framed.devicePixelRatio() == 2.0
    middle = framed.toImage().pixelColor(framed.width() // 2, 0)
    assert middle.name() == QColor(fxstyle.colors().border_light).name()


def test_the_floor_follows_a_new_model(qtbot):
    view = QTreeView()
    view.setRootIsDecorated(False)
    view.header().setStretchLastSection(False)
    view.header().setMinimumSectionSize(10)
    view.setItemDelegate(FXThumbnailDelegate(view))
    view.setModel(QStandardItemModel(view))
    qtbot.addWidget(view)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(view)

    model = QStandardItemModel(view)
    item = QStandardItem("Asset")
    item.setData("#ff00ff", FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE)
    item.setData("Ready", FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE)
    model.appendRow(item)
    view.setModel(model)
    view.header().resizeSection(0, 20)
    assert view.header().sectionSize(0) > 60


def test_a_second_floor_replaces_the_first(qtbot):
    tree, _ = _tree(qtbot)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree, floor=100)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree, floor=200)
    tree.header().resizeSection(0, 50)
    assert tree.header().sectionSize(0) == 200
    floors = [
        child
        for child in tree.children()
        if type(child).__name__ == "_ColumnFloor"
    ]
    assert len(floors) == 1


def test_owning_the_row_is_one_registered_rule(qtbot):
    tree, _ = _tree(qtbot)
    tree.setStyleSheet("QTreeWidget { color: red; }")
    FXThumbnailDelegate.apply_transparent_selection(tree)
    FXThumbnailDelegate.apply_transparent_selection(tree)
    assert tree.styleSheet() == "QTreeWidget { color: red; }"
    assert tree.property("fxOwnsRow") is True
    assert 'fxOwnsRow="true"' in fxstyle._build_stylesheet()


def _contrast(one: QColor, two: QColor) -> float:
    return fxstyle.get_contrast_ratio(one.name(), two.name())


def test_a_status_label_ink_reads_on_its_fill(qtbot):
    delegate = FXThumbnailDelegate()
    fill = QColor("#ff0000")
    canvas = QImage(200, 40, QImage.Format_RGB32)
    canvas.fill(fill)
    font = QFont()
    font.setPixelSize(30)
    font.setBold(True)
    painter = QPainter(canvas)
    delegate._INDICATOR_BAND_HEIGHT = 40
    delegate._INDICATOR_BAND_TOP = 0
    try:
        delegate._draw_status_label(
            painter, QRect(0, 0, 200, 40), 0, 200, 0, fill, "HHHH", font
        )
    finally:
        painter.end()
    best = max(
        _contrast(canvas.pixelColor(x, y), fill)
        for x in range(0, 200, 2)
        for y in range(4, 36, 2)
    )
    assert best >= 4.5


def _paint_row(qtbot, state, text="Asset"):
    """Paint one plain row in `state` and return the canvas and the tree."""
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, [text])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 120, 28)
    option.state = QStyle.State_Enabled | state
    option.widget = tree
    option.palette = tree.palette()
    canvas = QImage(120, 28, QImage.Format_RGB32)
    canvas.fill(QColor("#123456"))
    painter = QPainter(canvas)
    try:
        delegate.paint(painter, option, tree.model().index(0, 0))
    finally:
        painter.end()
    return canvas, tree


def test_a_hovered_row_is_the_neutral_hover_fill_not_an_accent(qtbot):
    canvas, _ = _paint_row(qtbot, QStyle.State_MouseOver, text="")
    colors = fxstyle.colors()
    seen = canvas.pixelColor(110, 14).name()
    assert seen == QColor(colors.state_hover).name()
    assert seen not in (
        QColor(colors.accent_primary).name(),
        QColor(colors.accent_secondary).name(),
    )


def test_a_hovered_row_keeps_its_text_ink():
    option = QStyleOptionViewItem()
    option.state = QStyle.State_Enabled | QStyle.State_MouseOver
    assert (
        FXThumbnailDelegate._text_color(option).name()
        == option.palette.text().color().name()
    )


def test_a_selected_row_keeps_the_accent_in_a_view_without_focus(qtbot):
    canvas, tree = _paint_row(qtbot, QStyle.State_Selected, text="")
    assert not tree.hasFocus()
    assert (
        canvas.pixelColor(110, 14).name()
        == QColor(fxstyle.colors().accent_primary).name()
    )


# FXSortFilterProxyModel ---------------------------------------------------


def _proxy(texts):
    model = QStandardItemModel()
    for text in texts:
        model.appendRow(QStandardItem(text))
    proxy = FXSortFilterProxyModel(ratio=0.5)
    proxy.setSourceModel(model)
    return model, proxy


def _rows(proxy):
    return [proxy.index(row, 0).data() for row in range(proxy.rowCount())]


def test_a_substring_hit_ranks_with_a_perfect_score(qapp):
    _, proxy = _proxy(["heron", "character_hero_main"])
    proxy.set_filter_text("hero")
    # A tie keeps the source order.
    assert _rows(proxy) == ["heron", "character_hero_main"]
    assert proxy.score("character_hero_main") == 1.0
    assert proxy.score("heron") == 1.0


def test_a_substring_hit_sorts_above_a_fuzzy_one(qapp):
    _, proxy = _proxy(["hrxo", "the_hero"])
    proxy.set_ratio(0.1)
    proxy.set_filter_text("hero")
    assert _rows(proxy) == ["the_hero", "hrxo"]


def test_each_row_is_scored_once_per_filter(qapp, monkeypatch):
    texts = [f"asset_{n:03d}_hero" for n in range(40)]
    _, proxy = _proxy(texts)
    calls = []
    real = fxcore._score

    def counting(*args):
        calls.append(args)
        return real(*args)

    monkeypatch.setattr(fxcore, "_score", counting)
    proxy.set_filter_text("ast")
    for row in range(proxy.rowCount()):
        proxy.index(row, 0).data(Qt.ForegroundRole)
    assert len(calls) <= len(texts)


# FXSortedTreeWidgetItem ---------------------------------------------------


def test_keyed_and_keyless_rows_sort_in_two_blocks(qtbot):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    role = fxwidgets.FXSortedTreeWidgetItem.SORT_ROLE
    a = fxwidgets.FXSortedTreeWidgetItem(tree, ["a"])
    b = fxwidgets.FXSortedTreeWidgetItem(tree, ["b"])
    c = fxwidgets.FXSortedTreeWidgetItem(tree, ["c"])
    a.setData(0, role, 2)
    c.setData(0, role, 1)
    assert not (a < b and b < c and c < a)
    tree.sortItems(0, Qt.AscendingOrder)
    assert [tree.topLevelItem(n).text(0) for n in range(3)] == ["c", "a", "b"]


# FXFilteredTree ------------------------------------------------------------


def test_building_the_filtered_tree_shows_no_window(qtbot, qapp):
    from qtpy.QtCore import QEvent, QObject

    shown = []

    class _Spy(QObject):
        def eventFilter(self, watched, event):
            if (
                event.type() == QEvent.Show
                and hasattr(watched, "isWindow")
                and watched.isWindow()
            ):
                shown.append(type(watched).__name__)
            return False

    spy = _Spy()
    qapp.installEventFilter(spy)
    try:
        search = fxwidgets.FXFilteredTree()
        qtbot.addWidget(search)
        qapp.processEvents()
    finally:
        qapp.removeEventFilter(spy)
    assert shown == []
