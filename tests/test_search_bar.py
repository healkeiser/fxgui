"""The search bar's focus ring and its focus call both work."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLineEdit

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXSearchBar


def _bar(qtbot):
    host = QLineEdit()
    bar = FXSearchBar()
    qtbot.addWidget(bar)
    qtbot.addWidget(host)
    bar.show()
    qtbot.waitExposed(bar)
    bar.activateWindow()
    qtbot.waitUntil(bar.isActiveWindow, timeout=1000)
    return bar


def test_set_focus_takes_a_reason_and_lands_in_the_field(qtbot, qapp):
    bar = _bar(qtbot)
    bar.setFocus(Qt.TabFocusReason)
    qtbot.waitUntil(lambda: bar._input.hasFocus(), timeout=1000)


def test_focus_in_the_field_lights_the_container(qtbot, qapp):
    bar = _bar(qtbot)
    # Activation gave the field focus; it comes back by Tab.
    bar._input.clearFocus()
    bar.setFocus(Qt.TabFocusReason)
    qtbot.waitUntil(lambda: bar._input.hasFocus(), timeout=1000)
    assert bar._search_container.property("focused") is True
    bar._input.clearFocus()
    assert bar._search_container.property("focused") is False


def test_search_bar_styles_through_the_theme_sheet(qtbot, qapp):
    bar = _bar(qtbot)
    for child in (bar._search_container, bar._input, bar._clear_button,
                  bar._search_icon):
        assert child.styleSheet() == ""
    assert 'fx_search_container[focused="true"]' in fxstyle.build_stylesheet()


def test_the_bar_is_one_tab_stop_even_with_text_in_it(qtbot, qapp):
    from qtpy.QtWidgets import QVBoxLayout, QWidget

    window = QWidget()
    qtbot.addWidget(window)
    column = QVBoxLayout(window)
    before, bar, after = QLineEdit(), FXSearchBar(), QLineEdit()
    for widget in (before, bar, after):
        column.addWidget(widget)
    bar.text = "comp"
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    before.setFocus()
    qtbot.waitUntil(before.hasFocus, timeout=1000)

    qtbot.keyClick(before, Qt.Key_Tab)
    assert bar.line_edit().hasFocus()
    qtbot.keyClick(bar.line_edit(), Qt.Key_Tab)
    assert after.hasFocus(), "the clear button took no stop"


def test_line_edit_is_the_field_typing_goes_to(qtbot, qapp):
    bar = FXSearchBar()
    qtbot.addWidget(bar)

    qtbot.keyClicks(bar.line_edit(), "fx")

    assert bar.text == "fx" and isinstance(bar.line_edit(), QLineEdit)
