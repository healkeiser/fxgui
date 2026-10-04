"""Item delegates: caching, menus, focus ring, layout agreement, theming."""

# Built-in
import builtins
from pathlib import Path

# Third-party
from qtpy.QtCore import QPoint, QRect, Qt
from qtpy.QtGui import QColor, QFont, QPixmapCache
from qtpy.QtWidgets import (
    QMenu,
    QStyle,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle, fxutils
from fxgui.fxwidgets import _delegates
from fxgui.fxwidgets import FXThumbnailDelegate

from _helpers import delegate_tree

_IMAGE = str(
    Path(_delegates.__file__).parent.parent / "images" / "missing_image.png"
)


def _tree(qtbot):
    tree, delegate, _ = delegate_tree(qtbot, headers=["Name"], height=160)
    return tree, delegate


def _raw_option(tree, index):
    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    option.font = tree.font()
    option.widget = tree
    return option


def test_a_thumbnail_is_loaded_once_across_paints(qtbot, monkeypatch):
    loads = []
    real = _delegates.QPixmap

    class CountingPixmap(real):
        def __init__(self, *args):
            if args and isinstance(args[0], str):
                loads.append(args[0])
            super().__init__(*args)

    monkeypatch.setattr(_delegates, "QPixmap", CountingPixmap)
    QPixmapCache.clear()
    tree, _ = _tree(qtbot)
    item = QTreeWidgetItem(tree, ["Shot"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, _IMAGE)
    tree.viewport().grab()
    tree.viewport().grab()
    assert loads.count(_IMAGE) == 1


def test_a_missing_thumbnail_checks_the_fallback_once(qtbot, monkeypatch):
    checks = []
    real_exists = Path.exists

    def counting_exists(self):
        checks.append(str(self))
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", counting_exists)
    QPixmapCache.clear()
    tree, _ = _tree(qtbot)
    for name in ("a", "b"):
        item = QTreeWidgetItem(tree, [name])
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, "")
    tree.viewport().grab()
    tree.viewport().grab()
    assert len([c for c in checks if "missing_image" in c]) <= 1


def test_the_markdown_import_is_not_retried_per_call(monkeypatch):
    attempts = []
    real_import = builtins.__import__

    def counting_import(name, *args, **kwargs):
        if name == "markdown":
            attempts.append(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", counting_import)
    fxutils.markdown_to_plain_text("**a**")
    fxutils.markdown_to_plain_text("**b**")
    assert len(attempts) <= 1


def test_the_picker_menu_is_parented_and_opened_at_a_global_point(
    qtbot, monkeypatch
):
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Version"])
    tree.setColumnWidth(0, 200)
    tree.resize(360, 120)
    delegate = FXThumbnailDelegate()
    delegate.show_thumbnail = False
    delegate.picker_column = 1
    tree.setItemDelegate(delegate)
    item = QTreeWidgetItem(tree, ["Beauty", "v002"])
    item.setData(1, FXThumbnailDelegate.PICKER_TEXT_ROLE, "v002")
    item.setData(1, FXThumbnailDelegate.PICKER_CHOICES_ROLE, ["v001", "v002"])
    qtbot.addWidget(tree)
    tree.move(200, 150)
    tree.show()
    qtbot.waitExposed(tree)

    seen = {}

    def fake_exec(menu, pos=None, *args):
        seen["parent"] = menu.parent()
        seen["pos"] = QPoint(pos)
        return None

    monkeypatch.setattr(QMenu, "exec_", fake_exec)
    index = tree.model().index(0, 1)
    rect = QRect(10, 10, 40, 16)
    delegate._open_picker(rect, index, tree)
    assert seen["parent"] is tree
    assert seen["pos"] == tree.viewport().mapToGlobal(rect.bottomLeft())


def test_the_focus_ring_spans_a_checkable_row(qtbot):
    from qtpy.QtGui import QPainter, QPixmap

    tree, delegate = _tree(qtbot)
    delegate.show_thumbnail = False
    item = QTreeWidgetItem(tree, ["Beauty"])
    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
    item.setCheckState(0, Qt.Unchecked)
    index = tree.model().index(0, 0)

    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 200, 30)
    option.state = QStyle.State_Enabled | QStyle.State_HasFocus
    option.widget = None
    canvas = QPixmap(200, 30)
    canvas.fill(QColor("#ff00ff"))
    painter = QPainter(canvas)
    try:
        delegate.paint(painter, option, index)
    finally:
        painter.end()
    image = canvas.toImage()
    accent = QColor(fxstyle.colors().accent_primary).name()
    # The ring's left edge sits in the first two pixels, left of the box.
    left_edge = {image.pixelColor(x, 15).name() for x in range(0, 2)}
    assert accent in left_edge


def test_check_width_matches_what_paint_consumes(qtbot):
    tree, delegate = _tree(qtbot)
    delegate.show_thumbnail = False
    item = QTreeWidgetItem(tree, ["Beauty"])
    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
    item.setCheckState(0, Qt.Unchecked)
    index = tree.model().index(0, 0)
    option = _raw_option(tree, index)
    painted = QStyleOptionViewItem(option)
    delegate.initStyleOption(painted, index)
    box = delegate._check_rect(painted)
    consumed = box.right() + 1 - option.rect.left()
    assert delegate._check_width(delegate._init(option, index), index) == consumed


def test_the_floor_makes_room_for_the_check_box(qtbot):
    tree, delegate = _tree(qtbot)
    plain = QTreeWidgetItem(tree, ["Plain"])
    ticked = QTreeWidgetItem(tree, ["Ticked"])
    ticked.setFlags(ticked.flags() | Qt.ItemIsUserCheckable)
    ticked.setCheckState(0, Qt.Unchecked)
    for item in (plain, ticked):
        item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, "#0f0")
    plain_index = tree.model().index(0, 0)
    ticked_index = tree.model().index(1, 0)
    plain_option = delegate._init(_raw_option(tree, plain_index), plain_index)
    ticked_option = delegate._init(
        _raw_option(tree, ticked_index), ticked_index
    )
    assert delegate._row_minimum_width(
        ticked_option, ticked_index, True
    ) == delegate._row_minimum_width(
        plain_option, plain_index, True
    ) + delegate._check_width(ticked_option, ticked_index)


def test_the_floor_is_not_remeasured_on_every_resize(qtbot, monkeypatch):
    tree, delegate = _tree(qtbot)
    for i in range(5):
        item = QTreeWidgetItem(tree, [f"Row {i}"])
        item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, "#0f0")
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    calls = []
    real = FXThumbnailDelegate._measure_minimum_width.__func__

    def counting(cls, view, column):
        calls.append(column)
        return real(cls, view, column)

    monkeypatch.setattr(
        FXThumbnailDelegate, "_measure_minimum_width", classmethod(counting)
    )
    for width in (60, 50, 40, 30, 20):
        tree.header().resizeSection(0, width)
    assert len(calls) <= 1


def test_the_floor_follows_a_model_change(qtbot):
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, ["Row"])
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree)
    tree.header().resizeSection(0, 10)
    narrow = tree.columnWidth(0)
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, "A long label")
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, "#c678dd")
    tree.header().resizeSection(0, 10)
    assert tree.columnWidth(0) > narrow


def test_badges_follow_the_view_font(qtbot):
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, ["Row"])
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, "Review")
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, "#c678dd")
    index = tree.model().index(0, 0)
    small = delegate._indicator_metrics(index, _raw_option(tree, index))[0]
    font = QFont(tree.font())
    font.setPointSize(24)
    tree.setFont(font)
    large = delegate._indicator_metrics(index, _raw_option(tree, index))[0]
    assert large > small


def test_a_theme_switch_repaints_with_the_new_colors(qtbot):
    tree, _ = _tree(qtbot)
    # A row's ground is its view's well, which a themed root's sheet sets.
    fxstyle.register_themed_root(tree)
    QTreeWidgetItem(tree, ["Row"])
    index = tree.model().index(0, 0)
    rect = tree.visualRect(index)
    point = QPoint(rect.right() - 2, rect.center().y())
    fxstyle.apply_theme("dark")
    dark = tree.viewport().grab().toImage().pixelColor(point).name()
    fxstyle.apply_theme("light")
    light = tree.viewport().grab().toImage().pixelColor(point).name()
    assert dark != light
    assert light == QColor(fxstyle.colors().surface_sunken).name()


def test_a_colour_decoration_paints_as_a_swatch(qtbot):
    tree, delegate, item = delegate_tree(
        qtbot, row=["Red", "Also"], widths=(200, 200), show_thumbnail=False
    )
    for column in (0, 1):
        item.setData(column, Qt.DecorationRole, QColor("#ff0000"))

    shot = tree.viewport().grab().toImage()

    for column in (0, 1):
        rect = tree.visualRect(tree.indexFromItem(item, column))
        centre = delegate._icon_rect(rect).center()
        assert shot.pixelColor(centre).name() == "#ff0000"
    # The thumbnail's overlay takes the swatch too.
    delegate.show_thumbnail = True
    tree.viewport().grab()


def _inks(image, rect):
    return {
        image.pixelColor(x, y).name()
        for x in range(rect.left(), rect.right())
        for y in range(rect.top(), rect.bottom())
    }


def test_a_description_is_drawn_in_text_muted(qtbot):
    tree, _delegate, item = delegate_tree(
        qtbot, row=["Title"], show_thumbnail=False
    )
    item.setData(0, FXThumbnailDelegate.DESCRIPTION_ROLE, "WWWW")
    rect = tree.visualRect(tree.indexFromItem(item, 0))

    inks = _inks(tree.viewport().grab().toImage(), rect)

    assert QColor(fxstyle.colors().text_muted).name() in inks
