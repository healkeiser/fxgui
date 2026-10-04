"""An eliding label has to elide, which means it has to yield its width.

`QLabel`'s own minimum width IS the width of its whole text, and a
minimum is not a preference: a label that will not go below its own text
width does not shorten its text when the room runs out, it takes the room
from whatever shares its row and, failing that, from the window. Measured
on a plain `QLabel`, a 47-character identity in a row with a button in a
window told to be 200px wide: the window came out 680px and the button
moved from x=90 to x=570.
"""

# Third-party
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

    assert label.elided_text() != IDENTITY
    assert "\u2026" in label.elided_text() or "..." in label.elided_text()


def test_eliding_from_the_right_is_still_the_default(qtbot, qapp):
    """The one behaviour here that existing consumers already depend on.
    """
    label = FXElidedLabel(IDENTITY)
    label.setFixedWidth(120)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)

    assert label.elided_text().startswith("valentin"), "the head survived"
    assert label.mode() == Qt.ElideRight


def test_a_label_can_be_asked_to_elide_from_the_middle(qtbot, qapp):
    """What tells apart strings that share a tail. Two email-shaped
    identities at one domain, cut from the right, come out identical.
    """
    label = FXElidedLabel(IDENTITY, mode=Qt.ElideMiddle)
    label.setFixedWidth(200)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)

    painted = label.elided_text()

    assert painted != IDENTITY, "it did elide"
    # Split at the ellipsis rather than asserting a character count: how
    # much of each end survives is a pixel measurement, and what matters
    # is that BOTH ends do.
    head, _, tail = painted.partition("\u2026")
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
        return label.elided_text()

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
    before = label.elided_text()

    label.set_mode(Qt.ElideMiddle)

    assert label.elided_text() != before


def test_text_answers_the_whole_string(qtbot, qapp):
    """`text()` is what was set; the shortened string is `elided_text()`."""
    label = FXElidedLabel(IDENTITY)
    label.setFixedWidth(80)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)

    assert label.text() == IDENTITY
    assert len(label.elided_text()) < len(IDENTITY)


def test_size_hint_measures_the_whole_string(qtbot, qapp):
    """A layout asking for room gets the full width, not the cut one."""
    label = FXElidedLabel(IDENTITY)
    plain = QLabel(IDENTITY)
    qtbot.addWidget(label)
    label.resize(60, 20)
    label.show()
    qtbot.waitExposed(label)

    assert label.sizeHint().width() >= plain.sizeHint().width()


def test_a_wrapped_label_elides_from_the_right_at_its_maximum_height(
    qtbot, qapp
):
    label = FXElidedLabel(" ".join(["word"] * 200), mode=Qt.ElideMiddle)
    qtbot.addWidget(label)
    label.setWordWrap(True)
    label.setFixedWidth(120)
    label.setMaximumHeight(40)
    label.show()
    qtbot.waitExposed(label)

    painted = label.elided_text()

    assert painted.startswith("word"), "the head survives"
    assert painted.endswith("..."), "and the cut is at the end"


def test_a_wrapped_label_with_no_maximum_keeps_its_whole_text(qtbot, qapp):
    text = " ".join(["word"] * 60)
    label = FXElidedLabel(text)
    qtbot.addWidget(label)
    label.setWordWrap(True)
    label.setFixedWidth(120)
    label.resize(120, 10)
    label.show()
    qtbot.waitExposed(label)

    assert label.elided_text() == text


def test_a_font_change_cuts_the_text_again(qtbot, qapp):
    label = FXElidedLabel(IDENTITY)
    label.setFixedWidth(160)
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)
    before = label.elided_text()
    font = label.font()
    font.setPixelSize(30)

    label.setFont(font)

    assert label.elided_text() != before


def _hover_tip(label, qapp):
    """Send `label` the tooltip event a hover sends; return the tip shown."""
    from qtpy.QtCore import QEvent, QPoint
    from qtpy.QtGui import QHelpEvent
    from qtpy.QtWidgets import QToolTip

    QToolTip.hideText()
    centre = QPoint(label.width() // 2, label.height() // 2)
    event = QHelpEvent(QEvent.ToolTip, centre, label.mapToGlobal(centre))
    qapp.sendEvent(label, event)
    return QToolTip.text() if QToolTip.isVisible() else ""


def test_a_cut_label_shows_its_whole_text_on_hover(qtbot, qapp):
    label = FXElidedLabel(IDENTITY, mode=Qt.ElideMiddle)
    qtbot.addWidget(label)
    label.setFixedWidth(80)
    label.show()
    qtbot.waitExposed(label)

    assert label.elided_text() != IDENTITY
    assert _hover_tip(label, qapp) == IDENTITY


def test_a_label_that_fits_shows_no_tip(qtbot, qapp):
    label = FXElidedLabel("short")
    qtbot.addWidget(label)
    label.setFixedWidth(300)
    label.show()
    qtbot.waitExposed(label)

    assert _hover_tip(label, qapp) == ""


def test_a_tip_the_caller_set_wins(qtbot, qapp):
    label = FXElidedLabel(IDENTITY)
    label.setToolTip("Signed in")
    qtbot.addWidget(label)
    label.setFixedWidth(80)
    label.show()
    qtbot.waitExposed(label)

    assert _hover_tip(label, qapp) == "Signed in"
