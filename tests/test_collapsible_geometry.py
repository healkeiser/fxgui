"""Four things a collapsible section got wrong about its own height.

All four are inherited by `FXAccordion`, which is built out of these.

- A layout raises its widget's own minimum height when a child grows and
  never lowers it again, and every layout between a section and the
  window caches the height it worked out for a given width. So a section
  opened once left the window permanently taller. Measured on PySide6
  6.11: 552px against the 472px it started at, and invalidating the outer
  layout changed nothing, because the sections sat in a nested one and an
  outer layout does not reach into one.
- The animation drives `maximumHeight`, so an opened section stayed
  capped at whatever height its content wanted at the moment it opened.
  Anything added afterwards was clipped by a number from before.
- A group run backwards starts at its own end value, so a header clicked
  twice quickly snapped to a height it had never reached and fell from
  there.
- `expanded` and `collapsed` both arrive before a single frame is drawn,
  which is no use to a window sized to its own contents: it has to grow
  WITH the movement, not after it.
"""

# Third-party
from qtpy.QtCore import QAbstractAnimation
from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

# Internal
from fxgui.fxwidgets import FXCollapsibleWidget


ROWS = 8
ROW_HEIGHT = 24


def _rows():
    """A content layout tall enough for the height to be visible."""
    layout = QVBoxLayout()
    for index in range(ROWS):
        row = QLabel(f"row {index}")
        row.setFixedHeight(ROW_HEIGHT)
        layout.addWidget(row)
    return layout


def _section(**kwargs):
    """A section with rows in it, registered with nobody.

    Deliberately not handed to `qtbot`: every test here puts it inside a
    host that IS registered, and registering both means pytest-qt closes
    the parent first and then reaches for a child C++ Qt has already
    destroyed with it.
    """
    section = FXCollapsibleWidget(title="Settings", **kwargs)
    section.set_content_layout(_rows())
    return section


def _settled():
    """Let the layouts re-activate.

    A geometry change is a request, not a redraw: `updateGeometry` marks
    the parent layouts dirty and they answer with the new number on the
    next event loop pass. Every height assertion here is about what the
    window ends up reporting, so every one of them waits.
    """
    QApplication.processEvents()


def _nested_host(qtbot, section):
    """A window whose section sits in a NESTED layout.

    Which is the shape the geometry finding was measured in, and the
    reason it could not be fixed by invalidating the window's own outer
    layout: that call does not reach into a nested one.

    The caller MUST keep the returned window: pytest-qt holds only a
    weak reference, so a discarded host is collected and takes the
    section inside it along.
    """
    host = QWidget()
    qtbot.addWidget(host)
    outer = QVBoxLayout(host)
    band = QWidget()
    inner = QVBoxLayout(band)
    inner.addWidget(section)
    outer.addWidget(band)
    host.show()
    qtbot.waitExposed(host)
    return host


def test_a_section_shut_again_gives_the_window_its_height_back(qtbot, qapp):
    """The permanently-taller-window bug, which every consumer of this
    class and of FXAccordion has today."""
    section = _section()
    host = _nested_host(qtbot, section)
    shut_height = host.sizeHint().height()

    section.expand(animate=False)
    _settled()
    opened_height = host.sizeHint().height()
    section.collapse(animate=False)
    _settled()

    assert opened_height > shut_height, "it did grow when opened"
    assert host.sizeHint().height() == shut_height, (
        "and gave every pixel back when shut"
    )


def test_an_opened_section_is_released_from_the_animations_cap(qtbot, qapp):
    """Left capped, the area stays at the height its content happened to
    want when it opened."""
    section = _section(max_content_height=0)

    section.expand(animate=False)

    assert section.content_area.maximumHeight() == (
        FXCollapsibleWidget.NO_CAP
    ), "no cap asked for, so none left behind"
    assert section.content_area.minimumHeight() > 0, "and still open"


def test_a_row_added_after_opening_is_not_clipped(qtbot, qapp):
    """The consequence of the stale cap, in the shape it is met in: a
    section is opened, and then something is added to it."""
    section = _section(max_content_height=0)
    host = _nested_host(qtbot, section)
    section.expand(animate=False)
    before = section.content_area.minimumHeight()

    extra = QLabel("a row added later")
    extra.setFixedHeight(ROW_HEIGHT)
    section.content_area.widget().layout().addWidget(extra)
    _settled()
    # Re-opening is what re-measures, and it is also what a consumer
    # does; what matters is that the number it lands on is the new one.
    section.collapse(animate=False)
    section.expand(animate=False)

    assert section.content_area.minimumHeight() > before


def test_a_requested_cap_is_still_a_cap(qtbot, qapp):
    """`max_content_height` is a limit the caller asked for, so releasing
    the animation's cap must not release that one -- and it is the cap
    itself rather than the measured height, which is what lets taller
    content scroll instead of being cut."""
    limit = 60
    section = _section(max_content_height=limit)

    section.expand(animate=False)

    assert section.content_area.maximumHeight() == limit
    assert section.content_area.minimumHeight() == limit


def _first_animation(section):
    """The `maximumHeight` animation inside the group."""
    return section._animation.animationAt(0)


def test_an_interrupted_opening_is_reversed_from_where_it_got_to(
    qtbot, qapp
):
    """A header clicked twice quickly. Measured on the group run
    backwards: the content snapped to its full height and fell from
    there, an end it had never reached."""
    section = _section(animation_duration=400)
    host = _nested_host(qtbot, section)

    section.expand(animate=True)
    qtbot.waitUntil(
        lambda: 0 < section.content_area.maximumHeight() < ROWS * ROW_HEIGHT,
        timeout=2000,
    )
    reached = section.content_area.maximumHeight()

    section.collapse(animate=True)

    assert _first_animation(section).startValue() == reached, (
        "the reversal starts from the height on screen"
    )
    assert _first_animation(section).endValue() == 0
    assert section._animation.direction() == QAbstractAnimation.Forward, (
        "forwards to a lower number, rather than a group run backwards"
    )


def test_a_collapse_after_a_finished_expansion_does_not_grow_first(
    qtbot, qapp
):
    """The shape the interrupted-movement tests cannot reach.

    They interrupt mid-flight, where `maximumHeight` genuinely IS the
    height on screen, so a start value read from it is right for the
    wrong reason. Once an expansion FINISHES, the maximum is released to
    the cap -- so reading it there starts the collapse from the cap.
    Measured on a 90px body under the default 300px cap: the first frame
    jumped to 300, a 210px upward lurch, out of the same commit that
    fixed the mid-flight jump.
    """
    section = _section(animation_duration=400)
    host = _nested_host(qtbot, section)
    section.expand(animate=False)
    _settled()
    on_screen = section.content_area.height()
    assert on_screen < section.max_content_height, (
        "the body must be SHORTER than its cap, or the bug hides"
    )
    frames = []
    section.resized.connect(frames.append)

    section.collapse(animate=True)

    assert _first_animation(section).startValue() <= on_screen, (
        "a collapse starts from the height on screen, not from the cap"
    )
    qtbot.waitUntil(lambda: bool(frames), timeout=2000)
    assert max(frames) <= on_screen, f"it grew before falling: {frames}"


def test_an_uncapped_section_never_reports_qwidgetsize_max(qtbot, qapp):
    """With `max_content_height=0` the released maximum is
    QWIDGETSIZE_MAX, so a collapse read from it ran 16,777,215 -> 0: the
    whole visible range in the first frame, and that number handed to
    the very consumer `resized` exists for."""
    section = _section(animation_duration=400, max_content_height=0)
    host = _nested_host(qtbot, section)
    section.expand(animate=False)
    _settled()
    on_screen = section.content_area.height()
    frames = []
    section.resized.connect(frames.append)

    section.collapse(animate=True)
    qtbot.waitUntil(lambda: bool(frames), timeout=2000)

    assert FXCollapsibleWidget.NO_CAP not in frames
    assert max(frames) <= on_screen, f"reported off-screen heights: {frames}"


def test_an_interrupted_closing_is_reversed_from_where_it_got_to(
    qtbot, qapp
):
    section = _section(animation_duration=400)
    host = _nested_host(qtbot, section)
    section.expand(animate=False)
    full = section.content_area.minimumHeight()

    section.collapse(animate=True)
    qtbot.waitUntil(
        lambda: 0 < section.content_area.maximumHeight() < full, timeout=2000
    )
    reached = section.content_area.maximumHeight()

    section.expand(animate=True)

    assert _first_animation(section).startValue() == reached
    assert _first_animation(section).endValue() == full


def test_the_movement_reports_every_frame(qtbot, qapp):
    """A window sized to its own contents has to grow WITH the movement.
    `expanded` and `collapsed` both arrive before a frame is drawn."""
    section = _section(animation_duration=200, max_content_height=0)
    host = _nested_host(qtbot, section)
    frames = []
    section.resized.connect(frames.append)

    section.expand(animate=True)
    qtbot.waitUntil(
        lambda: section._animation.state() != QAbstractAnimation.Running,
        timeout=3000,
    )

    assert len(frames) > 2, f"one value per frame, got {frames}"
    assert frames == sorted(frames), "and they climb rather than jump"
    assert frames[-1] == ROWS * ROW_HEIGHT + _spacing(section)


def _spacing(section):
    """Whatever the content layout's own margins and spacing add."""
    return (
        section.content_area.widget().sizeHint().height() - ROWS * ROW_HEIGHT
    )


def test_the_signal_reports_progress_and_not_only_the_end(qtbot, qapp):
    """The whole point of a per-frame signal, said as the thing a host
    can actually use: values arrive that are neither the height it
    started at nor the height it finished at.

    `expanded` gives a host one call, before a frame is drawn, and
    nothing after it. A window sized to its own contents needs the
    intermediate numbers or it grows only once the movement is over.
    """
    section = _section(animation_duration=300, max_content_height=0)
    host = _nested_host(qtbot, section)
    frames = []
    section.resized.connect(frames.append)

    section.expand(animate=True)
    qtbot.waitUntil(
        lambda: section._animation.state() != QAbstractAnimation.Running,
        timeout=3000,
    )

    target = frames[-1]
    midway = [height for height in frames if 0 < height < target]

    assert midway, f"nothing between the ends, got {frames}"
    assert target > 0
