"""Rows, trees, tables and headers: the reference look's layout.

A header 36 px tall with its words 12 px in, cells 12 px in, a hairline
under every plain row, square list rows, small nav chips, 22 px tree levels
with a 14 px chevron.
"""

# Built-in
from pathlib import Path

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QListWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle

from _helpers import near, themed_window


def _ink_left(image, rect, ground=None):
    """Return the first column in `rect` that differs from its ground."""
    ground = ground or image.pixelColor(rect.right() - 2, rect.center().y())
    for x in range(rect.left(), rect.right()):
        for y in range(rect.top() + 2, rect.bottom() - 1):
            if not near(image.pixelColor(x, y), ground, 60):
                return x - rect.left()
    return None


def _tree(rows=3):
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name"])
    tree.setRootIsDecorated(False)
    for row in range(rows):
        QTreeWidgetItem(tree, [f"Mmm {row}"])
    return tree


def test_a_header_is_36_px_with_its_words_12_px_in(qtbot):
    tree = _tree()
    _window = themed_window(qtbot, "dark", tree)
    header = tree.header()
    assert header.height() == 36
    image = header.grab().toImage()
    rect = header.rect().adjusted(0, 0, 0, -1)
    # The words' first ink: 12 px in, give or take a glyph's side bearing.
    assert _ink_left(image, rect) in (12, 13)


def test_the_header_s_words_are_medium():
    sheet = (Path(fxstyle.__file__).parent / "qss" / "style.qss").read_text()
    section = sheet.split("QHeaderView::section  {", 1)[1].split("}", 1)[0]
    assert "font-weight: @emphasis_weight" in section


@pytest.mark.parametrize("selected", [False, True])
def test_a_plain_cell_s_text_sits_12_px_in(qtbot, selected):
    """In a tree, a list and a table, resting or highlighted alike."""
    tree = _tree()
    listing = QListWidget()
    table = QTableWidget(3, 1)
    for row in range(3):
        listing.addItem(f"Mmm {row}")
        table.setItem(row, 0, QTableWidgetItem(f"Mmm {row}"))
    _window = themed_window(qtbot, "dark", tree, listing, table, size=(320, 520))
    cells = (
        (tree, tree.topLevelItem(1)),
        (listing, listing.item(1)),
        (table, table.item(1, 0)),
    )
    for view, item in cells:
        item.setSelected(selected)
        rect = view.visualItemRect(item)
        image = view.viewport().grab().toImage()
        assert _ink_left(image, rect) in (12, 13), view


def test_a_plain_tree_rules_each_row(qtbot):
    tree = _tree()
    _window = themed_window(qtbot, "dark", tree)
    image = tree.viewport().grab().toImage()
    for row in range(2):
        rect = tree.visualItemRect(tree.topLevelItem(row))
        x = rect.right() - 4
        rule = image.pixelColor(x, rect.bottom())
        assert rule != image.pixelColor(x, rect.center().y()), row


def _unruled(image, rect):
    x = rect.right() - 12
    return image.pixelColor(x, rect.bottom()) == image.pixelColor(
        x, rect.center().y()
    )


def test_a_nav_list_draws_no_rule(qtbot):
    listing = QListWidget()
    for row in range(3):
        listing.addItem(f"Page {row}")
    fxstyle.mark_as_nav(listing)
    _window = themed_window(qtbot, "dark", listing)
    image = listing.viewport().grab().toImage()
    rect = listing.visualItemRect(listing.item(1))
    # The chip sits 1 px in: the row's own last line is the list's ground.
    assert _unruled(image, rect)


def test_a_combo_popup_draws_no_rule(qtbot):
    combo = QComboBox()
    combo.addItems(["One", "Two", "Three"])
    _window = themed_window(qtbot, "dark", combo)
    combo.showPopup()
    view = combo.view()
    qtbot.waitExposed(view)
    image = view.viewport().grab().toImage()
    rect = view.visualRect(view.model().index(2, 0))
    combo.hidePopup()
    assert view.window().windowType() == Qt.Popup
    assert _unruled(image, rect)


def test_a_list_row_is_square_and_full_bleed(qtbot):
    listing = QListWidget()
    for row in range(3):
        listing.addItem(f"Mmm {row}")
    _window = themed_window(qtbot, "dark", listing)
    listing.item(1).setSelected(True)
    rect = listing.visualItemRect(listing.item(1))
    image = listing.viewport().grab().toImage()
    fill = image.pixelColor(rect.right() - 2, rect.center().y())
    assert image.pixelColor(rect.topLeft()) == fill
    assert image.pixelColor(rect.left(), rect.bottom()) == fill


def test_a_nav_chip_is_round_at_6_px_and_1_px_in(qtbot):
    listing = QListWidget()
    for row in range(3):
        listing.addItem(f"Page {row}")
    fxstyle.mark_as_nav(listing)
    _window = themed_window(qtbot, "dark", listing)
    listing.setCurrentRow(1)
    rect = listing.visualItemRect(listing.item(1))
    image = listing.viewport().grab().toImage()
    ground = image.pixelColor(1, rect.center().y())
    chip = image.pixelColor(rect.center().x(), rect.top() + 1)
    assert chip != ground
    # 1 px in at the top, 4 px in at the side, as before.
    assert image.pixelColor(rect.center().x(), rect.top()) == ground
    assert image.pixelColor(3, rect.center().y()) == ground
    assert image.pixelColor(4, rect.center().y()) == chip
    # Inside a 6 px corner, outside a 9 px one.
    assert near(image.pixelColor(6, rect.top() + 3), chip, 12)
    assert image.pixelColor(4, rect.top() + 1) != chip


def test_a_tree_level_is_22_px_with_a_14_px_chevron_in_its_middle(qtbot):
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    for row in range(2):
        QTreeWidgetItem(QTreeWidgetItem(tree, [f"Row {row}"]), ["Child"])
    tree.topLevelItem(0).setExpanded(True)
    _window = themed_window(qtbot, "dark", tree)
    assert tree.indentation() == 22
    child = tree.visualItemRect(tree.topLevelItem(0).child(0))
    assert child.left() == 44
    rect = tree.visualItemRect(tree.topLevelItem(1))
    image = tree.viewport().grab().toImage()
    ground = image.pixelColor(rect.right() - 2, rect.top() + 3)
    inked = [
        (x, y)
        for x in range(rect.left())
        for y in range(rect.top(), rect.bottom())
        if image.pixelColor(x, y) != ground
    ]
    xs = [x for x, _ in inked]
    ys = [y - rect.top() for _, y in inked]
    # Lucide's chevron-right fills the middle third of its 14 px box.
    assert max(xs) - min(xs) <= 7
    assert abs((min(xs) + max(xs)) / 2 - 11) <= 1
    assert abs((min(ys) + max(ys)) / 2 - rect.height() / 2) <= 1.5


def test_a_set_indentation_is_kept(qtbot):
    tree = _tree()
    tree.setIndentation(30)
    _window = themed_window(qtbot, "dark", tree)
    assert tree.indentation() == 30


def test_an_icon_grid_draws_no_rule(qtbot):
    from qtpy.QtWidgets import QListView

    from fxgui.fxstyle import _ruled

    listing = QListWidget()
    listing.setViewMode(QListView.IconMode)
    assert not _ruled(listing)
    listing.setViewMode(QListView.ListMode)
    assert _ruled(listing)


def test_a_tree_s_row_rule_runs_under_its_indentation_too(qtbot):
    from qtpy.QtWidgets import QWidget
    from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem

    from fxgui import fxstyle

    host = QWidget()
    qtbot.addWidget(host)
    fxstyle.register_themed_root(host)
    tree = QTreeWidget(host)
    tree.setHeaderHidden(True)
    parent = QTreeWidgetItem(tree, ["seq010"])
    child = QTreeWidgetItem(parent, ["sh0010"])
    QTreeWidgetItem(parent, ["sh0020"])
    tree.expandAll()
    tree.resize(300, 200)
    host.resize(300, 200)
    host.show()
    qtbot.waitExposed(host)

    image = tree.viewport().grab().toImage()
    cell = tree.visualItemRect(child)
    bottom = cell.bottom()
    under_cell = image.pixelColor(cell.left() + 20, bottom).name()
    under_indent = image.pixelColor(2, bottom).name()
    # One line, edge to edge: the same ink under the indent as under the cell.
    assert under_indent == under_cell
    assert under_indent != image.pixelColor(2, bottom - 4).name()
