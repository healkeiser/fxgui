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
    return bar


def test_set_focus_takes_a_reason_and_lands_in_the_field(qtbot, qapp):
    bar = _bar(qtbot)
    bar.setFocus(Qt.TabFocusReason)
    qtbot.waitUntil(lambda: bar._input.hasFocus(), timeout=1000)


def test_focus_in_the_field_lights_the_container(qtbot, qapp):
    bar = _bar(qtbot)
    bar.setFocus()
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
