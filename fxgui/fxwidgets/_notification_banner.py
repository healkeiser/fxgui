"""FXNotificationBanner - Toast/banner notification widget."""

# Built-in
import os
from typing import Optional

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from qtpy.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

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
    """Animated notification banners that slide in from top or bottom.

    This widget provides toast-style notifications with severity levels,
    auto-dismiss, and optional action buttons.

    Args:
        parent: Parent widget.
        message: The notification message.
        severity: Severity level (CRITICAL, ERROR, WARNING, SUCCESS, INFO, DEBUG).
        timeout: Auto-dismiss timeout in milliseconds (0 = no auto-dismiss).
        action_text: Text for the optional action button.
        closable: Whether to show a close button.
        position: Position of the banner ('top' or 'bottom').

    Signals:
        closed: Emitted when the banner is closed.
        action_clicked: Emitted when the action button is clicked.

    Examples:
        >>> banner = FXNotificationBanner(
        ...     message="File saved successfully!",
        ...     severity=SUCCESS,
        ...     timeout=3000
        ... )
        >>> banner.show()
    """

    closed = Signal()
    action_clicked = Signal()

    # Severity icons mapping
    SEVERITY_ICONS = {
        CRITICAL: "cancel",
        ERROR: "error",
        WARNING: "warning",
        SUCCESS: "check_circle",
        INFO: "info",
        DEBUG: "bug_report",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "",
        severity: int = INFO,
        timeout: int = 5000,
        action_text: Optional[str] = None,
        closable: bool = True,
        position: str = "top",
    ):
        super().__init__(parent)

        self._message = message
        self._severity = severity
        self._timeout = timeout
        self._position = position
        self._action_text = action_text
        self._closable = closable

        # Get colors (will be refreshed in _apply_theme_styles)
        self._colors = self._get_severity_colors(severity)

        # Setup frame styling
        self.setFrameShape(QFrame.StyledPanel)
        self._apply_styling()

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Icon
        self._icon_label = QLabel()
        icon_name = self.SEVERITY_ICONS.get(severity, "info")
        icon = fxicons.get_icon(icon_name, color=self._colors["icon"])
        self._icon_label.setPixmap(icon.pixmap(20, 20))
        self._icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._icon_label)

        # Message
        self._message_label = QLabel(message)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self._colors['text']};
                background: transparent;
            }}
        """
        )
        layout.addWidget(self._message_label, 1)

        # Action button (optional)
        if action_text:
            self._action_button = QPushButton(action_text)
            self._action_button.setCursor(Qt.PointingHandCursor)
            self._action_button.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {self._colors['action']};
                    border: 1px solid {self._colors['action']};
                    border-radius: 3px;
                    padding: 4px 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                }}
            """
            )
            self._action_button.clicked.connect(self.action_clicked.emit)
            layout.addWidget(self._action_button)

        # Close button
        if closable:
            self._close_button = QPushButton()
            fxicons.set_icon(
                self._close_button, "close", color=self._colors["icon"]
            )
            self._close_button.setFixedSize(24, 24)
            self._close_button.setFlat(True)
            self._close_button.setCursor(Qt.PointingHandCursor)
            self._close_button.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
            """
            )
            self._close_button.clicked.connect(self.dismiss)
            layout.addWidget(self._close_button)

        # Setup animations
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0)

        self._fade_animation = QPropertyAnimation(
            self._opacity_effect, b"opacity", self
        )
        self._fade_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._fade_animation.setDuration(200)

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)

        # Size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _get_severity_colors(self, severity: int) -> dict:
        """Get colors based on severity level."""
        # Get feedback colors from theme JSONC
        colors = fxstyle.get_colors()
        feedback = colors.get("feedback", {})

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
        fb = feedback.get(key, {})
        foreground = fb.get("foreground", "#ffffff")
        background = fb.get("background", "#372d75")

        return {
            "background": background,
            "border": foreground,
            "text": "#ffffff",
            "icon": foreground,
            "action": "#ffffff",
        }

    def _apply_styling(self) -> None:
        """Apply styling based on severity."""
        self.setStyleSheet(
            f"""
            FXNotificationBanner {{
                background-color: {self._colors['background']};
                border: 1px solid {self._colors['border']};
                border-radius: 6px;
            }}
        """
        )

    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styles."""
        # Refresh severity colors
        self._colors = self._get_severity_colors(self._severity)
        self._apply_styling()

        # Update icon
        icon_name = self.SEVERITY_ICONS.get(self._severity, "info")
        icon = fxicons.get_icon(icon_name, color=self._colors["icon"])
        self._icon_label.setPixmap(icon.pixmap(20, 20))

        # Update message label
        self._message_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self._colors['text']};
                background: transparent;
            }}
        """
        )

        # Update action button if exists
        if hasattr(self, "_action_button"):
            self._action_button.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {self._colors['action']};
                    border: 1px solid {self._colors['action']};
                    border-radius: 3px;
                    padding: 4px 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                }}
            """
            )

        # Update close button if exists
        if hasattr(self, "_close_button"):
            fxicons.set_icon(
                self._close_button, "close", color=self._colors["icon"]
            )

    def show(self) -> None:
        """Show the notification with fade-in animation."""
        super().show()

        # Fade in
        self._fade_animation.stop()
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()

        # Start auto-dismiss timer
        if self._timeout > 0:
            self._dismiss_timer.start(self._timeout)

    def dismiss(self) -> None:
        """Dismiss the notification with fade-out animation."""
        self._dismiss_timer.stop()

        # Fade out
        self._fade_animation.stop()
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self._on_fade_out_finished)
        self._fade_animation.start()

    def _on_fade_out_finished(self) -> None:
        """Handle fade-out completion."""
        self._fade_animation.finished.disconnect(self._on_fade_out_finished)
        self.hide()
        self.closed.emit()

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


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
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

    # Track active banners for stacking
    active_banners = []

    def reposition_banners():
        """Reposition all active banners at the top of the window."""
        y_offset = 10
        for banner in active_banners:
            banner.setGeometry(
                10,
                y_offset,
                content_widget.width() - 20,
                banner.sizeHint().height(),
            )
            banner.raise_()
            y_offset += banner.sizeHint().height() + 8

    def show_notification(severity, message, timeout=3000):
        banner = FXNotificationBanner(
            parent=content_widget,
            message=message,
            severity=severity,
            timeout=timeout,
            action_text="Undo" if severity == SUCCESS else None,
        )
        active_banners.insert(0, banner)

        def on_closed():
            if banner in active_banners:
                active_banners.remove(banner)
            banner.deleteLater()
            reposition_banners()

        banner.closed.connect(on_closed)
        banner.show()
        reposition_banners()

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

    content_layout.addWidget(buttons_group)
    content_layout.addStretch()

    window.setCentralWidget(content_widget)

    # Handle resize to reposition banners
    original_resize = content_widget.resizeEvent

    def on_resize(event):
        reposition_banners()
        if original_resize:
            original_resize(event)

    content_widget.resizeEvent = on_resize

    window.resize(550, 500)
    window.show()
    sys.exit(app.exec())
