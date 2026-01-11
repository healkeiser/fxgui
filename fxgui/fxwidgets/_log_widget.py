"""Output log widget with ANSI color support."""

# Built-in
import os
import logging
import re
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QKeyEvent,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
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
from fxgui import fxicons
from fxgui.fxwidgets._inputs import FXIconLineEdit
from fxgui.fxwidgets._tooltip import FXTooltip


class FXOutputLogHandler(logging.Handler):
    """Custom logging handler that sends log messages to an output log widget.

    This handler is used internally by `FXOutputLogWidget` to capture
    log messages and display them in the widget.

    Args:
        log_widget: The `FXOutputLogWidget` to send messages to.
    """

    def __init__(self, log_widget: "FXOutputLogWidget"):
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the output log widget."""
        try:
            msg = self.format(record)
            # Use the widget's signal to ensure thread-safe delivery
            self.log_widget.log_message.emit(msg)
        except Exception:
            self.handleError(record)


# Pre-compiled regex for ANSI escape codes (module-level for reuse)
_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[([0-9;]+)m")


class FXOutputLogWidget(QWidget):
    """A reusable read-only output log widget for displaying application logs.

    This widget provides a text display area that captures and shows
    logging output from the application. It supports ANSI color codes,
    search functionality, and log throttling for performance.

    Args:
        parent: Parent widget.
        capture_output: If `True`, adds a logging handler to capture
            log output from Python's logging module.

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

    # ANSI color mapping for terminal colors
    ANSI_COLORS = {
        "30": "#000000",
        "31": "#cd3131",
        "32": "#0dbc79",
        "33": "#e5e510",
        "34": "#2472c8",
        "35": "#bc3fbc",
        "36": "#11a8cd",
        "37": "#e5e5e5",
        "90": "#666666",
        "91": "#f14c4c",
        "92": "#23d18b",
        "93": "#f5f543",
        "94": "#3b8eea",
        "95": "#d670d6",
        "96": "#29b8db",
        "97": "#ffffff",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        capture_output: bool = False,
    ):
        """Initialize the output log widget."""
        super().__init__(parent)

        self._capture_output = capture_output
        self._log_handler = None
        self._modified_loggers = []
        self._logger_check_timer = None

        # Throttling mechanism to prevent UI freezing during
        # high-frequency logging
        self._pending_log = None
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._flush_pending_log)
        self._throttle_interval = 16

        # Connect signal to slot for thread-safe log appending
        self.log_message.connect(self._queue_log_message)

        # Setup UI
        self._setup_ui()

        # Setup output capture if requested
        if self._capture_output:
            self._setup_output_capture()

    def _setup_ui(self) -> None:
        """Setup the log widget UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Output area (read-only)
        # We're using `QTextEdit` for HTML support
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.output_area.setObjectName("fxOutputLogArea")
        self._output_area_tooltip = FXTooltip(
            parent=self.output_area,
            title="Output Area",
            description="Displays log messages from the application<br>Press <code>Ctrl+F</code> to search",
            shortcut="Ctrl+F",
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
        self._prev_button_tooltip = FXTooltip(
            parent=self.prev_button,
            title="Find Previous",
            description="Find previous match",
            shortcut="Shift+Enter",
        )
        self.prev_button.hide()
        bottom_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        fxicons.set_icon(self.next_button, "keyboard_arrow_right")
        self.next_button.setProperty("icon_name", "keyboard_arrow_right")
        self.next_button.setMaximumWidth(80)
        self.next_button.clicked.connect(self._find_next)
        self._next_button_tooltip = FXTooltip(
            parent=self.next_button,
            title="Find Next",
            description="Find next match",
            shortcut="Enter",
        )
        self.next_button.hide()
        bottom_layout.addWidget(self.next_button)

        self.close_search_button = QPushButton("")
        fxicons.set_icon(self.close_search_button, "close")
        self.close_search_button.setProperty("icon_name", "close")
        self.close_search_button.setMaximumWidth(30)
        self._close_search_tooltip = FXTooltip(
            parent=self.close_search_button,
            title="Close Search",
            description="Close the search bar",
            shortcut="Esc",
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
        self._clear_button_tooltip = FXTooltip(
            parent=self.clear_button,
            title="Clear Log",
            description="Clear all log messages",
        )
        bottom_layout.addWidget(self.clear_button)

        layout.addLayout(bottom_layout)

    def _show_search(self) -> None:
        """Show the search bar and focus the input."""
        self.search_label.show()
        self.search_input.show()
        self.search_count_label.show()
        self.prev_button.show()
        self.next_button.show()
        self.close_search_button.show()
        # Limit spacer width when search is visible
        self.log_spacer.setMaximumWidth(50)
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
        # Clear any existing search highlighting
        cursor = self.output_area.textCursor()
        cursor.clearSelection()
        self.output_area.setTextCursor(cursor)

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
            self._show_search()
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

        # Add to root logger only - messages propagate up from child loggers
        logging.root.addHandler(self._log_handler)

        # Track loggers with propagate=False that need direct handler attachment
        self._modified_loggers = []
        for name in list(logging.root.manager.loggerDict.keys()):
            logger_instance = logging.getLogger(name)
            if isinstance(logger_instance, logging.Logger):
                # Only add handler to loggers that don't propagate
                if not logger_instance.propagate:
                    if self._log_handler not in logger_instance.handlers:
                        logger_instance.addHandler(self._log_handler)
                        self._modified_loggers.append(name)

        # Setup a timer to periodically check for new loggers
        self._logger_check_timer = QTimer(self)
        self._logger_check_timer.timeout.connect(self._check_for_new_loggers)
        self._logger_check_timer.start(1000)  # Check every second

    def _check_for_new_loggers(self) -> None:
        """Check for newly created loggers and attach handler to them."""
        for name in list(logging.root.manager.loggerDict.keys()):
            if name not in self._modified_loggers:
                logger_instance = logging.getLogger(name)
                if isinstance(logger_instance, logging.Logger):
                    # Only add handler to loggers that don't propagate
                    if not logger_instance.propagate:
                        if self._log_handler not in logger_instance.handlers:
                            logger_instance.addHandler(self._log_handler)
                            self._modified_loggers.append(name)

    def _queue_log_message(self, text: str) -> None:
        """Queue a log message for throttled display.

        This ensures the UI stays responsive by limiting update frequency
        to ~60 FPS while still showing all messages.

        Args:
            text: Text to queue for display.
        """
        # Store the message
        self._pending_log = text

        # Start timer if not already running
        if not self._throttle_timer.isActive():
            # First message arrives immediately for responsiveness
            self._flush_pending_log()

    def _flush_pending_log(self) -> None:
        """Flush the pending log message to the display."""
        if self._pending_log is not None:
            text = self._pending_log
            self._pending_log = None

            # Display the message
            self._insert_text_with_ansi(text)

            # Add extra line break after each log entry
            cursor = self.output_area.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_area.setTextCursor(cursor)
            self.output_area.insertPlainText("\n")

            # Auto-scroll to bottom
            scrollbar = self.output_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

            # Schedule next update if needed
            self._throttle_timer.start(self._throttle_interval)

    def append_log(self, text: str) -> None:
        """Append text to the log output with ANSI color conversion.

        Args:
            text: Text to append (may contain ANSI color codes).
        """
        self._queue_log_message(text)

    def _insert_text_with_ansi(self, text: str) -> None:
        """Insert text with ANSI colors using QTextCharFormat.

        Args:
            text: Text with ANSI escape codes.
        """
        # Move cursor to end
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Get the widget's font to preserve monospace
        base_font = self.output_area.font()

        # Fast path: if no ANSI codes, insert plain text directly
        if "\x1b[" not in text:
            cursor.insertText(text)
            return

        # Track current styles
        current_color = None
        is_dim = False
        is_bright = False
        last_end = 0

        # Find all ANSI escape sequences using module-level compiled pattern
        for match in _ANSI_ESCAPE_PATTERN.finditer(text):
            # Insert text before this escape code
            if match.start() > last_end:
                segment = text[last_end : match.start()]

                # Create format for this segment, preserving monospace font
                fmt = QTextCharFormat()
                fmt.setFont(base_font)

                if current_color:
                    color = QColor(current_color)
                    if is_dim:
                        color.setAlpha(128)  # 50% opacity
                    fmt.setForeground(color)
                elif is_dim:
                    fmt.setForeground(QColor("#808080"))

                if is_bright:
                    font = QFont(base_font)
                    font.setBold(True)
                    fmt.setFont(font)

                cursor.insertText(segment, fmt)

            # Parse the escape code
            codes = match.group(1).split(";")
            for code in codes:
                if code == "0" or code == "":  # Reset
                    current_color = None
                    is_dim = False
                    is_bright = False
                elif code == "1":  # Bright/Bold
                    is_bright = True
                elif code == "2":  # Dim
                    is_dim = True
                elif code == "22":  # Normal intensity
                    is_bright = False
                    is_dim = False
                elif code in self.ANSI_COLORS:
                    current_color = self.ANSI_COLORS[code]

            last_end = match.end()

        # Insert remaining text
        if last_end < len(text):
            segment = text[last_end:]

            # Create format for this segment, preserving monospace font
            fmt = QTextCharFormat()
            fmt.setFont(base_font)

            if current_color:
                color = QColor(current_color)
                if is_dim:
                    color.setAlpha(128)  # 50% opacity
                fmt.setForeground(color)
            elif is_dim:
                fmt.setForeground(QColor("#808080"))

            if is_bright:
                font = QFont(base_font)
                font.setBold(True)
                fmt.setFont(font)

            cursor.insertText(segment, fmt)

    def clear_log(self) -> None:
        """Clear the log output."""
        self.output_area.clear()

    def restore_output_streams(self) -> None:
        """Remove logging handler from all loggers where it was added."""
        # Flush any pending message
        if hasattr(self, "_throttle_timer"):
            self._throttle_timer.stop()
            if self._pending_log is not None:
                self._flush_pending_log()

        # Stop the logger check timer if it exists
        if hasattr(self, "_logger_check_timer") and self._logger_check_timer:
            self._logger_check_timer.stop()
            self._logger_check_timer.deleteLater()
            self._logger_check_timer = None

        # Remove logging handler from all loggers where it was added
        if self._log_handler:
            logging.root.removeHandler(self._log_handler)

            # Remove from all modified loggers
            if hasattr(self, "_modified_loggers"):
                for logger_name in self._modified_loggers:
                    logger_instance = logging.getLogger(logger_name)
                    if (
                        logger_instance
                        and self._log_handler in logger_instance.handlers
                    ):
                        logger_instance.removeHandler(self._log_handler)

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
