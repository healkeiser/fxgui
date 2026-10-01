"""A dialog that asks for a thing's name before destroying it."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, Qt
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle


fxstyle.register_widget_style(
    """
    FXConfirmDeleteDialog QLabel#fxConfirmHint {
        color: @feedback_error_foreground;
    }
    """
)


class FXConfirmDeleteDialog(QDialog):
    """Ask for a word, typed exactly, before an act with no undo.

    Delete opens only while the field holds `confirm_word` exactly, and it
    is never the default button, so a stray Enter destroys nothing.
    Clicking the word copies it.

    Args:
        parent: Parent widget.
        title: The window title, naming what is going.
        body: What will be destroyed, including that it cannot be undone.
        confirm_word: What has to be typed.

    Examples:
        >>> dialog = FXConfirmDeleteDialog(
        ...     window, title="Delete beauty v004",
        ...     body="This cannot be undone.", confirm_word="beauty")
        >>> if dialog.exec_():
        ...     delete_version()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: str,
        body: str,
        confirm_word: str,
    ):
        super().__init__(parent)
        self._word = confirm_word
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        message = QLabel(body)
        message.setWordWrap(True)
        layout.addWidget(message)
        # Copying lowers the bar to a paste, but a name nobody can read
        # accurately gets worked around in worse ways.
        self.word_label = QLabel(
            f"Type <b>{confirm_word}</b> to confirm (click it to copy)"
        )
        self.word_label.setTextFormat(Qt.RichText)
        self.word_label.setCursor(Qt.PointingHandCursor)
        self.word_label.installEventFilter(self)
        layout.addWidget(self.word_label)
        self.field = QLineEdit()
        self.field.textChanged.connect(self._on_typed)
        layout.addWidget(self.field)
        # Says why Delete is shut, so it reads as a guard, not a fault.
        self.hint = QLabel("")
        self.hint.setObjectName("fxConfirmHint")
        layout.addWidget(self.hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        # Destructive, not Accept: a button box makes its first Accept
        # button the default when shown, whatever was set before.
        self.delete_button = buttons.addButton(
            "Delete", QDialogButtonBox.DestructiveRole
        )
        self.delete_button.setEnabled(False)
        self.delete_button.setAutoDefault(False)
        self.delete_button.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def copy_word(self) -> None:
        """Put the confirmation word on the clipboard."""
        QApplication.clipboard().setText(self._word)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Copy the word when its label is clicked."""
        if (
            watched is self.word_label
            and event.type() == QEvent.MouseButtonPress
        ):
            self.copy_word()
            return True
        return super().eventFilter(watched, event)

    def _on_typed(self, text: str) -> None:
        """Open Delete only on an exact, case-sensitive match."""
        matches = text == self._word
        self.delete_button.setEnabled(matches)
        # Silent while empty: nobody has answered yet.
        self.hint.setText("" if matches or not text else "Does not match")
