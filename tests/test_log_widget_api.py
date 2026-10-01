"""A log pane takes a batch of lines, hangs wrapped lines, and opens search."""

# Third-party
from qtpy.QtGui import QFontMetricsF

# Internal
from fxgui.fxwidgets import FXOutputLogWidget


# The "HH:MM:SS LEVEL origin " header a console formatter writes.
HEADER = r"^\d\d:\d\d:\d\d\s+[A-Z]+\s+\S+\s+"


def _header(clock, level, origin):
    return f"{clock} {level:<8s} {origin} "


def _blocks(panel):
    """Every non-empty block (one per record) the pane holds, in order."""
    document = panel.output_area.document()
    blocks = (document.findBlockByNumber(n) for n in range(document.blockCount()))
    return [block for block in blocks if block.text()]


def _panel(qtbot, **kwargs):
    panel = FXOutputLogWidget(**kwargs)
    qtbot.addWidget(panel)
    return panel


def test_a_records_block_hangs_at_its_own_message_column(qtbot):
    panel = _panel(qtbot, hang_indent=HEADER)
    header = _header("04:42:26", "INFO", "pipeline.workflow:463")
    line = f"{header}would set sh0010/Lighting to to_review; would fire post"

    panel.append_log(line)

    (block,) = _blocks(panel)
    metrics = QFontMetricsF(panel.output_area.font())
    expected = metrics.horizontalAdvance(" " * len(header))
    fmt = block.blockFormat()
    assert fmt.leftMargin() == expected
    assert fmt.textIndent() == -expected


def test_two_records_hang_at_their_own_columns(qtbot):
    """A short origin and a long one must not share one hang column."""
    panel = _panel(qtbot, hang_indent=HEADER)

    panel.append_many([
        _header("04:42:26", "INFO", "a:1") + "a short message",
        _header("04:42:26", "INFO", "pipeline.apps.banner:35") + "a longer",
    ])

    first, second = _blocks(panel)
    assert first.blockFormat().leftMargin() != second.blockFormat().leftMargin()


def test_a_line_with_no_header_gets_no_hang_indent(qtbot):
    panel = _panel(qtbot, hang_indent=HEADER)

    panel.append_log("no header here, just a message")

    (block,) = _blocks(panel)
    assert block.blockFormat().leftMargin() == 0


def test_without_a_pattern_nothing_hangs(qtbot):
    panel = _panel(qtbot)

    panel.append_log(_header("04:42:26", "INFO", "a:1") + "message")

    (block,) = _blocks(panel)
    assert block.blockFormat().leftMargin() == 0


def test_a_hung_block_copies_back_as_the_original_line(qtbot):
    panel = _panel(qtbot, hang_indent=HEADER)
    line = _header("04:42:26", "INFO", "pipeline.workflow:463") + "message"

    panel.append_log(line)

    (block,) = _blocks(panel)
    assert block.text() == line


def test_append_many_writes_every_line_in_order_after_what_is_queued(qtbot):
    panel = _panel(qtbot)
    panel.append_log("first")
    panel.append_log("queued")

    panel.append_many([f"history {n}" for n in range(3)])
    qtbot.waitUntil(lambda: len(_blocks(panel)) == 5, timeout=1000)

    assert [b.text() for b in _blocks(panel)] == [
        "first", "queued", "history 0", "history 1", "history 2"
    ]


def test_show_search_opens_the_bar_with_the_cursor_in_it(qtbot):
    panel = _panel(qtbot)
    panel.show()
    qtbot.waitExposed(panel)

    panel.show_search()

    assert panel.search_input.isVisible()
    assert panel.focusWidget() is panel.search_input
