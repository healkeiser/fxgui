"""FXKeyboardTree, FXSplitButton and FXFilteredTree answer the keyboard."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QLineEdit,
    QMenu,
    QToolButton,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui.fxwidgets import FXFilteredTree, FXKeyboardTree, FXSplitButton


def _shown(qtbot, *widgets):
    window = QWidget()
    qtbot.addWidget(window)
    layout = QVBoxLayout(window)
    for widget in widgets:
        layout.addWidget(widget)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitActive(window)
    return window


def _press(key, modifiers=Qt.NoModifier):
    """Press `key` on whatever holds focus, as a person would."""
    QApplication.processEvents()
    focus = QApplication.focusWidget()
    assert focus is not None, "nothing holds focus"
    QTest.keyClick(focus, key, modifiers)


def _tree_and_field(qtbot):
    tree = FXKeyboardTree()
    field = QLineEdit()
    window = _shown(qtbot, field, tree)
    top = QTreeWidgetItem(tree, ["top"])
    QTreeWidgetItem(top, ["child"])
    QTreeWidgetItem(tree, ["other"])
    tree.setCurrentItem(top)
    tree.setFocus()
    QApplication.processEvents()
    assert QApplication.focusWidget() is tree
    return window, tree, field, top


def test_typing_on_the_tree_goes_to_the_filter_field(qtbot):
    _window, tree, field, _top = _tree_and_field(qtbot)
    tree.type_into(field)
    _press(Qt.Key_A)
    assert field.hasFocus(), "the first character moves focus to the field"
    _press(Qt.Key_S)
    assert field.text() == "as"


def test_qt_s_own_tree_keys_stay_on_the_tree(qtbot):
    _window, tree, field, top = _tree_and_field(qtbot)
    tree.type_into(field)
    _press(Qt.Key_Plus)
    assert top.isExpanded()
    _press(Qt.Key_Minus)
    assert not top.isExpanded()
    _press(Qt.Key_Asterisk)
    assert top.isExpanded()
    _press(Qt.Key_Space)
    assert field.text() == "" and tree.hasFocus()


def test_a_command_chord_is_not_typing(qtbot):
    _window, tree, field, _top = _tree_and_field(qtbot)
    tree.type_into(field)
    _press(Qt.Key_A, Qt.ControlModifier)
    assert field.text() == "" and tree.hasFocus()


def test_without_a_field_typing_stays_qt_s(qtbot):
    _window, tree, field, _top = _tree_and_field(qtbot)
    _press(Qt.Key_O)
    assert tree.currentItem().text(0) == "other", "Qt's keyboard search"


def test_enter_runs_the_primary_act_on_the_current_row(qtbot):
    _window, tree, _field, top = _tree_and_field(qtbot)
    acted = []
    tree.set_primary_act(acted.append)
    _press(Qt.Key_Return)
    assert acted == [top]


def test_the_menu_key_and_shift_f10_ask_for_the_row_s_menu(qtbot):
    _window, tree, _field, top = _tree_and_field(qtbot)
    asked = []
    tree.customContextMenuRequested.connect(asked.append)
    _press(Qt.Key_Menu)
    _press(Qt.Key_F10, Qt.ShiftModifier)
    centre = tree.visualItemRect(top).center()
    assert asked == [centre, centre]


def test_the_menu_key_on_an_empty_tree_asks_nothing(qtbot):
    tree = FXKeyboardTree()
    _window = _shown(qtbot, tree)
    asked = []
    tree.customContextMenuRequested.connect(asked.append)
    assert tree.open_current_menu() is False
    assert asked == []


def _split(qtbot):
    button = FXSplitButton()
    button.setText("Launch")
    menu = QMenu(button)
    menu.addAction("Other")
    button.setMenu(menu)
    window = _shown(qtbot, button)
    button.setFocus()
    QApplication.processEvents()
    assert QApplication.focusWidget() is button
    return window, button, menu


def test_enter_clicks_a_split_button(qtbot):
    _window, button, _menu = _split(qtbot)
    clicks = []
    button.clicked.connect(lambda: clicks.append(True))
    _press(Qt.Key_Return)
    assert clicks == [True]


def test_alt_down_and_the_menu_key_open_the_dropdown(qtbot):
    window, button, menu = _split(qtbot)
    _press(Qt.Key_Down, Qt.AltModifier)
    assert menu.isVisible()
    menu.close()
    window.activateWindow()
    qtbot.waitActive(window)
    button.setFocus()
    _press(Qt.Key_Menu)
    assert menu.isVisible()
    menu.close()


def test_the_dropdown_hint_names_both_keys():
    hint = FXSplitButton.dropdown_hint()
    assert "Down" in hint and "Menu" in hint


def test_settle_drops_the_arrow_when_the_menu_is_empty(qtbot):
    button = FXSplitButton()
    button.setMenu(QMenu(button))
    _window = _shown(qtbot, button)
    button.settle(click=True)
    assert button.menu() is None
    assert button.isVisible()


def test_settle_makes_a_click_open_the_menu_when_nothing_else_runs(qtbot):
    button = FXSplitButton()
    menu = QMenu(button)
    menu.addAction("one")
    button.setMenu(menu)
    button.settle(click=False)
    assert button.popupMode() == QToolButton.InstantPopup


def test_settle_hides_a_button_with_nothing_to_do(qtbot):
    button = FXSplitButton()
    window = _shown(qtbot, button)
    button.settle(click=False)
    assert not button.isVisible()
    assert window.isVisible()


def test_a_filtered_tree_narrows_as_its_bar_changes(qtbot):
    panel = FXFilteredTree()
    _window = _shown(qtbot, panel)
    top = QTreeWidgetItem(panel.tree, ["Beauty"])
    other = QTreeWidgetItem(panel.tree, ["Other"])
    panel.filter_bar.setText("beau")
    qtbot.waitUntil(other.isHidden)
    assert not top.isHidden()


def test_a_filtered_tree_takes_typing_and_folds(qtbot):
    panel = FXFilteredTree()
    _window = _shown(qtbot, panel)
    top = QTreeWidgetItem(panel.tree, ["top"])
    QTreeWidgetItem(top, ["child"])
    panel.tree.setCurrentItem(top)
    panel.tree.setFocus()
    _press(Qt.Key_T)
    assert panel.filter_bar.text() == "t"
    panel.expand_button.click()
    assert top.isExpanded()
    panel.collapse_button.click()
    assert not top.isExpanded()


def test_a_filtered_tree_wraps_a_tree_it_is_given(qtbot):
    tree = FXKeyboardTree()
    panel = FXFilteredTree(tree)
    assert panel.tree is tree
    assert tree.parent() is panel


def test_the_fold_buttons_wear_the_house_tip(qtbot):
    panel = FXFilteredTree()
    qtbot.addWidget(panel)
    assert panel.expand_button.statusTip() == "Expand all"
    assert panel.collapse_button.statusTip() == "Collapse all"
