"""What the log widget's throttle is allowed to delay, and what it is
not allowed to drop.

The throttle exists so a flood of records cannot freeze the UI, and the
one thing it must not buy that with is records. Measured against the
single-slot version: six entries handed over back to back left TWO in
the pane, and only around 20ms of spacing between them let all six
survive. Nothing on screen said any had gone.
"""

# Third-party
from qtpy.QtCore import QTimer

# Internal
from fxgui.fxwidgets import FXOutputLogWidget


# Comfortably longer than the widget's own 16ms interval, so a flush that
# is going to happen has happened.
_DRAIN_MS = 500


def _pane(qtbot):
    """A log pane, not capturing anything the process logs.

    `capture_output=False` because what is under test is the path from
    `append_log` to the document, and a handler attached to the root
    logger would put the suite's own records in the same pane.
    """
    pane = FXOutputLogWidget(capture_output=False)
    qtbot.addWidget(pane)
    return pane


def _lines(pane):
    """The entries in the pane, in order, without the blank tail."""
    return [line for line in pane.output_area.toPlainText().split("\n") if line]


def test_a_burst_of_records_all_reach_the_pane(qtbot, qapp):
    """Six entries in one go, with no event loop pass between them: the
    exact shape that used to leave two."""
    pane = _pane(qtbot)

    for index in range(6):
        pane.append_log(f"entry {index}")

    qtbot.waitUntil(lambda: len(_lines(pane)) == 6, timeout=_DRAIN_MS)
    assert _lines(pane) == [f"entry {index}" for index in range(6)]


def test_the_first_record_still_arrives_without_waiting(qtbot, qapp):
    """The throttle delays the catch-up, not the first line. An artist
    watching a pane that shows nothing for 16ms has no way to tell it
    from a pane that is not wired up."""
    pane = _pane(qtbot)

    pane.append_log("the first thing that happened")

    assert _lines(pane) == ["the first thing that happened"]


def test_records_queued_behind_the_timer_keep_their_order(qtbot, qapp):
    """Out of order is as misleading as missing: a log's whole claim is
    that what is above happened before what is below."""
    pane = _pane(qtbot)

    for index in range(20):
        pane.append_log(f"{index:02d}")

    qtbot.waitUntil(lambda: len(_lines(pane)) == 20, timeout=_DRAIN_MS)
    assert _lines(pane) == [f"{index:02d}" for index in range(20)]


def test_records_arriving_across_several_windows_all_survive(qtbot, qapp):
    """A flush schedules the next window, and a record handed over
    during it waits for that one. Two bursts a window apart go through
    both the immediate path and the queued one."""
    pane = _pane(qtbot)

    pane.append_log("first burst a")
    pane.append_log("first burst b")
    qtbot.waitUntil(lambda: len(_lines(pane)) == 2, timeout=_DRAIN_MS)

    pane.append_log("second burst a")
    pane.append_log("second burst b")

    qtbot.waitUntil(lambda: len(_lines(pane)) == 4, timeout=_DRAIN_MS)
    assert _lines(pane) == [
        "first burst a",
        "first burst b",
        "second burst a",
        "second burst b",
    ]


def test_a_record_from_the_signal_is_queued_like_any_other(qtbot, qapp):
    """`log_message` is the thread-safe way in, and it lands in the same
    queue: `FXOutputLogHandler` emits it for every record, so a burst
    from a background thread is the common case rather than the odd one.
    """
    pane = _pane(qtbot)

    for index in range(6):
        pane.log_message.emit(f"through the signal {index}")

    qtbot.waitUntil(lambda: len(_lines(pane)) == 6, timeout=_DRAIN_MS)
    assert _lines(pane) == [f"through the signal {index}" for index in range(6)]


def test_each_queued_entry_is_parsed_for_ansi_on_its_own(qtbot, qapp):
    """A drained queue inserts its entries one at a time rather than
    joining them into one string, so each one's own escape codes are
    read against a fresh parse and none of them is left in the text.

    What this does NOT claim is that an entry cannot colour the entry
    after it: an unterminated code leaves the cursor's own character
    format behind, and the next entry's fast path inserts straight onto
    it. That is a separate defect in `_insert_text_with_ansi`, older
    than the queue and not touched by it.
    """
    pane = _pane(qtbot)

    pane.append_log("\x1b[32mgreen\x1b[0m")
    pane.append_log("\x1b[31mred\x1b[0m")

    qtbot.waitUntil(lambda: len(_lines(pane)) == 2, timeout=_DRAIN_MS)
    assert _lines(pane) == ["green", "red"], "codes consumed, text kept"


def test_one_flush_is_bounded_however_large_the_burst(qtbot, qapp):
    """Keeping every record is only half of staying responsive.

    An unbounded drain makes one flush cost O(burst), and a producer that
    never yields the event loop hands over the whole burst at once.
    Measured at about 8.7 microseconds a record: 50,000 in one flush is a
    513ms freeze on the main thread.
    """
    pane = _pane(qtbot)
    burst = FXOutputLogWidget.MAX_RECORDS_PER_FLUSH * 3

    for index in range(burst):
        pane.append_log(f"record {index}")

    # One flush by hand, so what is measured is one flush rather than
    # however many ticks the event loop happened to run.
    before = len(pane._pending_logs)
    pane._flush_pending_log()
    written = before - len(pane._pending_logs)

    assert written == FXOutputLogWidget.MAX_RECORDS_PER_FLUSH
    assert pane._pending_logs, "the rest is still queued, not dropped"


def test_a_bounded_flush_still_shows_every_record_eventually(qtbot, qapp):
    """The bound decides how long the pane takes to catch up, never
    whether a record survives -- the timer re-arms whichever way a flush
    returns, so a partial drain continues on the next tick."""
    pane = _pane(qtbot)
    burst = FXOutputLogWidget.MAX_RECORDS_PER_FLUSH * 2 + 7

    for index in range(burst):
        pane.append_log(f"{index:06d}")

    qtbot.waitUntil(lambda: len(_lines(pane)) == burst, timeout=10000)
    assert _lines(pane) == [f"{index:06d}" for index in range(burst)]
    assert not pane._pending_logs, "the queue drained to nothing"


def test_the_flush_chain_stops_when_the_queue_empties(qtbot, qapp):
    """The early return on an empty queue is what ends the chain: a timer
    that re-armed forever would be a widget that never idles."""
    pane = _pane(qtbot)
    pane.append_log("one")

    qtbot.waitUntil(
        lambda: not pane._throttle_timer.isActive(), timeout=_DRAIN_MS
    )

    assert _lines(pane) == ["one"]


def test_the_document_is_unbounded_by_default(qtbot, qapp):
    """Unchanged behaviour, and deliberately so: pruning the OLDEST
    records silently is the same class of defect as dropping the newest,
    and only a consumer knows whether a file behind the pane makes it
    safe."""
    pane = _pane(qtbot)

    assert pane.output_area.document().maximumBlockCount() == 0


def test_a_consumer_can_bound_the_document(qtbot, qapp):
    """For a pane that is a view onto a log it does not own, which is the
    case a scrollback limit is for."""
    pane = FXOutputLogWidget(capture_output=False, max_blocks=20)
    qtbot.addWidget(pane)

    for index in range(60):
        pane.append_log(f"record {index}")

    qtbot.waitUntil(lambda: not pane._pending_logs, timeout=_DRAIN_MS)

    lines = _lines(pane)
    assert len(lines) <= 20, f"pruned to the cap, got {len(lines)}"
    assert lines[-1] == "record 59", "and it is the newest that survive"


def test_a_pending_queue_is_written_out_before_the_handler_goes(qtbot, qapp):
    """`restore_output_streams` is the last chance those records have.
    Called while a window is open, it must not leave the queue behind."""
    pane = _pane(qtbot)

    pane.append_log("flushed on the way in")
    pane.append_log("still queued")
    pane.append_log("also queued")
    assert len(_lines(pane)) == 1, "the throttle is genuinely holding two"

    pane.restore_output_streams()

    assert _lines(pane) == [
        "flushed on the way in",
        "still queued",
        "also queued",
    ]


def test_the_last_flush_ignores_the_per_flush_bound(qtbot, qapp):
    """More queued than one flush may write, and no next tick coming:
    there is no event loop left to continue a partial drain on, so the
    bound has to give way to not losing the records."""
    pane = _pane(qtbot)
    burst = FXOutputLogWidget.MAX_RECORDS_PER_FLUSH * 2 + 3
    for index in range(burst):
        pane.append_log(f"{index:06d}")
    assert len(pane._pending_logs) > FXOutputLogWidget.MAX_RECORDS_PER_FLUSH

    pane.restore_output_streams()

    assert not pane._pending_logs, "nothing left behind"
    assert len(_lines(pane)) == burst
    assert not pane._throttle_timer.isActive(), "and it does not idle armed"


def test_the_queue_survives_a_record_logged_from_a_timer_callback(
    qtbot, qapp
):
    """A record produced while the flush itself is running -- a handler
    that logs, a signal that logs -- must not be lost to the drain it
    arrives during."""
    pane = _pane(qtbot)
    later = QTimer(pane)
    later.setSingleShot(True)
    later.timeout.connect(lambda: pane.append_log("from the callback"))

    pane.append_log("before")
    later.start(0)

    qtbot.waitUntil(lambda: len(_lines(pane)) == 2, timeout=_DRAIN_MS)
    assert _lines(pane) == ["before", "from the callback"]
