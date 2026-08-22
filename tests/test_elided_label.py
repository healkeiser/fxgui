"""An eliding label has to elide, which means it has to yield its width.

`QLabel`'s own minimum width IS the width of its whole text, and a
minimum is not a preference: a label that will not go below its own text
width does not shorten its text when the room runs out, it takes the room
from whatever shares its row and, failing that, from the window. Measured
on a plain `QLabel`, a 47-character identity in a row with a button in a
window told to be 200px wide: the window came out 680px and the button
moved from x=90 to x=570.
"""

# Built-in
import warnings

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

# Internal
from fxgui.fxwidgets import FXElidedLabel


IDENTITY = "valentin.beaumont@lotchi.live.example"
WIDE = "a" * 200


def _row(label, qtbot):
    """A 200px-wide window holding `label` and a button beside it."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(label)
    button = QPushButton("Sign out")
    layout.addWidget(button)
    host.resize(200, 40)
    host.show()
    qtbot.waitExposed(host)
    return host, button


def test_the_label_does_not_widen_its_own_window(qtbot, qapp):
    label = FXElidedLabel(IDENTITY)

    host, button = _row(label, qtbot)

    assert host.width() == 200, "the window kept the width it was given"
    assert button.x() < 150, "and the button kept its place in the row"


def test_a_plain_label_in_the_same_row_does_widen_it(qtbot, qapp):
    """The comparison that makes the fix a fix rather than a preference.
    """
    plain = QLabel(IDENTITY)

    host, button = _row(plain, qtbot)

    assert host.minimumSizeHint().width() > 200, (
        "a plain label insists on its whole text width"
    )


def test_the_minimum_width_is_zero(qtbot, qapp):
    label = FXElidedLabel(WIDE)

    assert label.minimumSizeHint().width() == 0


def test_the_minimum_height_is_still_a_line(qtbot, qapp):
    """Yielding the width must not make a row stop being a row."""
    label = FXElidedLabel(IDENTITY)
    plain = QLabel(IDENTITY)

    assert label.minimumSizeHint().height() == plain.minimumSizeHint().height()
    assert label.minimumSizeHint().height() > 0


def test_the_text_is_actually_shortened_when_the_room_runs_out(qtbot, qapp):
    label = FXElidedLabel(IDENTITY)
    label.setFixedWidth(80)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)

    assert label.text() != IDENTITY
    assert "…" in label.text() or "..." in label.text()


def test_eliding_from_the_right_is_still_the_default(qtbot, qapp):
    """The one behaviour here that existing consumers already depend on.
    """
    label = FXElidedLabel(IDENTITY)
    label.setFixedWidth(120)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)

    assert label.text().startswith("valentin"), "the head survived"
    assert label.mode == Qt.ElideRight


def test_a_label_can_be_asked_to_elide_from_the_middle(qtbot, qapp):
    """What tells apart strings that share a tail. Two email-shaped
    identities at one domain, cut from the right, come out identical.
    """
    label = FXElidedLabel(IDENTITY, mode=Qt.ElideMiddle)
    label.setFixedWidth(200)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)

    painted = label.text()

    assert painted != IDENTITY, "it did elide"
    # Split at the ellipsis rather than asserting a character count: how
    # much of each end survives is a pixel measurement, and what matters
    # is that BOTH ends do.
    head, _, tail = painted.partition("…")
    assert head and tail, "cut in the middle, not at an end"
    assert IDENTITY.startswith(head), "the part that identifies"
    assert IDENTITY.endswith(tail), "and the part that qualifies it"


def test_two_identities_sharing_a_tail_stay_tellable_apart(qtbot, qapp):
    """The measured reason the mode is worth an argument."""
    first = "valentin.beaumont@a.very.long.studio.domain.example"
    second = "valerie.beaumarchais@a.very.long.studio.domain.example"

    def painted(text, mode):
        label = FXElidedLabel(text, mode=mode)
        label.setFixedWidth(140)
        qtbot.addWidget(label)
        label.show()
        qtbot.waitExposed(label)
        return label.text()

    from_right = (
        painted(first, Qt.ElideRight),
        painted(second, Qt.ElideRight),
    )
    from_middle = (
        painted(first, Qt.ElideMiddle),
        painted(second, Qt.ElideMiddle),
    )

    assert from_right[0] != from_right[1] or from_middle[0] != from_middle[1]
    assert from_middle[0] != from_middle[1], "the middle keeps them apart"


def test_changing_the_mode_re_cuts_the_text(qtbot, qapp):
    label = FXElidedLabel(IDENTITY)
    label.setFixedWidth(120)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)
    before = label.text()

    label.mode = Qt.ElideMiddle

    assert label.text() != before


def test_text_still_answers_what_is_painted(qtbot, qapp):
    """`QLabel`'s own contract, deliberately kept: a caller reading this
    label back gets what is on screen. Anything else would put an
    ellipsis somewhere nobody could see it was a shortening."""
    label = FXElidedLabel(IDENTITY)
    label.setFixedWidth(80)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)

    assert label.text() == label.text().strip()
    assert len(label.text()) < len(IDENTITY)


def test_word_wrap_overruling_the_mode_says_so(qtbot, qapp):
    """The defect was silence, not the behaviour: `mode` governs the
    single-line case, and a caller who asked for `ElideMiddle` and then
    turned word wrap on got `ElideRight` with nothing saying so."""
    label = FXElidedLabel(IDENTITY, mode=Qt.ElideMiddle)
    qtbot.addWidget(label)

    with pytest.warns(RuntimeWarning, match="single-line"):
        label.setWordWrap(True)


def test_the_warning_names_a_way_out(qtbot, qapp):
    label = FXElidedLabel(IDENTITY, mode=Qt.ElideMiddle)
    qtbot.addWidget(label)

    with pytest.warns(RuntimeWarning) as caught:
        label.setWordWrap(True)

    said = str(caught[0].message)
    assert "wordWrap" in said
    assert "Turn word wrap off" in said


def test_the_default_mode_under_word_wrap_is_silent(qtbot, qapp):
    """`ElideRight` IS what a wrapped label does, so there is nothing to
    warn about."""
    label = FXElidedLabel(IDENTITY)
    qtbot.addWidget(label)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        label.setWordWrap(True)


def test_setting_the_mode_after_word_wrap_warns_too(qtbot, qapp):
    """Either order reaches the same moot combination."""
    label = FXElidedLabel(IDENTITY)
    qtbot.addWidget(label)
    label.setWordWrap(True)

    with pytest.warns(RuntimeWarning, match="single-line"):
        label.mode = Qt.ElideMiddle


def test_the_warning_lands_once_per_label(qtbot, qapp):
    """A label re-elides on every resize; a warning per frame would be
    noise nobody reads."""
    label = FXElidedLabel(IDENTITY, mode=Qt.ElideMiddle)
    qtbot.addWidget(label)

    with pytest.warns(RuntimeWarning):
        label.setWordWrap(True)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        label.setWordWrap(False)
        label.setWordWrap(True)
        label.mode = Qt.ElideLeft


def test_a_wrapped_label_still_elides_from_the_right(qtbot, qapp):
    """What the warning says it does, asserted rather than asserted-about.
    """
    label = FXElidedLabel(" ".join(["word"] * 200), mode=Qt.ElideMiddle)
    qtbot.addWidget(label)
    with pytest.warns(RuntimeWarning):
        label.setWordWrap(True)
    label.setFixedWidth(120)
    label.setMaximumHeight(40)
    label.show()
    qtbot.waitExposed(label)

    painted = label.text()

    assert painted.startswith("word"), "the head survives"
    assert painted.endswith("..."), "and the cut is at the end"
