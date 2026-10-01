"""Emoji picker popup, and the tool button that opens it."""

# Built-in
import unicodedata
from typing import List, Optional, Sequence, Tuple

# Third-party
from qtpy.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, Signal
from qtpy.QtGui import QFont, QGuiApplication
from qtpy.QtWidgets import (
    QFrame,
    QGridLayout,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QToolButton,
    QWidget,
)

# Internal
from fxgui import _compat, fxstyle
from fxgui.fxwidgets._buttons import FXIconButton


# Reactions and studio work, in the order the grid shows them.
_EMOJI_NAMES = {
    "\U0001F44D": "Thumbs Up",
    "\U0001F44E": "Thumbs Down",
    "\U0001F44C": "OK Hand",
    "\U0001F44F": "Clapping Hands",
    "\U0001F64F": "Folded Hands",
    "\U0001F64C": "Raising Hands",
    "\u2764\ufe0f": "Red Heart",
    "\U0001F525": "Fire",
    "\u2728": "Sparkles",
    "\U0001F389": "Party Popper",
    "\U0001F680": "Rocket",
    "\U0001F440": "Eyes",
    "\U0001F914": "Thinking Face",
    "\U0001F602": "Tears of Joy",
    "\U0001F605": "Grinning Face with Sweat",
    "\U0001F609": "Winking Face",
    "\U0001F604": "Grinning Face with Smiling Eyes",
    "\U0001F642": "Slightly Smiling Face",
    "\U0001F610": "Neutral Face",
    "\U0001F615": "Confused Face",
    "\U0001F622": "Crying Face",
    "\U0001F631": "Screaming in Fear",
    "\U0001F926": "Facepalm",
    "\U0001F937": "Shrug",
    "\u2705": "Check Mark",
    "\u274c": "Cross Mark",
    "\u26a0\ufe0f": "Warning",
    "\u2753": "Question Mark",
    "\u2757": "Exclamation Mark",
    "\U0001F4A1": "Light Bulb",
    "\u23f3": "Hourglass",
    "\U0001F4C5": "Calendar",
    "\U0001F4F7": "Camera",
    "\U0001F3A5": "Movie Camera",
    "\U0001F3AC": "Clapper Board",
    "\U0001F3A8": "Artist Palette",
    "\U0001F58C\ufe0f": "Paintbrush",
    "\U0001F4CC": "Pushpin",
    "\u2b50": "Star",
    "\U0001F4AF": "Hundred Points",
}

DEFAULT_EMOJIS: Tuple[str, ...] = tuple(_EMOJI_NAMES)

_EMOJI_PIXELS = 18
_CELL = 36


def _emoji_name(emoji: str) -> str:
    """Return a readable name for `emoji`, from Unicode when not in the table."""
    if emoji in _EMOJI_NAMES:
        return _EMOJI_NAMES[emoji]
    try:
        return unicodedata.name(emoji[0]).title()
    except (ValueError, IndexError):
        return emoji


fxstyle.register_widget_style("""
FXEmojiPicker {
    background-color: @surface_sunken;
    border: 1px solid @border;
    border-radius: 2px;
}
FXEmojiPicker QToolButton {
    border: 1px solid transparent;
    border-radius: 4px;
    background-color: transparent;
    padding: 0px;
    font-size: 18px;
}
FXEmojiPicker QToolButton:hover,
FXEmojiPicker QToolButton[fxFocusVisible="true"]:focus {
    background-color: @state_hover;
    border: 1px solid @accent_primary;
}
""")


class FXEmojiPicker(QFrame):
    """A popup grid of emoji; picking one emits it and closes the popup.

    Arrow keys move through the grid, Enter or Space picks, Escape closes
    without picking.

    Args:
        parent: Parent widget; the popup stays its child.
        emojis: The emoji to offer. Defaults to `DEFAULT_EMOJIS`.
        columns: How many emoji per row.

    Signals:
        emoji_picked(str): The emoji picked.

    Examples:
        >>> picker = FXEmojiPicker(button)
        >>> picker.emoji_picked.connect(editor.insertPlainText)
        >>> picker.popup_at(button.mapToGlobal(QPoint(0, button.height())))
    """

    emoji_picked = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        emojis: Optional[Sequence[str]] = None,
        columns: int = 8,
    ):
        super().__init__(parent, Qt.Popup)
        # A shaped frame: the theme hides the border of a NoFrame QFrame.
        self.setFrameShape(QFrame.StyledPanel)
        self._columns = max(1, columns)
        self._anchor: Optional[QRect] = None
        self._buttons: List[QToolButton] = []
        layout = QGridLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        font = QFont(self.font())
        font.setPixelSize(_EMOJI_PIXELS)
        for index, emoji in enumerate(
            DEFAULT_EMOJIS if emojis is None else emojis
        ):
            button = QToolButton(self)
            button.setText(emoji)
            button.setToolTip(_emoji_name(emoji))
            button.setAccessibleName(_emoji_name(emoji))
            button.setFont(font)
            button.setAutoRaise(True)
            button.setFixedSize(QSize(_CELL, _CELL))
            button.setFocusPolicy(Qt.StrongFocus)
            button.clicked.connect(
                lambda _checked=False, e=emoji: self._pick(e))
            button.installEventFilter(self)
            layout.addWidget(
                button, index // self._columns, index % self._columns)
            self._buttons.append(button)

    def buttons(self) -> List[QToolButton]:
        """Return the grid's buttons, one per emoji, in order."""
        return list(self._buttons)

    def columns(self) -> int:
        """Return how many emoji each row holds."""
        return self._columns

    def popup_at(self, pos: QPoint, anchor: Optional[QRect] = None) -> None:
        """Show the popup at global `pos`, kept on screen.

        Args:
            pos: The popup's top-left, in global coordinates.
            anchor: The global rect of the widget that opened it. With no
                room below, the popup opens above it instead of covering it.
        """
        screen = (
            QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        )
        area = screen.availableGeometry()
        self._anchor = anchor
        self.move(pos)
        self.show()
        # Measured once shown: a platform may add a frame around the popup.
        size = self.frameGeometry().size()
        y = pos.y()
        if anchor is not None and y + size.height() - 1 > area.bottom():
            y = anchor.top() - size.height()
        x = max(area.left(), min(pos.x(), area.right() - size.width() + 1))
        y = max(area.top(), min(y, area.bottom() - size.height() + 1))
        self.move(x, y)
        if self._buttons:
            self._buttons[0].setFocus(Qt.PopupFocusReason)

    def mousePressEvent(self, event) -> None:
        """Close on a press outside, without reopening from the anchor."""
        # Qt replays the closing press to the widget under it; on the button
        # that opened the popup, that press would open it again.
        anchor = self._anchor
        on_anchor = anchor is not None and anchor.contains(
            event.globalPosition().toPoint())
        self.setAttribute(Qt.WA_NoMouseReplay, on_anchor)
        super().mousePressEvent(event)

    def _pick(self, emoji: str) -> None:
        # Closed first, so a listener can hand focus back to its editor.
        self.close()
        self.emoji_picked.emit(emoji)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Move through the grid with the arrows, pick with Enter or Space."""
        if event.type() != QEvent.KeyPress or watched not in self._buttons:
            return super().eventFilter(watched, event)
        key = event.key()
        index = self._buttons.index(watched)
        steps = {
            Qt.Key_Left: -1,
            Qt.Key_Right: 1,
            Qt.Key_Up: -self._columns,
            Qt.Key_Down: self._columns,
        }
        if key in steps:
            target = index + steps[key]
            if 0 <= target < len(self._buttons):
                self._buttons[target].setFocus(Qt.TabFocusReason)
            return True
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self._pick(watched.text())
            return True
        if key == Qt.Key_Escape:
            self.close()
            return True
        return super().eventFilter(watched, event)


class FXEmojiButton(FXIconButton):
    """A round icon button that opens an `FXEmojiPicker` just below itself.

    Args:
        parent: Parent widget.
        emojis: The emoji to offer. Defaults to `DEFAULT_EMOJIS`.
        size: The circle's diameter, in logical pixels.

    Signals:
        emoji_picked(str): The emoji picked.

    Examples:
        >>> button = FXEmojiButton(toolbar)
        >>> button.attach(comment_editor)
    """

    emoji_picked = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        emojis: Optional[Sequence[str]] = None,
        size: int = 28,
    ):
        super().__init__(
            "add_reaction", parent, tip="Insert an emoji", size=size
        )
        self._emojis = emojis
        self._picker: Optional[FXEmojiPicker] = None
        self._editor: Optional[QWidget] = None
        self.emoji_picked.connect(self._insert)
        self.setAccessibleName("Insert an emoji")
        self.clicked.connect(self.open_picker)

    def picker(self) -> FXEmojiPicker:
        """Return the popup, built on first use."""
        if self._picker is None:
            self._picker = FXEmojiPicker(self, self._emojis)
            self._picker.emoji_picked.connect(self.emoji_picked)
        return self._picker

    def open_picker(self) -> None:
        """Show the popup just below the button, or above it near the bottom."""
        self.picker().popup_at(
            self.mapToGlobal(QPoint(0, self.height())),
            QRect(self.mapToGlobal(QPoint(0, 0)), self.size()),
        )

    def attach(self, editor: QWidget) -> None:
        """Insert each picked emoji at `editor`'s cursor and focus it again.

        Replaces the editor attached before, if any.

        Args:
            editor: A QLineEdit, QPlainTextEdit or QTextEdit.

        Raises:
            TypeError: If `editor` is none of those.
        """
        if not isinstance(editor, (QLineEdit, QPlainTextEdit, QTextEdit)):
            raise TypeError(f"cannot insert text into {type(editor).__name__}")
        self._editor = editor

    def _insert(self, emoji: str) -> None:
        editor = self._editor
        if editor is None or not _compat.is_valid(editor):
            self._editor = None
            return
        if isinstance(editor, QLineEdit):
            editor.insert(emoji)
        else:
            editor.insertPlainText(emoji)
        editor.setFocus(Qt.OtherFocusReason)
