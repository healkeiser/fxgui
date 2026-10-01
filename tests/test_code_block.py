"""The Pygments highlighter colours the right characters, once per change."""

# Third-party
from qtpy.QtGui import QFontInfo, QTextCursor
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
    assert "FXCodeBlock" in fxstyle._build_stylesheet()


def test_the_highlighter_is_public():
    from fxgui import fxwidgets
    from fxgui.fxwidgets._code_block import FXPygmentsHighlighter

    assert fxwidgets.FXPygmentsHighlighter is FXPygmentsHighlighter
    assert "FXPygmentsHighlighter" in fxwidgets.__all__


def test_a_class_rule_gives_an_editor_the_mono_face_inside_a_host(qtbot):
    from qtpy.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

    class _MonoProbeEditor(QPlainTextEdit):
        pass

    fxstyle.register_widget_style(
        "_MonoProbeEditor { font-family: @font_mono; font-size: 17px; }")
    root = QWidget()
    QVBoxLayout(root)
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    root.show()
    editor = _MonoProbeEditor()
    root.layout().addWidget(editor)
    editor.ensurePolished()
    assert editor.font().pixelSize() == 17, "the class rule beats the host's"


def test_the_code_block_rule_adds_only_what_the_base_sheet_lacks():
    rule = fxstyle._build_stylesheet().split("FXCodeBlock QTextEdit {")[1]
    rule = rule.split("}")[0]

    for repeated in ("background-color", "border", "selection", "color:"):
        assert repeated not in rule
    assert "font-family" in rule


def test_the_block_fits_its_lines_in_the_stylesheet_font(qtbot, qapp):
    root = QPlainTextEdit()
    fxstyle.register_themed_root(root)
    qtbot.addWidget(root)
    short = FXCodeBlock("x = 1", parent=root)
    tall = FXCodeBlock("\n".join(f"x{i} = {i}" for i in range(8)), parent=root)

    edit = tall._text_edit
    assert QFontInfo(edit.font()).family() == QFontInfo(
        short._text_edit.font()).family()
    lines = edit.fontMetrics().lineSpacing() * 8
    assert edit.height() >= lines
    assert edit.height() > short._text_edit.height()
