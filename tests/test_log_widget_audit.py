"""The log pane lets go of logging when it dies and leaves the reader alone."""

# Built-in
import gc
import logging

# Third-party
from qtpy.QtCore import QEvent
from qtpy.QtGui import QTextCursor

# Internal
from fxgui.fxwidgets import FXOutputLogHandler, FXOutputLogWidget


def _lines(pane):
    return [line for line in pane.output_area.toPlainText().split("\n") if line]


def test_handler_detaches_once_its_widget_is_deleted(qtbot, qapp):
    pane = FXOutputLogWidget()
    handler = FXOutputLogHandler(pane)
    logging.root.addHandler(handler)
    errors = []
    handler.handleError = lambda record: errors.append(record)
    try:
        pane.deleteLater()
        qapp.sendPostedEvents(None, QEvent.DeferredDelete)
        del pane
        gc.collect()
        logging.getLogger("fxgui.test").warning("after the pane is gone")
        assert handler not in logging.root.handlers
        assert errors == []
    finally:
        logging.root.removeHandler(handler)


def test_flush_keeps_the_readers_selection(qtbot, qapp):
    pane = FXOutputLogWidget()
    qtbot.addWidget(pane)
    pane.append_log("first line to select")
    qtbot.waitUntil(lambda: _lines(pane) == ["first line to select"])
    cursor = pane.output_area.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(5, QTextCursor.KeepAnchor)
    pane.output_area.setTextCursor(cursor)

    pane.append_log("a later line")
    qtbot.waitUntil(lambda: len(_lines(pane)) == 2)

    after = pane.output_area.textCursor()
    assert (after.anchor(), after.position()) == (0, 5)
    assert after.selectedText() == "first"


def test_flush_scrolls_only_a_pane_already_at_the_bottom(qtbot, qapp):
    pane = FXOutputLogWidget()
    qtbot.addWidget(pane)
    pane.resize(300, 120)
    pane.show()
    for index in range(200):
        pane.append_log(f"line {index}")
    qtbot.waitUntil(lambda: len(_lines(pane)) == 200, timeout=2000)
    bar = pane.output_area.verticalScrollBar()
    assert bar.value() == bar.maximum() > 0

    bar.setValue(0)
    pane.append_log("while reading the top")
    qtbot.waitUntil(lambda: len(_lines(pane)) == 201)
    assert bar.value() == 0

    bar.setValue(bar.maximum())
    pane.append_log("while following")
    qtbot.waitUntil(lambda: len(_lines(pane)) == 202)
    assert bar.value() == bar.maximum()


def test_mid_and_tail_ansi_segments_share_one_format(qtbot, qapp):
    pane = FXOutputLogWidget()
    qtbot.addWidget(pane)
    pane.append_log("\x1b[1;2;31mmid\x1b[0m\x1b[1;2;31mtail")
    qtbot.waitUntil(lambda: _lines(pane) == ["midtail"])
    block = pane.output_area.document().firstBlock()
    formats = []
    it = block.begin()
    while not it.atEnd():
        fragment = it.fragment()
        fmt = fragment.charFormat()
        formats.append(
            (fmt.foreground().color().name(), fmt.foreground().color().alpha(),
             fmt.font().bold())
        )
        it += 1
    from fxgui import fxstyle

    error = fxstyle.readable_ink(
        fxstyle.colors().surface_sunken,
        fxstyle.get_feedback_colors()["error"]["foreground"],
    )
    assert formats == [(error, 128, True)] * len(formats)
    assert formats
