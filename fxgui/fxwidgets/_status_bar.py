"""Custom status bar widget."""

# Built-in
import logging
from typing import Optional, Tuple

# Third-party
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import (
    QFrame,
    QLabel,
    QStatusBar,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._constants import (
    CRITICAL,
    ERROR,
    WARNING,
    SUCCESS,
    INFO,
    DEBUG,
)


class FXStatusBar(fxstyle.FXThemeAware, QStatusBar):
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

        # Store colors for status line (will be set in _apply_theme_styles)
        self._status_line_color_a = None
        self._status_line_color_b = None

        # Create status line (gradient bar at the top of the status bar)
        self.status_line = QFrame(self)
        self.status_line.setFrameShape(QFrame.NoFrame)
        self.status_line.setFixedHeight(3)

        # Create border line (sits just below the status line)
        self.border_line = QFrame(self)
        self.border_line.setFrameShape(QFrame.NoFrame)
        self.border_line.setFixedHeight(1)

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

    def resizeEvent(self, event) -> None:
        """Handle resize to position the status line and border correctly."""
        super().resizeEvent(event)
        # Status line at the very top
        self.status_line.setGeometry(0, 0, self.width(), 3)
        # Border line just below the status line
        self.border_line.setGeometry(0, 3, self.width(), 1)
        # Raise both to ensure they're on top
        self.status_line.raise_()
        self.border_line.raise_()

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
            icon_name, color=feedback["foreground"]
        ).pixmap(14, 14)

        return (
            prefix,
            icon_pixmap,
            feedback["background"],
            feedback["foreground"],
        )

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

        colors_dict = fxstyle.get_colors()
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
        # Use inline style for bold as QSS can interfere with <b> tag rendering
        message_prefix = (
            f"<b>{severity_prefix}</b>: {fxutils.get_formatted_time()} - "
            if time
            else f"<b>{severity_prefix}</b>: "
        )
        notification_message = f"{message_prefix} {message}"
        self.icon_label.setPixmap(severity_icon)
        self.message_label.setText(notification_message)
        # self.clearMessage()

        if set_color:
            self._update_border_line_color(status_bar_border_color)
            self.setStyleSheet(
                f"""QStatusBar {{
                    background: {status_bar_color};
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
            self._apply_stylesheet()

    def _update_status_line_colors(self) -> None:
        """Update the status line gradient colors.

        Warning:
            This method is intended for internal use only.
        """
        self.status_line.setStyleSheet(
            f"background: qlineargradient("
            f"x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {self._status_line_color_a}, "
            f"stop:1 {self._status_line_color_b});"
        )

    def set_status_line_colors(self, color_a: str, color_b: str) -> None:
        """Set the status line gradient colors.

        Args:
            color_a: The first color of the gradient.
            color_b: The second color of the gradient.
        """
        self._status_line_color_a = color_a
        self._status_line_color_b = color_b
        self._update_status_line_colors()

    def _update_border_line_color(self, color: str) -> None:
        """Update the border line color.

        Args:
            color: The color for the border line.
        """
        self.border_line.setStyleSheet(f"background: {color};")

    def _apply_stylesheet(self, with_status_line_padding: bool = True) -> None:
        """Apply the status bar stylesheet.

        Args:
            with_status_line_padding: Whether to include padding for the
                status line. Defaults to `True`.
        """
        # Update accent colors from current theme
        self._status_line_color_a = self.theme.accent_primary
        self._status_line_color_b = self.theme.accent_secondary
        self._update_status_line_colors()

        # Update theme colors
        self._update_border_line_color(self.theme.border)
        self.setStyleSheet(
            f"""
            QStatusBar {{
                border: 0px solid transparent;
                background: {self.theme.surface_sunken};
            }}
        """
        )

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        self._apply_stylesheet()

    def hide_status_line(self) -> None:
        """Hide the status line and border line."""
        self.status_line.hide()
        self.border_line.hide()
        self._apply_stylesheet(with_status_line_padding=False)

    def show_status_line(self) -> None:
        """Show the status line and border line."""
        self.status_line.show()
        self.border_line.show()
        self._apply_stylesheet(with_status_line_padding=True)


def example() -> None:
    import sys
    from qtpy.QtCore import QTimer
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QPushButton
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXStatusBar Demo")

    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Create buttons to show different message types
    btn_info = QPushButton("Show Info Message")
    btn_success = QPushButton("Show Success Message")
    btn_warning = QPushButton("Show Warning Message")
    btn_error = QPushButton("Show Error Message")

    layout.addWidget(btn_info)
    layout.addWidget(btn_success)
    layout.addWidget(btn_warning)
    layout.addWidget(btn_error)

    # Connect buttons to show messages
    btn_info.clicked.connect(
        lambda: window.status_bar.showMessage("Info message", INFO)
    )
    btn_success.clicked.connect(
        lambda: window.status_bar.showMessage("Success message", SUCCESS)
    )
    btn_warning.clicked.connect(
        lambda: window.status_bar.showMessage("Warning message", WARNING)
    )
    btn_error.clicked.connect(
        lambda: window.status_bar.showMessage("Error message", ERROR)
    )

    window.resize(500, 300)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
