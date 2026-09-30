"""The Pygments highlighter colours the right characters, once per change."""

# Third-party
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QPlainTextEdit

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import _code_block
from fxgui.fxwidgets._code_block import FXCodeBlock, FXPygmentsHighlighter


def _format_at(document, block_number, column):
    """The foreground colour the highlighter put on one character."""
    block = document.findBlockByNumber(block_number)
    for fmt_range in block.layout().formats():
        if fmt_range.start <= column < fmt_range.start + fmt_range.length:
            return fmt_range.format.foreground().color().name()
    return None


def _string_colour(highlighter):
    from pygments.token import String

    return highlighter._get_format_for_token(String).foreground().color().name()


def test_leading_blank_lines_do_not_shift_the_colours(qapp):
    edit = QPlainTextEdit()
    document = edit.document()
    highlighter = FXPygmentsHighlighter(document, "python")
    # Qt defers a new highlighter's first pass to the event loop.
    qapp.processEvents()
    document.setPlainText("\n\n    x = 'text'")
    # Column of the opening quote on the third line.
    assert _format_at(document, 2, 8) == _string_colour(highlighter)
    assert _format_at(document, 2, 4) != _string_colour(highlighter)


def test_opening_a_multiline_string_recolours_the_lines_below(qapp):
    edit = QPlainTextEdit()
    document = edit.document()
    highlighter = FXPygmentsHighlighter(document, "python")
    # Qt defers a new highlighter's first pass to the event loop.
    qapp.processEvents()
    document.setPlainText("a = 1\nb = 2\nc = 3")
    assert _format_at(document, 2, 0) != _string_colour(highlighter)

    cursor = QTextCursor(document)
    cursor.insertText('"""')

    assert _format_at(document, 2, 0) == _string_colour(highlighter)


def test_one_change_is_lexed_once(qapp, monkeypatch):
    calls = []
    real_lex = _code_block.lex

    def counting_lex(*args, **kwargs):
        calls.append(1)
        return real_lex(*args, **kwargs)

    monkeypatch.setattr(_code_block, "lex", counting_lex)
    edit = QPlainTextEdit()
    document = edit.document()
    highlighter = FXPygmentsHighlighter(document, "python")
    # Qt defers a new highlighter's first pass to the event loop.
    qapp.processEvents()
    document.setPlainText("\n".join(f"line_{index} = {index}" for index in range(50)))
    assert len(calls) == 1
    assert highlighter.language() == "python"


def test_a_theme_switch_rehighlights_a_code_block_once(qtbot, qapp):
    block = FXCodeBlock("x = 1\ny = 2")
    qtbot.addWidget(block)
    highlighter = block._highlighter
    calls = []
    real = highlighter.rehighlight

    def counting():
        calls.append(1)
        real()

    highlighter.rehighlight = counting
    fxstyle.apply_theme("light")
    qapp.processEvents()
    assert len(calls) == 1
    assert highlighter.language() == "python"


def test_code_block_sets_no_stylesheet_of_its_own(qtbot, qapp):
    block = FXCodeBlock("x = 1")
    qtbot.addWidget(block)
    assert block._text_edit.styleSheet() == ""
    assert "FXCodeBlock" in fxstyle.build_stylesheet()
