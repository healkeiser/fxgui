"""Toast/banner notification widget."""

# Built-in
import logging
import os
from typing import Optional
from weakref import WeakKeyDictionary

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from qtpy.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qtpy.QtGui import QColor

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._constants import (
    CRITICAL,
    ERROR,
    WARNING,
    SUCCESS,
    INFO,
    DEBUG,
)


class FXNotificationBanner(fxstyle.FXThemeAware, QFrame):
    """Animated pop-up notification cards that slide in from the right.

    This widget provides toast-style notifications with severity levels,
    auto-dismiss, and optional action buttons. Notifications automatically
    stack when multiple are shown and reposition when one is dismissed.

    Args:
        parent: Parent widget (required for positioning).
        message: The notification message.
        severity_type: Severity level (CRITICAL, ERROR, WARNING, SUCCESS, INFO, DEBUG).
            If None, a custom notification is shown using title and icon.
        timeout: Auto-dismiss timeout in milliseconds (0 = no auto-dismiss).
        action_text: Text for the optional action button.
        closable: Whether to show a close button.
        width: Fixed width of the notification card (default 320).
        logger: A logger object to log the message when shown. The severity
            level is mapped to the appropriate logging level.
        title: Custom title for the notification. Overrides severity-based title.
        icon: Custom icon name for the notification. Overrides severity-based icon.
        margin: Margin from the edges of the parent widget (default 16).
        spacing: Spacing between stacked notifications (default 8).

    Signals:
        closed: Emitted when the banner is closed.
        action_clicked: Emitted when the action button is clicked.

    Examples:
        >>> # Simple notification - auto-positions and stacks
        >>> banner = FXNotificationBanner(
        ...     parent=window,
        ...     message="File saved successfully!",
        ...     severity_type=SUCCESS,
        ... )
        >>> banner.show()
        >>>
        >>> # Custom notification
        >>> banner = FXNotificationBanner(
        ...     parent=window,
        ...     message="New version available!",
        ...     title="Update",
        ...     icon="system_update",
        ... )
        >>> banner.show()
    """

    closed = Signal()
    action_clicked = Signal()

    # Class-level tracking of active notifications per parent widget
    # Uses WeakKeyDictionary so entries are auto-removed when parent is deleted
    _active_notifications: WeakKeyDictionary = WeakKeyDictionary()

    # Severity icons mapping
    SEVERITY_ICONS = {
        CRITICAL: "cancel",
        ERROR: "error",
        WARNING: "warning",
        SUCCESS: "check_circle",
        INFO: "info",
        DEBUG: "bug_report",
    }

    # Severity titles mapping
    SEVERITY_TITLES = {
        CRITICAL: "Critical",
        ERROR: "Error",
        WARNING: "Warning",
        SUCCESS: "Success",
        INFO: "Info",
        DEBUG: "Debug",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "",
        severity_type: Optional[int] = None,
        timeout: int = 5000,
        action_text: Optional[str] = None,
        closable: bool = True,
        width: int = 320,
        logger: Optional[logging.Logger] = None,
        title: Optional[str] = None,
        icon: Optional[str] = None,
        margin: int = 16,
        spacing: int = 8,
    ):
        super().__init__(parent)

        self._message = message
        self._severity_type = severity_type
        self._timeout = timeout
        self._action_text = action_text
        self._closable = closable
        self._notification_width = width
        self._logger = logger
        self._custom_title = title
        self._custom_icon = icon
        self._margin = margin
        self._spacing = spacing

        # Fixed width for pop notification style
        self.setFixedWidth(width)

        # Setup frame styling
        self.setFrameShape(QFrame.StyledPanel)

        # Main layout (vertical like FXProgressCard)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

        # Header row (icon + title + close button)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Severity icon
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setStyleSheet("background: transparent;")
        header_layout.addWidget(self._icon_label)

        # Title (custom title, severity name, or default)
        display_title = (
            title
            if title is not None
            else self.SEVERITY_TITLES.get(severity_type, "Notification")
        )
        self._title_label = QLabel(display_title)
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        # Close button
        if closable:
            self._close_button = QPushButton()
            self._close_button.setFixedSize(20, 20)
            self._close_button.setFlat(True)
            self._close_button.setCursor(Qt.PointingHandCursor)
            self._close_button.clicked.connect(self.dismiss)
            header_layout.addWidget(self._close_button)

        main_layout.addLayout(header_layout)

        # Message label
        self._message_label = QLabel(message)
        self._message_label.setTextFormat(Qt.RichText)
        self._message_label.setWordWrap(True)
        self._message_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        main_layout.addWidget(self._message_label)

        # Action button (optional)
        if action_text:
            self._action_button = QPushButton(action_text)
            self._action_button.setCursor(Qt.PointingHandCursor)
            self._action_button.clicked.connect(self.action_clicked.emit)
            main_layout.addWidget(self._action_button)

        # Setup slide animation (from right)
        self._slide_animation = QPropertyAnimation(self, b"pos", self)
        self._slide_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._slide_animation.setDuration(250)

        # Track if we're sliding in (to update position after animation)
        self._is_sliding_in = False

        # Setup drop shadow effect
        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setBlurRadius(20)
        self._shadow_effect.setOffset(0, 0)
        self._shadow_effect.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self._shadow_effect)

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)

        # Size policy - fixed width, minimum height to fit content
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        # Apply initial styling
        self._on_theme_changed()

        # Ensure widget sizes to fit content
        self.adjustSize()

        # Install event filter on parent to track resize
        if parent:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        """Handle parent resize events to reposition notifications."""
        if obj == self.parent() and event.type() == QEvent.Resize:
            self._update_position()
        return super().eventFilter(obj, event)

    def _update_position(self) -> None:
        """Update position when parent is resized."""
        parent = self.parent()
        if not parent or not self.isVisible():
            return

        # If currently animating a slide-in, update the animation end value
        if self._slide_animation.state() == QPropertyAnimation.Running:
            if self._is_sliding_in:
                parent_width = parent.width()
                end_x = parent_width - self._notification_width - self._margin
                current_end = self._slide_animation.endValue()
                self._slide_animation.setEndValue(
                    QPoint(end_x, current_end.y())
                )
            return

        parent_width = parent.width()
        end_x = parent_width - self._notification_width - self._margin
        current_pos = self.pos()
        self.move(end_x, current_pos.y())

    def _get_severity_colors(self, severity: Optional[int]) -> dict:
        """Get colors based on severity level."""
        # If no severity, use default text color
        if severity is None:
            return {
                "icon": self.theme.text,
                "accent": self.theme.text,
            }

        # Map severity to feedback key
        severity_to_key = {
            CRITICAL: "error",
            ERROR: "error",
            WARNING: "warning",
            SUCCESS: "success",
            INFO: "info",
            DEBUG: "debug",
        }

        key = severity_to_key.get(severity, "info")
        feedback = fxstyle.get_feedback_colors()
        foreground = feedback[key]["foreground"]

        return {
            "icon": foreground,
            "accent": foreground,
        }

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        severity_colors = self._get_severity_colors(self._severity_type)

        # Frame styling (card-like, darker background to stand out)
        self.setStyleSheet(
            f"""
            FXNotificationBanner {{
                background-color: {self.theme.surface_sunken};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """
        )

        # Update icon (custom icon, severity-based, or default)
        if self._custom_icon:
            icon_name = self._custom_icon
        elif self._severity_type is not None:
            icon_name = self.SEVERITY_ICONS.get(self._severity_type, "info")
        else:
            icon_name = "notifications"  # Default icon for custom notifications

        icon = fxicons.get_icon(icon_name, color=severity_colors["icon"])
        self._icon_label.setPixmap(icon.pixmap(18, 18))

        # Title label (bold, like FXProgressCard)
        self._title_label.setStyleSheet(
            f"""
            QLabel {{
                color: {severity_colors['icon']};
                font-weight: bold;
                font-size: 14px;
                background: transparent;
            }}
        """
        )

        # Message label (muted text, like FXProgressCard description)
        # Note: We avoid setting font properties via stylesheet to preserve
        # rich text formatting (bold, italic, etc.) from HTML tags
        self._message_label.setStyleSheet(
            f"color: {self.theme.text_muted}; background: transparent;"
        )

        # Close button styling
        if hasattr(self, "_close_button"):
            fxicons.set_icon(
                self._close_button, "close", color=self.theme.text_muted
            )
            self._close_button.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background: {self.theme.surface_alt};
                }}
            """
            )

        # Action button styling
        if hasattr(self, "_action_button"):
            self._action_button.setStyleSheet(
                f"""
                QPushButton {{
                    background: {self.theme.accent_primary};
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {self.theme.accent_secondary};
                }}
            """
            )

    def show(self) -> None:
        """Show the notification with slide-in animation from the right.

        Automatically calculates position based on other active notifications
        for the same parent widget, stacking them vertically with spacing.
        """
        # Ensure layout is calculated before showing
        self.adjustSize()

        super().show()

        # Log message if logger is provided
        if self._logger is not None:
            self._log_message()

        # Calculate positions for slide-in from right
        parent = self.parent()
        if parent:
            # Register this notification with parent tracking
            if parent not in FXNotificationBanner._active_notifications:
                FXNotificationBanner._active_notifications[parent] = []

            active_list = FXNotificationBanner._active_notifications[parent]

            # Add self to tracking if not already there
            if self not in active_list:
                active_list.append(self)

            # Calculate y position based on existing visible notifications
            # Find the bottom-most notification to stack below it
            y_offset = self._margin
            for notification in active_list:
                if notification is not self and notification.isVisible():
                    notification_bottom = (
                        notification.y() + notification.height()
                    )
                    y_offset = max(
                        y_offset, notification_bottom + self._spacing
                    )

            parent_width = parent.width()
            # Start position: off-screen to the right
            start_x = parent_width
            # End position: visible on the right with margin
            end_x = parent_width - self._notification_width - self._margin

            self.move(start_x, y_offset)

            # Mark as sliding in and connect to finished signal
            self._is_sliding_in = True
            self._slide_animation.stop()
            self._slide_animation.setStartValue(QPoint(start_x, y_offset))
            self._slide_animation.setEndValue(QPoint(end_x, y_offset))
            self._slide_animation.finished.connect(self._on_slide_in_finished)
            self._slide_animation.start()

        # Start auto-dismiss timer
        if self._timeout > 0:
            self._dismiss_timer.start(self._timeout)

    def _on_slide_in_finished(self) -> None:
        """Handle slide-in completion to ensure correct final position."""
        try:
            self._slide_animation.finished.disconnect(
                self._on_slide_in_finished
            )
        except RuntimeError:
            pass  # Already disconnected

        self._is_sliding_in = False

        # Ensure final position is correct (handles any resize during animation)
        self._update_position()

    def dismiss(self) -> None:
        """Dismiss the notification with slide-out animation to the right."""
        self._dismiss_timer.stop()

        # Slide out to the right
        parent = self.parent()
        if parent:
            parent_width = parent.width()
            current_pos = self.pos()
            end_x = parent_width

            self._slide_animation.stop()
            self._slide_animation.setStartValue(current_pos)
            self._slide_animation.setEndValue(QPoint(end_x, current_pos.y()))
            self._slide_animation.finished.connect(self._on_slide_out_finished)
            self._slide_animation.start()
        else:
            self._on_slide_out_finished()

    def _on_slide_out_finished(self) -> None:
        """Handle slide-out completion and reposition remaining notifications."""
        try:
            self._slide_animation.finished.disconnect(
                self._on_slide_out_finished
            )
        except RuntimeError:
            pass  # Already disconnected

        # Remove from tracking
        parent = self.parent()
        if parent and parent in FXNotificationBanner._active_notifications:
            active_list = FXNotificationBanner._active_notifications[parent]
            if self in active_list:
                active_list.remove(self)
            # Reposition remaining notifications
            self._reposition_notifications(parent)

        self.hide()
        self.closed.emit()

    @classmethod
    def _reposition_notifications(cls, parent: QWidget) -> None:
        """Reposition all active notifications for a parent widget.

        Animates remaining notifications to fill gaps left by dismissed ones.

        Args:
            parent: The parent widget containing the notifications.
        """
        if parent not in cls._active_notifications:
            return

        active_list = cls._active_notifications[parent]
        visible_notifications = [n for n in active_list if n.isVisible()]

        # Sort by current y position to maintain order
        visible_notifications.sort(key=lambda n: n.y())

        # Recalculate positions
        y_offset = (
            visible_notifications[0]._margin if visible_notifications else 16
        )

        for notification in visible_notifications:
            current_pos = notification.pos()
            if current_pos.y() != y_offset:
                # Animate to new position
                notification._slide_animation.stop()
                notification._slide_animation.setStartValue(current_pos)
                notification._slide_animation.setEndValue(
                    QPoint(current_pos.x(), y_offset)
                )
                notification._slide_animation.start()

            y_offset += notification.height() + notification._spacing

    def set_message(self, message: str) -> None:
        """Set the notification message.

        Args:
            message: The new message text.
        """
        self._message = message
        self._message_label.setText(message)

    def set_timeout(self, timeout: int) -> None:
        """Set the auto-dismiss timeout.

        Args:
            timeout: Timeout in milliseconds (0 = no auto-dismiss).
        """
        self._timeout = timeout

    def _log_message(self) -> None:
        """Log the notification message to the configured logger.

        Maps the notification severity to the appropriate logging level.

        Warning:
            This method is intended for internal use only.
        """
        if self._logger is None:
            return

        log_methods = {
            CRITICAL: self._logger.critical,
            ERROR: self._logger.error,
            WARNING: self._logger.warning,
            SUCCESS: self._logger.info,
            INFO: self._logger.info,
            DEBUG: self._logger.debug,
        }
        log_method = log_methods.get(self._severity_type, self._logger.info)
        log_method(self._message)


def example() -> None:
    import sys
    from qtpy.QtWidgets import (
        QVBoxLayout,
        QHBoxLayout,
        QWidget,
        QPushButton,
        QLineEdit,
        QTextEdit,
        QComboBox,
        QCheckBox,
        QSlider,
        QGroupBox,
        QFormLayout,
    )
    from qtpy.QtCore import Qt
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXNotificationBanner Demo")

    # Main content widget
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)

    # Sample form content
    form_group = QGroupBox("Sample Form")
    form_layout = QFormLayout(form_group)

    name_input = QLineEdit()
    name_input.setPlaceholderText("Enter your name...")
    form_layout.addRow("Name:", name_input)

    email_input = QLineEdit()
    email_input.setPlaceholderText("Enter your email...")
    form_layout.addRow("Email:", email_input)

    category_combo = QComboBox()
    category_combo.addItems(
        ["General", "Bug Report", "Feature Request", "Support"]
    )
    form_layout.addRow("Category:", category_combo)

    priority_slider = QSlider(Qt.Horizontal)
    priority_slider.setRange(1, 5)
    priority_slider.setValue(3)
    form_layout.addRow("Priority:", priority_slider)

    subscribe_check = QCheckBox("Subscribe to newsletter")
    form_layout.addRow("", subscribe_check)

    content_layout.addWidget(form_group)

    # Text area
    notes_group = QGroupBox("Notes")
    notes_layout = QVBoxLayout(notes_group)
    notes_edit = QTextEdit()
    notes_edit.setPlaceholderText("Enter additional notes here...")
    notes_edit.setMaximumHeight(100)
    notes_layout.addWidget(notes_edit)
    content_layout.addWidget(notes_group)

    def show_notification(severity_type, message, timeout=5000):
        """Create and show a notification."""
        banner = FXNotificationBanner(
            parent=window.centralWidget(),
            message=message,
            severity_type=severity_type,
            timeout=timeout,
            action_text="Undo" if severity_type == SUCCESS else None,
        )
        # Connect to the action button
        banner.action_clicked.connect(lambda: print("Action clicked"))
        # Clean up after closed
        banner.closed.connect(banner.deleteLater)
        banner.show()

    # Buttons to trigger notifications
    buttons_group = QGroupBox("Trigger Notifications")
    buttons_layout = QHBoxLayout(buttons_group)

    success_btn = QPushButton("Success")
    success_btn.clicked.connect(
        lambda: show_notification(SUCCESS, "Operation completed successfully!")
    )
    buttons_layout.addWidget(success_btn)

    warning_btn = QPushButton("Warning")
    warning_btn.clicked.connect(
        lambda: show_notification(WARNING, "This action may have side effects.")
    )
    buttons_layout.addWidget(warning_btn)

    error_btn = QPushButton("Error")
    error_btn.clicked.connect(
        lambda: show_notification(
            ERROR, "An error occurred during the operation."
        )
    )
    buttons_layout.addWidget(error_btn)

    info_btn = QPushButton("Info")
    info_btn.clicked.connect(
        lambda: show_notification(INFO, "Informational message for the user.")
    )
    buttons_layout.addWidget(info_btn)

    debug_btn = QPushButton("Debug")
    debug_btn.clicked.connect(
        lambda: show_notification(DEBUG, "Debug: variable_x = 42")
    )
    buttons_layout.addWidget(debug_btn)

    long_btn = QPushButton("Long Rich Text")
    long_btn.clicked.connect(
        lambda: show_notification(
            INFO,
            "This is a <b>long notification</b> with <i>rich text formatting</i> "
            "to test how the banner adapts its height to content. "
            "It includes <b>bold</b>, <i>italic</i>, and even "
            "<span style='color: #ff6b6b;'>colored text</span>. "
            "The notification should grow vertically to accommodate all this text.<br><br>"
            "Make sure to test line breaks and overall appearance!",
        )
    )
    buttons_layout.addWidget(long_btn)

    content_layout.addWidget(buttons_group)
    content_layout.addStretch()

    window.setCentralWidget(content_widget)

    window.resize(550, 500)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
