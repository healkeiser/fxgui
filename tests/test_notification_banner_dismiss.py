"""A banner that is leaving has to actually leave.

All three slides -- in, out, and the restack that closes the gap a
dismissed banner leaves -- drove the same `QPropertyAnimation`, and each
one connected its own handler to `finished` without ever taking the
previous one off. `stop()` does not emit `finished`, so a handler that
was interrupted stayed connected and fired at the end of whichever slide
came next.

Two banners auto-dismissing a beat apart was enough: the first one's
completion restacked the survivors, the second was still visible so it
counted as a survivor, its slide-out was stopped half off-screen and
restarted as a vertical move, and its stale slide-out handler hid it
there. The artist saw a banner stall in the middle of the window and
blink out.
"""

# Third-party
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import _compat
from fxgui.fxwidgets import FXNotificationBanner
from fxgui.fxwidgets._severity import INFO


def _host(qtbot):
    """A parent wide enough for a 320px banner to have somewhere to go."""
    parent = QWidget()
    parent.resize(800, 600)
    qtbot.addWidget(parent)
    parent.show()
    return parent


def _banner(qtbot, parent, message):
    """A shown banner that never dismisses itself on a timer."""
    banner = FXNotificationBanner(
        parent=parent, message=message, severity_type=INFO, timeout=0
    )
    banner.show()
    # Where it was when it hid; it deletes itself right after.
    banner.closed.connect(lambda: _left_at.__setitem__(message, banner.x()))
    return banner


_left_at = {}


def _resting_x(banner):
    """Where the banner sits once it has finished sliding in."""
    return banner.parent().width() - banner.width() - banner._margin


def _assert_gone(qtbot, banner, parent):
    """The banner is hidden, and hidden from off-screen, not from mid-window."""
    message = banner._message
    qtbot.waitUntil(lambda: message in _left_at)
    assert _left_at.pop(message) >= parent.width(), (
        f"{message!r} stopped instead of leaving past x={parent.width()}"
    )


def test_staggered_dismissals_both_leave_the_window(qtbot):
    """The second banner's slide-out survives the first one's restack."""
    parent = _host(qtbot)
    first = _banner(qtbot, parent, "first")
    second = _banner(qtbot, parent, "second")
    qtbot.waitUntil(lambda: second.x() == _resting_x(second))

    # Far enough apart that `first` completes while `second` is mid-flight
    first.dismiss()
    qtbot.wait(120)
    second.dismiss()

    _assert_gone(qtbot, first, parent)
    _assert_gone(qtbot, second, parent)


def test_dismiss_during_slide_in_leaves_the_window(qtbot):
    """Closing a banner before it has arrived does not send it back in."""
    parent = _host(qtbot)
    banner = _banner(qtbot, parent, "impatient")
    qtbot.wait(60)  # Still sliding in
    banner.dismiss()

    _assert_gone(qtbot, banner, parent)


def test_a_new_banner_does_not_stack_under_a_leaving_one(qtbot):
    """A dismissing banner holds no slot, so the next one takes the top."""
    parent = _host(qtbot)
    leaving = _banner(qtbot, parent, "leaving")
    qtbot.waitUntil(lambda: leaving.x() == _resting_x(leaving))
    leaving.dismiss()

    arriving = _banner(qtbot, parent, "arriving")
    assert arriving.y() == arriving._margin


def test_a_dismissed_banner_deletes_itself(qtbot):
    parent = _host(qtbot)
    banner = _banner(qtbot, parent, "bye")

    banner.dismiss()

    qtbot.waitUntil(lambda: not _compat.is_valid(banner))


def test_banners_shown_on_a_hidden_parent_stack(qtbot):
    parent = QWidget()
    parent.resize(800, 600)
    qtbot.addWidget(parent)
    first = _banner(qtbot, parent, "first")
    second = _banner(qtbot, parent, "second")

    assert second._target_pos.y() >= (
        first._target_pos.y() + first.height() + first._spacing)


def test_the_banner_carries_no_sheet_and_follows_a_theme_switch(qtbot):
    from qtpy.QtCore import QPoint
    from qtpy.QtGui import QColor

    from fxgui import fxstyle

    fxstyle.apply_theme("dark")
    parent = _host(qtbot)
    fxstyle.register_themed_root(parent)
    banner = _banner(qtbot, parent, "themed")
    qtbot.waitUntil(lambda: banner.x() == _resting_x(banner))
    fxstyle.apply_theme("github_light")
    qtbot.wait(10)

    image = parent.grab().toImage()
    inside = banner.mapTo(parent, QPoint(banner.width() - 30, 6))

    assert banner.styleSheet() == ""
    assert all(not child.styleSheet() for child in banner.findChildren(QWidget))
    assert image.pixelColor(inside).name() == QColor(
        fxstyle.colors().surface_sunken).name()


def test_banners_on_two_parents_stack_apart(qtbot):
    one, two = _host(qtbot), _host(qtbot)
    _banner(qtbot, one, "one")

    other = _banner(qtbot, two, "two")

    assert other._target_pos.y() == other._margin


def test_the_survivor_moves_up_when_the_top_banner_leaves(qtbot):
    parent = _host(qtbot)
    top = _banner(qtbot, parent, "top")
    below = _banner(qtbot, parent, "below")
    assert below._target_pos.y() > below._margin

    top.dismiss()
    _assert_gone(qtbot, top, parent)

    assert below._target_pos.y() == below._margin
