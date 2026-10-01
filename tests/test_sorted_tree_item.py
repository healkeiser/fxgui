"""FXSortedTreeWidgetItem sorts by a role key first, natural text after."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QTreeWidget

# Internal
from fxgui.fxwidgets import FXSortedTreeWidgetItem


def _sorted(qtbot, rows, column=0):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setColumnCount(2)
    for texts, key in rows:
        item = FXSortedTreeWidgetItem(tree, texts)
        if key is not None:
            item.setData(column, FXSortedTreeWidgetItem.SORT_ROLE, key)
    tree.sortItems(column, Qt.AscendingOrder)
    return [
        tree.topLevelItem(i).text(column)
        for i in range(tree.topLevelItemCount())
    ]


def test_text_sorts_naturally(qtbot):
    rows = [(["v10", ""], None), (["v9", ""], None), (["v1", ""], None)]
    assert _sorted(qtbot, rows) == ["v1", "v9", "v10"]


def test_a_sort_key_beats_the_text(qtbot):
    rows = [(["Mon", ""], 1), (["Wed", ""], 3), (["Tue", ""], 2)]
    assert _sorted(qtbot, rows) == ["Mon", "Tue", "Wed"]


def test_the_sort_column_s_own_key_is_read(qtbot):
    rows = [(["a", "big"], 20), (["b", "small"], 3)]
    assert _sorted(qtbot, rows, column=1) == ["small", "big"]


def test_a_row_without_a_key_falls_back_to_text(qtbot):
    rows = [(["b", ""], 1), (["a", ""], None)]
    assert _sorted(qtbot, rows) == ["a", "b"]


def test_an_item_outside_a_tree_compares_column_zero():
    low, high = FXSortedTreeWidgetItem(["a2"]), FXSortedTreeWidgetItem(["a10"])
    assert low < high
    assert not high < low

