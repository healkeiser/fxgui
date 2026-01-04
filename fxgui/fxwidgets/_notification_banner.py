"""FXNotificationBanner - Toast/banner notification widget."""

from typing import Optional

from qtpy.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal
from qtpy.QtGui import QColor
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

from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._constants import (
    CRITICAL,
    ERROR,
    WARNING,
    SUCCESS,
    INFO,
    DEBUG,
)


class FXNotificationBanner(QFrame):
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

        # Get colors
        theme_colors = fxstyle.get_theme_colors()
        self._colors = self._get_severity_colors(severity, theme_colors)

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
        self._message_label.setStyleSheet(f"""
            QLabel {{
                color: {self._colors['text']};
                background: transparent;
            }}
        """)
        layout.addWidget(self._message_label, 1)

        # Action button (optional)
        if action_text:
            self._action_button = QPushButton(action_text)
            self._action_button.setCursor(Qt.PointingHandCursor)
            self._action_button.setStyleSheet(f"""
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
            """)
            self._action_button.clicked.connect(self.action_clicked.emit)
            layout.addWidget(self._action_button)

        # Close button
        if closable:
            self._close_button = QPushButton()
            self._close_button.setIcon(
                fxicons.get_icon("close", color=self._colors["icon"])
            )
            self._close_button.setFixedSize(24, 24)
            self._close_button.setFlat(True)
            self._close_button.setCursor(Qt.PointingHandCursor)
            self._close_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
            """)
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

    def _get_severity_colors(self, severity: int, theme_colors: dict) -> dict:
        """Get colors based on severity level."""
        severity_map = {
            CRITICAL: {
                "background": "#b71c1c",
                "border": "#d32f2f",
                "text": "#ffffff",
                "icon": "#ffffff",
                "action": "#ffffff",
            },
            ERROR: {
                "background": "#c62828",
                "border": "#e53935",
                "text": "#ffffff",
                "icon": "#ffffff",
                "action": "#ffffff",
            },
            WARNING: {
                "background": "#f57c00",
                "border": "#ff9800",
                "text": "#ffffff",
                "icon": "#ffffff",
                "action": "#ffffff",
            },
            SUCCESS: {
                "background": "#2e7d32",
                "border": "#43a047",
                "text": "#ffffff",
                "icon": "#ffffff",
                "action": "#ffffff",
            },
            INFO: {
                "background": "#1565c0",
                "border": "#1976d2",
                "text": "#ffffff",
                "icon": "#ffffff",
                "action": "#ffffff",
            },
            DEBUG: {
                "background": theme_colors["surface_alt"],
                "border": theme_colors["border"],
                "text": theme_colors["text"],
                "icon": theme_colors["text_secondary"],
                "action": fxstyle.get_accent_colors()["primary"],
            },
        }
        return severity_map.get(severity, severity_map[INFO])

    def _apply_styling(self) -> None:
        """Apply styling based on severity."""
        self.setStyleSheet(f"""
            FXNotificationBanner {{
                background-color: {self._colors['background']};
                border: 1px solid {self._colors['border']};
                border-radius: 6px;
            }}
        """)

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
    import os
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXNotificationBanner Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    success_banner = FXNotificationBanner(
        message="Operation completed successfully!",
        severity=SUCCESS,
        timeout=0,
        action_text="Undo"
    )
    success_banner.show()
    layout.addWidget(success_banner)

    warning_banner = FXNotificationBanner(
        message="This is a warning message.",
        severity=WARNING,
        timeout=0
    )
    warning_banner.show()
    layout.addWidget(warning_banner)

    error_banner = FXNotificationBanner(
        message="An error occurred during the operation.",
        severity=ERROR,
        timeout=0
    )
    error_banner.show()
    layout.addWidget(error_banner)

    info_banner = FXNotificationBanner(
        message="Informational message.",
        severity=INFO,
        timeout=0
    )
    info_banner.show()
    layout.addWidget(info_banner)

    layout.addStretch()
    window.resize(500, 300)
    window.show()
    sys.exit(app.exec())
