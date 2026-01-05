"""Custom label widgets."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import QLabel, QWidget


class FXElidedLabel(QLabel):
    """A QLabel that elides text with '...' when it doesn't fit.

    This label automatically truncates text and adds an ellipsis when the
    text is too long to fit within the available space.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._full_text = text

    def setText(self, text: str) -> None:
        """Set the text and store the full text for elision."""
        self._full_text = text
        super().setText(text)
        self._elide_text()

    def resizeEvent(self, event) -> None:
        """Re-elide text when the label is resized."""
        super().resizeEvent(event)
        self._elide_text()

    def _elide_text(self) -> None:
        """Elide the text to fit within the label's width."""
        if not self._full_text:
            return

        metrics = QFontMetrics(self.font())
        available_width = self.width() - 2  # Small margin

        if self.wordWrap():
            # For word-wrapped labels, limit by line count
            available_height = (
                self.maximumHeight()
                if self.maximumHeight() < 16777215
                else self.height()
            )
            line_height = metrics.lineSpacing()
            max_lines = (
                max(1, available_height // line_height)
                if line_height > 0
                else 5
            )

            # Simple approach: truncate text if it would exceed max lines
            words = self._full_text.split()
            current_text = ""
            line_count = 1
            current_line_width = 0

            for word in words:
                word_width = metrics.horizontalAdvance(word + " ")
                if current_line_width + word_width > available_width:
                    line_count += 1
                    current_line_width = word_width
                    if line_count > max_lines:
                        current_text = current_text.rstrip() + "..."
                        break
                else:
                    current_line_width += word_width
                current_text += word + " "
            else:
                current_text = self._full_text

            super().setText(current_text.rstrip())
        else:
            # Single line elision
            elided = metrics.elidedText(
                self._full_text, Qt.ElideRight, available_width
            )
            super().setText(elided)


def example() -> None:
    import sys

    from qtpy.QtWidgets import (
        QApplication,
        QGroupBox,
        QVBoxLayout,
        QWidget,
    )

    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app: FXApplication = FXApplication(sys.argv)

    # Main window
    window = FXMainWindow()
    window.setWindowTitle("Labels Example")
    window.resize(400, 200)
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)

    # Elided label examples
    elided_group = QGroupBox("Elided Labels")
    elided_layout = QVBoxLayout(elided_group)

    # Short text (won't be elided)
    short_label = FXElidedLabel("1. Short text that fits")
    elided_layout.addWidget(short_label)

    # Long text (will be elided)
    long_text = (
        "2. This is a very long text that will be automatically truncated "
        "with an ellipsis when it doesn't fit within the available width "
        "of the label widget."
    )
    long_label = FXElidedLabel(long_text)
    long_label.setFixedWidth(250)
    elided_layout.addWidget(long_label)

    # Word-wrapped elided label
    wrapped_text = (
        "3. This is a very long text that will be automatically truncated "
        "with an ellipsis when it doesn't fit within the available width "
        "of the label widget."
    )
    wrapped_label = FXElidedLabel(wrapped_text)
    wrapped_label.setWordWrap(True)
    wrapped_label.setFixedWidth(200)
    wrapped_label.setMaximumHeight(50)
    elided_layout.addWidget(wrapped_label)

    layout.addWidget(elided_group)
    layout.addStretch()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
