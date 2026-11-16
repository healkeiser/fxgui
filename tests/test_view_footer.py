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



# What a full window's teardown does to a footer (a dock, a window class of
# Python's deleted by Qt): the scroll bars' containers lose their wrappers,
# then the view still resizes and hides. The footer's event filter read a
# dead wrapper, raised mid-teardown, and the process died.
_TEARDOWN = """
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, {root!r})
import shiboken6
from qtpy.QtWidgets import (
    QApplication, QHBoxLayout, QPushButton, QTableWidget, QVBoxLayout,
    QWidget)
from fxgui import fxstyle
from fxgui.fxwidgets import FXSummaryRow, FXViewFooter

app = QApplication(sys.argv)
window = QWidget()
fxstyle.register_themed_root(window)
table = QTableWidget(40, 3)
for column in range(3):
    table.setColumnWidth(column, 300)
FXSummaryRow(table).set_texts(["40 records"])
actions = QHBoxLayout()
actions.addWidget(QPushButton("Add"))
footer = FXViewFooter(table, actions)
QVBoxLayout(window).addWidget(table)
window.resize(360, 320)
window.show()
for _ in range(3):
    app.processEvents()
for bar in (table.horizontalScrollBar(), table.verticalScrollBar()):
    # The same wrapper the footer holds: one per C++ object.
    shiboken6.invalidate(bar.parentWidget())
table.resize(table.width() - 20, table.height() - 20)
footer.hide()
window.close()
for _ in range(3):
    app.processEvents()
print("survived")
"""


def test_a_footer_outlives_the_wrappers_a_teardown_lets_go():
    import os
    import subprocess
    import sys

    from _helpers import isolated

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-c", isolated(_TEARDOWN.format(root=root))],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "already deleted" not in result.stderr, result.stderr[-2000:]
    assert result.stdout.strip().splitlines()[-1] == "survived"


# A summary row made before the footer, then a new row size: the summary
# set the margin from the new row height, the footer at once from the
# summary's height, which lags until the summary has moved; each set raised
# the other's event, without end, and the process died.
_ROW_SIZES = """
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, {root!r})
from qtpy.QtWidgets import (
    QApplication, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)
from fxgui import fxstyle
from fxgui.fxwidgets import FXSummaryRow, FXViewFooter

app = QApplication(sys.argv)
window = QWidget()
fxstyle.register_themed_root(window)
view = QTreeWidget()
view.setColumnCount(2)
for _ in range(5):
    QTreeWidgetItem(view, ["a", "b"])
FXSummaryRow(view).set_texts(["5 rows"])
actions = QHBoxLayout()
actions.addWidget(QPushButton("Add"))
footer = FXViewFooter(view, actions)
QVBoxLayout(window).addWidget(view)
window.resize(360, 320)
window.show()
for _ in range(3):
    app.processEvents()
for size in ("small", "big", "normal"):
    fxstyle.apply_row_size(size, save=False)
    for _ in range(3):
        app.processEvents()
    assert view.viewportMargins().bottom() == (
        fxstyle.row_height(view) + footer.height()), size
print("survived")
"""


def test_a_row_size_change_settles_the_summary_and_the_footer():
    import os
    import subprocess
    import sys

    from _helpers import isolated

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-c", isolated(_ROW_SIZES.format(root=root))],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().splitlines()[-1] == "survived"
