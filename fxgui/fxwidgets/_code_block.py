"""Code block widget with syntax highlighting.

Uses Pygments for syntax highlighting, supporting 500+ programming languages.
"""

# Built-in
import bisect
import zlib
from typing import Optional

# Third-party
from pygments import lex
from pygments.util import ClassNotFound
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from qtpy.QtCore import Qt
from qtpy.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from qtpy.QtWidgets import QTextEdit, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle


class FXPygmentsHighlighter(QSyntaxHighlighter):
    """Syntax highlighter using Pygments for multi-language support.

    The whole document is lexed once per change; each block then takes
    its slice of the tokens, and records the token type at its end as
    its state so Qt carries a change (an opened string) to the blocks
    below.

    Args:
        document: The QTextDocument to highlight.
        language: The programming language name (e.g., "python", "javascript").

    Example:
        >>> highlighter = FXPygmentsHighlighter(text_edit.document(), "python")
    """

    _DARK_STYLE = "one-dark"
    _LIGHT_STYLE = "friendly"

    def __init__(self, document: QTextDocument, language: str = "python"):
        super().__init__(document)
        self._language = language
        self._lexer = None
        self._formats = {}
        self._lexed_text = None
        self._spans = []
        self._span_starts = []

        self._update_lexer(language)
        self._update_formats()
        fxstyle.theme_changed.connect(self.refresh_formats)

    def _update_lexer(self, language: str) -> None:
        """Update the Pygments lexer for the specified language.

        Args:
            language: The programming language name.
        """
        # No stripping: token offsets must match the document's.
        options = {"stripnl": False, "stripall": False, "ensurenl": False}
        try:
            self._lexer = get_lexer_by_name(language, **options)
            self._language = language
        except ClassNotFound:
            self._lexer = get_lexer_by_name("text", **options)
            self._language = "text"
        self._lexed_text = None

    def set_language(self, language: str) -> None:
        """Change the syntax highlighting language.

        Args:
            language: The programming language name.
        """
        self._update_lexer(language)
        self.rehighlight()

    def language(self) -> str:
        """Get the current language.

        Returns:
            The current language name.
        """
        return self._language

    def _update_formats(self) -> None:
        """Build format dictionary from Pygments style."""
        self._formats = {}
        style_name = self._LIGHT_STYLE if fxstyle.is_light_theme() else self._DARK_STYLE

        try:
            style = get_style_by_name(style_name)
        except ClassNotFound:
            style = get_style_by_name("default")

        for token_type, style_dict in style:
            fmt = QTextCharFormat()
            if style_dict.get("color"):
                fmt.setForeground(QColor(f"#{style_dict['color']}"))
            if style_dict.get("bgcolor"):
                fmt.setBackground(QColor(f"#{style_dict['bgcolor']}"))
            if style_dict.get("bold"):
                fmt.setFontWeight(QFont.Bold)
            if style_dict.get("italic"):
                fmt.setFontItalic(True)
            if style_dict.get("underline"):
                fmt.setFontUnderline(True)
            self._formats[token_type] = fmt

    def _get_format_for_token(self, token_type) -> Optional[QTextCharFormat]:
        """Get the format for a token type, checking parent types.

        Args:
            token_type: The Pygments token type.

        Returns:
            The QTextCharFormat for the token, or None if not found.
        """
        while token_type:
            if token_type in self._formats:
                return self._formats[token_type]
            token_type = token_type.parent
        return None

    def _lex_document(self) -> None:
        """Lex the document again if its text changed since the last lex."""
        text = self.document().toPlainText()
        if text == self._lexed_text:
            return
        self._lexed_text = text
        self._spans = []
        position = 0
        for token_type, value in lex(text, self._lexer) if text else ():
            if value:
                self._spans.append((position, position + len(value), token_type))
                position += len(value)
        self._span_starts = [span[0] for span in self._spans]

    def highlightBlock(self, text: str) -> None:
        """Apply the document's tokens that fall inside this block."""
        if not self._lexer:
            return
        self._lex_document()
        block_start = self.currentBlock().position()
        block_end = block_start + len(text)
        index = max(0, bisect.bisect_right(self._span_starts, block_start) - 1)
        end_type = None
        for start, end, token_type in self._spans[index:]:
            if start > block_end:
                break
            end_type = token_type
            rel_start = max(0, start - block_start)
            rel_end = min(len(text), end - block_start)
            if rel_end > rel_start:
                fmt = self._get_format_for_token(token_type)
                if fmt:
                    self.setFormat(rel_start, rel_end - rel_start, fmt)
        state = zlib.crc32(str(end_type).encode("ascii")) & 0x7FFFFFFF
        self.setCurrentBlockState(state)

    def refresh_formats(self, _theme_name: Optional[str] = None) -> None:
        """Rebuild the formats for the current theme and rehighlight."""
        self._update_formats()
        self.rehighlight()


class FXCodeBlock(QWidget):
    """A read-only code block with syntax highlighting and theme styling.

    Args:
        code: The code string to display.
        language: The programming language (e.g., "python", "javascript").
        parent: The parent widget.

    Example:
        >>> code = '''
        ... def hello():
        ...     print("Hello, World!")
        ... '''
        >>> code_block = FXCodeBlock(code)
    """

    MIN_HEIGHT = 60
    MAX_HEIGHT = 400

    def __init__(
        self,
        code: str = "",
        language: str = "python",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._highlighter = FXPygmentsHighlighter(
            self._text_edit.document(), language
        )
        self._text_edit.setPlainText(code.strip())
        layout.addWidget(self._text_edit)
        self._adjust_height()

    def _adjust_height(self) -> None:
        """Fit the editor to its lines, between MIN_HEIGHT and MAX_HEIGHT."""
        edit = self._text_edit
        # The stylesheet's mono font and padding apply once polished.
        edit.ensurePolished()
        margins = edit.contentsMargins()
        height = (
            int(edit.document().size().height())
            + margins.top()
            + margins.bottom()
            + 2 * edit.frameWidth()
        )
        edit.setFixedHeight(max(self.MIN_HEIGHT, min(height, self.MAX_HEIGHT)))

    def set_code(self, code: str) -> None:
        """Set the code to display.

        Args:
            code: The code string.
        """
        self._text_edit.setPlainText(code.strip())
        self._adjust_height()

    def code(self) -> str:
        """Get the current code.

        Returns:
            The code string.
        """
        return self._text_edit.toPlainText()

    def set_language(self, language: str) -> None:
        """Set the programming language for syntax highlighting.

        Args:
            language: The language name. Supports 500+ languages via Pygments
                (e.g., "python", "javascript", "cpp", "rust", "go", "java").
                An unknown name shows plain text.
        """
        self._highlighter.set_language(language)


fxstyle.register_widget_style("""
FXCodeBlock QTextEdit {
    font-family: @font_mono;
    font-size: 9pt;
    padding: 8px;
}
""")
