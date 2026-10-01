"""Comment-thread pieces: a text box that names people, a line joining faces."""

# Built-in
import unicodedata
from collections import Counter
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

# Third-party
from qtpy.QtCore import (
    QEvent,
    QModelIndex,
    QObject,
    QPoint,
    QPointF,
    Qt,
    Signal,
)
from qtpy.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QStandardItem,
    QStandardItemModel,
    QTextCursor,
)
from qtpy.QtWidgets import QCompleter, QPlainTextEdit, QSizePolicy, QWidget

# Internal
from fxgui import fxstyle


_ID_ROLE = Qt.UserRole
# The completer matches on this, so `@helene` finds an accented name.
_FOLDED_ROLE = Qt.UserRole + 1


def _fold(text: str) -> str:
    """Return `text` without its accents."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


class FXMentionEdit(QPlainTextEdit):
    """A text box that offers people by name after an `@`.

    A chosen person is written as `@<their name>`; `mentions` answers who
    the text still names. Two people of one name are offered with their
    ids. Ctrl+Enter emits `submitted`, Escape `cancelled`.

    Args:
        parent: Parent widget.
        lines: How many lines tall the box is.
        closes: Whether Escape closes the box, so it takes Escape before
            any window shortcut does.

    Signals:
        submitted: Ctrl+Enter was pressed.
        cancelled: Escape was pressed with no name list open.

    Examples:
        >>> box = FXMentionEdit(card)
        >>> box.set_people({"anne.martin": "Anne Martin"})
        >>> box.submitted.connect(lambda: post(box.toPlainText()))
    """

    submitted = Signal()
    cancelled = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        lines: int = 3,
        closes: bool = False,
    ):
        super().__init__(parent)
        self._closes = closes
        self._people: Dict[str, str] = {}
        # Id to the name written: two people may share a name.
        self._chosen: Dict[str, str] = {}
        self._names = QStandardItemModel(self)
        self.completer = QCompleter(self._names, self)
        self.completer.setWidget(self)
        self.completer.setCompletionRole(_FOLDED_ROLE)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.activated[QModelIndex].connect(self._chose)
        self._lines = lines
        self._fit_lines()
        # A text edit asks to grow tall; left so, a card stretches round it.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setTabChangesFocus(True)

    def set_people(self, people: Mapping[str, str]) -> None:
        """Offer `people`, as id to the name shown."""
        self._people = dict(people)
        count = Counter(self._people.values())
        self._names.clear()
        for person, name in sorted(
            self._people.items(), key=lambda pair: (pair[1], pair[0])
        ):
            shown = name if count[name] == 1 else f"{name} ({person})"
            item = QStandardItem(shown)
            item.setData(person, _ID_ROLE)
            item.setData(_fold(shown), _FOLDED_ROLE)
            self._names.appendRow(item)

    def insert_mention(self, person: str) -> None:
        """Write `person` as `@<name>`, replacing an `@` being typed."""
        name = self._people.get(person, person)
        cursor = self.textCursor()
        typed = self._typed()
        if typed is not None:
            for _ in range(len(typed) + 1):
                cursor.deletePreviousChar()
        cursor.insertText(f"@{name} ")
        self.setTextCursor(cursor)
        self._chosen[person] = name
        self.completer.popup().hide()

    def mentions(self) -> Tuple[str, ...]:
        """Return the ids the text still names, in the order chosen."""
        text = self.toPlainText()
        return tuple(
            person for person, name in self._chosen.items()
            if f"@{name}" in text
        )

    def kept(self) -> Tuple[str, Dict[str, str]]:
        """Return the text and who it names, for `restore` to put back."""
        return self.toPlainText(), dict(self._chosen)

    def restore(self, text: str, chosen: Mapping[str, str]) -> None:
        """Put back what `kept` returned, the cursor at its end."""
        self.setPlainText(text)
        self._chosen = dict(chosen)
        self.moveCursor(QTextCursor.End)

    def reset(self) -> None:
        """Empty the box and forget who was named."""
        self.clear()
        self._chosen.clear()

    def changeEvent(self, event: QEvent) -> None:
        """Hold the lines again in a font a sheet or a theme hands it."""
        super().changeEvent(event)
        if event.type() == QEvent.FontChange:
            self._fit_lines()

    def _fit_lines(self) -> None:
        self.setFixedHeight(self.fontMetrics().lineSpacing() * self._lines + 12)

    def event(self, event: QEvent) -> bool:
        """Claim Escape from window shortcuts when the box closes on it."""
        if (
            self._closes
            and event.type() == QEvent.ShortcutOverride
            and event.key() == Qt.Key_Escape
        ):
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        """Submit on Ctrl+Enter; an open name list takes Enter and Escape."""
        choosing = (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab)
        if self.completer.popup().isVisible() and event.key() in choosing:
            event.ignore()
            return
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
        if (
            event.key() in (Qt.Key_Enter, Qt.Key_Return)
            and event.modifiers() & Qt.ControlModifier
        ):
            self.submitted.emit()
            return
        super().keyPressEvent(event)
        self._offer()

    def _typed(self) -> Optional[str]:
        """Return what follows the `@` being typed, None for no `@`."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        before = cursor.selectedText()
        at = before.rfind("@")
        if at < 0 or (at > 0 and not before[at - 1].isspace()):
            return None
        typed = before[at + 1:]
        # A name is two words at most; a longer run is a sentence.
        return typed if typed.count(" ") <= 1 else None

    def _offer(self) -> None:
        typed = self._typed()
        popup = self.completer.popup()
        if typed is None or not self._people:
            popup.hide()
            return
        self.completer.setCompletionPrefix(_fold(typed))
        if self.completer.completionCount() == 0:
            popup.hide()
            return
        area = self.cursorRect()
        area.setWidth(max(180, popup.sizeHintForColumn(0) + 24))
        self.completer.complete(area)

    def _chose(self, index: QModelIndex) -> None:
        self.insert_mention(str(index.data(_ID_ROLE)))


_REDRAWN = (QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.Hide)


class FXThreadLine(QWidget):
    """A line over a thread, from a comment's face into each reply's face.

    Laid over the thread and blind to the mouse, so it crosses the cards'
    borders; it follows the thread's size and the faces' moves.

    Args:
        thread: The widget holding the comment and its replies.

    Examples:
        >>> line = FXThreadLine(thread)
        >>> line.join(comment_avatar, [reply.avatar for reply in replies])
    """

    WIDTH = 2
    # Between the line and a face, and the radius of each elbow.
    GAP = 3
    ELBOW = 8

    def __init__(self, thread: QWidget):
        super().__init__(thread)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._head: Optional[QWidget] = None
        self._faces: List[QWidget] = []
        self._thread = thread
        thread.installEventFilter(self)

    def join(self, head: QWidget, faces: Sequence[QWidget]) -> None:
        """Draw the line from under `head` to each of `faces` shown."""
        self._head, self._faces = head, list(faces)
        # Their moves, not this widget's: a wrapped reply moves the faces,
        # and a card growing above moves the cards below it.
        for face in (head, *faces):
            for watched in (face, face.parentWidget()):
                if watched is not None:
                    watched.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Follow the thread's size, and a face that moves or hides."""
        if event.type() in _REDRAWN:
            if watched is self._thread:
                self.setGeometry(self._thread.rect())
                self.raise_()
            self.update()
        return False

    def path(self) -> QPainterPath:
        """Return the line: down from the head, an elbow into each face."""
        drawn = QPainterPath()
        shown = [f for f in self._faces if f.isVisibleTo(self._thread)]
        if self._head is None or not shown:
            return drawn
        head = self._at(self._head)
        x = head.x() + self._head.width() / 2
        drawn.moveTo(x, head.y() + self._head.height() + self.GAP)
        middles = [(self._at(face), face) for face in shown]
        last = middles[-1][0].y() + middles[-1][1].height() / 2
        drawn.lineTo(x, last - self.ELBOW)
        for corner, face in middles:
            middle = corner.y() + face.height() / 2
            drawn.moveTo(x, middle - self.ELBOW)
            drawn.quadTo(QPointF(x, middle), QPointF(x + self.ELBOW, middle))
            drawn.lineTo(corner.x() - self.GAP, middle)
        return drawn

    def paintEvent(self, event) -> None:
        """Draw the line in the theme's border colour."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(fxstyle.get_theme_colors()["border"]), self.WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())

    def _at(self, face: QWidget) -> QPoint:
        return self.mapFromGlobal(face.mapToGlobal(QPoint(0, 0)))
