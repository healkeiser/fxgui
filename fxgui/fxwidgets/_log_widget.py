"""Output log widget with ANSI color support."""

# Built-in
import bisect
import functools
import logging
import re
import weakref
from collections import deque
from typing import Deque, Optional, Pattern, Sequence, Union

# Third-party
from qtpy.QtCore import QEvent, QObject, Qt, QTimer, Signal
from qtpy.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui._compat import is_valid
from fxgui.fxwidgets._tips import apply_tip


class FXOutputLogHandler(logging.Handler):
    """Logging handler that sends records to an output log widget.

    The widget is held weakly: once it is deleted the handler removes
    itself from every logger instead of raising on each record.

    Args:
        log_widget: The `FXOutputLogWidget` to send messages to.
    """

    def __init__(self, log_widget: "FXOutputLogWidget"):
        super().__init__()
        self._widget = weakref.ref(log_widget)
        log_widget.destroyed.connect(self.detach)

    @property
    def log_widget(self) -> Optional["FXOutputLogWidget"]:
        """The widget records go to, or `None` once it is gone."""
        widget = self._widget()
        if widget is None or not is_valid(widget):
            return None
        return widget

    def emit(self, record: logging.LogRecord) -> None:
        """Send a record to the widget, or detach if the widget is gone."""
        widget = self.log_widget
        if widget is None:
            self.detach()
            return
        try:
            # The signal hands the text to the widget's thread.
            widget.log_message.emit(self.format(record))
        except Exception:  # noqa: BLE001 - logging's own handler contract
            self.handleError(record)

    def detach(self, *_args) -> None:
        """Remove this handler from the root logger and every named logger."""
        loggers = [logging.root, *logging.root.manager.loggerDict.values()]
        for logger in loggers:
            if isinstance(logger, logging.Logger) and self in logger.handlers:
                # A new list, not `removeHandler`: this may run inside the
                # logger's own loop over its handlers.
                logger.handlers = [h for h in logger.handlers if h is not self]


# Pre-compiled regex for ANSI escape codes (module-level for reuse)
_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[([0-9;]+)m")


# ANSI foreground code -> theme token, after colorlog's level colours.
ANSI_ROLES = {
    "30": "text_disabled",
    "90": "text_disabled",
    "37": "text",
    "97": "text",
    "31": "feedback_error_foreground",
    "91": "feedback_error_foreground",
    "35": "feedback_error_foreground",
    "95": "feedback_error_foreground",
    "33": "feedback_warning_foreground",
    "93": "feedback_warning_foreground",
    "32": "feedback_info_foreground",
    "92": "feedback_info_foreground",
    "34": "feedback_info_foreground",
    "94": "feedback_info_foreground",
    "36": "feedback_debug_foreground",
    "96": "feedback_debug_foreground",
}

# Char format properties that remember a segment's role across themes.
_ROLE = QTextFormat.UserProperty + 1
_DIM = QTextFormat.UserProperty + 2

_readable_ink = functools.lru_cache(maxsize=256)(fxstyle.readable_ink)


def _paint_role(fmt: QTextCharFormat, role: str, dim: bool) -> None:
    """Set `fmt`'s foreground to the `role` token, readable on the pane."""
    theme = fxstyle.colors()
    colour = QColor(_readable_ink(theme.surface_sunken, getattr(theme, role)))
    if dim:
        colour.setAlpha(128)
    fmt.setForeground(colour)


def _ansi_format(role: Optional[str], dim: bool, bright: bool) -> QTextCharFormat:
    """Build the character format for one ANSI-styled segment."""
    fmt = QTextCharFormat()
    if bright:
        fmt.setFontWeight(QFont.Bold)
    if dim and role is None:
        role, dim = "text_disabled", False
    if role:
        fmt.setProperty(_ROLE, role)
        fmt.setProperty(_DIM, dim)
        _paint_role(fmt, role, dim)
    return fmt


class FXOutputLogWidget(QWidget):
    """A read-only log pane with ANSI colours, search and a throttle.

    Records reach it through an `FXOutputLogHandler` added to a logger,
    or through `append_log` and `append_many`.

    Args:
        parent: Parent widget.
        max_blocks: How many lines the pane keeps before Qt prunes the
            oldest, as a terminal's scrollback does. Defaults to `0`, no
            limit: only the consumer knows whether dropping old records
            is safe.
        hang_indent: A regular expression matching a record's header, such
            as its time, level and logger name. A wrapped record's later
            lines then start under the end of the match, not at column 0.
            Nothing is added to the text, so a copy gives the original.

    Signals:
        log_message: Emitted when a log message is received (for thread-safe
            delivery).

    Examples:
        >>> import logging
        >>> from fxgui import fxwidgets
        >>> log_widget = fxwidgets.FXOutputLogWidget()
        >>> logging.root.addHandler(fxwidgets.FXOutputLogHandler(log_widget))
    """

    # Signal for thread-safe log message delivery
    log_message = Signal(str)

    # Records per flush: 1000 take about 8.5 ms, inside the 16 ms tick.
    MAX_RECORDS_PER_FLUSH = 1000

    # The match count waits this long after the last keystroke, in ms: a
    # count scans the whole document.
    COUNT_DELAY_MS = 150

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        max_blocks: int = 0,
        hang_indent: Optional[Union[str, Pattern]] = None,
    ):
        super().__init__(parent)

        self._max_blocks = max_blocks
        self._hang = re.compile(hang_indent) if hang_indent else None

        # The throttle limits repaints, never records: all are queued.
        self._pending_logs: Deque[str] = deque()
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._flush_pending_log)
        self._throttle_interval = 16

        self._count_timer = QTimer(self)
        self._count_timer.setSingleShot(True)
        self._count_timer.setInterval(self.COUNT_DELAY_MS)
        self._count_timer.timeout.connect(self._update_search_count)

        # Queued across threads: a handler may emit off the UI thread.
        self.log_message.connect(self.append_log)

        self._setup_ui()

        # Shown segments keep their role; a switch repaints them.
        fxstyle.theme_changed.connect(self._recolour)

    def _setup_ui(self) -> None:
        """Build the output area, the search bar and the Clear button."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # A QTextEdit, for its rich text formats.
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        # A log is never undone; the undo stack would grow with it.
        self.output_area.setUndoRedoEnabled(False)
        if self._max_blocks > 0:
            # Qt prunes from the top once the document is this long.
            self.output_area.document().setMaximumBlockCount(self._max_blocks)
        self.output_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.output_area.setObjectName("fxOutputLogArea")
        apply_tip(
            self.output_area,
            "Output Area",
            "Displays log messages from the application. "
            "Press Ctrl+F to search",
            "Ctrl+F",
        )
        layout.addWidget(self.output_area)

        # One container, shown and hidden whole.
        self._search_bar = QWidget()
        search_layout = QHBoxLayout(self._search_bar)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(5)

        self.search_label = QLabel("Find:")
        search_layout.addWidget(self.search_label)

        self.search_input = QLineEdit()
        self.search_input.addAction(
            fxicons.get_icon("search"), QLineEdit.LeadingPosition
        )
        self.search_input.setPlaceholderText("Search...")
        self.search_input.returnPressed.connect(self._find_next)
        self.search_input.textChanged.connect(self._count_timer.start)
        # Shift+Enter goes back; returnPressed cannot tell it from Enter.
        self.search_input.installEventFilter(self)
        search_layout.addWidget(self.search_input, 1)

        self.search_count_label = QLabel("")
        self.search_count_label.setMinimumWidth(60)
        search_layout.addWidget(self.search_count_label)

        self.prev_button = QPushButton("Previous")
        fxicons.set_icon(self.prev_button, "keyboard_arrow_left")
        self.prev_button.clicked.connect(self._find_previous)
        apply_tip(
            self.prev_button,
            "Find Previous",
            "Find previous match",
            "Shift+Enter",
        )
        search_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        fxicons.set_icon(self.next_button, "keyboard_arrow_right")
        self.next_button.clicked.connect(self._find_next)
        apply_tip(self.next_button, "Find Next", "Find next match", "Enter")
        search_layout.addWidget(self.next_button)

        self.close_search_button = QPushButton("")
        fxicons.set_icon(self.close_search_button, "close")
        apply_tip(
            self.close_search_button,
            "Close Search",
            "Close the search bar",
            "Esc",
        )
        self.close_search_button.clicked.connect(self._hide_search)
        search_layout.addWidget(self.close_search_button)

        self._search_bar.hide()

        self.clear_button = QPushButton("Clear")
        fxicons.set_icon(self.clear_button, "delete")
        self.clear_button.clicked.connect(self.clear_log)
        apply_tip(self.clear_button, "Clear Log", "Clear all log messages")

        # Clear keeps the right edge; the bar takes the rest. With both
        # hidden the row is empty and takes no room.
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)
        bottom_layout.addWidget(self._search_bar, 1)
        bottom_layout.addWidget(self.clear_button, 0, Qt.AlignRight)
        layout.addLayout(bottom_layout)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Send Shift+Enter in the search field to the previous match."""
        if (
            watched is self.search_input
            and event.type() == QEvent.KeyPress
            and event.key() in (Qt.Key_Return, Qt.Key_Enter)
            and event.modifiers() & Qt.ShiftModifier
        ):
            self._find_previous()
            return True
        return super().eventFilter(watched, event)

    def show_search(self) -> None:
        """Show the search bar and put the cursor in it."""
        self._search_bar.show()
        self.search_input.setFocus()
        self.search_input.selectAll()
        self._update_search_count()

    def _hide_search(self) -> None:
        """Hide the search bar and clear the match selection."""
        self._search_bar.hide()
        cursor = self.output_area.textCursor()
        cursor.clearSelection()
        self.output_area.setTextCursor(cursor)

    def _update_search_count(self) -> None:
        """Show "X of Y": the selected match's place among all matches."""
        self._count_timer.stop()
        search_text = self.search_input.text()
        if not search_text:
            self.search_count_label.setText("")
            return

        document = self.output_area.document()
        ends = []
        cursor = document.find(search_text, QTextCursor(document))
        while not cursor.isNull():
            ends.append(cursor.position())
            cursor = document.find(search_text, cursor)

        current = 0
        selected = self.output_area.textCursor()
        if ends and selected.hasSelection():
            current = min(
                bisect.bisect_left(ends, selected.position()) + 1, len(ends)
            )
        self.search_count_label.setText(f"{current} of {len(ends)}")

    def _find(self, backward: bool) -> None:
        """Select the next match, or the previous one, wrapping round."""
        search_text = self.search_input.text()
        if not search_text:
            return
        flags = [QTextDocument.FindBackward] if backward else []
        if not self.output_area.find(search_text, *flags):
            cursor = self.output_area.textCursor()
            cursor.movePosition(
                QTextCursor.End if backward else QTextCursor.Start
            )
            self.output_area.setTextCursor(cursor)
            self.output_area.find(search_text, *flags)
        self._update_search_count()

    def _find_next(self) -> None:
        """Select the next match."""
        self._find(backward=False)

    def _find_previous(self) -> None:
        """Select the previous match."""
        self._find(backward=True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Open search on Ctrl+F; close it on Escape."""
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.show_search()
            event.accept()
            return
        if event.key() == Qt.Key_Escape and self._search_bar.isVisible():
            self._hide_search()
            event.accept()
            return
        super().keyPressEvent(event)

    def _flush_pending_log(self) -> None:
        """Write up to `MAX_RECORDS_PER_FLUSH` queued messages.

        Bounded, so one burst cannot freeze the UI; the timer re-arms and
        the next tick continues. Writes through a document cursor, so the
        reader's cursor and selection stay put, and scrolls only a pane
        already at the bottom.
        """
        if not self._pending_logs:
            return

        scrollbar = self.output_area.verticalScrollBar()
        following = scrollbar.value() >= scrollbar.maximum()
        cursor = QTextCursor(self.output_area.document())
        for _ in range(min(len(self._pending_logs), self.MAX_RECORDS_PER_FLUSH)):
            self._insert_text_with_ansi(self._pending_logs.popleft())
            cursor.movePosition(QTextCursor.End)
            cursor.insertText("\n")

        if following:
            scrollbar.setValue(scrollbar.maximum())

        self._throttle_timer.start(self._throttle_interval)

    def append_log(self, text: str) -> None:
        """Queue text for the pane; every record queued is shown.

        The first record of a burst is written at once, the rest on the
        throttle's ticks.

        Args:
            text: Text to append (may contain ANSI color codes).
        """
        self._pending_logs.append(text)
        if not self._throttle_timer.isActive():
            self._flush_pending_log()

    def append_many(self, lines: Sequence[str]) -> None:
        """Queue `lines` in order, behind whatever is already queued.

        For a history written elsewhere: one call, and the throttle writes
        them in as few repaints as it can.

        Args:
            lines: Each without its own newline; may carry ANSI codes.
        """
        self._pending_logs.extend(lines)
        if not self._throttle_timer.isActive():
            self._flush_pending_log()

    def _insert_text_with_ansi(self, text: str) -> None:
        """Insert text with ANSI colors, then hang its wrapped lines.

        Args:
            text: Text with ANSI escape codes.
        """
        document = self.output_area.document()
        first = document.blockCount() - 1
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.End)
        role, dim, bright = None, False, False
        # split() alternates text and the codes captured between escapes.
        for index, part in enumerate(_ANSI_ESCAPE_PATTERN.split(text)):
            if index % 2 == 0:
                if part:
                    # Always an explicit format: the end of the document
                    # would otherwise lend the last segment's colour.
                    cursor.insertText(part, _ansi_format(role, dim, bright))
                continue
            for code in part.split(";"):
                if code in ("0", ""):
                    role, dim, bright = None, False, False
                elif code == "1":
                    bright = True
                elif code == "2":
                    dim = True
                elif code == "22":
                    dim = bright = False
                elif code == "39":
                    role = None
                elif code in ANSI_ROLES:
                    role = ANSI_ROLES[code]
        if self._hang is not None:
            self._hang_blocks(first)

    def _hang_blocks(self, first: int) -> None:
        """Indent each block from `first` on under its header's end."""
        document = self.output_area.document()
        metrics = QFontMetricsF(self.output_area.font())
        for number in range(first, document.blockCount()):
            block = document.findBlockByNumber(number)
            match = self._hang.match(block.text())
            if match is None:
                continue
            indent = metrics.horizontalAdvance(" " * match.end())
            block_format = block.blockFormat()
            block_format.setLeftMargin(indent)
            block_format.setTextIndent(-indent)
            QTextCursor(block).setBlockFormat(block_format)

    def _recolour(self, _theme_name: Optional[str] = None) -> None:
        """Repaint every role-coloured segment in the current theme."""
        document = self.output_area.document()
        changes = []
        block = document.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                fmt = fragment.charFormat()
                role = fmt.property(_ROLE)
                if role:
                    _paint_role(fmt, role, bool(fmt.property(_DIM)))
                    changes.append((fragment.position(), fragment.length(), fmt))
                it += 1
            block = block.next()
        cursor = QTextCursor(document)
        for position, length, fmt in changes:
            cursor.setPosition(position)
            cursor.setPosition(position + length, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)

    def clear_log(self) -> None:
        """Clear the log output."""
        self.output_area.clear()
