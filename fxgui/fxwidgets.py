"""Custom Qt widgets for the `fxgui` framework.

This module provides a comprehensive set of customized Qt widgets designed
for building consistent and modern user interfaces across different
Digital Content Creation (DCC) applications.

Classes:
    FXApplication: Customized QApplication with built-in styling.
    FXMainWindow: Feature-rich main window with menus, toolbar, and status bar.
    FXSplashScreen: Customizable splash screen with progress bar support.
    FXStatusBar: Enhanced status bar with severity-based messaging.
    FXFloatingDialog: Popup dialog appearing at cursor position.
    FXPasswordLineEdit: Password input with show/hide toggle.
    FXIconButton: Button with theme-aware icon refresh.
    FXIconLineEdit: Line edit with embedded icon.
    FXColorLabelDelegate: Custom delegate for colored item rendering.
    FXSortedTreeWidgetItem: Natural sorting for tree items.
    FXSystemTray: System tray icon with context menu.
    FXWidget: Base widget with UI loading support.
    FXElidedLabel: Label with automatic text elision.
    FXSingleton: Metaclass for Qt singleton classes.
    FXResizedScrollArea: Scroll area that emits signal on resize.
    FXCollapsibleWidget: Expandable/collapsible content widget.
    FXCamelCaseValidator: Validator for camelCase input.
    FXLowerCaseValidator: Validator for lowercase input.
    FXLettersUnderscoreValidator: Validator for letters and underscores.
    FXCapitalizedLetterValidator: Validator for capitalized names.
    FXOutputLogWidget: Reusable log output widget with search.

Constants:
    CRITICAL, ERROR, WARNING, SUCCESS, INFO, DEBUG: Severity levels.

Examples:
    Creating a basic application:

    >>> from fxgui import fxwidgets
    >>> app = fxwidgets.FXApplication()
    >>> window = fxwidgets.FXMainWindow(title="My App")
    >>> window.show()
    >>> app.exec_()
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
import os
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional
from webbrowser import open_new_tab
import re
from urllib.parse import urlparse

# Third-party
from qtpy.QtCore import (
    QAbstractAnimation,
    QModelIndex,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRegularExpression,
    QSize,
    QTimer,
    Qt,
    Signal,
    Slot,
)
from qtpy.QtGui import (
    QBitmap,
    QColor,
    QCursor,
    QCloseEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRegularExpressionValidator,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QValidator,
)
from qtpy.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QHBoxLayout,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSplashScreen,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QSystemTrayIcon,
    QTextEdit,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Conditional import based on Qt version
from qtpy import QT_VERSION

QT_VERSION_MAJOR = int(QT_VERSION.split(".")[0])
if QT_VERSION_MAJOR >= 6:
    from qtpy.QtGui import QScreen
else:
    from qtpy.QtWidgets import QDesktopWidget

# Internal
from fxgui import fxicons, fxstyle, fxutils, fxdcc


# Public API
__all__ = [
    # Severity constants
    "CRITICAL",
    "ERROR",
    "WARNING",
    "SUCCESS",
    "INFO",
    "DEBUG",
    # Core widgets
    "FXApplication",
    "FXMainWindow",
    "FXWidget",
    "FXSplashScreen",
    "FXStatusBar",
    "FXFloatingDialog",
    "FXSystemTray",
    # Input widgets
    "FXPasswordLineEdit",
    "FXIconButton",
    "FXIconLineEdit",
    # Layout widgets
    "FXCollapsibleWidget",
    "FXResizedScrollArea",
    # Tree/List widgets
    "FXSortedTreeWidgetItem",
    "FXColorLabelDelegate",
    # Labels
    "FXElidedLabel",
    # Validators
    "FXCamelCaseValidator",
    "FXLowerCaseValidator",
    "FXLettersUnderscoreValidator",
    "FXCapitalizedLetterValidator",
    # Log widget
    "FXOutputLogWidget",
    "FXOutputLogHandler",
    # Metaclasses
    "FXSingleton",
]


# Constants
CRITICAL = 0
ERROR = 1
WARNING = 2
SUCCESS = 3
INFO = 4
DEBUG = 5


class FXSingleton(type(QObject)):
    """Metaclass for Qt classes that are singletons.

    This metaclass ensures that only one instance of each class can exist.
    If an instance already exists, it returns the existing instance instead
    of creating a new one. Each subclass gets its own singleton instance.

    Examples:
        >>> from fxgui import fxwidgets
        >>>
        >>> class MySingletonWindow(fxwidgets.FXMainWindow, metaclass=fxwidgets.FXSingleton):
        ...     pass
        >>>
        >>> window1 = MySingletonWindow()
        >>> window2 = MySingletonWindow()
        >>> assert window1 is window2  # Same instance
    """

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls._instance: QWidget = None
        cls._initialized: bool = False

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
            cls._initialized = True
        else:
            # If instance already exists, just show it (if it's a window)
            if hasattr(cls._instance, "show"):
                cls._instance.show()
                cls._instance.raise_()
                cls._instance.activateWindow()
        return cls._instance

    def reset_instance(cls):
        """Reset the singleton instance. Useful for testing or cleanup."""
        cls._instance = None
        cls._initialized = False


class FXResizedScrollArea(QScrollArea):
    """A custom scroll area that emits a signal when resized.

    This widget extends QScrollArea to emit a `resized` signal whenever
    the widget is resized, which is useful for responsive layouts.

    Signals:
        resized: Emitted when the scroll area is resized.

    Examples:
        >>> scroll_area = FXResizedScrollArea()
        >>> scroll_area.resized.connect(lambda: print("Resized!"))
    """

    resized = Signal()

    def resizeEvent(self, event):
        """Emit the resized signal when the widget is resized."""
        self.resized.emit()
        return super().resizeEvent(event)


class FXCollapsibleWidget(QWidget):
    """A widget that can expand or collapse its content.

    The widget consists of a header with a toggle button and a content area
    that can be shown or hidden with an animation effect.

    Args:
        parent: Parent widget.
        title: Title displayed in the header.
        animation_duration: Duration of expand/collapse animation in ms.
        max_content_height: Maximum height for content area when
            expanded (0 = no limit).

    Examples:
        >>> from qtpy.QtWidgets import QLabel, QVBoxLayout
        >>> collapsible = FXCollapsibleWidget(title="Settings")
        >>> layout = QVBoxLayout()
        >>> layout.addWidget(QLabel("Option 1"))
        >>> layout.addWidget(QLabel("Option 2"))
        >>> collapsible.setContentLayout(layout)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        animation_duration: int = 200,
        max_content_height: int = 300,
    ):
        """Initialize the collapsible section."""
        super().__init__(parent=parent)

        # Store properties
        self.animation_duration = animation_duration
        self.max_content_height = max_content_height
        self._title = str(title)
        self._is_expanded = False
        self._has_been_expanded = False
        self._content_height = 0

        # Create fixed header layout
        self.header_widget = QWidget()
        self.header_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )

        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setIcon(fxicons.get_icon("chevron_right"))
        self.toggle_button.setProperty("icon_name", "chevron_right")
        self.toggle_button.setText(self._title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)

        # Button won't get smaller than this
        button_width = max(120, self.toggle_button.sizeHint().width())
        self.toggle_button.setMinimumWidth(button_width)
        self.toggle_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Header line
        self.header_line = QFrame()
        self.header_line.setFrameShape(QFrame.HLine)
        self.header_line.setFrameShadow(QFrame.Sunken)
        self.header_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.header_line)

        # Content area: always with scrollbars when needed
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_area.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )

        # Initially collapsed
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_widget)
        main_layout.addWidget(self.content_area)

        # Size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Set minimum width to ensure button visibility
        min_width = max(150, button_width + 30)
        self.setMinimumWidth(min_width)

        # Setup animation
        self.toggle_animation = QParallelAnimationGroup()
        self.toggle_animation.addAnimation(
            QPropertyAnimation(self.content_area, b"maximumHeight")
        )
        self.toggle_animation.addAnimation(
            QPropertyAnimation(self.content_area, b"minimumHeight")
        )

        # Connect signals
        self.toggle_button.clicked.connect(self._toggle_content)
        self.toggle_animation.finished.connect(self._on_animation_finished)

    def _toggle_content(self, checked: bool) -> None:
        """Toggle content visibility with animation."""
        # Update button icon and property
        icon_name = "expand_more" if checked else "chevron_right"
        self.toggle_button.setIcon(fxicons.get_icon(icon_name))
        self.toggle_button.setProperty("icon_name", icon_name)

        # Store expanded state
        self._is_expanded = checked

        if checked and not self._has_been_expanded:
            # First time expansion: measure content
            if self.content_area.widget():
                self._content_height = (
                    self.content_area.widget().sizeHint().height()
                )
            self._has_been_expanded = True

        # Calculate target height for animation
        target_height = 0
        if checked:
            target_height = self._calculate_content_height()

        # Update animations
        for i in range(self.toggle_animation.animationCount()):
            anim = self.toggle_animation.animationAt(i)
            anim.setDuration(self.animation_duration)
            anim.setStartValue(0)
            anim.setEndValue(target_height)

        # Run animation
        direction = (
            QAbstractAnimation.Forward
            if checked
            else QAbstractAnimation.Backward
        )
        self.toggle_animation.setDirection(direction)
        self.toggle_animation.start()

    def _calculate_content_height(self) -> int:
        """Calculate appropriate content height based on constraints."""
        if not self.content_area.widget():
            return 0

        # Get raw content height
        content_height = self._content_height

        # Apply max_content_height if specified
        if self.max_content_height > 0:
            content_height = min(content_height, self.max_content_height)

        return content_height

    def _on_animation_finished(self) -> None:
        """Handle animation completion."""
        if not self._is_expanded:
            # When collapsed, ensure content is hidden
            self.content_area.setMinimumHeight(0)
            self.content_area.setMaximumHeight(0)
            self.content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.content_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff
            )
        else:
            # When expanded, ensure scrollbars appear as needed
            height = self._calculate_content_height()
            self.content_area.setMinimumHeight(height)
            self.content_area.setMaximumHeight(height)

            # Enable scrollbars only if content exceeds visible area
            if self.content_area.widget():
                widget_width = self.content_area.widget().sizeHint().width()
                widget_height = self.content_area.widget().sizeHint().height()

                h_policy = (
                    Qt.ScrollBarAsNeeded
                    if widget_width > self.width()
                    else Qt.ScrollBarAlwaysOff
                )
                v_policy = (
                    Qt.ScrollBarAsNeeded
                    if widget_height > height
                    else Qt.ScrollBarAlwaysOff
                )

                self.content_area.setHorizontalScrollBarPolicy(h_policy)
                self.content_area.setVerticalScrollBarPolicy(v_policy)

    def setContentLayout(self, content_layout: QLayout) -> None:
        """Set the layout for the content area.

        Args:
            content_layout (QLayout): The layout to set for the content area.
        """
        # Create content widget
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        self.content_area.setWidget(content_widget)

        # Measure content height
        self._content_height = content_widget.sizeHint().height()

        # Initially collapsed
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)


class FXCamelCaseValidator(QRegularExpressionValidator):
    """Validator for camelCase without special characters or numbers.

    This validator ensures input follows camelCase format: starts with
    a lowercase letter, followed by zero or more groups of an uppercase
    letter followed by lowercase letters.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXCamelCaseValidator())
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Regular expression for camelCase without special characters or
        # numbers
        camel_case_regex = QRegularExpression("^[a-z]+([A-Z][a-z]*)*$")

        # Use the correct method based on what's available
        if hasattr(self, "setRegularExpression"):
            self.setRegularExpression(camel_case_regex)
        else:
            self.setRegExp(camel_case_regex)


class FXLowerCaseValidator(QRegularExpressionValidator):
    """Validator for lowercase letters only, with optional numbers and
    underscores support.

    Args:
        allow_numbers: If `True`, allows numbers in addition to lowercase
            letters.
        allow_underscores: If `True`, allows underscores in addition to
            lowercase letters.
        parent: Parent widget.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXLowerCaseValidator(allow_numbers=True))
    """

    def __init__(
        self,
        allow_numbers: bool = False,
        allow_underscores: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # Build regex pattern based on options
        pattern = "^[a-z"
        if allow_numbers:
            pattern += "0-9"
        if allow_underscores:
            pattern += "_"
        pattern += "]+$"

        lowercase_regex = QRegularExpression(pattern)

        # Use the correct method based on what's available
        if hasattr(self, "setRegularExpression"):
            self.setRegularExpression(lowercase_regex)
        else:
            self.setRegExp(lowercase_regex)


class FXLettersUnderscoreValidator(QRegularExpressionValidator):
    """Validator for letters and underscores, with optional numbers support.

    Args:
        allow_numbers: If `True`, allows numbers in addition to letters and
            underscores.
        parent: Parent widget.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXLettersUnderscoreValidator(allow_numbers=True))
    """

    def __init__(
        self, allow_numbers: bool = False, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # Regular expression for letters, underscores, and optionally numbers
        if allow_numbers:
            letters_underscore_regex = QRegularExpression("^[a-zA-Z0-9_]+$")
        else:
            letters_underscore_regex = QRegularExpression("^[a-zA-Z_]+$")

        # Use the correct method based on what's available
        if hasattr(self, "setRegularExpression"):
            self.setRegularExpression(letters_underscore_regex)
        else:
            self.setRegExp(letters_underscore_regex)


class FXCapitalizedLetterValidator(QValidator):
    """Validator for names that must start with a capital letter and contain
    only letters.

    This validator ensures the first character is uppercase and all
    characters are alphabetic.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXCapitalizedLetterValidator())
    """

    def validate(self, input_string: str, pos: int):
        """Allow only letters and must start with a capital letter."""
        if input_string:
            if not input_string[0].isupper() or not input_string.isalpha():
                return (QValidator.Invalid, input_string, pos)
        return (QValidator.Acceptable, input_string, pos)

    def fixup(self, input_string: str) -> str:
        """Automatically capitalize the first letter."""
        if input_string:
            return input_string[0].upper() + input_string[1:]
        return input_string


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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Output area (read-only)
        # We're using `QTextEdit` for HTML support
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.output_area.setObjectName("fxOutputLogArea")

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
        self.prev_button.setIcon(fxicons.get_icon("keyboard_arrow_left"))
        self.prev_button.setProperty("icon_name", "keyboard_arrow_left")
        self.prev_button.setMaximumWidth(80)
        self.prev_button.clicked.connect(self._find_previous)
        self.prev_button.hide()
        bottom_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        self.next_button.setIcon(fxicons.get_icon("keyboard_arrow_right"))
        self.next_button.setProperty("icon_name", "keyboard_arrow_right")
        self.next_button.setMaximumWidth(80)
        self.next_button.clicked.connect(self._find_next)
        self.next_button.hide()
        bottom_layout.addWidget(self.next_button)

        self.close_search_button = QPushButton("")
        self.close_search_button.setIcon(fxicons.get_icon("close"))
        self.close_search_button.setProperty("icon_name", "close")
        self.close_search_button.setMaximumWidth(30)
        self.close_search_button.setToolTip("Close search (Esc)")
        self.close_search_button.clicked.connect(self._hide_search)
        self.close_search_button.hide()
        bottom_layout.addWidget(self.close_search_button)

        # Spacer to push Clear button to the right
        self.log_spacer = QWidget()
        self.log_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_layout.addWidget(self.log_spacer)

        # Clear button (always visible)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setIcon(fxicons.get_icon("delete"))
        self.clear_button.setProperty("icon_name", "delete")
        self.clear_button.setMaximumWidth(80)
        self.clear_button.clicked.connect(self.clear_log)
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


class _FXTreeWidget(QTreeWidget):
    """Custom QTreeWidget with fixed row height.

    Warning:
        This class is deprecated and kept for reference only.
        Consider using a standard QTreeWidget with stylesheet-based
        row height configuration instead.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sizeHintForRow(self, row: int) -> int:
        """Override the size hint for each row to set a specific height.

        Args:
            row: The row index.

        Returns:
            The height for the specified row.
        """

        return 20  # Row height


class _FXColorLabelDelegate(QStyledItemDelegate):
    """A custom delegate to paint items with specific colors and icons.

    Warning:
        This class is deprecated. Use `FXColorLabelDelegate` instead,
        which provides improved functionality and margin support.
    """

    # Custom role to skip delegate
    SKIP_DELEGATE_ROLE = Qt.UserRole + 5

    def __init__(
        self,
        colors_icons: Dict[str, Tuple[QColor, QColor, QColor, QIcon, bool]],
        parent=None,
    ):
        """Initializes the delegate with a dictionary of colors and icons.

        Args:
            colors_icons: A dictionary where keys are text patterns and values
                are tuples containing background color, border color,
                text/icon color, icon, and a boolean indicating if the icon
                should be colored.
            parent: The parent object.
        """

        super().__init__(parent)
        self.colors_icons = colors_icons

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paints the item with the specified colors and icons.

        Args:
            painter: The painter used to draw the item.
            option: The style options for the item.
            index: The model index of the item.
        """

        skip_delegate = index.data(FXColorLabelDelegate.SKIP_DELEGATE_ROLE)
        if skip_delegate:
            super().paint(painter, option, index)
            return

        super().paint(painter, option, index)

        text = index.data()
        if not text:
            super().paint(painter, option, index)
            return

        # Default colors and icon (theme-aware)
        theme_colors = fxstyle.get_theme_colors()
        background_color, border_color, text_icon_color, icon, color_icon = (
            QColor(theme_colors["background"]),
            QColor(theme_colors["background"]),
            QColor(theme_colors["text"]),
            fxicons.get_icon("drag_indicator"),
            False,
        )

        # Find the best match for the text in the colors_icons dictionary
        best_match_length = 0
        best_match = None

        for key, value in self.colors_icons.items():
            if key in text.lower() and len(key) > best_match_length:
                best_match = value
                best_match_length = len(key)

        if best_match:
            (
                background_color,
                border_color,
                text_icon_color,
                icon,
                color_icon,
            ) = best_match

        # Adjust colors based on item state
        if option.state & QStyle.State_Selected:
            background_color = background_color.lighter(125)
            border_color = border_color.lighter(125)
        elif option.state & QStyle.State_MouseOver:
            background_color = background_color.darker(125)
            border_color = border_color.darker(125)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipRect(option.rect)

        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        rect = option.rect
        icon_size = QSize(15, 15)
        padding = 2

        # Calculate the rectangles for text and icon
        text_rect, icon_rect = self.calculate_rects(
            rect, text_width, text_height, icon_size, padding
        )

        # Draw the background rectangle
        painter.setBrush(background_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(
            text_rect.adjusted(-icon_size.width() - 10, -padding, 0, padding),
            2,
            2,
        )

        # Draw the icon
        if color_icon:
            pixmap = icon.pixmap(icon_size)
            colored_pixmap = QPixmap(pixmap.size())
            colored_pixmap.fill(Qt.transparent)

            painter2 = QPainter(colored_pixmap)
            painter2.setCompositionMode(QPainter.CompositionMode_Source)
            painter2.drawPixmap(0, 0, pixmap)
            painter2.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter2.fillRect(colored_pixmap.rect(), text_icon_color)
            painter2.end()

            painter.drawPixmap(icon_rect, colored_pixmap)
        else:
            icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )

        # Draw the text
        painter.setPen(text_icon_color)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        painter.restore()

    def calculate_rects(
        self,
        rect: QRect,
        text_width: int,
        text_height: int,
        icon_size: QSize,
        padding: int,
    ) -> Tuple[QRect, QRect]:
        """Calculates the rectangles for the text and icon.

        Args:
            rect: The bounding rectangle of the item.
            text_width: The width of the text.
            text_height: The height of the text.
            icon_size: The size of the icon.
            padding: The padding around the text and icon.

        Returns:
            A tuple containing the text rectangle and the icon rectangle.
        """

        text_rect = QRect(
            rect.left() + icon_size.width() + 12,
            rect.top() + (rect.height() - text_height) // 2,
            text_width + 10,
            text_height,
        )

        icon_rect = QRect(
            rect.left() + 8,
            rect.top() + (rect.height() - icon_size.height()) // 2,
            icon_size.width(),
            icon_size.height(),
        )

        # Adjust the text_rect to be `padding` pixels away from the item border
        text_rect = text_rect.adjusted(padding, padding, -padding, -padding)

        return text_rect, icon_rect

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        """
        Provides the size hint for the item.

        Args:
            option: The style options for the item.
            index: The model index of the item.

        Returns:
            The size hint for the item.
        """

        text = index.data()
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        icon_size = 15
        padding = 4
        return QSize(
            text_width + icon_size + 20,
            max(text_height, icon_size) + 2 * padding,
        )


class FXColorLabelDelegate(QStyledItemDelegate):
    """A custom delegate to paint items with specific colors and icons based
    on their text content."""

    # Custom role to skip delegate
    SKIP_DELEGATE_ROLE = Qt.UserRole + 5

    def __init__(
        self,
        colors_icons: Dict[str, Tuple[QColor, QColor, QColor, QIcon, bool]],
        parent: Optional[QWidget] = None,
        margin_left: int = 2,
        margin_top: Optional[int] = None,
        margin_bottom: Optional[int] = None,
    ):
        """Initializes the delegate with a dictionary of colors and icons.

        Args:
            colors_icons: A dictionary where keys are text patterns and values
                are tuples containing background color, border color,
                text/icon color, icon, and a boolean indicating if the icon
                should be colored.
            parent: The parent object.
            margin_left: The left margin for the text and icon. Defaults to 2.
            margin_top: The top margin for the text and icon. Defaults to
                `margin_left`.
            margin_bottom: The bottom margin for the text and icon. Defaults to
                `margin_left`.
        """

        super().__init__(parent)

        # Dictionary mapping item texts to (background_color, border_color,
        # text_icon_color, icon, color_icon)
        self.colors_icons = colors_icons

        # Margins
        self.margin_left = margin_left
        self.margin_top = self.margin_left if margin_top is None else margin_top
        self.margin_bottom = (
            self.margin_left if margin_bottom is None else margin_bottom
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paints the item with the specified colors and icons.

        Args:
            painter: The painter used to draw the item.
            option: The style options for the item.
            index: The model index of the item.
        """

        # Check if the delegate should skip drawing
        skip_delegate = index.data(FXColorLabelDelegate.SKIP_DELEGATE_ROLE)
        if skip_delegate:
            super().paint(painter, option, index)
            return

        # Retrieve the text and associated colors and icon
        text = index.data()
        if not text:
            return  # No need to paint anything if there's no text

        # Create a copy of the option to modify to clear the text and icon
        # XXX: Not working, need to investigate
        option_modified = QStyleOptionViewItem(option)
        option_modified.text = ""
        option_modified.icon = QIcon()

        # Call the base class paint method to draw selection and hover effects
        super().paint(painter, option_modified, index)

        # Set the default colors and icon (theme-aware)
        theme_colors = fxstyle.get_theme_colors()
        background_color, border_color, text_icon_color, icon, color_icon = (
            QColor(theme_colors["background"]),
            QColor(theme_colors["border_light"]),
            QColor(
                theme_colors["surface"]
                if fxstyle._theme == "dark"
                else "#ffffff"
            ),
            fxicons.get_icon("drag_indicator"),
            False,  # Default to not coloring the icon
        )

        # Find the best match for the text in the colors_icons dictionary
        best_match_length = 0
        best_match = None

        for key, value in self.colors_icons.items():
            if key in text.lower() and len(key) > best_match_length:
                best_match = value
                best_match_length = len(key)

        if best_match:
            (
                background_color,
                border_color,
                text_icon_color,
                icon,
                color_icon,
            ) = best_match

        # Adjust colors based on item state
        if option.state & QStyle.State_Selected:
            background_color = background_color.lighter(125)
            border_color = border_color.lighter(125)
        elif option.state & QStyle.State_MouseOver:
            background_color = background_color.darker(125)
            border_color = border_color.darker(125)

        # Save painter state
        painter.save()

        # Anti-aliasing for smoother rendering
        painter.setRenderHint(QPainter.Antialiasing)

        # Set the clipping region to the column's rectangle
        painter.setClipRect(option.rect)

        # Adjust the rectangle to be away from the border using margins
        rect = option.rect.adjusted(
            self.margin_left,
            self.margin_top,
            -self.margin_left,
            -self.margin_bottom,
        )

        # Use the default font and measure text size
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        # Define the rectangle around the text, aligned to the left
        icon_size = QSize(14, 14)  # Icon size
        text_rect = QRect(
            rect.left() + icon_size.width() + 2,  # Space between icon and text
            rect.top() + (rect.height() - text_height) // 2,
            text_width + 10,
            text_height + 0,
        )

        # Draw custom label with border and background colors from the mapping
        painter.setBrush(background_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(
            text_rect.adjusted(-icon_size.width() - 2, 0, 0, 0), 2, 2
        )

        # Draw the icon inside the rectangle, on the left of the text
        icon_rect = QRect(
            rect.left() + 2,
            rect.top() + (rect.height() - icon_size.height()) // 2,
            icon_size.width(),
            icon_size.height(),
        )

        if color_icon:
            # Convert the icon to a QPixmap and apply the text/icon color
            colored_pixmap = fxicons.change_pixmap_color(
                icon.pixmap(icon_size), text_icon_color
            )
            painter.drawPixmap(icon_rect, colored_pixmap)
        else:
            # Draw the original icon without coloring
            icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )

        # Draw the text inside the rectangle
        painter.setPen(text_icon_color)
        painter.drawText(text_rect, Qt.AlignCenter, text)

        # Restore painter state
        painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        """Provides the size hint for the item.

        Args:
            option: The style options for the item.
            index: The model index of the item.

        Returns:
            The size hint for the item.
        """

        text = index.data()
        if not text:
            return QSize()
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        icon_size = 14
        width = (
            text_width
            + icon_size
            + 20
            + self.margin_left * 2  # Add horizontal margins
        )
        height = (
            max(text_height, icon_size)
            + 2
            + self.margin_top
            + self.margin_bottom  # Add vertical margins
        )
        return QSize(width, height)


class _FXSortedTreeWidgetItem(QTreeWidgetItem):
    """Custom QTreeWidgetItem with QCollator-based natural sorting.

    Warning:
        This class is deprecated and kept for reference only.
        Use `FXSortedTreeWidgetItem` instead, which provides natural
        sorting without requiring QCollator import.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import QCollator locally to avoid unused import warning
        from qtpy.QtCore import QCollator

        self.collator = QCollator()
        self.collator.setNumericMode(True)

    def __lt__(self, other: "FXSortedTreeWidgetItem") -> bool:
        """Override the less-than operator to provide a custom sorting logic.

        Args:
            other: Another instance of `FXSortedTreeWidgetItem` to compare with.

        Returns:
            `True` if the current item is less than the other item according to
            the natural sort order, `False` otherwise.
        """

        # Get the index of the column currently being used for sorting
        column = self.treeWidget().sortColumn()

        # Compare the items using QCollator
        return self.collator.compare(self.text(column), other.text(column)) < 0


# Pre-compiled regex for natural sorting (module-level for reuse)
_NATURAL_SORT_PATTERN = re.compile(r"([0-9]+)")


class FXSortedTreeWidgetItem(QTreeWidgetItem):
    """Custom `QTreeWidgetItem` that provides natural sorting for strings
    containing numbers. This is useful for sorting items like version numbers
    or other strings where numeric parts should be ordered numerically.

    For example, this class will sort the following strings in the correct
    human-friendly order:

    - "something1"
    - "something9"
    - "something17"
    - "something25"

    Instead of the default sorting order:

    - "something1"
    - "something17"
    - "something25"
    - "something9"
    """

    def __lt__(self, other: "FXSortedTreeWidgetItem") -> bool:
        """Override the less-than operator to provide a custom sorting logic.

        Args:
            other: Another instance of `FXSortedTreeWidgetItem` to compare with.

        Returns:
            `True` if the current item is less than the other item according to
            the natural sort order, `False` otherwise.
        """
        # Get the index of the column currently being used for sorting
        column = self.treeWidget().sortColumn()

        # Compare the items using the custom natural sort key
        return self._generate_natural_sort_key(
            self.text(column)
        ) < self._generate_natural_sort_key(other.text(column))

    @staticmethod
    def _generate_natural_sort_key(s: str) -> list:
        """Generate a sort key for natural sorting of strings containing
        numbers in a human-friendly way.

        Args:
            s: The string to sort.

        Returns:
            A list of elements where numeric parts are converted to integers
            and other parts are converted to lowercase strings.
        """
        # Use pre-compiled regex for better performance
        return [
            int(text) if text.isdigit() else text.lower()
            for text in _NATURAL_SORT_PATTERN.split(s)
        ]


class FXApplication(QApplication):
    """Customized QApplication class."""

    _instance = None  # Private class attribute to hold the singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:

            # Create the instance if it doesn't exist
            cls._instance = super(FXApplication, cls).__new__(cls)

            # Initialize the instance once
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
        if not self.__initialized:
            super().__init__(*args, **kwargs)

            fxstyle.set_style(self, "Fusion")
            self.setStyleSheet(fxstyle.load_stylesheet())

            # Mark the instance as initialized
            self.__initialized = True

    @classmethod
    def instance(cls, *args, **kwargs):
        """Return the existing instance or create a new one if it doesn't
        exist.
        """

        # This ensures that `__new__` and `__init__` are called if the instance
        # doesn't exist
        return cls(*args, **kwargs)


class _FXBorderWidget(QWidget):
    """Internal widget to draw the border on top of all other content."""

    def __init__(
        self,
        parent: QWidget,
        border_width: int,
        border_color: str,
        corner_radius: int,
    ):
        super().__init__(parent)
        self.border_width = border_width
        self.border_color = border_color
        self.corner_radius = corner_radius
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event) -> None:
        if self.border_width <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(self.border_color))
        pen.setWidthF(self.border_width)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        rect = self.rect()
        half_pen = self.border_width / 2.0
        border_rect = rect.adjusted(half_pen, half_pen, -half_pen, -half_pen)

        if self.corner_radius > 0:
            adjusted_radius = max(0, self.corner_radius - half_pen)
            painter.drawRoundedRect(
                border_rect, adjusted_radius, adjusted_radius
            )
        else:
            painter.drawRect(border_rect)

        painter.end()


class FXSplashScreen(QSplashScreen):
    """Customized QSplashScreen class."""

    ICON_HEIGHT = 32
    IDEAL_WIDTH = 800
    IDEAL_HEIGHT = 450

    def __init__(
        self,
        image_path: Optional[str] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        information: Optional[str] = None,
        show_progress_bar: bool = False,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        color_a: str = fxstyle._COLOR_A_DEFAULT,
        color_b: str = fxstyle._COLOR_B_DEFAULT,
        fade_in: bool = False,
        set_stylesheet: bool = True,
        overlay_opacity: float = 1.0,
        corner_radius: int = 0,
        border_width: int = 0,
        border_color: str = "#4a4949",
    ):
        image = self._load_image(image_path)
        super().__init__(image)

        # Attributes
        self.pixmap: QPixmap = image
        self._default_icon = os.path.join(
            os.path.dirname(__file__), "icons", "favicon_light.png"
        )
        self.icon: QIcon = QIcon(icon) if icon else QIcon(self._default_icon)
        self.title: str = title or "Untitled"
        self.information: str = information or self._default_information()
        self.show_progress_bar: bool = show_progress_bar
        self.project: str = project or "Project"
        self.version: str = version or "0.0.0"
        self.company: str = company or "Company"
        self.color_a: str = color_a
        self.color_b: str = color_b
        self.fade_in: bool = fade_in
        self.overlay_opacity: float = overlay_opacity
        self.corner_radius: int = corner_radius
        self.border_width: int = border_width
        self.border_color: str = border_color

        # Enable transparency for smooth anti-aliased corners
        # Both flags are required for truly transparent rounded corners
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Methods
        self._grey_overlay()
        self._create_border_overlay()

        # Styling
        if set_stylesheet:
            self.setStyleSheet(
                fxstyle.load_stylesheet(
                    color_a=self.color_a, color_b=self.color_b
                )
            )

        # Apply overlay opacity after stylesheet to ensure it's not overridden
        self._apply_overlay_opacity()

    # Private methods
    def _load_image(self, image_path: Optional[str]) -> QPixmap:
        if image_path is None:
            image_path = os.path.join(
                os.path.dirname(__file__), "images", "snap.png"
            )
        elif not os.path.isfile(image_path):
            raise ValueError(f"Invalid image path: {image_path}")
        return self._resize_image(image_path)

    def _default_information(self) -> str:
        return (
            "At vero eos et accusamus et iusto odio dignissimos ducimus qui "
            "blanditiis praesentium voluptatum deleniti atque corrupti quos "
            "dolores et quas molestias excepturi sint occaecati cupiditate non "
            "provident, similique sunt in culpa qui officia deserunt mollitia "
            "animi, id est laborum et dolorum fuga. Et harum quidem rerum facilis "
            "est et expedita distinctio. Nam libero tempore, cum soluta nobis est "
            "eligendi optio cumque nihil impedit quo minus id quod maxime placeat "
            "facere possimus, omnis voluptas assumenda est, omnis dolor "
            "repellendus. Temporibus autem quibusdam et aut officiis debitis aut "
            "rerum necessitatibus saepe eveniet ut et voluptates repudiandae sint "
            "et molestiae non recusandae. Itaque earum rerum hic tenetur a "
            "sapiente delectus, ut aut reiciendis voluptatibus maiores alias "
            "consequatur aut perferendis doloribus asperiores repellat."
        )

    def _resize_image(self, image_path: str) -> QPixmap:
        pixmap = QPixmap(image_path)
        width = pixmap.width()
        height = pixmap.height()

        aspect = width / float(height)
        ideal_aspect = self.IDEAL_WIDTH / float(self.IDEAL_HEIGHT)

        if aspect > ideal_aspect:
            new_width = int(ideal_aspect * height)
            offset = (width - new_width) / 2
            crop_rect = QRect(offset, 0, new_width, height)
        else:
            new_height = int(width / ideal_aspect)
            offset = (height - new_height) / 2
            crop_rect = QRect(0, int(offset), width, new_height)

        cropped_pixmap = pixmap.copy(crop_rect)
        resized_pixmap = cropped_pixmap.scaled(
            self.IDEAL_WIDTH,
            self.IDEAL_HEIGHT,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        return resized_pixmap

    def _grey_overlay(self) -> None:
        self.overlay_frame = QFrame(self)
        self._update_overlay_geometry()
        fxutils.add_shadows(self, self.overlay_frame)

        # Apply background opacity via stylesheet
        self._apply_overlay_opacity()

        layout = QVBoxLayout(self.overlay_frame)
        layout.setContentsMargins(50, 50, 50, 50)

        self.icon_label = QLabel()
        pixmap = QPixmap(self.icon.pixmap(self.ICON_HEIGHT))
        self.icon_label.setPixmap(pixmap)

        self.title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("font-size: 18pt;")

        title_icon_layout = QHBoxLayout()
        title_icon_layout.addWidget(self.icon_label)
        title_icon_layout.addWidget(self.title_label)
        title_icon_layout.setSpacing(10)
        title_icon_layout.addStretch()
        layout.addLayout(title_icon_layout)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self.info_label = FXElidedLabel(self.information)
        self.info_label.setAlignment(Qt.AlignJustify)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 10pt;")
        # Limit height to allow proper text elision
        self.info_label.setMaximumHeight(120)
        layout.addWidget(self.info_label)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignLeft)
        self.message_label.setStyleSheet("font-size: 10pt;")
        layout.addWidget(self.message_label)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        if self.show_progress_bar:
            self.progress_bar = QProgressBar()
            layout.addWidget(self.progress_bar)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Copyright QLabel
        self.copyright_label = QLabel(
            f"{self.project} | {self.version} | {self.company}"
        )
        self.copyright_label.setStyleSheet(
            "font-size: 8pt; qproperty-alignment: AlignBottom;"
        )

        layout.addWidget(self.copyright_label)

    def _update_overlay_geometry(self) -> None:
        """Update overlay frame geometry accounting for border."""

        # Inset the overlay by the full border width so it doesn't cover the border
        inset = self.border_width
        x = inset
        y = inset
        width = (self.pixmap.width() // 2) - inset
        height = self.pixmap.height() - (2 * inset)
        self.overlay_frame.setGeometry(x, y, width, height)

    def _create_border_overlay(self) -> None:
        """Create a transparent overlay widget that draws the border on top."""

        self._border_widget = _FXBorderWidget(
            self,
            self.border_width,
            self.border_color,
            self.corner_radius,
        )
        self._border_widget.setGeometry(self.rect())
        self._border_widget.raise_()  # Ensure it's on top

    def _update_border_overlay(self) -> None:
        """Update the border overlay with current settings."""

        if hasattr(self, "_border_widget"):
            self._border_widget.border_width = self.border_width
            self._border_widget.border_color = self.border_color
            self._border_widget.corner_radius = self.corner_radius
            self._border_widget.setGeometry(self.rect())
            self._border_widget.update()

    def _update_copyright_label(self) -> None:
        project = self.project or "Project"
        version = self.version or "0.0.0"
        company = self.company or "\u00a9 Company"
        self.copyright_label.setText(f"{project} | {version} | {company}")

    def _fade_in(self) -> None:
        opaqueness = 0.0
        step = 0.001
        self.setWindowOpacity(opaqueness)
        self.show()

        @Slot()
        def update_opacity():
            nonlocal opaqueness
            if opaqueness < 1:
                self.setWindowOpacity(opaqueness)
                opaqueness += step * 100
            else:
                self.fade_timer.stop()

        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(update_opacity)
        self.fade_timer.start(100)

    # Public methods
    def set_progress(self, value: int, max_range: int = 100):
        """Set the progress value for the splash screen.

        Args:
            value: The progress value.
            max_range: The maximum progress value. Defaults to `100`.
        """

        self.progress_bar.setRange(0, max_range)
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def set_pixmap(self, image_path: str) -> None:
        """Set the pixmap for the splash screen.

        Args:
            image_path: The path to the image file.
        """

        self.pixmap = self._resize_image(image_path)
        self.setPixmap(self.pixmap)

    def set_icon(self, icon_path: str) -> None:
        """Set the icon for the splash screen.

        Args:
            icon_path: The path to the icon file.
        """

        self.icon = QIcon(icon_path)
        pixmap = QPixmap(icon_path).scaledToHeight(
            self.ICON_HEIGHT, Qt.SmoothTransformation
        )
        self.icon_label.setPixmap(pixmap)

    def set_title(self, title: str) -> None:
        """Set the title for the splash screen.

        Args:
            title: The title string.
        """

        self.title = title
        self.title_label.setText(title)

    def set_information_text(self, information: str) -> None:
        """Set the information text for the splash screen.

        Args:
            information: The information text.
        """

        self.information = information
        self.info_label.setText(information)

    def toggle_progress_bar_visibility(self, show: bool) -> None:
        """Toggle the visibility of the progress bar.

        Args:
            show: Whether to show the progress bar.
        """

        self.show_progress_bar = show
        self.progress_bar.setVisible(show)

    def set_project_label(self, project: str) -> None:
        """Set the project name for the splash screen.

        Args:
            project: The project name.
        """

        self.project = project
        self._update_copyright_label()

    def set_version_label(self, version: str) -> None:
        """Set the version information for the splash screen.

        Args:
            version: The version string.
        """

        self.version = version
        self._update_copyright_label()

    def set_company_label(self, company: str) -> None:
        """Set the company name for the splash screen.

        Args:
            company: The company name.
        """

        self.company = company
        self._update_copyright_label()

    def toggle_fade_in(self, fade_in: bool) -> None:
        """Toggle the fade-in effect for the splash screen.

        Args:
            fade_in: Whether to fade in the splash screen.
        """

        self.fade_in = fade_in

    def set_colors(self, color_a: str, color_b: str) -> None:
        """Set the color scheme for the splash screen.

        Args:
            color_a: The primary color.
            color_b: The secondary color.
        """

        self.color_a = color_a
        self.color_b = color_b
        self.setStyleSheet(
            fxstyle.load_stylesheet(color_a=color_a, color_b=color_b)
        )
        self._apply_overlay_opacity()

    def set_overlay_opacity(self, opacity: float) -> None:
        """Set the opacity of the grey overlay background.

        Args:
            opacity: The opacity value between 0.0 (transparent) and 1.0 (opaque).
        """

        self.overlay_opacity = max(0.0, min(1.0, opacity))
        self._apply_overlay_opacity()

    def _apply_overlay_opacity(self) -> None:
        """Apply the overlay opacity to the frame's background color."""

        alpha = int(self.overlay_opacity * 255)
        # Set the frame background with opacity, and ensure all child QLabel
        # widgets have transparent backgrounds so they don't show through
        self.overlay_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(45, 45, 45, {alpha});
            }}
            QFrame > QLabel {{
                background-color: transparent;
            }}
            """
        )

    def set_corner_radius(self, radius: int) -> None:
        """Set the corner radius for rounded corners.

        Args:
            radius: The corner radius in pixels. Use 0 for sharp corners.
        """

        self.corner_radius = max(0, radius)
        if self.corner_radius > 0:
            self._apply_rounded_mask()
        else:
            self.clearMask()
        self._update_border_overlay()
        self.update()

    def set_border(self, width: int, color: str = "#555555") -> None:
        """Set the border around the splash screen.

        Args:
            width: The border width in pixels. Use 0 for no border.
            color: The border color as a hex string.
        """

        self.border_width = max(0, width)
        self.border_color = color
        self._update_overlay_geometry()
        self._update_border_overlay()
        self.update()

    # Events
    def paintEvent(self, event) -> None:
        """Override to draw the pixmap with rounded corners."""

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Create rounded rectangle path
        path = QPainterPath()
        rect = self.rect()

        if self.corner_radius > 0:
            path.addRoundedRect(
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                self.corner_radius,
                self.corner_radius,
            )
        else:
            path.addRect(rect.x(), rect.y(), rect.width(), rect.height())

        # Clip to rounded rectangle and draw pixmap
        painter.setClipPath(path)
        painter.drawPixmap(rect, self.pixmap)
        painter.end()

    def mousePressEvent(self, _):
        pass

    def showEvent(self, event):
        super().showEvent(event)

        # Apply rounded mask for true window transparency
        if self.corner_radius > 0:
            self._apply_rounded_mask()

        if self.fade_in:
            self._fade_in()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reapply mask when resized
        if self.corner_radius > 0:
            self._apply_rounded_mask()

    def _apply_rounded_mask(self) -> None:
        """Apply a rounded rectangle mask for true window transparency."""

        # Create a bitmap mask with anti-aliased rounded corners
        bitmap = QBitmap(self.size())
        bitmap.fill(Qt.color0)  # Start fully transparent

        painter = QPainter(bitmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(Qt.color1)  # Opaque brush
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            self.rect(),
            self.corner_radius,
            self.corner_radius,
        )
        painter.end()

        self.setMask(bitmap)


class FXStatusBar(QStatusBar):
    """Customized QStatusBar class.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `None`.
        project (str, optional): Project name. Defaults to `None`.
        version (str, optional): Version information. Defaults to `None`.
        company (str, optional): Company name. Defaults to `None`.

    Attributes:
        project (str): The project name.
        version (str): The version string.
        company (str): The company name.
        icon_label (QLabel): The icon label.
        message_label (QLabel): The message label.
        project_label (QLabel): The project label.
        version_label (QLabel): The version label.
        company_label (QLabel): The company label.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
    ):

        super().__init__(parent)

        # Attributes
        self.project = project or "Project"
        self.version = version or "0.0.0"
        self.company = company or "\u00a9 Company"
        self.icon_label = QLabel()
        self.message_label = QLabel()
        self.project_label = QLabel(self.project)
        self.version_label = QLabel(self.version)
        self.company_label = QLabel(self.company)

        self.message_label.setTextFormat(Qt.RichText)

        left_widgets = [
            self.icon_label,
            self.message_label,
        ]

        right_widgets = [
            self.project_label,
            self.version_label,
            self.company_label,
        ]

        for widget in left_widgets:
            self.addWidget(widget)
            widget.setVisible(False)  # Hide if no message is shown

        for widget in right_widgets:
            self.addPermanentWidget(widget)

        self.messageChanged.connect(self._on_status_message_changed)

    def _get_severity_info(
        self, severity_type: int, colors_dict: dict
    ) -> Tuple[str, QPixmap, str, str]:
        """Returns severity information for the given severity type.

        Args:
            severity_type: The severity level (0-5).
            colors_dict: The colors dictionary from fxstyle.

        Returns:
            Tuple of (prefix, icon_pixmap, background_color, border_color).

        Warning:
            This method is intended for internal use only.
        """

        severity_configs = {
            CRITICAL: ("Critical", "cancel", "error"),
            ERROR: ("Error", "error", "error"),
            WARNING: ("Warning", "warning", "warning"),
            SUCCESS: ("Success", "check_circle", "success"),
            INFO: ("Info", "info", "info"),
            DEBUG: ("Debug", "bug_report", "debug"),
        }

        prefix, icon_name, feedback_key = severity_configs.get(
            severity_type, ("Info", "info", "info")
        )
        feedback = colors_dict["feedback"][feedback_key]

        icon_pixmap = fxicons.get_icon(
            icon_name, color=feedback["light"]
        ).pixmap(14, 14)

        return prefix, icon_pixmap, feedback["background"], feedback["dark"]

    def showMessage(
        self,
        message: str,
        severity_type: int = 4,
        duration: float = 2.5,
        time: bool = True,
        logger: Optional[logging.Logger] = None,
        set_color: bool = True,
        pixmap: Optional[QPixmap] = None,
        background_color: Optional[str] = None,
    ):
        """Display a message in the status bar with a specified severity.

        Args:
            message (str): The message to be displayed.
            severity_type (int, optional): The severity level of the message.
                Should be one of `CRITICAL`, `ERROR`, `WARNING`, `SUCCESS`,
                `INFO`, or `DEBUG`. Defaults to `INFO`.
            duration (float, optional): The duration in seconds for which
                the message should be displayed. Defaults to` 2.5`.
            time (bool, optional): Whether to display the current time before
                the message. Defaults to `True`.
            logger (Logger, optional): A logger object to log the message.
                Defaults to `None`.
            set_color (bool): Whether to set the status bar color depending on
                the log verbosity. Defaults to `True`.
            pixmap (QPixmap, optional): A custom pixmap to be displayed in the
                status bar. Defaults to `None`.
            background_color (str, optional): A custom background color for
                the status bar. Defaults to `None`.

        Examples:
            To display a critical error message with a red background
            >>> self.showMessage(
            ...     "Critical error occurred!",
            ...     severity_type=self.CRITICAL,
            ...     duration=5,
            ...     logger=my_logger,
            ... )

        Note:
            You can either use the `FXMainWindow` instance to retrieve the
            verbosity constants, or the `fxwidgets` module.
            Overrides the base class method.
        """

        # Send fake signal to trigger the `messageChanged` event
        super().showMessage(" ", timeout=int(duration * 1000))

        # Show the icon and message label which were hidden at init time
        self.icon_label.setVisible(True)
        self.message_label.setVisible(True)

        colors_dict = fxstyle.load_colors_from_jsonc()
        (
            severity_prefix,
            severity_icon,
            status_bar_color,
            status_bar_border_color,
        ) = self._get_severity_info(severity_type, colors_dict)

        # Use custom pixmap if provided
        if pixmap is not None:
            severity_icon = pixmap

        # Use custom background color if provided
        if background_color is not None:
            status_bar_color = background_color

        # Message
        message_prefix = (
            f"<b>{severity_prefix}</b>: {fxutils.get_formatted_time()} - "
            if time
            else f"{severity_prefix}: "
        )
        notification_message = f"{message_prefix} {message}"
        self.icon_label.setPixmap(severity_icon)
        self.message_label.setText(notification_message)
        # self.clearMessage()

        if set_color:
            self.setStyleSheet(
                f"""QStatusBar {{
                    background: {status_bar_color};
                    border-top: 1px solid {status_bar_border_color};
                }}
                QStatusBar QLabel {{
                    color: white;
                }}"""
            )

        # Link `Logger` object
        if logger is not None:
            log_methods = {
                CRITICAL: logger.critical,
                ERROR: logger.error,
                WARNING: logger.warning,
                SUCCESS: logger.info,
                INFO: logger.info,
                DEBUG: logger.debug,
            }
            log_method = log_methods.get(severity_type, logger.info)
            log_method(message)

    def clearMessage(self):
        """Clears the message from the status bar.

        Note:
            Overrides the base class method.
        """

        self.icon_label.clear()
        self.icon_label.setVisible(False)
        self.message_label.clear()
        self.message_label.setVisible(False)
        super().clearMessage()

    @Slot()
    def _on_status_message_changed(self, args):
        """If there are no arguments, which means the message is being removed,
        then change the status bar background back to black.
        """

        if not args:
            self.clearMessage()
            # Reset to theme-appropriate colors
            theme_colors = fxstyle.get_theme_colors()
            self.setStyleSheet(
                f"""
                QStatusBar {{
                    border: 0px solid transparent;
                    background: {theme_colors['background']};
                    border-top: 1px solid {theme_colors['border']};
                }}
            """
            )


class FXMainWindow(QMainWindow):
    """Customized QMainWindow class.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (str, optional): Path to the window icon image. Defaults to `None`.
        title (str, optional): Title of the window. Defaults to `None`.
        size (Tuple[int, int], optional): Window size as width and height.
            Defaults to `None`.
        documentation (str, optional): URL to the tool's documentation.
            Defaults to `None`.
        version (str, optional): Version label for the window.
            Defaults to `None`.
        company (str, optional): Company name for the window.
            Defaults to `Company`.
        color_a (str, optional):Color to be applied to the window.
            Defaults to `#649eff`.
        color_b (str, optional): Color to be applied to the window.
            Defaults to `#4188ff`.
        ui_file (str, optional): Path to the UI file for loading.
            Defaults to `None`.
        set_stylesheet (bool, optional): Whether to set the default stylesheet.
            Defaults to `True`.

    Attributes:
        _default_icon (str): Path to the default icon image.
        window_icon (QIcon): The window icon.
        window_title (str): The window title.
        window_size (QSize): The window size.
        documentation (str): URL to the tool's documentation.
        project (str): The project name.
        version (str): The version label.
        company (str): The company name.
        color_a (str): The first color to be applied to the window.
        color_b (str): The second color to be applied to the window.
        ui_file (str): Path to the UI file for loading.
        ui (Optional[QWidget]): The loaded UI widget.
        CRITICAL (int): Constant for critical severity level.
        ERROR (int): Constant for error severity level.
        WARNING (int): Constant for warning severity level.
        SUCCESS (int): Constant for success severity level.
        INFO (int): Constant for info severity level.
        about_action (QAction): Action for the "About" menu item.
        check_updates_action (QAction): Action for the "Check for Updates" menu item.
        hide_action (QAction): Action for the "Hide" menu item.
        hide_others_action (QAction): Action for the "Hide Others" menu item.
        close_action (QAction): Action for the "Close" menu item.
        settings_action (QAction): Action for the "Settings" menu item.
        window_on_top_action (QAction): Action for the "Always On Top" menu item.
        minimize_window_action (QAction): Action for the "Minimize" menu item.
        maximize_window_action (QAction): Action for the "Maximize" menu item.
        open_documentation_action (QAction): Action for the "Documentation" menu item.
        home_action (QAction): Action for the "Home" toolbar item.
        previous_action (QAction): Action for the "Previous" toolbar item.
        next_action (QAction): Action for the "Next" toolbar item.
        refresh_action (QAction): Action for the "Refresh" toolbar item.
        menu_bar (QMenuBar): The menu bar of the window.
        main_menu (QMenu): The main menu of the window.
        about_menu (QAction): The "About" menu item.
        check_updates_menu (QAction): The "Check for Updates" menu item.
        close_menu (QAction): The "Close" menu item.
        hide_main_menu (QAction): The "Hide" menu item.
        hide_others_menu (QAction): The "Hide Others" menu item.
        edit_menu (QMenu): The edit menu of the window.
        settings_menu (QAction): The "Settings" menu item.
        window_menu (QMenu): The window menu of the window.
        minimize_menu (QAction): The "Minimize" menu item.
        maximize_menu (QAction): The "Maximize" menu item.
        on_top_menu (QAction): The "Always On Top" menu item.
        help_menu (QMenu): The help menu of the window.
        open_documentation_menu (QAction): The "Documentation" menu item.
        toolbar (QToolBar): The toolbar of the window.
        home_toolbar (QAction): The "Home" toolbar item.
        previous_toolbar (QAction): The "Previous" toolbar item.
        next_toolbar (QAction): The "Next" toolbar item.
        refresh_toolbar (QAction): The "Refresh" toolbar item.
        banner (QLabel): The banner label.
        status_line (QFrame): The status line frame.
        status_bar (FXStatusBar): The status bar of the window.
        about_dialog (QDialog): The "About" dialog.

    Examples:
        Outside a DCC (standalone)
        >>> application = fxgui.FXApplication()
        >>> window = fxwidgets.FXMainWindow(
        ...     icon="path/to/icon.png",
        ...     title="My Custom Window",
        ...     size=(800, 600),
        ...     documentation="https://my_tool_docs.com",
        ...     project="Awesome Project",
        ...     version="v1.0.0",
        ...     company="\u00a9 Super Company",
        ...     version="v1.0.0",
        ...     ui_file="path/to/ui_file.ui",
        ... )
        >>> window.show()
        >>> window.set_statusbar_message("Window initialized", window.INFO)
        >>> sys.exit(app.exec_())

        Inside a DCC (Houdini)
        >>> houdini_window = fxdcc.get_houdini_main_window()
        >>> window = fxwidgets.FXMainWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...   )
        >>> window.show()
        >>> window.set_statusbar_message("Window initialized", window.INFO)

        Inside a DCC (Houdini), hide toolbar, menu bar ans status bar
        >>> houdini_window = fxdcc.get_houdini_main_window()
        >>> window = fxwidgets.FXMainWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...   )
        >>> window.toolbar.hide()
        >>> window.menu_bar.hide()
        >>> window.status_bar.hide()
        >>> window.show()

        Inside a DCC (Houdini), override the `fxgui` stylesheet with the Houdini
        one
        >>> houdini_window = fxdcc.get_houdini_main_window()
        >>> window = fxwidgets.FXMainWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...   )
        >>> window.setStyleSheet(hou.qt.styleSheet())
        >>> window.show()
        >>> window.set_statusbar_message("Window initialized", window.INFO)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        size: Optional[int] = None,
        documentation: Optional[str] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        color_a: Optional[str] = None,
        color_b: Optional[str] = None,
        ui_file: Optional[str] = None,
        set_stylesheet: bool = True,
    ):
        super().__init__(parent)

        # Attributes
        self._default_icon = os.path.join(
            os.path.dirname(__file__),
            "images",
            "fxgui_logo_background_dark.svg",
        )
        self.window_icon: QIcon = icon
        self.window_title: str = title
        self.window_size: QSize = size
        self.documentation: str = documentation
        self.project: str = project or "Project"
        self.version: str = version or "0.0.0"
        self.company: str = company or "\u00a9 Company"
        self.color_a: str = color_a or fxstyle._COLOR_A_DEFAULT
        self.color_b: str = color_b or fxstyle._COLOR_B_DEFAULT
        self.ui_file: str = ui_file
        self.ui = None

        self.CRITICAL: int = CRITICAL
        self.ERROR: int = ERROR
        self.WARNING: int = WARNING
        self.SUCCESS: int = SUCCESS
        self.INFO: int = INFO

        # Methods
        self._create_actions()
        self._create_banner()
        self._create_status_line()
        self._load_ui()
        self.setWindowTitle(self.window_title)
        self._set_window_icon()
        self._set_window_size()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._check_documentation()
        self._add_shadows()

        # Styling
        if set_stylesheet:
            self.setStyleSheet(
                fxstyle.load_stylesheet(
                    color_a=self.color_a, color_b=self.color_b
                )
            )

    # Private methods
    def _load_ui(self) -> None:
        """Loads the UI from the specified UI file and sets it as the central
        widget of the main window.

        Warning:
            This method is intended for internal use only.
        """

        if self.ui_file is not None:
            self.ui = fxutils.load_ui(self, self.ui_file)

            # Add the loaded UI to the main window
            self.setCentralWidget(self.ui)

    def _set_window_icon(self) -> None:
        """Sets the window icon from the specified icon path.

        Warning:
            This method is intended for internal use only.
        """

        icon_path = (
            self.window_icon
            if self.window_icon and os.path.isfile(self.window_icon)
            else self._default_icon
        )
        self.setWindowIcon(QIcon(icon_path))

    def _set_window_size(self) -> None:
        """Sets the window size from the specified size.

        Warning:
            This method is intended for internal use only.
        """

        self.resize(
            QSize(*self.window_size)
            if self.window_size and len(self.window_size) >= 1
            else QSize(500, 600)
        )

    def _create_actions(self) -> None:
        """Creates the actions for the window.

        Warning:
            This method is intended for internal use only.
        """

        # Main menu
        self.about_action = fxutils.create_action(
            self,
            "About",
            fxicons.get_icon("help"),  # About icon
            self._show_about_dialog,
            enable=True,
            visible=True,
        )

        self.check_updates_action = fxutils.create_action(
            self,
            "Check for Updates...",
            fxicons.get_icon("update"),  # Update icon
            None,
            enable=False,
            visible=True,
        )

        self.hide_action = fxutils.create_action(
            self,
            "Hide",
            fxicons.get_icon("visibility_off"),  # Visibility off icon
            self.hide,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+h",
        )

        self.hide_others_action = fxutils.create_action(
            self,
            "Hide Others",
            fxicons.get_icon("disabled_visible"),  # Disabled visible icon
            None,
            enable=False,
            visible=True,
        )

        self.close_action = fxutils.create_action(
            self,
            "Close",
            fxicons.get_icon("close"),  # Close icon
            self.close,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+q",
        )

        # Edit menu
        self.settings_action = fxutils.create_action(
            self,
            "Settings",
            fxicons.get_icon("settings"),  # Settings icon
            None,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+s",
        )

        # Window menu
        self.window_on_top_action = fxutils.create_action(
            self,
            "Always On Top",
            fxicons.get_icon("hdr_strong"),  # Always on top icon
            self._toggle_window_on_top,
            enable=True,
            visible=True,
            shortcut="Ctrl+Shift+t",
        )

        self.minimize_window_action = fxutils.create_action(
            self,
            "Minimize",
            fxicons.get_icon("minimize"),  # Minimize icon
            self.showMinimized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+m",
        )

        self.maximize_window_action = fxutils.create_action(
            self,
            "Maximize",
            fxicons.get_icon("maximize"),  # Maximize icon
            self.showMaximized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+f",
        )

        self.toggle_theme_action = fxutils.create_action(
            self,
            "Toggle Theme",
            fxicons.get_icon("brightness_4"),  # Toggle theme icon
            self._toggle_theme,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+t",
        )

        # Help menu
        self.open_documentation_action = fxutils.create_action(
            self,
            "Documentation",
            fxicons.get_icon("menu_book"),  # Documentation icon
            lambda: open_new_tab(self.documentation),
            enable=True,
            visible=True,
        )

        # Toolbar
        self.home_action = fxutils.create_action(
            self,
            "Home",
            fxicons.get_icon("home"),  # Home icon
            None,
            enable=False,
            visible=True,
        )

        self.previous_action = fxutils.create_action(
            self,
            "Previous",
            fxicons.get_icon("arrow_back"),  # Previous icon
            None,
            enable=False,
            visible=True,
        )

        self.next_action = fxutils.create_action(
            self,
            "Next",
            fxicons.get_icon("arrow_forward"),  # Next icon
            None,
            enable=False,
            visible=True,
        )

        self.refresh_action = fxutils.create_action(
            self,
            "Refresh",
            fxicons.get_icon("refresh"),  # Refresh icon
            None,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+r",
        )

    def _create_menu_bar(
        self,
        native_menu_bar: bool = False,
    ) -> None:
        """Creates the menu bar for the window.

        Args:
            native_menu_bar: Whether to use the native menu bar.
                Defaults to `False`.
            enable_logo_menu_bar: Whether to enable the logo menu bar.
                Defaults to `True`.

        Warning:
            This method is intended for internal use only.
        """

        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(native_menu_bar)  # Mostly for macOS

        # Main menu
        self.main_menu = self.menu_bar.addMenu("File")
        self.about_menu = self.main_menu.addAction(self.about_action)
        self.main_menu.addSeparator()
        self.check_updates_menu = self.main_menu.addAction(
            self.check_updates_action
        )
        self.main_menu.addSeparator()
        self.hide_main_menu = self.main_menu.addAction(self.hide_action)
        self.hide_others_menu = self.main_menu.addAction(
            self.hide_others_action
        )
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)

        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("Edit")
        self.settings_menu = self.edit_menu.addAction(self.settings_action)

        # Window menu
        self.window_menu = self.menu_bar.addMenu("Window")
        self.minimize_menu = self.window_menu.addAction(
            self.minimize_window_action
        )
        self.maximize_menu = self.window_menu.addAction(
            self.maximize_window_action
        )
        self.window_menu.addSeparator()
        self.on_top_menu = self.window_menu.addAction(self.window_on_top_action)
        self.window_menu.addSeparator()
        self.toggle_theme_menu = self.window_menu.addAction(
            self.toggle_theme_action
        )

        # Help menu
        self.help_menu = self.menu_bar.addMenu("Help")
        self.open_documentation_menu = self.help_menu.addAction(
            self.open_documentation_action
        )

    def _create_toolbars(self) -> None:
        """Creates the toolbar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setIconSize(QSize(17, 17))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.home_toolbar = self.toolbar.addAction(self.home_action)
        self.previous_toolbar = self.toolbar.addAction(self.previous_action)
        self.next_toolbar = self.toolbar.addAction(self.next_action)
        self.refresh_toolbar = self.toolbar.addAction(self.refresh_action)
        self.toolbar.setMovable(True)

    def _generate_label(self, attribute: str, default: str) -> QLabel:
        """Generates a label for the status bar.

        Args:
            attribute (str): The attribute to be displayed.
            default (str): The default value to be displayed if the attribute
                is not set.

        Warning:
            This method is intended for internal use only.
        """

        return QLabel(attribute if attribute else default)

    def _create_banner(self) -> None:
        """Creates a banner with the window title for the window.

        Note:
            This method is intended for internal use only.
        """

        theme_colors = fxstyle.get_theme_colors()
        self.banner = QLabel("Banner", self)
        self.banner.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.banner.setStyleSheet(
            f"color: {theme_colors['text']}; font-size: 16px; padding: 10px; "
            f"border-bottom: 1px solid {theme_colors['border']};"
        )
        self.banner.setFixedHeight(50)

        central_widget = self.centralWidget()
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.banner)

        if central_widget is not None:
            layout.addWidget(central_widget)
        else:
            central_widget = QWidget()
            layout.addWidget(central_widget)

        self.setCentralWidget(widget)

    def _create_status_line(
        self,
        color_a: str = fxstyle._COLOR_A_DEFAULT,
        color_b: str = fxstyle._COLOR_A_DEFAULT,
    ) -> None:
        """Creates a custom status line for the window.

        Args:
            color_a: The first color of the gradient. Defaults to `#cc00cc`.
            color_b: The second color of the gradient. Defaults to `#4ab5cc`.

        Note:
            This method is intended for internal use only.
        """

        self.status_line = QFrame(self)
        self.status_line.setFrameShape(QFrame.HLine)
        self.status_line.setFrameShadow(QFrame.Sunken)
        self.status_line.setFixedHeight(3)
        self.status_line.setSizePolicy(
            QSizePolicy.Expanding,
            self.status_line.sizePolicy().verticalPolicy(),
        )
        self.set_status_line_colors(color_a, color_b)

        central_widget = self.centralWidget()
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        if central_widget is not None:
            layout.addWidget(central_widget)
        else:
            central_widget = QWidget()
            layout.addWidget(central_widget)

        layout.addWidget(self.status_line)
        self.setCentralWidget(widget)

    def _create_status_bar(self) -> None:
        """Creates the status bar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.status_bar = FXStatusBar(
            parent=self,
            project=self.project,
            version=self.version,
            company=self.company,
        )
        self.setStatusBar(self.status_bar)

    def _show_about_dialog(self) -> None:
        """Shows the "About" dialog.

        Warning:
            This method is intended for internal use only.
        """

        # ! Repetition from `_create_status_bar` is necessary to create new
        # ! objects
        # If the dialog already exists and is open, close it
        if hasattr(self, "about_dialog") and self.about_dialog is not None:
            self.about_dialog.close()

        # Create a new dialog with self (window) as the parent
        self.about_dialog = QDialog(self)
        self.about_dialog.setWindowTitle("About")

        project_label = self._generate_label(self.project, "Project")
        project_label.setAlignment(Qt.AlignCenter)
        version_label = self._generate_label(self.version, "0.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        company_label = self._generate_label(self.company, "\u00a9 Company")
        company_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(project_label)
        layout.addWidget(version_label)
        layout.addWidget(company_label)
        layout.addStretch()

        self.about_dialog.setFixedSize(200, 150)
        self.about_dialog.setLayout(layout)
        self.about_dialog.exec_()

    def _toggle_window_on_top(self) -> None:
        """Sets the window on top of all other windows or not.

        Warning:
            This method is intended for internal use only.
        """

        flags = self.windowFlags()
        stays_on_top = bool(flags & Qt.WindowStaysOnTopHint)
        flags ^= Qt.WindowStaysOnTopHint

        if stays_on_top:
            self.window_on_top_action.setText("Always on Top")
            self.window_on_top_action.setIcon(fxicons.get_icon("hdr_strong"))
        else:
            self.window_on_top_action.setText("Regular Position")
            self.window_on_top_action.setIcon(fxicons.get_icon("hdr_weak"))

        self.setWindowFlags(flags)
        self.show()

    def _move_window(self) -> None:
        """Moves the window to the selected area of the screen.

        Warning:
            This method is intended for internal use only.
        """

        frame_geo = self.frameGeometry()

        if QT_VERSION_MAJOR >= 6:
            screen: QScreen = QApplication.primaryScreen()
            desktop_geometry = screen.availableGeometry()
        else:
            desktop_geometry: QRect = QDesktopWidget().availableGeometry()

        center_point = desktop_geometry.center()
        left_top_point = QPoint(desktop_geometry.left(), desktop_geometry.top())
        right_top_point = QPoint(
            desktop_geometry.right(), desktop_geometry.top()
        )
        left_bottom_point = QPoint(
            desktop_geometry.left(), desktop_geometry.bottom()
        )
        right_bottom_point = QPoint(
            desktop_geometry.right(), desktop_geometry.bottom()
        )

        moving_position = {
            1: center_point,
            2: left_top_point,
            3: right_top_point,
            4: left_bottom_point,
            5: right_bottom_point,
        }.get(3, center_point)

        moving_position.setX(moving_position.x() + 0)
        moving_position.setY(moving_position.y() + 0)
        frame_geo.moveCenter(moving_position)
        self.move(frame_geo.topLeft())

    def _is_valid_url(self, url: str) -> bool:
        """Checks if the specified URL is valid.

        Args:
            url (str): The URL to check.

        Warning:
            This method is intended for internal use only.
        """

        if not url:
            return False
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except (ValueError, AttributeError):
            return False

    def _check_documentation(self):
        """Checks if the documentation URL is valid and enables/disables the
        action accordingly.

        Warning:
            This method is intended for internal use only.
        """

        self.open_documentation_action.setEnabled(
            self._is_valid_url(self.documentation)
        )

    def _add_shadows(
        self,
        menu_bar: bool = False,
        toolbar: bool = False,
        status_bar: bool = False,
    ) -> None:
        """Adds shadows to the window elements.

        Args:
            menu_bar (bool, optional): Whether to add shadows to the menu bar.
                Defaults to `False`.
            toolbar (bool, optional): Whether to add shadows to the toolbar.
                Defaults to `False`.
            status_bar (bool, optional): Whether to add shadows to the status bar.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        if menu_bar:
            fxutils.add_shadows(self, self.menu_bar)
        if toolbar:
            fxutils.add_shadows(self, self.toolbar)
        if status_bar:
            fxutils.add_shadows(self, self.statusBar())

    def _toggle_theme(self) -> None:
        """Toggles the theme of the window between light and dark.

        Warning:
            This method is intended for internal use only.
        """

        # Use centralized theme toggling
        new_theme = fxstyle.toggle_theme(
            self, color_a=self.color_a, color_b=self.color_b
        )

        # Get the theme colors for the new theme
        theme_colors = fxstyle.get_theme_colors()

        # Update banner for the new theme
        self.banner.setStyleSheet(
            f"color: {theme_colors['text']}; font-size: 16px; padding: 10px; "
            f"border-bottom: 1px solid {theme_colors['border']};"
        )

        # Update status bar colors for the new theme
        self.status_bar.setStyleSheet(
            f"""QStatusBar {{
                background: {theme_colors['background']};
                border-top: 1px solid {theme_colors['border']};
            }}"""
        )

        # Update all action icons for the new theme
        self._refresh_action_icons()

    def _refresh_action_icons(self) -> None:
        """Refresh all action icons after a theme change.

        Warning:
            This method is intended for internal use only.
        """

        # Map of actions to their icon names
        action_icon_map = {
            self.about_action: "help",
            self.check_updates_action: "update",
            self.hide_action: "visibility_off",
            self.hide_others_action: "disabled_visible",
            self.close_action: "close",
            self.settings_action: "settings",
            self.window_on_top_action: "hdr_strong",
            self.minimize_window_action: "minimize",
            self.maximize_window_action: "maximize",
            self.toggle_theme_action: "brightness_4",
            self.open_documentation_action: "menu_book",
            self.home_action: "home",
            self.previous_action: "arrow_back",
            self.next_action: "arrow_forward",
            self.refresh_action: "refresh",
        }

        for action, icon_name in action_icon_map.items():
            action.setIcon(fxicons.get_icon(icon_name))

        # Also refresh QDialogButtonBox icons throughout the window
        self._refresh_dialog_button_icons()

    def _refresh_dialog_button_icons(self) -> None:
        """Refresh all QDialogButtonBox button icons after a theme change.

        Warning:
            This method is intended for internal use only.
        """

        from qtpy.QtWidgets import QDialogButtonBox, QPushButton

        # Map of standard button roles to their icon names
        button_icon_map = {
            QDialogButtonBox.Ok: "check",
            QDialogButtonBox.Cancel: "cancel",
            QDialogButtonBox.Close: "close",
            QDialogButtonBox.Save: "save",
            QDialogButtonBox.SaveAll: "save_all",
            QDialogButtonBox.Open: "open_in_new",
            QDialogButtonBox.Yes: "check",
            QDialogButtonBox.YesToAll: "done_all",
            QDialogButtonBox.No: "cancel",
            QDialogButtonBox.NoToAll: "do_not_disturb",
            QDialogButtonBox.Abort: "cancel",
            QDialogButtonBox.Retry: "restart_alt",
            QDialogButtonBox.Ignore: "notifications_off",
            QDialogButtonBox.Discard: "delete",
            QDialogButtonBox.Help: "help",
            QDialogButtonBox.Apply: "check",
            QDialogButtonBox.Reset: "cleaning_services",
            QDialogButtonBox.RestoreDefaults: "settings_backup_restore",
        }

        # Find all QDialogButtonBox widgets in the window
        for button_box in self.findChildren(QDialogButtonBox):
            for role, icon_name in button_icon_map.items():
                button = button_box.button(role)
                if button is not None:
                    button.setIcon(fxicons.get_icon(icon_name))

        # Also refresh icons in custom widgets that support it
        self._refresh_custom_widget_icons()

    def _refresh_custom_widget_icons(self) -> None:
        """Refresh icons on all child widgets that have an 'icon_name' property.

        This method uses Qt's property system to find widgets with icons.
        Any widget (QPushButton, QToolButton, etc.) with a dynamic property
        'icon_name' will have its icon refreshed from the cache.

        To make a button's icon theme-aware, simply set the property:
            button.setProperty("icon_name", "save")
            button.setIcon(fxicons.get_icon("save"))

        Warning:
            This method is intended for internal use only.
        """

        from qtpy.QtWidgets import QAbstractButton, QToolButton

        # Find all button-like widgets with an icon_name property
        for widget in self.findChildren(QAbstractButton):
            icon_name = widget.property("icon_name")
            if icon_name:
                widget.setIcon(fxicons.get_icon(icon_name))

        # Also check QToolButtons specifically (for QToolButton in toolbars)
        for widget in self.findChildren(QToolButton):
            icon_name = widget.property("icon_name")
            if icon_name:
                widget.setIcon(fxicons.get_icon(icon_name))

    # Public methods
    def toggle_theme(self) -> str:
        """Toggle the theme of the window between light and dark.

        This method can be called from external code to switch themes,
        including when running inside a DCC like Houdini, Maya, or Nuke
        where you don't have direct access to QApplication.

        Returns:
            str: The new theme that was applied ("dark" or "light").

        Examples:
            >>> window = FXMainWindow()
            >>> window.show()
            >>> new_theme = window.toggle_theme()
            >>> print(f"Switched to {new_theme} theme")
        """

        self._toggle_theme()
        return fxstyle._theme

    # Overrides
    def statusBar(self) -> FXStatusBar:
        """Returns the FXStatusBar instance associated with this window.

        Returns:
            FXStatusBar: The FXStatusBar instance associated with this window.

        Note:
            Overrides the base class method.
        """

        return self.status_bar

    def setCentralWidget(self, widget):
        """Overrides the QMainWindow's setCentralWidget method to ensure that the
        status line is always at the bottom of the window and the banner is always at the top.

        Args:
            widget (QWidget): The widget to set as the central widget.

        Note:
            Overrides the base class method.
        """

        # Create a new QWidget to hold the banner, widget, and the status line
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add the banner first (top)
        if hasattr(self, "banner") and self.banner is not None:
            layout.addWidget(self.banner)

        # Add the widget to the new layout
        layout.addWidget(widget)

        # Add the status line last (bottom)
        if hasattr(self, "status_line") and self.status_line is not None:
            layout.addWidget(self.status_line)

        # Call the parent's setCentralWidget method with the new central widget
        super().setCentralWidget(central_widget)

    def setWindowTitle(self, title: str) -> None:
        """Override the `setWindowTitle` method to use `_set_window_title`.

        Args:
            title (str): The new window title.
        """

        title = f"{title if title else 'Window'}"
        super().setWindowTitle(title)

    # Public methods
    def set_colors(self, color_a: str, color_b: str) -> None:
        """Sets the accent color of the window.

        Args:
            color_a (str): The first color.
            color_b (str): The second color.
        """

        self.color_a = color_a
        self.color_b = color_b
        self.setStyleSheet(
            fxstyle.load_stylesheet(color_a=color_a, color_b=color_b)
        )

    def set_banner_text(self, text: str) -> None:
        """Sets the text of the banner.

        Args:
            text (str): The text to set in the banner.
        """

        self.banner.setText(text)

    def hide_banner(self) -> None:
        """Hides the banner."""

        self.banner.hide()

    def show_banner(self) -> None:
        """Shows the banner."""

        self.banner.show()

    def set_status_line_colors(self, color_a: str, color_b: str) -> None:
        """Set the colors of the status line.

        Args:
            color_a (str): The first color of the gradient.
            color_b (str): The second color of the gradient.
        """

        self.status_line.setStyleSheet(
            f"""
            QFrame {{
                background-color: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0, stop:0 {color_a}, stop:1 {color_b});
                border: 0px solid transparent;
                border-radius: 0px;
            }}
        """
        )

    def hide_status_line(self) -> None:
        """Hides the status line."""

        self.status_line.hide()

    def show_status_line(self) -> None:
        """Shows the status line."""

        self.status_line.show()

    def set_ui_file(self, ui_file: str) -> None:
        """Sets the UI file and loads the UI."""

        self.ui_file = ui_file
        self._load_ui()

    def set_project_label(self, project: str) -> None:
        """Sets the project label in the status bar.

        Args:
            project (str): The project name.

        Note:
            Overrides the base class method.
        """

        self.statusBar().project_label.setText(project)

    def set_company_label(self, company: str) -> None:
        """Sets the company label in the status bar.

        Args:
            company (str): The company name.

        Note:
            Overrides the base class method.
        """

        self.statusBar().company_label.setText(company)

    def set_version_label(self, version: str) -> None:
        """Sets the version label in the status bar.

        Args:
            version (str): The version string.

        Note:
            Overrides the base class method.
        """

        self.statusBar().version_label.setText(version)

    # Events
    def closeEvent(self, _) -> None:
        self.setParent(None)


class FXWidget(QWidget):
    def __init__(
        self,
        parent=None,
        ui_file: Optional[str] = None,
    ):
        super().__init__(parent)

        # Attributes
        self.ui_file: str = ui_file
        self.ui = None

        # Methods
        self._load_ui()
        self._set_layout()

        # Styling
        self.setStyleSheet(fxstyle.load_stylesheet())

    # Private methods
    def _load_ui(self) -> None:
        """Loads the UI from the specified UI file and sets it as the central
        widget of the main window.

        Warning:
            This method is intended for internal use only.
        """

        if self.ui_file is not None:
            self.ui = fxutils.load_ui(self, self.ui_file)

    def _set_layout(self) -> None:
        """Sets the layout of the widget.

        Warning:
            This method is intended for internal use only.
        """

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(9, 9, 9, 9)
        if self.ui:
            self.layout.addWidget(self.ui)


class FXFloatingDialog(QDialog):
    """A floating dialog that appears at the cursor's position.
    It closes when any mouse button except the right one is pressed.

    Args:
        parent (QtWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (QPixmap): The QPixmap icon.
        title (str): The dialog title.

    Attributes:
        dialog_icon (QIcon): The icon of the dialog.
        dialog_title (str): The title of the dialog.
        drop_position (QPoint): The drop position of the dialog.
        dialog_position (Tuple[int, int]): The position of the dialog.
        parent_package (int): Whether the dialog is standalone application, or belongs to a DCC parent.
        popup (bool): Whether the dialog is a popup or not.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[QPixmap] = None,
        title: Optional[str] = None,
        parent_package: Optional[int] = None,
        popup: bool = False,
    ):
        super().__init__(parent)

        # Attributes
        theme_colors = fxstyle.get_theme_colors()
        _icon = fxicons.get_icon("home", color=theme_colors["icon"]).pixmap(
            32, 32
        )
        self._default_icon = _icon
        self.dialog_icon: QIcon = icon
        self.dialog_title: str = title

        self.drop_position = QCursor.pos()
        self.dialog_position = (
            self.drop_position.x() - (self.width() / 2),
            self.drop_position.y() - (self.height() / 2),
        )

        self.parent_package = parent_package

        # Methods
        self._setup_title()
        self._setup_main_widget()
        self._setup_buttons()
        self._setup_layout()
        self._handle_connections()
        self.set_dialog_icon(self.dialog_icon)
        self.set_dialog_title(self.dialog_title)

        # Window
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(200, 40)

        if popup:
            self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        if (
            self.parent_package == fxdcc.STANDALONE
            or self.parent_package == None
        ):
            pass

        elif self.parent_package == fxdcc.HOUDINI:
            # Custom stylesheet for Houdini (use theme colors)
            theme_colors = fxstyle.get_theme_colors()
            self.title_widget.setStyleSheet(
                f"background-color: {theme_colors['background_alt']};"
            )
            self.setStyleSheet(
                f"""
                FXFloatingDialog {{
                    border-top: 1px solid {theme_colors['border_light']};
                    border-left: 1px solid {theme_colors['border_light']};
                    border-bottom: 1px solid {theme_colors['background']};
                    border-right: 1px solid {theme_colors['background']};
                }}
            """
            )

        elif self.parent_package == fxdcc.MAYA:
            pass

        elif self.parent_package == fxdcc.NUKE:
            pass

        else:
            pass

    # Private methods
    def _setup_title(self):
        """Sets up the title bar with icon and label.

        Warning:
            This method is intended for internal use only.
        """

        self._icon_label = QLabel(self)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title_widget = QWidget(self)

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignLeft)
        self.title_label.setFont(font)

        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setSpacing(10)
        self.title_layout.addWidget(self._icon_label)
        self.title_layout.addWidget(self.title_label)

    def _setup_main_widget(self):
        """Sets up the main content widget and layout.

        Warning:
            This method is intended for internal use only.
        """

        self.main_widget = QWidget(self)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

    def _setup_buttons(self):
        """Sets up the dialog button box with close button.

        Warning:
            This method is intended for internal use only.
        """

        self.button_box = QDialogButtonBox(self)
        self.button_box.setContentsMargins(10, 10, 10, 10)
        self.button_close = self.button_box.addButton(QDialogButtonBox.Close)

    def _setup_layout(self):
        """Sets up the main dialog layout with title, content, and buttons.

        Warning:
            This method is intended for internal use only.
        """

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.addWidget(self.title_widget)
        self.layout.addWidget(self.main_widget)
        self.layout.addWidget(self.button_box)

    def _handle_connections(self) -> None:
        """Connects the dialog's slots."""

        self.button_box.rejected.connect(self.reject)
        self.button_box.rejected.connect(self.close)  # TODO: Check if needed

    # Public methods
    def set_dialog_icon(self, icon: Optional[QPixmap] = None) -> None:
        """Sets the dialog's icon.

        Args:
            icon (QPixmap, optional): The QPixmap icon.
        """

        icon = icon if icon else self._default_icon
        self._icon_label.setPixmap(
            icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.dialog_icon = icon

    def set_dialog_title(self, title: str = None) -> None:
        """Sets the dialog's title.

        Args:
            title (str): The title of the dialog.
        """

        self.title_label.setText(title if title else "Floating Dialog")

    def show_under_cursor(self) -> int:
        """Moves the dialog to the current cursor position and displays it.

        Returns:
            int: The result of the `QDialog exec_()` method, which is an integer.
                It returns a `DialogCode` that can be `Accepted` or `Rejected`.
        """

        self.move(*self.dialog_position)
        return self.exec_()

    # Events
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Closes the dialog when any mouse button except the right one is pressed.

        Args:
            event (QMouseEvent): The mouse press event.
        """

        if event.button() != Qt.RightButton:
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Removes the parent of the dialog and closes it.

        Args:
            event (QCloseEvent): The close event.
        """

        self.setParent(None)


class FXPasswordLineEdit(QWidget):
    """
    A custom widget that includes a password line edit with a show/hide button.

    Args:
        parent: The parent widget.
        icon_position: The position of the icon ('left' or 'right').
    """

    def __init__(
        self, parent: Optional[QWidget] = None, icon_position: str = "left"
    ):
        super().__init__(parent)
        self.line_edit = FXIconLineEdit(icon_position=icon_position)
        self.line_edit.setEchoMode(QLineEdit.Password)

        # Show/hide button
        self.reveal_button = self.line_edit.icon_button
        self.reveal_button.setIcon(fxicons.get_icon("visibility"))
        self.reveal_button.setProperty("icon_name", "visibility")
        self.reveal_button.setCursor(Qt.PointingHandCursor)
        self.reveal_button.clicked.connect(self.toggle_reveal)

        # Layout for lineEdit and button
        layout = QHBoxLayout()
        layout.addWidget(self.line_edit)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @Slot()
    def toggle_reveal(self):
        """Toggles the echo mode between password and normal, and changes the
        icon of the reveal button accordingly.
        """

        if self.line_edit.echoMode() == QLineEdit.Password:
            self.line_edit.setEchoMode(QLineEdit.Normal)
            self.reveal_button.setIcon(fxicons.get_icon("disabled_visible"))
            self.reveal_button.setProperty("icon_name", "disabled_visible")
        else:
            self.line_edit.setEchoMode(QLineEdit.Password)
            self.reveal_button.setIcon(fxicons.get_icon("visibility"))
            self.reveal_button.setProperty("icon_name", "visibility")


class FXIconButton(QPushButton):
    """A QPushButton that stores its icon name for theme-aware refresh.

    This button automatically updates its icon when the application theme
    changes, as long as it's a child of an FXMainWindow.

    Args:
        text: The button text.
        icon_name: The name of the icon (from fxicons).
        parent: The parent widget.

    Examples:
        >>> btn = FXIconButton("Save", icon_name="save")
        >>> btn.clicked.connect(save_action)
    """

    def __init__(
        self,
        text: str = "",
        icon_name: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(text, parent)
        if icon_name is not None:
            self.setIcon(fxicons.get_icon(icon_name))
            self.setProperty("icon_name", icon_name)

    def set_icon_name(self, icon_name: str) -> None:
        """Set the icon by name.

        Args:
            icon_name: The name of the icon to display.
        """
        self.setIcon(fxicons.get_icon(icon_name))
        self.setProperty("icon_name", icon_name)


class FXIconLineEdit(QLineEdit):
    """A line edit that displays an icon on the left or right side.

    The icon is theme-aware and will refresh automatically when the
    application theme changes.

    Args:
            icon_name: The name of the icon to display.
            icon_position: The position of the icon ('left' or 'right').
            parent: The parent widget.
    """

    def __init__(
        self,
        icon_name: Optional[str] = None,
        icon_position: str = "left",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # Create a `QPushButton` to hold the icon
        self.icon_button = QPushButton(self)
        self.icon_button.setFlat(True)
        self.icon_button.setStyleSheet(
            "background-color: transparent; border: none;"
        )
        self.icon_button.setFixedSize(18, 18)

        # Set icon using property-based approach
        if icon_name is not None:
            self.icon_button.setIcon(fxicons.get_icon(icon_name))
            self.icon_button.setProperty("icon_name", icon_name)

        # Create a layout to hold the icon and the line edit
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if icon_position == "left":
            self.layout.addWidget(self.icon_button)
            self.layout.addStretch()
            self.setTextMargins(22, 0, 0, 0)
        elif icon_position == "right":
            self.layout.addStretch()
            self.layout.addWidget(self.icon_button)
            self.setTextMargins(0, 0, 22, 0)
        else:
            raise ValueError("icon_position must be 'left' or 'right'")

        self.setLayout(self.layout)

    def resizeEvent(self, event):
        """Reposition the icon when the line edit is resized."""

        super().resizeEvent(event)
        if self.layout.itemAt(0).widget() == self.icon_button:
            self.icon_button.move(
                5, (self.height() - self.icon_button.height()) // 2
            )
        else:
            self.icon_button.move(
                self.width() - self.icon_button.width() - 5,
                (self.height() - self.icon_button.height()) // 2,
            )


class FXSystemTray(QObject):
    """A system tray icon with a context menu.

    Args:
        parent (QWidget, optional): The parent widget. Defaults to None.
        icon (str, optional): The icon path. Defaults to None.

    Attributes:
        tray_icon (QSystemTrayIcon): The system tray icon.
        quit_action (QAction): The action to quit the application.
        tray_menu (QMenu): The tray menu.

    Methods:
        show: Shows the system tray icon.
        on_tray_icon_activated: Shows the tray menu above the taskbar.
        closeEvent: Closes the application.

    Examples:
        >>> app = FXApplication()
        >>> system_tray = FXSystemTray()
        >>> hello_action = QAction(
        ...     fxicons.get_icon("visibility"), "Set Project", system_tray
        ... )
        >>> system_tray.tray_menu.insertAction(
        ...     system_tray.quit_action, hello_action
        ... )
        >>> system_tray.tray_menu.insertSeparator(system_tray.quit_action)
        >>> system_tray.show()
        >>> app.exec_()

    Note:
        Inherits from QObject, not QSystemTrayIcon.
    """

    def __init__(self, parent=None, icon=None):
        super().__init__(parent)

        self.icon = (
            icon
            or (
                Path(__file__).parent / "images" / "fxgui_logo_light.svg"
            ).as_posix()
        )
        self.tray_icon = QSystemTrayIcon(QIcon(self.icon), parent)

        # Methods
        self._create_actions()
        self._create_menu()
        self._handle_connections()

    # Private methods
    def _create_actions(self) -> None:
        """Creates the actions for the window.

        Warning:
            This method is intended for internal use only.
        """

        # Main menu
        self.quit_action = fxutils.create_action(
            self,
            "Quit",
            fxicons.get_icon("close"),
            self.closeEvent,
            enable=True,
            visible=True,
        )

    def _create_menu(self) -> None:
        self.tray_menu = QMenu(self.parent())
        self.tray_menu.addAction(self.quit_action)

        # Styling
        self.tray_menu.setStyleSheet(fxstyle.load_stylesheet())

    @Slot()
    def _handle_connections(self) -> None:
        # Right-click
        # self.tray_icon.setContextMenu(self.tray_menu)

        # Left-click
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

    @Slot()
    def _on_tray_icon_activated(self, reason):
        """Shows the tray menu at the cursor's position.

        Args:
            reason (QSystemTrayIcon.ActivationReason): The reason for the tray
                icon activation.
        """

        if reason == QSystemTrayIcon.Trigger:
            # Calculate taskbar position
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()
            available_geometry = screen.availableGeometry()
            tray_icon_geometry = self.tray_icon.geometry()

            # Calculate the center position of the tray icon
            tray_icon_center = tray_icon_geometry.center()

            menu_width = self.tray_menu.sizeHint().width()
            menu_height = self.tray_menu.sizeHint().height()

            margin = 20  # Margin between the taskbar and the system tray menu

            if available_geometry.y() > screen_geometry.y():
                # Taskbar is on the top
                pos = QPoint(
                    tray_icon_center.x() - menu_width / 2,
                    tray_icon_geometry.bottom() + margin,
                )
            elif available_geometry.x() > screen_geometry.x():
                # Taskbar is on the left
                pos = QPoint(
                    tray_icon_geometry.right() + margin,
                    tray_icon_center.y() - menu_height / 2,
                )
            elif available_geometry.height() < screen_geometry.height():
                # Taskbar is on the bottom
                pos = QPoint(
                    tray_icon_center.x() - menu_width / 2,
                    tray_icon_geometry.top() - menu_height - margin,
                )
            else:
                # Taskbar is on the right or default position
                pos = QPoint(
                    tray_icon_geometry.left() - menu_width - margin,
                    tray_icon_center.y() - menu_height / 2,
                )

            # Ensure the menu is completely visible
            if pos.x() < available_geometry.x():
                pos.setX(available_geometry.x())
            if pos.y() < available_geometry.y():
                pos.setY(available_geometry.y())
            if pos.x() + menu_width > available_geometry.right():
                pos.setX(available_geometry.right() - menu_width)
            if pos.y() + menu_height > available_geometry.bottom():
                pos.setY(available_geometry.bottom() - menu_height)

            self.tray_menu.exec_(pos)

    # Public methods
    def add_action(self, action: QAction) -> None:
        """Adds an action to the tray menu.

        Args:
            action: The action to add to the tray menu.
        """

        self.tray_menu.addAction(action)

    def set_icon(self, icon_path: str) -> None:
        """Sets a new icon for the system tray.

        Args:
            icon_path: The path to the new icon.
        """

        self.icon = icon_path
        self.tray_icon.setIcon(QIcon(self.icon))

    def show(self):
        """Shows the system tray icon."""

        self.tray_icon.show()

    # Events
    def closeEvent(self, _) -> None:
        FXApplication.instance().quit()
        QApplication.instance().quit()
        self.setParent(None)


if __name__ == "__main__":
    _application = FXApplication()
    window = FXMainWindow()
    window.show()
    _application.exec_()
