"""The stretch that pushes the Clear button, and what it does when
there is no Clear button to push.

A consumer with nothing to clear -- a live view of a session's log --
hides that button. The stretch was left behind pushing nothing, and the
50px cap the search bar applies then reads as dead space between the
bar's close button and the widget's own right edge.
"""

# Internal
from fxgui.fxwidgets import FXOutputLogWidget


def _shown(qtbot, clear=True):
    """A log pane on screen, with or without its Clear button.

    On screen because the assertions are about geometry, and the search
    bar is laid out when it is first opened.
    """
    pane = FXOutputLogWidget(capture_output=False)
    if not clear:
        pane.clear_button.hide()
    qtbot.addWidget(pane)
    pane.resize(600, 300)
    pane.show()
    qtbot.waitExposed(pane)
    return pane


def test_the_spacer_holds_room_while_the_clear_button_is_there(qtbot, qapp):
    pane = _shown(qtbot)

    pane._show_search()

    assert pane.log_spacer.isVisible()
    assert pane.clear_button.isVisible()


def test_a_hidden_clear_button_takes_its_spacer_with_it(qtbot, qapp):
    """The right edge of the search bar is the right edge of the widget,
    rather than 50 pixels short of it."""
    pane = _shown(qtbot, clear=False)

    pane._show_search()

    assert not pane.log_spacer.isVisible()
    assert (
        pane.close_search_button.geometry().right()
        >= pane.width() - pane.close_search_button.width()
    ), "the search bar reaches the widget's own right edge"


def test_the_spacer_comes_back_with_the_clear_button(qtbot, qapp):
    pane = _shown(qtbot, clear=False)
    pane._show_search()

    pane.clear_button.show()
    pane._show_search()

    assert pane.log_spacer.isVisible()
