"""A dialog that asks before destroying a thing, and can ask for its name."""

# Built-in
import html
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, Qt
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle, fxutils
from fxgui.fxwidgets._buttons import FXIconButton

# ls-ui's ConfirmModal: a 512 px card, a 32 px X 12 px in from its corner,
# 4 px from title to description and 8 px from there to the buttons.
_CARD_WIDTH = 512
_CLOSE_SIZE = 32
_CLOSE_INSET = 12
_BUTTON_HEIGHT = 32

fxstyle.register_widget_style(
    """
    FXConfirmDeleteDialog {
        background: transparent;
    }
    #fxConfirmCard {
        background-color: @surface;
        border: 1px solid @border;
        border-radius: @card_radius;
    }
    #fxConfirmCard QLabel {
        background: transparent;
    }
    #fxConfirmCard QLabel#fxConfirmTitle {
        color: @text_strong;
    }
    #fxConfirmCard QLabel#fxConfirmBody {
        color: @text_muted;
    }
    FXConfirmDeleteDialog QLabel#fxConfirmHint {
        color: @feedback_error_foreground;
    }
    QPushButton[fxRole="danger"] {
        color: @text_on_danger;
        background-color: @danger_button;
        border-color: @danger_button;
    }
    QPushButton[fxRole="danger"]:hover {
        background-color: @danger_button_hover;
        border-color: @danger_button_hover;
    }
    QPushButton[fxRole="danger"]:pressed {
        background-color: @danger_button_pressed;
        border-color: @danger_button_pressed;
    }
    QPushButton[fxRole="danger"]:disabled {
        color: @text_disabled;
        background-color: @surface_alt;
        border-color: @border;
    }
    """
)


class FXConfirmDeleteDialog(QDialog):
    """Ask before an act with no undo: Cancel, then a red Delete.

    A card titled with the question, what goes with it in muted text, an X
    at the top right, and at the bottom right Cancel then Delete. Focus
    starts on Cancel, Escape cancels, and Delete is never the default
    button, so a stray Enter destroys nothing. While shown modal it dims
    the window behind it.

    With `require_typing`, Delete opens only while a field holds
    `confirm_word` exactly; clicking the word copies it.

    Args:
        parent: Parent widget; its window is dimmed while the dialog is up.
        title: The question, shown in the card and as the window title.
        body: What will be destroyed, including that it cannot be undone.
        confirm_word: The word to type when `require_typing` is on.
        require_typing: Whether Delete waits for `confirm_word` to be
            typed. Defaults to on when a `confirm_word` is given, so a
            caller from before the option keeps its guard, else off.

    Raises:
        ValueError: If `require_typing` is on without a `confirm_word`.

    Examples:
        >>> dialog = FXConfirmDeleteDialog(
        ...     window, title="Delete SH010?",
        ...     body="Its tasks and comments go with it.")
        >>> if dialog.exec():
        ...     delete_shot()
        >>> guarded = FXConfirmDeleteDialog(
        ...     window, title="Delete beauty v004",
        ...     body="This cannot be undone.", confirm_word="beauty")
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: str,
        body: str = "",
        confirm_word: Optional[str] = None,
        require_typing: Optional[bool] = None,
    ):
        super().__init__(parent)
        if require_typing is None:
            require_typing = confirm_word is not None
        if require_typing and not confirm_word:
            raise ValueError("require_typing needs a confirm_word")
        self._word = confirm_word or ""
        self._require_typing = require_typing
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._card = QFrame(self)
        self._card.setObjectName("fxConfirmCard")
        self._card.setFixedWidth(_CARD_WIDTH)
        card = QVBoxLayout(self._card)
        gutter, edge = fxstyle.DIALOG_GUTTER, fxstyle.DIALOG_EDGE
        # Less the card's 1 px border, which already stands its content in.
        card.setContentsMargins(gutter - 1, edge - 1, gutter - 1, edge - 1)
        card.setSpacing(0)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("fxConfirmTitle")
        self.title_label.setTextFormat(Qt.PlainText)
        self.title_label.setWordWrap(True)
        # Clear of the X, which stands nearer the edge than the gutter.
        self.title_label.setContentsMargins(
            0, 0, _CLOSE_SIZE + _CLOSE_INSET - gutter + 8, 0)
        fxstyle.mark_as_title(self.title_label, rank="section")
        card.addWidget(self.title_label)
        card.addSpacing(4)
        self.body_label = QLabel(body)
        self.body_label.setObjectName("fxConfirmBody")
        self.body_label.setTextFormat(Qt.PlainText)
        self.body_label.setWordWrap(True)
        self.body_label.setVisible(bool(body))
        card.addWidget(self.body_label)

        # The guard: made either way, so a caller that reaches for the
        # field finds it; shown only when asked for.
        self._guard = QWidget(self._card)
        guard = QVBoxLayout(self._guard)
        guard.setContentsMargins(0, fxstyle.DIALOG_GAP, 0, 0)
        guard.setSpacing(8)
        # Copying lowers the bar to a paste, but a name nobody can read
        # accurately gets worked around in worse ways.
        self.word_label = QLabel(
            f"Type <b>{html.escape(self._word)}</b> to confirm"
            " (click it to copy)"
        )
        self.word_label.setTextFormat(Qt.RichText)
        self.word_label.setCursor(Qt.PointingHandCursor)
        self.word_label.installEventFilter(self)
        guard.addWidget(self.word_label)
        self.field = QLineEdit()
        self.field.textChanged.connect(self._on_typed)
        guard.addWidget(self.field)
        # Says why Delete is shut, so it reads as a guard, not a fault.
        self.hint = QLabel("")
        self.hint.setObjectName("fxConfirmHint")
        guard.addWidget(self.hint)
        self._guard.setVisible(require_typing)
        card.addWidget(self._guard)

        card.addSpacing(8)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFlat(True)
        self.cancel_button.clicked.connect(self.reject)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setProperty("fxRole", "danger")
        # Never the default, so Enter anywhere but on Cancel does nothing.
        self.delete_button.setAutoDefault(False)
        self.delete_button.setEnabled(not require_typing)
        self.delete_button.clicked.connect(self.accept)
        for button in (self.cancel_button, self.delete_button):
            button.setMinimumHeight(_BUTTON_HEIGHT)
            buttons.addWidget(button)
        card.addLayout(buttons)

        # Out of the layout, so the title's line keeps the gutter.
        self.close_button = FXIconButton(
            "x", self._card, tip="Close", size=_CLOSE_SIZE)
        self.close_button.clicked.connect(self.reject)
        self._card.installEventFilter(self)

        layout = QVBoxLayout(self)
        # Room for the shadow, which falls 6 px down.
        layout.setContentsMargins(8, 8, 8, 16)
        layout.addWidget(self._card)
        fxutils.add_shadow(self._card)
        (self.field if require_typing else self.cancel_button).setFocus()
        fxutils.dim_behind(self)
        # Opened over a host that is not themed, it still wears the theme.
        fxstyle.register_themed_root(self)

    def copy_word(self) -> None:
        """Put the confirmation word on the clipboard."""
        QApplication.clipboard().setText(self._word)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Copy the word when its label is clicked; keep the X in its corner."""
        if (
            watched is self.word_label
            and event.type() == QEvent.MouseButtonPress
        ):
            self.copy_word()
            return True
        if watched is self._card and event.type() == QEvent.Resize:
            self.close_button.move(
                self._card.width() - _CLOSE_INSET - _CLOSE_SIZE, _CLOSE_INSET)
        return super().eventFilter(watched, event)

    def _on_typed(self, text: str) -> None:
        """Open Delete only on an exact, case-sensitive match."""
        if not self._require_typing:
            return
        matches = text == self._word
        self.delete_button.setEnabled(matches)
        # Silent while empty: nobody has answered yet.
        self.hint.setText("" if matches or not text else "Does not match")
