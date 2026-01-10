"""Code block widget with syntax highlighting."""

# Built-in
import os
import re
from typing import Optional

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from qtpy.QtWidgets import QTextEdit, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle


class FXPythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code with theme-aware colors."""

    # Python keywords
    KEYWORDS = [
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "None",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "True",
        "False",
        "try",
        "while",
        "with",
        "yield",
    ]

    # Python builtins
    BUILTINS = [
        "abs",
        "all",
        "any",
        "bin",
        "bool",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "vars",
        "zip",
    ]

    def __init__(self, document):
        super().__init__(document)
        self._formats = {}
        self._update_formats()

    def _update_formats(self) -> None:
        """Update syntax highlighting formats based on current theme."""
        theme = fxstyle.FXThemeColors(fxstyle.get_theme_colors())
        feedback = fxstyle.get_feedback_colors()

        # Keyword format (purple/magenta)
        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor("#c678dd"))
        keyword_fmt.setFontWeight(QFont.Bold)
        self._formats["keyword"] = keyword_fmt

        # Builtin format (cyan)
        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor("#56b6c2"))
        self._formats["builtin"] = builtin_fmt

        # String format (green)
        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor(feedback["success"]["foreground"]))
        self._formats["string"] = string_fmt

        # Comment format (gray)
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor(theme.text_disabled))
        comment_fmt.setFontItalic(True)
        self._formats["comment"] = comment_fmt

        # Number format (orange)
        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor(feedback["warning"]["foreground"]))
        self._formats["number"] = number_fmt

        # Function/method format (blue)
        function_fmt = QTextCharFormat()
        function_fmt.setForeground(QColor(feedback["info"]["foreground"]))
        self._formats["function"] = function_fmt

        # Decorator format (yellow)
        decorator_fmt = QTextCharFormat()
        decorator_fmt.setForeground(QColor("#e5c07b"))
        self._formats["decorator"] = decorator_fmt

        # Self format (red/italic)
        self_fmt = QTextCharFormat()
        self_fmt.setForeground(QColor(feedback["error"]["foreground"]))
        self_fmt.setFontItalic(True)
        self._formats["self"] = self_fmt

    def highlightBlock(self, text: str) -> None:
        """Apply syntax highlighting to a block of text."""

        # Keywords
        keyword_pattern = r"\b(" + "|".join(self.KEYWORDS) + r")\b"
        for match in re.finditer(keyword_pattern, text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._formats["keyword"],
            )

        # Builtins
        builtin_pattern = r"\b(" + "|".join(self.BUILTINS) + r")\b"
        for match in re.finditer(builtin_pattern, text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._formats["builtin"],
            )

        # Self
        for match in re.finditer(r"\bself\b", text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._formats["self"],
            )

        # Function definitions and calls
        for match in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", text):
            name = match.group(1)
            if name not in self.KEYWORDS and name not in self.BUILTINS:
                self.setFormat(
                    match.start(),
                    len(name),
                    self._formats["function"],
                )

        # Decorators
        for match in re.finditer(r"@[a-zA-Z_][a-zA-Z0-9_]*", text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._formats["decorator"],
            )

        # Numbers
        for match in re.finditer(r"\b\d+\.?\d*\b", text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._formats["number"],
            )

        # Strings (single and double quoted)
        string_patterns = [
            r'""".*?"""',  # Triple double quotes
            r"'''.*?'''",  # Triple single quotes
            r'"[^"\\]*(\\.[^"\\]*)*"',  # Double quotes
            r"'[^'\\]*(\\.[^'\\]*)*'",  # Single quotes
            r'f"[^"\\]*(\\.[^"\\]*)*"',  # f-strings double
            r"f'[^'\\]*(\\.[^'\\]*)*'",  # f-strings single
        ]
        for pattern in string_patterns:
            for match in re.finditer(pattern, text, re.DOTALL):
                self.setFormat(
                    match.start(),
                    match.end() - match.start(),
                    self._formats["string"],
                )

        # Comments (must be last to override other formats)
        for match in re.finditer(r"#.*$", text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._formats["comment"],
            )

    def refresh_formats(self) -> None:
        """Refresh formats when theme changes."""
        self._update_formats()
        self.rehighlight()


class FXCodeBlock(fxstyle.FXThemeAware, QWidget):
    """A code block widget with syntax highlighting and theme-aware styling.

    This widget displays code with:
    - Syntax highlighting for Python code
    - Theme-aware background and text colors
    - Monospace font
    - Read-only, selectable text
    - Optional line numbers (future)

    Args:
        code: The code string to display.
        language: The programming language (currently only "python" supported).
        parent: The parent widget.

    Example:
        >>> code = '''
        ... def hello():
        ...     print("Hello, World!")
        ... '''
        >>> code_block = FXCodeBlock(code)
    """

    def __init__(
        self,
        code: str = "",
        language: str = "python",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._language = language

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Text edit for code display
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Set monospace font
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.Monospace)
        self._text_edit.setFont(font)

        # Set up syntax highlighter
        self._highlighter = None
        if language == "python":
            self._highlighter = FXPythonHighlighter(self._text_edit.document())

        # Set the code
        self._text_edit.setPlainText(code.strip())

        layout.addWidget(self._text_edit)

        # Apply initial theme styles
        self._on_theme_changed()

        # Adjust height to content
        self._adjust_height()

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Apply theme-aware colors. Called on init and theme changes."""
        theme = self.theme

        # Style the text edit
        self._text_edit.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {theme.surface_sunken};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 8px;
                selection-background-color: {theme.accent_primary};
                selection-color: {theme.text};
            }}
            QScrollBar:vertical {{
                background: {theme.surface};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.border};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {theme.surface};
                height: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {theme.border};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            """
        )

        # Refresh syntax highlighting colors
        if self._highlighter:
            self._highlighter.refresh_formats()

    def _adjust_height(self) -> None:
        """Adjust widget height based on content."""
        doc = self._text_edit.document()
        # Calculate height based on line count with some padding
        line_count = doc.blockCount()
        line_height = self._text_edit.fontMetrics().lineSpacing()
        # Add padding for margins and border
        height = (line_count * line_height) + 32
        # Set minimum and maximum heights
        height = max(60, min(height, 400))
        self._text_edit.setFixedHeight(height)

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
            language: The language name (currently only "python" supported).
        """
        self._language = language

        # Remove old highlighter
        if self._highlighter:
            self._highlighter.setDocument(None)
            self._highlighter = None

        # Create new highlighter
        if language == "python":
            self._highlighter = FXPythonHighlighter(self._text_edit.document())


def example() -> None:
    """Example demonstrating the FXCodeBlock widget."""
    import sys
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)

    window = FXMainWindow(title="FXCodeBlock Example")
    window.toolbar.hide()

    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel

    central = QWidget()
    layout = QVBoxLayout(central)

    layout.addWidget(QLabel("Python code with syntax highlighting:"))

    code = '''
def update_item_colors(_theme_name: str = None):
    """Update item backgrounds based on current theme."""
    theme = FXThemeColors(get_theme_colors())
    feedback = get_feedback_colors()

    for i, item in enumerate(items):
        # Get feedback color for status
        status_key = item.data(0, Qt.UserRole + 100)
        if status_key in feedback:
            color = QColor(feedback[status_key]["foreground"])
            item.setData(0, STATUS_DOT_COLOR_ROLE, color)

        # Apply themed background
        bg = QColor(theme.surface_sunken).darker(110 + i * 5)
        item.setBackground(0, bg)

    tree.viewport().update()

# Apply initial colors and connect to theme changes
update_item_colors()
theme_manager.theme_changed.connect(update_item_colors)
'''

    code_block = FXCodeBlock(code)
    layout.addWidget(code_block)

    layout.addStretch()

    window.setCentralWidget(central)
    window.resize(600, 500)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
