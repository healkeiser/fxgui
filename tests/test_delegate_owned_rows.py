"""The delegate owns its rows: no native row panel, focus rect or pill."""

# Third-party
import pytest
from qtpy.QtCore import QModelIndex, QRect, Qt
from qtpy.QtGui import QColor, QPainter, QPixmap
from qtpy.QtWidgets import (
    QApplication,
    QProxyStyle,
    QStyle,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate

_OWNED = (
    QStyle.PrimitiveElement.PE_PanelItemViewRow,
    QStyle.PrimitiveElement.PE_FrameFocusRect,
)


class _Spy(QProxyStyle):
    def __init__(self, drawn):
        super().__init__("Fusion")
        self._drawn = drawn

    def drawPrimitive(self, element, option, painter, widget=None):
        self._drawn.append(element)
        super().drawPrimitive(element, option, painter, widget)


def _themed_tree(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    tree = QTreeWidget(root)
    QVBoxLayout(root).addWidget(tree)
    tree.setColumnCount(2)
    tree.setAllColumnsShowFocus(True)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    parent = QTreeWidgetItem(tree, ["parent", "a"])
    child = QTreeWidgetItem(parent, ["child", "b"])
    parent.setExpanded(True)
    fxstyle.register_themed_root(root)
    root.resize(300, 200)
    root.show()
    qtbot.waitExposed(root)
    root.activateWindow()
    qtbot.waitUntil(root.isActiveWindow, timeout=1000)
    tree.clearFocus()
    tree.setFocus(Qt.TabFocusReason)
    tree.setCurrentItem(child)
    child.setSelected(True)
    QApplication.processEvents()
    tree.root = root
    return tree


def _drawn_through(tree, style_class):
    drawn = []
    style = style_class(_Spy(drawn))
    style.setParent(tree)
    tree.setStyle(style)
    tree.viewport().grab()
    return drawn


def test_a_plain_view_draws_the_native_row_panel_and_focus_rect(qtbot):
    drawn = _drawn_through(_themed_tree(qtbot), QProxyStyle)
    for element in _OWNED:
        assert element in drawn, element


def test_the_delegate_s_rows_skip_the_native_row_panel_and_focus_rect(qtbot):
    tree = _themed_tree(qtbot)
    FXThumbnailDelegate.apply_transparent_selection(tree)
    style = tree.findChild(QProxyStyle)
    assert style is not None, "apply_transparent_selection installs a style"
    drawn = _drawn_through(tree, type(style))
    assert drawn, "the row paint path still reaches the style"
    for element in _OWNED:
        assert element not in drawn, element


def test_applying_twice_installs_one_style(qtbot):
    tree = _themed_tree(qtbot)
    FXThumbnailDelegate.apply_transparent_selection(tree)
    FXThumbnailDelegate.apply_transparent_selection(tree)
    assert len(tree.findChildren(QProxyStyle)) == 1


def _ring(delegate, *, first, last, selected=False):
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 60, 30)
    option.state = QStyle.State_Enabled | QStyle.State_HasFocus
    if selected:
        option.state |= QStyle.State_Selected
    option.widget = None
    canvas = QPixmap(60, 30)
    canvas.fill(QColor("#ff00ff"))
    painter = QPainter(canvas)
    try:
        delegate._draw_focus_indicator(
            painter, option.rect, option, QModelIndex(), (first, last)
        )
    finally:
        painter.end()
    return canvas.toImage()


def test_a_cell_ring_closes_on_both_sides_of_a_middle_cell(qtbot):
    delegate = FXThumbnailDelegate()
    delegate.focus_ring = "cell"
    image = _ring(delegate, first=False, last=False)
    accent = QColor(fxstyle.colors().accent_primary).name()
    assert image.pixelColor(0, 15).name() == accent
    assert image.pixelColor(59, 15).name() == accent


def test_a_row_ring_leaves_a_middle_cell_open(qtbot):
    image = _ring(FXThumbnailDelegate(), first=False, last=False)
    assert image.pixelColor(0, 15).name() == "#ff00ff"
    assert image.pixelColor(59, 15).name() == "#ff00ff"


def test_a_cell_ring_marks_the_current_cell_only(qtbot):
    tree = _themed_tree(qtbot)
    delegate = tree.itemDelegate()
    delegate.focus_ring = "cell"
    option = QStyleOptionViewItem()
    option.widget = tree
    current = tree.currentIndex()
    assert tree.hasFocus()
    assert delegate.has_focus_ring(option, current)
    assert not delegate.has_focus_ring(option, current.sibling(0, 1))


def test_focus_ring_refuses_an_unknown_mode():
    with pytest.raises(ValueError):
        FXThumbnailDelegate().focus_ring = "column"


def _paint_selected(qtbot, delegate):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    QTreeWidgetItem(tree, ["row"])
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 120, 30)
    option.state = (
        QStyle.State_Enabled | QStyle.State_Selected | QStyle.State_HasFocus
    )
    option.widget = None
    canvas = QPixmap(120, 30)
    canvas.fill(QColor("#ff00ff"))
    painter = QPainter(canvas)
    try:
        delegate.paint(painter, option, tree.model().index(0, 0))
    finally:
        painter.end()
    return canvas.toImage()


def test_paint_selection_off_leaves_the_fill_and_keeps_the_ring(qtbot):
    delegate = FXThumbnailDelegate()
    delegate.paint_selection = False
    image = _paint_selected(qtbot, delegate)
    accent = QColor(fxstyle.colors().accent_primary).name()
    assert image.pixelColor(110, 15).name() != accent, "no accent fill"
    assert image.pixelColor(110, 0).name() == accent, "the ring still marks it"


def test_paint_selection_on_fills_a_selected_row(qtbot):
    image = _paint_selected(qtbot, FXThumbnailDelegate())
    accent = QColor(fxstyle.colors().accent_primary).name()
    assert image.pixelColor(110, 15).name() == accent


def test_a_table_item_background_shows_in_a_themed_root(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    table = QTableWidget(1, 1, root)
    QVBoxLayout(root).addWidget(table)
    item = QTableWidgetItem("cell")
    item.setBackground(QColor("#aa3333"))
    table.setItem(0, 0, item)
    fxstyle.register_themed_root(root)
    root.resize(300, 200)
    root.show()
    qtbot.waitExposed(root)
    rect = table.visualItemRect(item)
    image = table.viewport().grab().toImage()
    fill = image.pixelColor(rect.right() - 4, rect.center().y()).name()
    assert fill == "#aa3333"


def test_a_floor_holds_a_column_before_any_row_exists(qtbot):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setColumnCount(3)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree, floor=300)
    header = tree.header()
    assert header.sectionSize(0) >= 300
    header.resizeSection(0, 60)
    assert header.sectionSize(0) == 300
    header.resizeSection(0, 480)
    assert header.sectionSize(0) == 480
    header.resizeSection(1, 40)
    assert header.sectionSize(1) == 40, "other columns keep their own width"


def test_the_content_floor_wins_over_a_smaller_one(qtbot):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setColumnCount(2)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    item = QTreeWidgetItem(tree, ["row", "b"])
    item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, "In progress")
    item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, QColor("red"))
    content = FXThumbnailDelegate._measure_minimum_width(tree, 0)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree, floor=10)
    tree.header().resizeSection(0, 5)
    header = tree.header()
    assert header.sectionSize(0) == content
    assert content > 10
