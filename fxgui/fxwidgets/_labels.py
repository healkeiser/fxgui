"""Custom label widgets."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import QLabel, QWidget


class FXElidedLabel(QLabel):
    """A QLabel that elides text with '...' when it doesn't fit.

    This label automatically truncates text and adds an ellipsis when the
    text is too long to fit within the available space.

    Args:
        text: The label's text. Defaults to `""`.
        parent: Parent widget. Defaults to `None`.
        mode: Where the text is cut when it does not fit. Defaults to
            `Qt.ElideRight`. `Qt.ElideMiddle` is what tells apart
            strings that share a tail -- paths under a common root, or
            email-shaped identities at one domain, where two long values
            cut from the right come out looking identical.

    Examples:
        >>> from qtpy.QtCore import Qt
        >>> from fxgui import fxwidgets
        >>> label = fxwidgets.FXElidedLabel(
        ...     "a very long identity", mode=Qt.ElideMiddle
        ... )
    """

    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        mode: Qt.TextElideMode = Qt.ElideRight,
    ):
        super().__init__(text, parent)
        self._full_text = text
        self._mode = mode

    def minimumSizeHint(self) -> QSize:
        """No width at all, and the height one line of this font needs.

        `QLabel`'s own minimum width IS the width of its whole text --
        measured, 696px for a 58-character string -- and a minimum is
        not a preference: a label that will not go below its own text
        width does not elide when the room runs out, it takes the room
        from whatever shares its row and, failing that, from the window.
        Measured: a 47-character string in a row with a button, in a
        window told to be 200px wide, forced the window to 680px and
        pushed the button from x=90 to x=570.

        Which makes an eliding label with `QLabel`'s minimum a widget
        that cannot do the one thing it exists for. This yields the
        width instead, which is what eliding means, and keeps the height
        so a row is still a row.

        Returns:
            QSize: Zero width, at `QLabel`'s own minimum height.
        """
        return QSize(0, super().minimumSizeHint().height())

    @property
    def mode(self) -> Qt.TextElideMode:
        """Where the text is cut when it does not fit."""
        return self._mode

    @mode.setter
    def mode(self, mode: Qt.TextElideMode) -> None:
        self._mode = mode
        self._elide_text()

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
                self._full_text, self._mode, available_width
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
