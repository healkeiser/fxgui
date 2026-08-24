"""A banner you are meant to answer has to wait for the answer.

The banner had one action button, wired to a bare `action_clicked` signal:
the caller got told the button was pressed and nothing else happened. The
banner stayed up, and it stayed on its five-second timer, so "Retry" could
slide off the screen while the artist was still moving the mouse toward it.

An action now carries its callback, cancels the auto-dismiss on the way in,
and closes the banner on the way out.
"""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import FXNotificationBanner
from fxgui.fxwidgets._constants import ERROR


def _host(qtbot):
    """A parent wide enough for a 320px banner to have somewhere to go."""
    parent = QWidget()
    parent.resize(800, 600)
    qtbot.addWidget(parent)
    parent.show()
    return parent


def test_actions_run_their_callback_then_close_the_banner(qtbot):
    """Answering the banner both does the thing and clears the banner."""
    parent = _host(qtbot)
    answered = []
    banner = FXNotificationBanner(
        parent=parent,
        message="Publish failed on 3 shots.",
        severity_type=ERROR,
        actions={"Retry": lambda: answered.append("Retry")},
    )
    banner.show()

    banner._action_buttons[0].click()

    assert answered == ["Retry"]
    qtbot.waitUntil(lambda: not banner.isVisible(), timeout=3000)


def test_actions_cancel_the_auto_dismiss(qtbot):
    """A banner with a button on it does not walk off while you reach for it."""
    parent = _host(qtbot)
    banner = FXNotificationBanner(
        parent=parent,
        message="Overwrite the published version?",
        timeout=200,
        actions={"Overwrite": lambda: None, "Keep both": lambda: None},
    )
    banner.show()

    qtbot.wait(400)  # Twice the timeout it was asked for
    assert banner.isVisible()
    assert not banner._dismiss_timer.isActive()


def test_actions_keep_their_declared_order(qtbot):
    """Left to right is the order they were given in, first one leading."""
    parent = _host(qtbot)
    banner = FXNotificationBanner(
        parent=parent,
        message="Overwrite the published version?",
        actions={"Overwrite": lambda: None, "Keep both": lambda: None},
    )

    labels = [button.text() for button in banner._action_buttons]
    assert labels == ["Overwrite", "Keep both"]


def test_action_text_still_emits_action_clicked(qtbot):
    """The old single-button API keeps working, on top of the new one."""
    parent = _host(qtbot)
    banner = FXNotificationBanner(
        parent=parent, message="File saved.", action_text="Undo"
    )
    banner.show()

    with qtbot.waitSignal(banner.action_clicked, timeout=1000):
        banner._action_buttons[0].click()


def test_a_plain_banner_grows_no_action_row(qtbot):
    """No actions, no layout, no stray gap above the bottom margin."""
    parent = _host(qtbot)
    plain = FXNotificationBanner(parent=parent, message="File saved.")
    acting = FXNotificationBanner(
        parent=parent, message="File saved.", actions={"Undo": lambda: None}
    )

    assert plain._actions_layout is None
    assert acting.sizeHint().height() > plain.sizeHint().height()


def test_action_buttons_are_clickable_looking(qtbot):
    """The pointer says the banner can be answered."""
    parent = _host(qtbot)
    banner = FXNotificationBanner(
        parent=parent,
        message="Publish failed.",
        actions={"Retry": lambda: None},
    )

    button = banner._action_buttons[0]
    assert button.cursor().shape() == Qt.PointingHandCursor
    assert button.styleSheet()  # Styled, not a bare platform button
