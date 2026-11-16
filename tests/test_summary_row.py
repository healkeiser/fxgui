"""FXSummaryRow: pinned under a view's rows, lined up with its columns."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QAccessible, QColor, QPalette, QStandardItemModel
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QListView,
    QTableView,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXKeyboardTree, FXSummaryRow

from _helpers import themed_window

LEAD = 12
TEXTS = ["9 shots", "5/63 tasks done", "300", "0.1 d"]


def _view(qtbot, kind=QTreeView, rows=200, columns=4):
    view = kind()
    if isinstance(view, QTreeWidget):
        view.setColumnCount(columns)
        for row in range(rows):
            QTreeWidgetItem(view, [str(row)])
    else:
        view.setModel(QStandardItemModel(rows, columns, view))
    for column in range(columns):
        view.setColumnWidth(column, 140)
    window = themed_window(qtbot, "dark", view, size=(420, 320))
    summary = FXSummaryRow(view)
    summary.set_texts(TEXTS)
    QApplication.processEvents()
    # The window goes with its last Python reference: the caller holds it.
    return view, summary, window


def _column_x(view, column):
    """The column's left edge in the view's coordinates, as the view says."""
    return view.viewport().x() + view.columnViewportPosition(column)


def _lined_up(view, summary) -> bool:
    """Return whether every cell sits over its column, as the view says."""
    header = view.header() if isinstance(view, QTreeView) else (
        view.horizontalHeader())
    for column in range(header.count()):
        label = summary.cell(column)
        if header.isSectionHidden(column):
            if label.isVisible():
                return False
            continue
        left = summary.mapTo(view, label.geometry().topLeft()).x()
        if left - LEAD != _column_x(view, column) or (
                label.width() != view.columnWidth(column) - 2 * LEAD):
            return False
    return True


def _assert_lined_up(qtbot, view, summary):
    # A stretched last section takes its size one event loop turn late.
    qtbot.waitUntil(lambda: _lined_up(view, summary), timeout=1000)


@pytest.mark.parametrize("kind", [QTreeView, QTableView, FXKeyboardTree])
def test_the_row_sits_under_the_viewport_and_stays_while_rows_scroll(
        qtbot, kind):
    view, summary, _window = _view(qtbot, kind)
    viewport = view.viewport().geometry()
    assert summary.geometry().top() == viewport.bottom() + 1
    assert summary.geometry().left() == viewport.left()
    assert summary.width() == viewport.width()
    assert view.viewportMargins().bottom() == summary.height()
    before = summary.geometry()

    view.verticalScrollBar().setValue(view.verticalScrollBar().maximum())
    QApplication.processEvents()
    assert summary.geometry() == before
    assert summary.isVisible()
    # Not a model row: the model is untouched, and the last row shows whole.
    assert view.model().rowCount() == 200
    last = view.visualRect(view.model().index(199, 0))
    assert last.bottom() < view.viewport().height()


@pytest.mark.parametrize("kind", [QTreeView, QTableView])
def test_cells_follow_resize_hide_move_and_horizontal_scroll(qtbot, kind):
    view, summary, _window = _view(qtbot, kind)
    header = view.header() if kind is QTreeView else view.horizontalHeader()
    _assert_lined_up(qtbot, view, summary)

    header.resizeSection(0, 220)
    _assert_lined_up(qtbot, view, summary)

    header.hideSection(1)
    _assert_lined_up(qtbot, view, summary)
    header.showSection(1)

    header.moveSection(3, 0)  # visual order differs from logical now
    _assert_lined_up(qtbot, view, summary)
    assert summary.cell(3).x() < summary.cell(0).x()

    scroll_bar = view.horizontalScrollBar()
    scroll_bar.setValue(scroll_bar.maximum())
    assert scroll_bar.value() > 0
    _assert_lined_up(qtbot, view, summary)


def test_the_row_follows_the_vertical_scroll_bar(qtbot):
    view, summary, _window = _view(qtbot, rows=2)
    narrow = summary.width()
    view.model().insertRows(0, 300)
    qtbot.waitUntil(view.verticalScrollBar().isVisible)
    assert summary.width() == view.viewport().width() < narrow


@pytest.mark.parametrize("name", sorted(fxstyle.ROW_SIZES))
def test_the_height_follows_the_row_size(qtbot, set_row_size, name):
    view, summary, _window = _view(qtbot)
    assert summary.height() == fxstyle.ROW_SIZES["normal"] == 36
    set_row_size(name)
    QApplication.processEvents()
    assert summary.height() == fxstyle.ROW_SIZES[name]
    assert view.viewportMargins().bottom() == fxstyle.ROW_SIZES[name]
    assert summary.geometry().top() == view.viewport().geometry().bottom() + 1


def test_hiding_the_row_gives_its_room_back(qtbot):
    view, summary, _window = _view(qtbot)
    summary.setVisible(False)
    QApplication.processEvents()
    assert view.viewportMargins().bottom() == 0
    summary.show()
    QApplication.processEvents()
    assert view.viewportMargins().bottom() == 36


def test_a_cell_takes_its_own_alignment_else_the_headers_else_left(qtbot):
    view, summary, _window = _view(qtbot)
    view.model().setHeaderData(
        2, Qt.Horizontal, int(Qt.AlignRight), Qt.TextAlignmentRole)
    summary.set_text(2, "300")
    summary.set_text(3, "0.1 d", Qt.AlignHCenter)
    horizontal = Qt.AlignHorizontal_Mask
    assert summary.cell(0).alignment() & horizontal == Qt.AlignLeft
    assert summary.cell(2).alignment() & horizontal == Qt.AlignRight
    assert summary.cell(3).alignment() & horizontal == Qt.AlignHCenter
    assert summary.cell(2).alignment() & Qt.AlignVCenter


def test_text_is_small_muted_and_strong_on_request(qtbot):
    view, summary, _window = _view(qtbot)
    summary.set_text(1, "5/63 tasks done", strong=True)
    QApplication.processEvents()
    theme = fxstyle.colors()
    muted = summary.cell(0).palette().color(QPalette.WindowText)
    strong = summary.cell(1).palette().color(QPalette.WindowText)
    assert muted == QColor(theme.text_muted)
    assert strong == QColor(theme.text)
    assert summary.cell(0).font().pixelSize() == fxstyle.FONT_SIZE - 1
    assert summary.text(1) == "5/63 tasks done"
    assert summary.text(9) == ""


def test_the_band_and_its_rule_are_painted(qtbot):
    view, summary, _window = _view(qtbot)
    summary.clear()
    image = summary.grab().toImage()
    theme = fxstyle.colors()
    assert QColor(image.pixel(5, 0)) == QColor(theme.border)
    band = QColor(fxstyle.depth_shade(theme.surface, 1))
    assert QColor(image.pixel(5, summary.height() // 2)) == band


def test_screen_readers_read_a_summary_not_a_data_row(qtbot):
    view, summary, _window = _view(qtbot)
    assert summary.accessibleName() == "Summary"
    assert summary.accessibleDescription()
    for column in range(4):
        cell = QAccessible.queryAccessibleInterface(summary.cell(column))
        assert cell.role() == QAccessible.StaticText
        assert cell.text(QAccessible.Name) == TEXTS[column]
    strip = QAccessible.queryAccessibleInterface(summary)
    assert strip.role() not in (QAccessible.Row, QAccessible.Cell)


def test_the_row_takes_no_focus_and_no_selection(qtbot):
    view, summary, _window = _view(qtbot)
    view.setSelectionMode(QTableView.ExtendedSelection)
    view.setFocus()
    assert summary.focusPolicy() == Qt.NoFocus
    assert all(
        summary.cell(c).focusPolicy() == Qt.NoFocus for c in range(4))
    QTest.mouseClick(summary, Qt.LeftButton, pos=QPoint(20, 10))
    QTest.mouseClick(summary.cell(1), Qt.LeftButton)
    assert not view.selectionModel().hasSelection()
    for _ in range(6):
        QTest.keyClick(view.window(), Qt.Key_Tab)
        focus = QApplication.focusWidget()
        assert focus is not summary and focus not in summary.children()


def test_clear_empties_every_cell(qtbot):
    view, summary, _window = _view(qtbot)
    summary.clear()
    assert summary.cell(0) is None
    assert summary.text(0) == ""


def test_a_view_without_a_header_is_refused(qtbot):
    view = QListView()
    qtbot.addWidget(view)
    with pytest.raises(TypeError):
        FXSummaryRow(view)


def test_the_frames_round_corners_stay_above_the_row(qtbot):
    view, summary, _window = _view(qtbot)
    corners = view.findChild(fxstyle._ViewportCorners)
    assert corners is not None
    view.resize(view.width() + 10, view.height())
    QApplication.processEvents()
    children = view.children()
    assert children.index(view.viewport()) < children.index(summary)
    assert children.index(summary) < children.index(corners)
