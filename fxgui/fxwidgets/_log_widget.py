"""Output log widget with ANSI color support."""

# Built-in
import os
import logging
import functools
import re
import weakref
from collections import deque
from typing import Deque, Optional, Pattern, Sequence, Union

# Third-party
from qtpy.QtCore import QEvent, QObject, Qt, QTimer, Signal
from qtpy.QtGui import (
    QCloseEvent,
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
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui._compat import is_valid
from fxgui.fxwidgets._inputs import FXIconLineEdit
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


# ANSI foreground code -> theme role, after colorlog's level colours.
# Feedback roles name `get_feedback_colors()` entries, others theme tokens.
ANSI_ROLES = {
    "30": "text_disabled",
    "90": "text_disabled",
    "37": "text",
    "97": "text",
    "31": "error",
    "91": "error",
    "35": "error",
    "95": "error",
    "33": "warning",
    "93": "warning",
    "32": "info",
    "92": "info",
    "34": "info",
    "94": "info",
    "36": "debug",
    "96": "debug",
}

# Char format properties that remember a segment's role across themes.
_ROLE = QTextFormat.UserProperty + 1
_DIM = QTextFormat.UserProperty + 2

_readable_ink = functools.lru_cache(maxsize=256)(fxstyle.readable_ink)


def _paint_role(fmt: QTextCharFormat, role: str, dim: bool) -> None:
    """Set `fmt`'s foreground to `role` in the current theme, readable."""
    theme = fxstyle.colors()
    feedback = fxstyle.get_feedback_colors()
    wanted = (
        feedback[role]["foreground"] if role in feedback else getattr(theme, role)
    )
    colour = QColor(_readable_ink(theme.surface_sunken, wanted))
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
    """A reusable read-only output log widget for displaying application logs.

    This widget provides a text display area that captures and shows
    logging output from the application. It supports ANSI color codes,
    search functionality, and log throttling for performance.

    Args:
        parent: Parent widget.
        capture_output: If `True`, adds a logging handler to capture
            log output from Python's logging module.
        max_blocks: How many lines the pane keeps before Qt prunes the
            oldest, as a terminal's scrollback does. Defaults to `0`, no
            limit: only the consumer knows whether dropping old records
            is safe.
        hang_indent: A regular expression matching a record's header, such
            as its time, level and logger name. A wrapped record's later
            lines then start under the end of the match, not at column 0. Nothing is added to the text, so a copy gives the
            original line.

    Signals:
        log_message: Emitted when a log message is received (for thread-safe
            delivery).

    Examples:
        >>> from fxgui import fxwidgets
        >>> log_widget = fxwidgets.FXOutputLogWidget(capture_output=True)
        >>> log_widget.show()
    """

    # Signal for thread-safe log message delivery
    log_message = Signal(str)

    # Records per flush: 1000 take about 8.5 ms, inside the 16 ms tick.
    MAX_RECORDS_PER_FLUSH = 1000

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        capture_output: bool = False,
        max_blocks: int = 0,
        hang_indent: Optional[Union[str, Pattern]] = None,
    ):
        """Initialize the output log widget."""
        super().__init__(parent)

        self._capture_output = capture_output
        self._max_blocks = max_blocks
        self._hang = re.compile(hang_indent) if hang_indent else None
        self._log_handler = None
        self._logger_check_timer = None

        # The throttle limits repaints, never records: all are queued.
        self._pending_logs: Deque[str] = deque()
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._flush_pending_log)
        self._throttle_interval = 16

        # Queued across threads: a handler may emit off the UI thread.
        self.log_message.connect(self.append_log)

        # Setup UI
        self._setup_ui()

        # Setup output capture if requested
        if self._capture_output:
            self._setup_output_capture()

        # Shown segments keep their role; a switch repaints them.
        fxstyle.theme_changed.connect(self._recolour)

    def _setup_ui(self) -> None:
        """Setup the log widget UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Output area (read-only)
        # We're using `QTextEdit` for HTML support
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        # A log is never undone; the undo stack would grow with it.
        self.output_area.setUndoRedoEnabled(False)
        if self._max_blocks > 0:
            # Qt prunes from the top once the document is this long. Off
            # by default on purpose -- see the class docstring.
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

        # Set monospace font (colors will come from theme stylesheet)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.Monospace)
        self.output_area.setFont(font)

        layout.addWidget(self.output_area)

        # Bottom bar with search and buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)

        # Search controls (initially hidden)
        self.search_label = QLabel("Find:")
        self.search_label.hide()
        bottom_layout.addWidget(self.search_label)

        self.search_input = FXIconLineEdit(icon_name="search")
        self.search_input.setPlaceholderText("Search...")
        self.search_input.returnPressed.connect(self._find_next)
        self.search_input.textChanged.connect(self._update_search_count)
        self.search_input.hide()
        bottom_layout.addWidget(self.search_input)

        # Search count label (shows "X of Y" matches)
        self.search_count_label = QLabel("")
        self.search_count_label.setMinimumWidth(60)
        self.search_count_label.hide()
        bottom_layout.addWidget(self.search_count_label)

        self.prev_button = QPushButton("Previous")
        fxicons.set_icon(self.prev_button, "keyboard_arrow_left")
        self.prev_button.setProperty("icon_name", "keyboard_arrow_left")
        self.prev_button.setMaximumWidth(100)
        self.prev_button.clicked.connect(self._find_previous)
        apply_tip(
            self.prev_button,
            "Find Previous",
            "Find previous match",
            "Shift+Enter",
        )
        self.prev_button.hide()
        bottom_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        fxicons.set_icon(self.next_button, "keyboard_arrow_right")
        self.next_button.setProperty("icon_name", "keyboard_arrow_right")
        self.next_button.setMaximumWidth(80)
        self.next_button.clicked.connect(self._find_next)
        apply_tip(
            self.next_button,
            "Find Next",
            "Find next match",
            "Enter",
        )
        self.next_button.hide()
        bottom_layout.addWidget(self.next_button)

        self.close_search_button = QPushButton("")
        fxicons.set_icon(self.close_search_button, "close")
        self.close_search_button.setProperty("icon_name", "close")
        self.close_search_button.setMaximumWidth(30)
        apply_tip(
            self.close_search_button,
            "Close Search",
            "Close the search bar",
            "Esc",
        )
        self.close_search_button.clicked.connect(self._hide_search)
        self.close_search_button.hide()
        bottom_layout.addWidget(self.close_search_button)

        # Spacer to push Clear button to the right
        self.log_spacer = QWidget()
        self.log_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_layout.addWidget(self.log_spacer)

        # Clear button (always visible)
        self.clear_button = QPushButton("Clear")
        fxicons.set_icon(self.clear_button, "delete")
        self.clear_button.setProperty("icon_name", "delete")
        self.clear_button.setMaximumWidth(80)
        self.clear_button.clicked.connect(self.clear_log)
        apply_tip(
            self.clear_button,
            "Clear Log",
            "Clear all log messages",
        )
        bottom_layout.addWidget(self.clear_button)
        # A consumer may hide Clear at any time; the spacer follows it.
        self.clear_button.installEventFilter(self)

        layout.addLayout(bottom_layout)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Keep the spacer in step as the Clear button is shown or hidden."""
        if watched is self.clear_button and event.type() in (
            QEvent.ShowToParent,
            QEvent.HideToParent,
        ):
            self._sync_spacer()
        return super().eventFilter(watched, event)

    def show_search(self) -> None:
        """Show the search bar and put the cursor in it."""
        self.search_label.show()
        self.search_input.show()
        self.search_count_label.show()
        self.prev_button.show()
        self.next_button.show()
        self.close_search_button.show()
        # Limit spacer width when search is visible
        self.log_spacer.setMaximumWidth(50)
        self._sync_spacer()
        self.search_input.setFocus()
        self.search_input.selectAll()
        # Update count on show
        self._update_search_count()

    def _hide_search(self) -> None:
        """Hide the search bar and clear highlighting."""
        self.search_label.hide()
        self.search_input.hide()
        self.search_count_label.hide()
        self.prev_button.hide()
        self.next_button.hide()
        self.close_search_button.hide()
        # Remove spacer width limit when search is hidden
        self.log_spacer.setMaximumWidth(16777215)  # Qt's QWIDGETSIZE_MAX
        self._sync_spacer()
        # Clear any existing search highlighting
        cursor = self.output_area.textCursor()
        cursor.clearSelection()
        self.output_area.setTextCursor(cursor)

    def _sync_spacer(self) -> None:
        """Give the spacer room only while it has a Clear button to push.

        `isHidden`, not `isVisible`: this runs before the window is shown.
        """
        self.log_spacer.setVisible(not self.clear_button.isHidden())

    def _update_search_count(self) -> None:
        """Count total occurrences and update the count label."""
        search_text = self.search_input.text()
        if not search_text:
            self.search_count_label.setText("")
            return

        # Save current cursor position
        original_cursor = self.output_area.textCursor()

        # Count total occurrences
        cursor = QTextCursor(self.output_area.document())
        total_count = 0
        current_index = 0
        found_positions = []

        while True:
            cursor = self.output_area.document().find(search_text, cursor)
            if cursor.isNull():
                break
            total_count += 1
            found_positions.append(cursor.position())

        # Determine current position index
        if total_count > 0 and original_cursor.hasSelection():
            current_pos = original_cursor.position()
            for idx, pos in enumerate(found_positions):
                if pos >= current_pos:
                    current_index = idx + 1
                    break
            if current_index == 0:
                current_index = len(found_positions)

        # Update label
        if total_count == 0:
            self.search_count_label.setText("0 of 0")
        elif current_index > 0:
            self.search_count_label.setText(f"{current_index} of {total_count}")
        else:
            self.search_count_label.setText(f"0 of {total_count}")

    def _find_next(self) -> None:
        """Find next occurrence of search text."""
        search_text = self.search_input.text()
        if not search_text:
            return

        # Search forward from current position
        found = self.output_area.find(search_text)

        # If not found, wrap around to beginning
        if not found:
            cursor = self.output_area.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.output_area.setTextCursor(cursor)
            self.output_area.find(search_text)

        # Update the count display
        self._update_search_count()

    def _find_previous(self) -> None:
        """Find previous occurrence of search text."""
        search_text = self.search_input.text()
        if not search_text:
            return

        # Search backward from current position
        found = self.output_area.find(search_text, QTextDocument.FindBackward)

        # If not found, wrap around to end
        if not found:
            cursor = self.output_area.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_area.setTextCursor(cursor)
            self.output_area.find(search_text, QTextDocument.FindBackward)

        # Update the count display
        self._update_search_count()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard shortcuts."""
        # CTRL+F to show search
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.show_search()
            event.accept()
            return

        # ESC to hide search
        if event.key() == Qt.Key_Escape and self.search_input.isVisible():
            self._hide_search()
            event.accept()
            return

        super().keyPressEvent(event)

    def _setup_output_capture(self) -> None:
        """Setup logging capture.

        Adds a handler to the root logger to capture log messages
        and display them in the widget. Messages from child loggers
        will propagate up to the root logger automatically.
        """
        # Add logging handler to root logger only
        # Child loggers will propagate messages up to root by default
        self._log_handler = FXOutputLogHandler(self)
        self._log_handler.setLevel(logging.DEBUG)

        # Set a standard formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self._log_handler.setFormatter(formatter)

        logging.root.addHandler(self._log_handler)
        self._check_for_new_loggers()
        # A logger that does not propagate never reaches root; poll for them.
        self._logger_check_timer = QTimer(self)
        self._logger_check_timer.timeout.connect(self._check_for_new_loggers)
        self._logger_check_timer.start(1000)

    def _check_for_new_loggers(self) -> None:
        """Attach the handler to every logger that does not propagate."""
        for logger in list(logging.root.manager.loggerDict.values()):
            if (
                isinstance(logger, logging.Logger)
                and not logger.propagate
                and self._log_handler not in logger.handlers
            ):
                logger.addHandler(self._log_handler)

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

        # Schedule next update if needed
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

    def restore_output_streams(self) -> None:
        """Flush what is queued, then detach the handler from logging."""
        # No next tick will come, so drain everything past the bound.
        while self._pending_logs:
            self._flush_pending_log()
        self._throttle_timer.stop()
        if self._logger_check_timer:
            self._logger_check_timer.stop()
            self._logger_check_timer.deleteLater()
            self._logger_check_timer = None

        if self._log_handler:
            self._log_handler.detach()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle widget close event to restore output streams."""
        if self._capture_output:
            self.restore_output_streams()
        super().closeEvent(event)


def example() -> None:
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QGroupBox, QPushButton, QHBoxLayout
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app: FXApplication = FXApplication(sys.argv)

    # Main window
    window = FXMainWindow()
    window.setWindowTitle("FXOutputLogWidget")
    window.resize(700, 500)
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)

    # Log widget group
    log_group = QGroupBox("Output Log Widget")
    log_layout = QVBoxLayout(log_group)

    # Create the log widget with output capture
    log_widget = FXOutputLogWidget(capture_output=True)
    log_layout.addWidget(log_widget)

    # Buttons to simulate logging
    button_layout = QHBoxLayout()

    # Create a logger
    logger = logging.getLogger("example")
    logger.setLevel(logging.DEBUG)

    def log_debug():
        logger.debug("This is a debug message")

    def log_info():
        logger.info("This is an info message")

    def log_warning():
        logger.warning("This is a warning message")

    def log_error():
        logger.error("This is an error message")

    def log_ansi():
        # Log with ANSI colors
        log_widget.append_log(
            "\x1b[32mGreen text\x1b[0m - \x1b[31mRed text\x1b[0m - \x1b[34mBlue text\x1b[0m\x1b[0m"
        )

    debug_btn = QPushButton("Log Debug")
    debug_btn.clicked.connect(log_debug)
    button_layout.addWidget(debug_btn)

    info_btn = QPushButton("Log Info")
    info_btn.clicked.connect(log_info)
    button_layout.addWidget(info_btn)

    warning_btn = QPushButton("Log Warning")
    warning_btn.clicked.connect(log_warning)
    button_layout.addWidget(warning_btn)

    error_btn = QPushButton("Log Error")
    error_btn.clicked.connect(log_error)
    button_layout.addWidget(error_btn)

    ansi_btn = QPushButton("Log ANSI Colors")
    ansi_btn.clicked.connect(log_ansi)
    button_layout.addWidget(ansi_btn)

    log_layout.addLayout(button_layout)
    layout.addWidget(log_group)

    # Add initial log message
    log_widget.append_log("Log widget initialized. Press Ctrl+F to search.")

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
