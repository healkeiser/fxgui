"""Code block widget with syntax highlighting.

Uses Pygments for syntax highlighting, supporting 500+ programming languages.
"""

# Built-in
import os
from typing import Optional

# Third-party
from pygments import lex
from pygments.lexers import get_lexer_by_name, get_all_lexers
from pygments.styles import get_style_by_name
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from qtpy.QtWidgets import QTextEdit, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle


def get_supported_languages() -> list[str]:
    """Get a list of all supported language names.

    Returns:
        A sorted list of language names that can be used with FXCodeBlock.

    Example:
        >>> languages = get_supported_languages()
        >>> "python" in languages
        True
        >>> "javascript" in languages
        True
    """
    languages = set()
    for name, aliases, _, _ in get_all_lexers():
        languages.add(name.lower())
        for alias in aliases:
            languages.add(alias.lower())
    return sorted(languages)


class FXPygmentsHighlighter(fxstyle.FXThemeAware, QSyntaxHighlighter):
    """Syntax highlighter using Pygments for multi-language support.

    This highlighter uses Pygments lexers and styles to tokenize and format code.
    It leverages Pygments' built-in style system for consistent token coloring.

    Args:
        document: The QTextDocument to highlight.
        language: The programming language name (e.g., "python", "javascript").

    Example:
        >>> highlighter = FXPygmentsHighlighter(text_edit.document(), "python")
    """

    # Pygments style to use (One Dark-like theme)
    _DARK_STYLE = "one-dark"
    _LIGHT_STYLE = "friendly"

    def __init__(self, document, language: str = "python"):
        super().__init__(document)
        self._language = language
        self._lexer = None
        self._style = None
        self._formats = {}

        # Get the lexer for the specified language
        self._update_lexer(language)
        # Initialize formats from Pygments style
        self._update_formats()

        # Connect to document changes to trigger rehighlight
        document.contentsChanged.connect(self._on_content_changed)

    def _on_content_changed(self) -> None:
        """Handle document content changes."""
        # QSyntaxHighlighter automatically rehighlights on content change
        pass

    def _update_lexer(self, language: str) -> None:
        """Update the Pygments lexer for the specified language.

        Args:
            language: The programming language name.
        """
        try:
            self._lexer = get_lexer_by_name(language, stripall=True)
            self._language = language
        except Exception:
            # Fallback to text if language not found
            self._lexer = get_lexer_by_name("text", stripall=True)
            self._language = "text"

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

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Update syntax highlighting formats based on current theme."""
        self._update_formats()
        self.rehighlight()

    def _update_formats(self) -> None:
        """Build format dictionary from Pygments style."""
        self._formats = {}

        # Select style based on theme brightness
        style_name = self._LIGHT_STYLE if fxstyle.is_light_theme() else self._DARK_STYLE

        try:
            self._style = get_style_by_name(style_name)
        except Exception:
            self._style = get_style_by_name("default")

        # Build formats for all token types from the style
        for token_type, style_dict in self._style:
            fmt = QTextCharFormat()

            # Foreground color
            if style_dict.get("color"):
                fmt.setForeground(QColor(f"#{style_dict['color']}"))

            # Background color (usually not set for code editors)
            if style_dict.get("bgcolor"):
                fmt.setBackground(QColor(f"#{style_dict['bgcolor']}"))

            # Font weight
            if style_dict.get("bold"):
                fmt.setFontWeight(QFont.Bold)

            # Italic
            if style_dict.get("italic"):
                fmt.setFontItalic(True)

            # Underline
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
        # Walk up the token type hierarchy until we find a match
        while token_type:
            if token_type in self._formats:
                return self._formats[token_type]
            # Move to parent token type
            token_type = token_type.parent
        return None

    def highlightBlock(self, text: str) -> None:
        """Apply syntax highlighting to a block of text.

        Args:
            text: The text to highlight.
        """
        if not self._lexer or not text:
            return

        # Get the starting position of this block in the full document
        block = self.currentBlock()
        block_start = block.position()

        # Get full document text for proper context
        document = self.document()
        full_text = document.toPlainText()

        # Tokenize the entire document to get proper context
        # Then filter to tokens that affect this block
        block_end = block_start + len(text)

        current_pos = 0
        for token_type, token_value in lex(full_text, self._lexer):
            token_len = len(token_value)
            token_end = current_pos + token_len

            # Check if this token overlaps with the current block
            if token_end > block_start and current_pos < block_end:
                # Calculate the portion of this token that falls within the block
                rel_start = max(0, current_pos - block_start)
                rel_end = min(len(text), token_end - block_start)

                if rel_end > rel_start:
                    fmt = self._get_format_for_token(token_type)
                    if fmt:
                        self.setFormat(rel_start, rel_end - rel_start, fmt)

            # Skip processing once we're past this block
            if current_pos > block_end:
                break

            current_pos = token_end

    def refresh_formats(self) -> None:
        """Refresh formats when theme changes."""
        self._update_formats()
        self.rehighlight()


class FXCodeBlock(fxstyle.FXThemeAware, QWidget):
    """A code block widget with syntax highlighting and theme-aware styling.

    This widget displays code with:
    - Syntax highlighting for 500+ languages via Pygments
    - Theme-aware background and text colors
    - Monospace font
    - Read-only, selectable text

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

        # Set up syntax highlighter for any language
        self._highlighter = FXPygmentsHighlighter(
            self._text_edit.document(), language
        )

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
            language: The language name. Supports 500+ languages via Pygments
                (e.g., "python", "javascript", "cpp", "rust", "go", "java").
                Use get_supported_languages() to see all available options.
        """
        self._language = language
        self._highlighter.set_language(language)


def example() -> None:
    """Example demonstrating the FXCodeBlock widget with multiple languages."""
    import sys
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)

    window = FXMainWindow(title="FXCodeBlock Example")
    window.toolbar.hide()

    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel, QScrollArea

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)

    central = QWidget()
    layout = QVBoxLayout(central)

    # Python example
    layout.addWidget(QLabel("Python:"))
    python_code = '''
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Print first 10 Fibonacci numbers
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
'''
    layout.addWidget(FXCodeBlock(python_code, language="python"))

    # JavaScript example
    layout.addWidget(QLabel("JavaScript:"))
    js_code = """
async function fetchUserData(userId) {
    // Fetch user data from API
    const response = await fetch(`/api/users/${userId}`);
    if (!response.ok) {
        throw new Error("Failed to fetch user");
    }
    return response.json();
}

const users = ["alice", "bob", "charlie"];
users.forEach(user => console.log(user.toUpperCase()));
"""
    layout.addWidget(FXCodeBlock(js_code, language="javascript"))

    # C++ example
    layout.addWidget(QLabel("C++:"))
    cpp_code = """
#include <iostream>
#include <vector>

template<typename T>
T sum(const std::vector<T>& values) {
    T result = 0;
    for (const auto& val : values) {
        result += val;
    }
    return result;
}

int main() {
    std::vector<int> nums = {1, 2, 3, 4, 5};
    std::cout << "Sum: " << sum(nums) << std::endl;
    return 0;
}
"""
    layout.addWidget(FXCodeBlock(cpp_code, language="cpp"))

    # Rust example
    layout.addWidget(QLabel("Rust:"))
    rust_code = """
fn main() {
    let numbers: Vec<i32> = (1..=5).collect();

    // Using iterators and closures
    let doubled: Vec<i32> = numbers
        .iter()
        .map(|x| x * 2)
        .collect();

    println!("Doubled: {:?}", doubled);
}
"""
    layout.addWidget(FXCodeBlock(rust_code, language="rust"))

    layout.addStretch()

    scroll.setWidget(central)
    window.setCentralWidget(scroll)
    window.resize(700, 600)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
