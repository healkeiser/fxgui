"""The search bar is a line edit: one Tab stop, its icon and clear as actions."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLineEdit, QPushButton, QToolButton

# Internal
from fxgui.fxwidgets import FXSearchBar


def _bar(qtbot, **kwargs):
    bar = FXSearchBar(**kwargs)
    qtbot.addWidget(bar)
    bar.show()
    qtbot.waitExposed(bar)
    return bar


def test_the_bar_is_the_line_edit(qtbot, qapp):
    bar = _bar(qtbot)
    assert isinstance(bar, QLineEdit)
    assert bar.isClearButtonEnabled()
    assert bar.findChildren(QPushButton) == []


def test_typing_is_debounced_into_one_search_changed(qtbot, qapp):
    bar = _bar(qtbot, debounce_ms=50)
    seen = []
    bar.search_changed.connect(seen.append)
    with qtbot.waitSignal(bar.search_changed):
        qtbot.keyClicks(bar, "abc")
    assert seen == ["abc"]


def test_enter_submits_and_cancels_the_pending_change(qtbot, qapp):
    bar = _bar(qtbot, debounce_ms=50)
    changed, submitted = [], []
    bar.search_changed.connect(changed.append)
    bar.search_submitted.connect(submitted.append)
    qtbot.keyClicks(bar, "abc")
    qtbot.keyClick(bar, Qt.Key_Return)
    qtbot.wait(150)
    assert submitted == ["abc"] and changed == []


def test_the_bar_is_one_tab_stop_even_with_text_in_it(qtbot, qapp):
    from qtpy.QtWidgets import QVBoxLayout, QWidget

    window = QWidget()
    qtbot.addWidget(window)
    column = QVBoxLayout(window)
    before, bar, after = QLineEdit(), FXSearchBar(), QLineEdit()
    for widget in (before, bar, after):
        column.addWidget(widget)
    bar.setText("comp")
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    before.setFocus()
    qtbot.waitUntil(before.hasFocus)

    qtbot.keyClick(before, Qt.Key_Tab)
    assert bar.hasFocus()
    qtbot.keyClick(bar, Qt.Key_Tab)
    assert after.hasFocus(), "the clear button took no stop"
    for button in bar.findChildren(QToolButton):
        assert button.focusPolicy() == Qt.NoFocus


def test_clearing_leaves_focus_where_it_was(qtbot, qapp):
    from qtpy.QtWidgets import QVBoxLayout, QWidget

    window = QWidget()
    qtbot.addWidget(window)
    column = QVBoxLayout(window)
    other, bar = QLineEdit(), FXSearchBar()
    column.addWidget(other)
    column.addWidget(bar)
    bar.setText("comp")
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    other.setFocus()
    qtbot.waitUntil(other.hasFocus)

    bar.clear()

    assert bar.text() == "" and other.hasFocus()


def test_the_shortcut_shows_at_the_right_end_while_empty(qtbot, qapp):
    """As Lumen's filter box: the keys that reach it, until text hides them."""
    from fxgui.fxwidgets import FXKeycap

    bar = _bar(qtbot, keys="Ctrl+F")
    bar.resize(240, bar.height())
    cap = bar.findChild(FXKeycap)
    assert cap is not None and cap.isVisible()
    assert cap.geometry().right() < bar.width()
    assert cap.x() > bar.width() // 2
    bar.setText("hero")
    assert not cap.isVisible()


def test_keys_set_later_show_and_clear(qtbot, qapp):
    """A bar a wrapper built gets its keys afterwards, and can drop them."""
    from fxgui.fxwidgets import FXKeycap

    bar = _bar(qtbot)
    bar.resize(240, bar.height())
    bar.set_keys("/")
    cap = bar.findChild(FXKeycap)
    assert cap is not None and cap.keys() == "/" and cap.isVisible()
    bar.set_keys("")
    assert not cap.isVisible()


def test_a_bar_without_keys_shows_none(qtbot, qapp):
    from fxgui.fxwidgets import FXKeycap

    assert _bar(qtbot).findChild(FXKeycap) is None
