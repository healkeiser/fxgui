"""The bottom row: the search bar takes the width, Clear keeps the right
edge, and an empty row takes no room."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtTest import QTest

# Internal
from fxgui.fxwidgets import FXOutputLogWidget


def _shown(qtbot, clear=True):
    """A log pane on screen, with or without its Clear button."""
    pane = FXOutputLogWidget()
    if not clear:
        pane.clear_button.hide()
    qtbot.addWidget(pane)
    pane.resize(600, 300)
    pane.show()
    qtbot.waitExposed(pane)
    return pane


def _right_edge(pane, widget, qapp):
    qapp.processEvents()
    return widget.mapTo(pane, widget.rect().topRight()).x()


def test_clear_keeps_the_right_edge_beside_the_search_bar(qtbot, qapp):
    pane = _shown(qtbot)

    pane.show_search()

    assert _right_edge(pane, pane.clear_button, qapp) == pane.width() - 1
    assert _right_edge(pane, pane.close_search_button, qapp) < (
        pane.clear_button.mapTo(pane, pane.clear_button.rect().topLeft()).x()
    )


def test_without_clear_the_search_bar_reaches_the_right_edge(qtbot, qapp):
    pane = _shown(qtbot, clear=False)

    pane.show_search()

    assert _right_edge(pane, pane.close_search_button, qapp) == pane.width() - 1


def test_clear_alone_sits_at_the_right_edge(qtbot, qapp):
    pane = _shown(qtbot)

    assert _right_edge(pane, pane.clear_button, qapp) == pane.width() - 1


def _output_gap(pane, qapp):
    qapp.processEvents()
    return pane.height() - 1 - pane.output_area.geometry().bottom()


def test_an_empty_bottom_row_takes_no_room(qtbot, qapp):
    pane = _shown(qtbot, clear=False)

    assert _output_gap(pane, qapp) == 0


def test_the_bottom_row_follows_the_clear_button_both_ways(qtbot, qapp):
    pane = _shown(qtbot)
    pane.clear_button.hide()
    assert _output_gap(pane, qapp) == 0

    pane.clear_button.show()

    assert _output_gap(pane, qapp) > 0


def test_the_search_bar_still_opens_and_closes_without_clear(qtbot, qapp):
    pane = _shown(qtbot, clear=False)

    pane.show_search()
    assert pane.search_input.isVisible()
    assert _output_gap(pane, qapp) > 0
    pane._hide_search()

    assert not pane.search_input.isVisible()
    assert _output_gap(pane, qapp) == 0


def _searching(qtbot, qapp, text="match"):
    pane = _shown(qtbot)
    pane.append_many([f"{text} {index}" for index in range(3)])
    qtbot.waitUntil(lambda: not pane._pending_logs)
    pane.show_search()
    pane.search_input.setText(text)
    return pane


def test_shift_enter_goes_to_the_previous_match(qtbot, qapp):
    pane = _searching(qtbot, qapp)
    QTest.keyClick(pane.search_input, Qt.Key_Return)
    QTest.keyClick(pane.search_input, Qt.Key_Return)
    assert pane.search_count_label.text() == "2 of 3"

    QTest.keyClick(pane.search_input, Qt.Key_Return, Qt.ShiftModifier)

    assert pane.search_count_label.text() == "1 of 3"


def test_typing_counts_once_the_keys_stop(qtbot, qapp, monkeypatch):
    pane = _searching(qtbot, qapp)
    pane._update_search_count()
    calls = []
    real = pane.output_area.document().find
    monkeypatch.setattr(
        pane.output_area.document().__class__,
        "find",
        lambda self, *args: calls.append(1) or real(*args),
    )

    for key in "atch":
        pane.search_input.setText("m" + key)

    assert calls == [], "no scan per keystroke"
    qtbot.waitUntil(lambda: bool(calls))


def test_the_search_widgets_live_in_one_container(qtbot, qapp):
    pane = _shown(qtbot)

    pane.show_search()

    for widget in (
        pane.search_label,
        pane.search_input,
        pane.search_count_label,
        pane.prev_button,
        pane.next_button,
        pane.close_search_button,
    ):
        assert widget.parentWidget() is pane._search_bar
        assert not widget.isHidden()
