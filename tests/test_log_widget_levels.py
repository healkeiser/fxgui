"""A log pane shows only the levels it is asked for, and every level again."""

# Built-in
import logging

# Internal
from fxgui.fxwidgets import FXOutputLogHandler, FXOutputLogWidget


def _pane(qtbot):
    pane = FXOutputLogWidget()
    qtbot.addWidget(pane)
    return pane


def _shown(pane):
    """The text of every non-empty block on screen, in order."""
    document = pane.output_area.document()
    blocks = (document.findBlockByNumber(n) for n in range(document.blockCount()))
    return [b.text() for b in blocks if b.text() and b.isVisible()]


def _fill(pane):
    pane.append_log("info", logging.INFO)
    pane.append_log("warning", logging.WARNING)
    pane.append_log("error\nTraceback line", logging.ERROR)
    pane.append_log("critical", logging.CRITICAL)
    pane.append_log("no level")
    pane._flush_pending_log()


def test_every_line_shows_until_filtered(qtbot):
    pane = _pane(qtbot)
    _fill(pane)
    assert _shown(pane) == [
        "info", "warning", "error", "Traceback line", "critical", "no level"]
    assert pane._filter_bar.isHidden()


def test_warnings_only_hides_errors_and_info(qtbot):
    pane = _pane(qtbot)
    _fill(pane)

    pane.show_levels(logging.WARNING, below=logging.ERROR)

    assert _shown(pane) == ["warning"]
    assert not pane._filter_bar.isHidden()
    assert pane.filter_label.text() == "Showing warnings only"


def test_errors_and_above_keep_a_records_traceback(qtbot):
    pane = _pane(qtbot)
    _fill(pane)

    pane.show_levels(logging.ERROR)

    assert _shown(pane) == ["error", "Traceback line", "critical"]
    assert pane.filter_label.text() == "Showing errors and above"


def test_a_record_arriving_while_filtered_obeys_the_filter(qtbot):
    pane = _pane(qtbot)
    pane.show_levels(logging.ERROR)

    for index in range(2):
        pane.append_log(f"late error {index}", logging.ERROR)
        pane.append_log(f"late info {index}", logging.INFO)
    qtbot.waitUntil(lambda: not pane._pending_logs)

    assert _shown(pane) == ["late error 0", "late error 1"]


def test_show_all_brings_every_line_back(qtbot):
    pane = _pane(qtbot)
    _fill(pane)
    pane.show_levels(logging.ERROR)

    pane.show_all_button.click()

    assert len(_shown(pane)) == 6
    assert pane._filter_bar.isHidden()


def test_a_hidden_line_takes_no_room(qtbot):
    pane = _pane(qtbot)
    for index in range(40):
        pane.append_log(f"info {index}", logging.INFO)
    pane.append_log("the one error", logging.ERROR)
    qtbot.waitUntil(lambda: not pane._pending_logs)
    document = pane.output_area.document()
    # An unshown pane is never laid out; a set width lays it out now.
    document.setTextWidth(400)
    full = document.size().height()

    pane.show_levels(logging.ERROR)

    assert document.size().height() < full / 4


def test_the_handler_sends_each_records_level(qtbot):
    pane = _pane(qtbot)
    logger = logging.getLogger("fxgui.tests.levels")
    logger.propagate = False
    handler = FXOutputLogHandler(pane)
    logger.addHandler(handler)
    try:
        logger.warning("from the logger")
        logger.error("an error from the logger")
    finally:
        logger.removeHandler(handler)
    qtbot.waitUntil(lambda: len(_shown(pane)) == 2)

    pane.show_levels(logging.WARNING, below=logging.ERROR)

    assert _shown(pane) == ["from the logger"]
