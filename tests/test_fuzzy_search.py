"""Fuzzy search list and tree: one base, recursive filter, item bookkeeping."""

# Third-party
from qtpy.QtCore import Qt

# Internal
from fxgui.fxwidgets import FXFuzzySearchList, FXFuzzySearchTree


def _tree(qtbot):
    tree = FXFuzzySearchTree()
    qtbot.addWidget(tree)
    return tree


def test_list_and_tree_share_one_base():
    from fxgui.fxwidgets._fuzzy_search_list import _FXFuzzySearchBase

    assert issubclass(FXFuzzySearchList, _FXFuzzySearchBase)
    assert issubclass(FXFuzzySearchTree, _FXFuzzySearchBase)


def test_removing_a_parent_removes_its_children(qtbot):
    tree = _tree(qtbot)
    tree.set_items({"Characters": ["Hero", "Villain"], "Props": ["Sword"]})
    assert tree.remove_item("Characters")
    assert sorted(tree.items) == ["Props", "Sword"]


def test_duplicate_texts_are_separate_items(qtbot):
    tree = _tree(qtbot)
    tree.set_items({"A": ["Hero"], "B": ["Hero"]})
    assert tree.items.count("Hero") == 2
    assert tree.remove_item("Hero")
    assert tree.items.count("Hero") == 1


def test_item_data_lives_under_one_role(qtbot):
    tree = _tree(qtbot)
    item = tree.add_item("Hero", data={"id": 7, "type": "asset"})
    assert item.data(FXFuzzySearchTree.DATA_ROLE) == {"id": 7, "type": "asset"}


def test_a_child_can_be_added_under_an_item(qtbot):
    tree = _tree(qtbot)
    first = tree.add_item("Group")
    tree.add_item("Group")
    tree.add_item("Leaf", parent=first)
    assert first.rowCount() == 1


def test_the_tree_filter_is_recursive(qtbot):
    tree = _tree(qtbot)
    tree.set_items({"Characters": ["character_hero"], "Props": ["sword"]})
    grand = tree.get_item("character_hero")
    tree.add_item("deep_needle", parent=grand)
    proxy = tree.proxy_model
    assert proxy.isRecursiveFilteringEnabled()
    tree._on_search_changed("needle")
    top = [proxy.index(r, 0).data() for r in range(proxy.rowCount())]
    assert top == ["Characters"]
    hero = proxy.index(0, 0, proxy.index(0, 0))
    assert hero.data() == "character_hero"
    assert proxy.index(0, 0, hero).data(Qt.DisplayRole) == "deep_needle"
