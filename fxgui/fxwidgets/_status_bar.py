"""Custom status bar widget."""

# Built-in
import logging
from typing import Optional, Tuple

# Third-party
from qtpy.QtCore import QEvent, Qt, Slot
from qtpy.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from qtpy.QtWidgets import QLabel, QStatusBar, QWidget

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._constants import INFO
from fxgui.fxwidgets._severity import log, severity

# The painted lines replace the base sheet's top border.
fxstyle.register_widget_style(
    """
    FXStatusBar {
        border: none;
    }
    """
)

# Accent line height, then the border line under it.
STATUS_LINE_HEIGHT = 3


class FXStatusBar(QStatusBar):
    """Customized QStatusBar class.

    The accent line and the border under it are painted along the top,
    except on the frame (`fxstyle.mark_as_frame`) or after
    `hide_status_line`.

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

        # Line state; `None` colours read the theme when painted.
        self._line_wanted = True
        self._line_colors: Optional[Tuple[str, str]] = None
        self._tint_border: Optional[str] = None

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

        for widget in (self.icon_label, self.message_label):
            self.addWidget(widget)
            widget.setVisible(False)  # Hide if no message is shown

        for widget in (self.project_label, self.version_label, self.company_label):
            self.addPermanentWidget(widget)

        self.messageChanged.connect(self._on_status_message_changed)
        fxstyle.theme_changed.connect(self._theme_switched)

    def showMessage(
        self,
        message: str,
        severity_type: int = INFO,
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
            set_color (bool): Whether to tint the bar in the severity's
                colors until the message goes. Defaults to `True`.
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

        # Qt's own message only drives `messageChanged` and the timeout.
        super().showMessage(" ", timeout=int(duration * 1000))

        self.icon_label.setVisible(True)
        self.message_label.setVisible(True)

        kind = severity(severity_type)
        feedback = fxstyle.get_colors()["feedback"][kind.feedback]
        severity_prefix = kind.title
        severity_icon = pixmap or fxicons.get_icon(
            kind.icon, color=feedback["foreground"]
        ).pixmap(14, 14)
        status_bar_color = background_color or feedback["background"]
        status_bar_border_color = feedback["foreground"]

        # Use inline style for bold as QSS can interfere with <b> tag rendering
        message_prefix = (
            f"<b>{severity_prefix}</b>: {fxutils.get_formatted_time()} - "
            if time
            else f"<b>{severity_prefix}</b>: "
        )
        self.icon_label.setPixmap(severity_icon)
        self.message_label.setText(f"{message_prefix} {message}")

        if set_color:
            # The bar's own sheet is the tint and nothing else.
            self._tint_border = status_bar_border_color
            self.setStyleSheet(
                f"""FXStatusBar {{
                    background: {status_bar_color};
                }}
                FXStatusBar QLabel {{
                    color: {fxstyle.readable_ink(status_bar_color)};
                }}"""
            )
            self.update()

        log(logger, severity_type, message)

    def clearMessage(self):
        """Clear the message and its tint.

        Note:
            Overrides the base class method.
        """
        super().clearMessage()
        self._clear()

    def _clear(self) -> None:
        """Hide the message labels and drop the tint.

        Warning:
            This method is intended for internal use only.
        """
        self.icon_label.clear()
        self.icon_label.setVisible(False)
        self.message_label.clear()
        self.message_label.setVisible(False)
        self._tint_border = None
        self.setStyleSheet("")
        self.update()

    @Slot(str)
    def _on_status_message_changed(self, message: str) -> None:
        """Clear the labels and tint when Qt's timeout empties the message."""
        if not message:
            self._clear()

    def _theme_switched(self, _theme_name: str) -> None:
        """Call `_on_theme_changed` without the theme name."""
        self._on_theme_changed()

    def _on_theme_changed(self, _theme_name: Optional[str] = None) -> None:
        """Drop a tint drawn in the old theme's colors; override to extend."""
        if self._tint_border is not None:
            self._clear()

    def set_status_line_colors(self, color_a: str, color_b: str) -> None:
        """Paint the accent line as a gradient from `color_a` to `color_b`."""
        self._line_colors = (color_a, color_b)
        self.update()

    def hide_status_line(self) -> None:
        """Hide the accent line and the border under it."""
        self._line_wanted = False
        self.update()

    def show_status_line(self) -> None:
        """Show the accent line and border, unless the bar is on the frame."""
        self._line_wanted = True
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the bar, then its accent line and the border under it."""
        super().paintEvent(event)
        # On the frame the bar joins the chrome, so it draws no line on top.
        if not self._line_wanted or self.property(fxstyle.FRAME_PROPERTY):
            return
        theme = fxstyle.colors()
        start, end = self._line_colors or (
            theme.accent_primary,
            theme.accent_secondary,
        )
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(start))
        gradient.setColorAt(1, QColor(end))
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), STATUS_LINE_HEIGHT, gradient)
        painter.fillRect(
            0,
            STATUS_LINE_HEIGHT,
            self.width(),
            1,
            QColor(self._tint_border or theme.border),
        )
        painter.end()

    def event(self, event: QEvent) -> bool:
        """Repaint when `fxstyle.mark_as_frame` marks or unmarks the bar."""
        if (
            event.type() == QEvent.DynamicPropertyChange
            and bytes(event.propertyName()) == fxstyle.FRAME_PROPERTY.encode()
        ):
            self.update()
        return super().event(event)


def example() -> None:
    import sys
    from fxgui.fxwidgets._constants import ERROR, SUCCESS, WARNING
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
