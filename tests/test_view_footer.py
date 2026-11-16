"""Any carded tree or table: its actions in its card, a rule over its header.

The footer and the header's rule were FXFilteredTree's alone: a record
table with Add and Remove, or a list with a line of text above its header,
kept the old look.
"""

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXSummaryRow, FXViewFooter

from _helpers import near, pixel, themed_window


def _settle():
    for _ in range(3):
        QApplication.processEvents()


def _table(rows=3, columns=2):
    table = QTableWidget(rows, columns)
    table.setHorizontalHeaderLabels([f"Column {c}" for c in range(columns)])
    for row in range(rows):
        for column in range(columns):
            table.setItem(row, column, QTableWidgetItem(f"r{row}c{column}"))
    return table


def _actions(*texts):
    layout = QHBoxLayout()
    buttons = [QPushButton(text) for text in texts]
    for button in buttons:
        layout.addWidget(button)
    layout.addStretch()
    return layout, buttons


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_record_tables_actions_are_its_cards_footer(qtbot, theme):
    table = _table()
    FXSummaryRow(table).set_texts(["3 records"])
    actions, (add, _remove) = _actions("Add", "Remove")
    footer = FXViewFooter(table, actions)
    window = themed_window(qtbot, theme, table, size=(360, 320))
    _settle()

    frame = table.frameWidth()
    inside = table.rect().adjusted(frame, frame, -frame, -frame)
    summary = table.findChild(FXSummaryRow)
    assert footer.geometry().top() == summary.geometry().bottom() + 1
    assert footer.geometry().bottom() == inside.bottom()
    assert footer.geometry().left() == inside.left()
    assert footer.geometry().right() == inside.right()
    assert inside.contains(QRect(add.mapTo(table, QPoint(0, 0)), add.size()))
    colors = fxstyle.colors()
    assert near(pixel(window, footer, 4, 0), colors.border, 2)
    middle = add.geometry().center().y()
    assert near(pixel(window, footer, 4, middle), colors.surface_sunken, 2)


def test_a_tables_scroll_bars_end_above_its_footer(qtbot):
    table = _table(rows=40, columns=3)
    for column in range(3):
        table.setColumnWidth(column, 300)
    FXSummaryRow(table).set_texts(["40 records"])
    footer = FXViewFooter(table, _actions("Add")[0])
    window = themed_window(qtbot, "dark", table, size=(360, 320))  # noqa: F841
    horizontal = table.horizontalScrollBar()
    _settle()

    assert horizontal.isVisible()
    summary = table.findChild(FXSummaryRow)
    bar = QRect(horizontal.mapTo(table, QPoint(0, 0)), horizontal.size())
    assert bar.top() == summary.geometry().bottom() + 1
    assert footer.geometry().top() == bar.bottom() + 1
    side = table.verticalScrollBar()
    assert side.mapTo(table, QPoint(0, side.height() - 1)).y() == (
        summary.geometry().bottom())


def test_a_hidden_footer_gives_its_room_back(qtbot):
    table = _table()
    footer = FXViewFooter(table, _actions("Add")[0])
    window = themed_window(qtbot, "dark", table, size=(360, 320))  # noqa: F841
    _settle()
    assert table.viewportMargins().bottom() == footer.height() > 0

    footer.hide()
    _settle()

    assert table.viewportMargins().bottom() == 0


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("kind", ["table", "tree"])
def test_a_frameless_views_header_has_a_rule_on_top(qtbot, theme, kind):
    if kind == "table":
        view = _table()
        header = view.horizontalHeader()
    else:
        view = QTreeWidget()
        view.setHeaderLabels(["Name", "Status"])
        QTreeWidgetItem(view, ["sh0010", "WIP"])
        header = view.header()
    fxstyle.mark_flush(view)
    # A line of text above, no filter bar: the rule is the header's own.
    window = themed_window(
        qtbot, theme, QLabel("Every row here exists tracker-wide."), view,
        size=(360, 240))
    _settle()

    border = fxstyle.colors().border
    for x in (0, header.width() // 2, header.width() - 1):
        assert near(pixel(window, header, x, 0), border, 2), x
    assert not near(pixel(window, header, header.width() // 2, 1), border, 2)
    # Its frame back, the card's edge is the rule: no second one.
    fxstyle.mark_flush(view, False)
    _settle()
    assert view.frameWidth() > 0
    assert not near(pixel(window, header, header.width() // 2, 0), border, 2)
