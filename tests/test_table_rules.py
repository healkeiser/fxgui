"""A table rules its rows with a hairline, as Lumen's, and keeps cell colours."""

# Third-party
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTableWidget, QTableWidgetItem

# Internal
from _helpers import themed_window


def test_a_row_ends_in_a_hairline_over_its_own_colour(qtbot):
    table = QTableWidget(2, 2)
    for row in range(2):
        for column in range(2):
            table.setItem(row, column, QTableWidgetItem("cell"))
    table.item(0, 1).setData(Qt.BackgroundRole, QColor("#ff0000"))
    window = themed_window(qtbot, "dark", table)
    image = table.viewport().grab().toImage()
    bottom = table.rowViewportPosition(0) + table.rowHeight(0) - 1
    left = table.columnViewportPosition(0) + 2
    middle = table.rowViewportPosition(0) + table.rowHeight(0) // 2
    assert image.pixelColor(QPoint(left, bottom)) != image.pixelColor(
        QPoint(left, middle)
    ), "no rule under the row"
    red = table.columnViewportPosition(1) + 2
    assert image.pixelColor(QPoint(red, middle)).name() == "#ff0000"
    assert window is not None


def test_the_sort_arrow_follows_the_label(qtbot):
    """As Lumen's: right after the words, not pinned to the section's end."""
    from qtpy.QtCore import QRect
    from qtpy.QtWidgets import QStyle, QStyleOptionHeader

    from fxgui import fxstyle

    style = fxstyle.FXProxyStyle()
    option = QStyleOptionHeader()
    option.rect = QRect(0, 0, 400, 32)
    option.text = "Name"
    option.sortIndicator = QStyleOptionHeader.SortDown
    arrow = style.subElementRect(QStyle.SE_HeaderArrow, option, None)
    assert 20 < arrow.left() < 100, arrow
    assert arrow.width() == arrow.height() == fxstyle._SORT_ARROW


def test_a_round_corner_shows_what_the_view_sits_on(qtbot):
    """Outside its arc a framed view shows its parent's colour, not surface."""
    from qtpy.QtWidgets import QFrame, QTreeWidget, QVBoxLayout

    holder = QFrame()
    holder.setObjectName("holder")
    holder.setStyleSheet("#holder { background: #ff0000; }")
    tree = QTreeWidget(holder)
    QVBoxLayout(holder).addWidget(tree)
    window = themed_window(qtbot, "dark", holder)
    image = window.grab().toImage()
    corner = tree.mapTo(window, tree.rect().topLeft())
    assert image.pixelColor(corner.x() + 1, corner.y() + 1).name() == "#ff0000"


def test_a_right_aligned_label_keeps_the_arrow_at_its_end(qtbot):
    from qtpy.QtCore import QRect, Qt
    from qtpy.QtWidgets import QProxyStyle, QStyle, QStyleOptionHeader

    from fxgui import fxstyle

    style = fxstyle.FXProxyStyle()
    option = QStyleOptionHeader()
    option.rect = QRect(0, 0, 400, 32)
    option.text = "Name"
    option.textAlignment = Qt.AlignRight | Qt.AlignVCenter
    option.sortIndicator = QStyleOptionHeader.SortDown
    arrow = style.subElementRect(QStyle.SE_HeaderArrow, option, None)
    # The base style's place, untouched.
    plain = QProxyStyle().subElementRect(QStyle.SE_HeaderArrow, option, None)
    assert arrow == plain
