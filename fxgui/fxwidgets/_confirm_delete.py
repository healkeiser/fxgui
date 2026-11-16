"""A card that asks before an act: a verb, Cancel, maybe a third choice."""

# Built-in
import html
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, QPoint, Qt
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
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
# A verb's tone, and the button role that dresses it.
_TONES = {"plain": "primary", "danger": "danger"}

fxstyle.register_widget_style(
    """
    FXConfirmDialog {
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
    FXConfirmDialog QLabel#fxConfirmHint {
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


class FXConfirmDialog(QDialog):
    """Ask before an act, as the web look's confirm card.

    A card titled with the question, what follows from it in muted text,
    an X at the top right, and at the bottom right Cancel then the verb;
    an optional third choice stands at the bottom left. While shown modal
    it dims the window behind it. Escape cancels; Enter takes the default
    choice, which is the verb in the plain tone and Cancel in the danger
    tone unless `default` says otherwise.

    With `require_typing`, the verb opens only while a field holds
    `confirm_word` exactly; clicking the word copies it.

    `exec()` returns `VERB` (`QDialog.Accepted`), `CANCEL`
    (`QDialog.Rejected`) or `ALTERNATIVE`; `choice()` names it.

    Args:
        parent: Parent widget; its window is dimmed while the dialog is up.
        title: The question, shown in the card and as the window title.
        body: What follows from the act.
        verb: The act's button, such as "Save" or "Replace".
        tone: "plain" (the verb is a primary button) or "danger" (red).
        alternative: A third choice's label, such as "Discard"; None for
            none.
        alternative_tone: The third choice's tone: "plain" (a flat button)
            or "danger".
        default: The choice Enter takes: "verb", "cancel" or
            "alternative". None: the verb in the plain tone, Cancel in the
            danger tone.
        confirm_word: The word to type when `require_typing` is on.
        require_typing: Whether the verb waits for `confirm_word` to be
            typed. Defaults to on when a `confirm_word` is given.

    Raises:
        ValueError: If a tone or `default` is unknown, `default` names an
            alternative there is none of, or `require_typing` is on
            without a `confirm_word`.

    Examples:
        >>> ask = FXConfirmDialog(
        ...     window, title="Close sh0010?", body="Its edits are not saved.",
        ...     verb="Save", alternative="Discard", alternative_tone="danger")
        >>> answer = ask.exec()
        >>> if answer == FXConfirmDialog.VERB:
        ...     save()
        ... elif answer == FXConfirmDialog.ALTERNATIVE:
        ...     discard()
    """

    VERB = QDialog.Accepted
    CANCEL = QDialog.Rejected
    ALTERNATIVE = 2

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: str,
        body: str = "",
        verb: str = "OK",
        tone: str = "plain",
        alternative: Optional[str] = None,
        alternative_tone: str = "plain",
        default: Optional[str] = None,
        confirm_word: Optional[str] = None,
        require_typing: Optional[bool] = None,
    ):
        for given in (tone, alternative_tone):
            if given not in _TONES:
                raise ValueError(f"No tone {given!r}: one of {list(_TONES)}")
        if default is None:
            default = "cancel" if tone == "danger" else "verb"
        if default not in ("verb", "cancel", "alternative"):
            raise ValueError(
                f"No default {default!r}: 'verb', 'cancel' or 'alternative'")
        if default == "alternative" and not alternative:
            raise ValueError("default 'alternative' needs an alternative")
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
        self._drag_from: Optional[QPoint] = None
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
        self.verb_button = QPushButton(verb)
        self.verb_button.setProperty("fxRole", _TONES[tone])
        self.verb_button.setEnabled(not require_typing)
        self.verb_button.clicked.connect(self.accept)
        self.alternative_button = None
        if alternative:
            self.alternative_button = QPushButton(alternative)
            if alternative_tone == "danger":
                self.alternative_button.setProperty("fxRole", "danger")
            else:
                self.alternative_button.setFlat(True)
            self.alternative_button.clicked.connect(
                lambda _=False: self.done(self.ALTERNATIVE))
            self.alternative_button.setMinimumHeight(_BUTTON_HEIGHT)
            buttons.insertWidget(0, self.alternative_button)
        for button in (self.cancel_button, self.verb_button):
            button.setMinimumHeight(_BUTTON_HEIGHT)
            buttons.addWidget(button)
        # Enter takes the default only; every other button stays out of it.
        chosen = {
            "verb": self.verb_button,
            "cancel": self.cancel_button,
            "alternative": self.alternative_button,
        }[default]
        for button in (
            self.cancel_button, self.verb_button, self.alternative_button
        ):
            if button is not None:
                button.setAutoDefault(False)
                button.setDefault(button is chosen)
        card.addLayout(buttons)

        # Out of the layout, so the title's line keeps the gutter.
        self.close_button = FXIconButton(
            "x", self._card, tip="Close", size=_CLOSE_SIZE)
        self.close_button.clicked.connect(self.reject)
        self._card.installEventFilter(self)
        # A frameless card has no title bar: its title moves it instead, so
        # what it covers can be read.
        self.title_label.installEventFilter(self)

        layout = QVBoxLayout(self)
        # Room for the shadow, which falls 6 px down.
        layout.setContentsMargins(8, 8, 8, 16)
        # The card's own size, its wrapped lines all in: a smaller one
        # squeezed the body under the field.
        layout.setSizeConstraint(QLayout.SetFixedSize)
        layout.addWidget(self._card)
        fxutils.add_shadow(self._card)
        (self.field if require_typing else chosen).setFocus()
        fxutils.dim_behind(self)
        # Opened over a host that is not themed, it still wears the theme.
        fxstyle.register_themed_root(self)

    def choice(self) -> str:
        """Return what was chosen: "verb", "alternative" or "cancel"."""
        return {self.VERB: "verb", self.ALTERNATIVE: "alternative"}.get(
            self.result(), "cancel")

    def copy_word(self) -> None:
        """Put the confirmation word on the clipboard."""
        QApplication.clipboard().setText(self._word)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Copy the word when its label is clicked; keep the X in its corner;
        move the card by its title."""
        if watched is self.title_label and self._drag(event):
            return True
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

    def _drag(self, event: QEvent) -> bool:
        """Move the dialog while its title is held; True when it was used."""
        kind = event.type()
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._drag_from = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft())
            return True
        if kind == QEvent.MouseMove and self._drag_from is not None:
            self.move(event.globalPosition().toPoint() - self._drag_from)
            return True
        if kind == QEvent.MouseButtonRelease and self._drag_from is not None:
            self._drag_from = None
            return True
        return False

    def _on_typed(self, text: str) -> None:
        """Open Delete only on an exact, case-sensitive match."""
        if not self._require_typing:
            return
        matches = text == self._word
        self.verb_button.setEnabled(matches)
        # Silent while empty: nobody has answered yet.
        self.hint.setText("" if matches or not text else "Does not match")


class FXConfirmDeleteDialog(FXConfirmDialog):
    """Ask before an act with no undo: Cancel, then a red Delete.

    `FXConfirmDialog` in the danger tone: focus starts on Cancel and Enter
    takes Cancel, so a stray Enter destroys nothing. With
    `require_typing`, Delete opens only while a field holds
    `confirm_word` exactly.

    Args:
        parent: Parent widget; its window is dimmed while the dialog is up.
        title: The question, shown in the card and as the window title.
        body: What will be destroyed, including that it cannot be undone.
        confirm_word: The word to type when `require_typing` is on.
        require_typing: Whether Delete waits for `confirm_word` to be
            typed. Defaults to on when a `confirm_word` is given, so a
            caller from before the option keeps its guard, else off.
        verb: The red button's label. Defaults to "Delete".

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
        verb: str = "Delete",
    ):
        super().__init__(
            parent,
            title=title,
            body=body,
            verb=verb,
            tone="danger",
            confirm_word=confirm_word,
            require_typing=require_typing,
        )
        #: The red Delete button (`verb_button`), by its old name.
        self.delete_button = self.verb_button
