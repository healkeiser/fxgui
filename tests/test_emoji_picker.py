"""FXEmojiPicker and FXEmojiButton: pick an emoji from a popup grid."""

import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import (
    QApplication,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from fxgui.fxwidgets import DEFAULT_EMOJIS, FXEmojiButton, FXEmojiPicker


@pytest.fixture
def parent(qtbot):
    # A fixture, since pytest-qt holds its widgets only weakly.
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _shown_picker(qtbot, parent):
    picker = FXEmojiPicker(parent)
    picker.popup_at(parent.mapToGlobal(QPoint(0, 0)))
    qtbot.waitUntil(picker.isVisible)
    return picker


def _focused():
    return QApplication.focusWidget()


def test_the_default_set_is_about_forty_named_emoji():
    assert 35 <= len(DEFAULT_EMOJIS) <= 50
    assert len(set(DEFAULT_EMOJIS)) == len(DEFAULT_EMOJIS)
    assert "\U0001F44D" in DEFAULT_EMOJIS


def test_the_picker_is_a_popup_with_one_named_button_per_emoji(qtbot, parent):
    picker = _shown_picker(qtbot, parent)
    assert picker.windowFlags() & Qt.WindowType.Popup == Qt.WindowType.Popup
    buttons = picker.buttons()
    assert [b.text() for b in buttons] == list(DEFAULT_EMOJIS)
    assert buttons[0].toolTip() == "Thumbs Up"
    assert all(b.toolTip() for b in buttons)


def test_an_unknown_emoji_is_named_from_unicode(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    picker = FXEmojiPicker(parent, emojis=["\U0001F955"])
    assert picker.buttons()[0].toolTip() == "Carrot"


def test_a_click_emits_the_emoji_and_closes(qtbot, parent):
    picker = _shown_picker(qtbot, parent)
    with qtbot.waitSignal(picker.emoji_picked) as blocker:
        qtbot.mouseClick(picker.buttons()[2], Qt.MouseButton.LeftButton)
    assert blocker.args == [DEFAULT_EMOJIS[2]]
    assert not picker.isVisible()


def test_escape_closes_without_emitting(qtbot, parent):
    picker = _shown_picker(qtbot, parent)
    seen = []
    picker.emoji_picked.connect(seen.append)
    assert _focused() is picker.buttons()[0]
    qtbot.keyClick(_focused(), Qt.Key.Key_Escape)
    assert not picker.isVisible()
    assert seen == []


def test_arrows_move_and_enter_picks_the_neighbour(qtbot, parent):
    picker = _shown_picker(qtbot, parent)
    qtbot.keyClick(_focused(), Qt.Key.Key_Right)
    assert _focused() is picker.buttons()[1]
    qtbot.keyClick(_focused(), Qt.Key.Key_Down)
    assert _focused() is picker.buttons()[1 + picker.columns()]
    qtbot.keyClick(_focused(), Qt.Key.Key_Up)
    qtbot.keyClick(_focused(), Qt.Key.Key_Left)
    qtbot.keyClick(_focused(), Qt.Key.Key_Left)
    assert _focused() is picker.buttons()[0]
    qtbot.keyClick(_focused(), Qt.Key.Key_Right)
    with qtbot.waitSignal(picker.emoji_picked) as blocker:
        qtbot.keyClick(_focused(), Qt.Key.Key_Return)
    assert blocker.args == [DEFAULT_EMOJIS[1]]
    assert not picker.isVisible()


def test_space_picks_too(qtbot, parent):
    picker = _shown_picker(qtbot, parent)
    with qtbot.waitSignal(picker.emoji_picked) as blocker:
        qtbot.keyClick(_focused(), Qt.Key.Key_Space)
    assert blocker.args == [DEFAULT_EMOJIS[0]]


def test_popup_at_keeps_the_popup_on_screen(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    picker = FXEmojiPicker(parent)
    screen = QApplication.primaryScreen().availableGeometry()
    picker.popup_at(screen.bottomRight() + QPoint(50, 50))
    qtbot.waitUntil(picker.isVisible)
    assert screen.contains(picker.frameGeometry())


def _button_under(qtbot, window):
    button = FXEmojiButton(window)
    QVBoxLayout(window).addWidget(button)
    button.show()
    return button


def test_the_button_opens_its_picker_below_itself(qtbot, parent):
    button = _button_under(qtbot, parent)
    assert button.autoRaise()
    assert button.toolTip() == "Insert an emoji"
    assert not button.icon().isNull()
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    picker = button.picker()
    qtbot.waitUntil(picker.isVisible)
    assert picker.parent() is button
    below = button.mapToGlobal(QPoint(0, button.height()))
    assert picker.geometry().top() >= below.y() - 1


def test_the_button_re_emits_the_pick(qtbot, parent):
    button = _button_under(qtbot, parent)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    picker = button.picker()
    qtbot.waitUntil(picker.isVisible)
    with qtbot.waitSignal(button.emoji_picked) as blocker:
        qtbot.mouseClick(picker.buttons()[3], Qt.MouseButton.LeftButton)
    assert blocker.args == [DEFAULT_EMOJIS[3]]


def test_attach_inserts_at_the_cursor_of_a_plain_text_edit(qtbot, parent):
    button = _button_under(qtbot, parent)
    editor = QPlainTextEdit(parent)
    parent.layout().addWidget(editor)
    editor.show()
    button.attach(editor)
    editor.setPlainText("ab")
    cursor = editor.textCursor()
    cursor.setPosition(1)
    editor.setTextCursor(cursor)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    picker = button.picker()
    qtbot.waitUntil(picker.isVisible)
    qtbot.mouseClick(picker.buttons()[0], Qt.MouseButton.LeftButton)
    assert editor.toPlainText() == "a\U0001F44Db"
    qtbot.waitUntil(editor.hasFocus)


@pytest.mark.parametrize("kind", [QLineEdit, QTextEdit])
def test_attach_inserts_into_a_line_edit_and_a_text_edit(qtbot, parent, kind):
    button = _button_under(qtbot, parent)
    editor = kind(parent)
    button.attach(editor)
    button.emoji_picked.emit("\U0001F525")
    text = editor.text() if kind is QLineEdit else editor.toPlainText()
    assert text == "\U0001F525"


def test_attach_refuses_what_holds_no_text(qtbot, parent):
    with pytest.raises(TypeError):
        _button_under(qtbot, parent).attach(QWidget(parent))


def _windows() -> set:
    return {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()}


def test_building_them_with_a_parent_opens_no_window(qtbot, parent):
    before = _windows()
    button = _button_under(qtbot, parent)
    picker = FXEmojiPicker(parent)
    picker.buttons()[0].show()
    qtbot.wait(10)
    assert _windows() == before
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(button.picker().isVisible)
    assert _windows() - before == {id(button.picker())}
