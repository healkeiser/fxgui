"""Toast/banner notification widget."""

# Built-in
import logging
import os
from typing import Callable, Mapping, Optional

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
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._severity import SEVERITIES, log, severity


fxstyle.register_widget_style(
    """
    FXNotificationBanner {
        background-color: @surface_sunken;
        border: 1px solid @border;
        border-radius: 8px;
    }
    FXNotificationBanner QLabel {
        background: transparent;
    }
    FXNotificationBanner QLabel#fxBannerTitle {
        color: @text;
        font-weight: bold;
        font-size: 14px;
    }
    FXNotificationBanner[severity="error"] QLabel#fxBannerTitle {
        color: @feedback_error_foreground;
    }
    FXNotificationBanner[severity="warning"] QLabel#fxBannerTitle {
        color: @feedback_warning_foreground;
    }
    FXNotificationBanner[severity="success"] QLabel#fxBannerTitle {
        color: @feedback_success_foreground;
    }
    FXNotificationBanner[severity="info"] QLabel#fxBannerTitle {
        color: @feedback_info_foreground;
    }
    FXNotificationBanner[severity="debug"] QLabel#fxBannerTitle {
        color: @feedback_debug_foreground;
    }
    FXNotificationBanner QLabel#fxBannerMessage {
        color: @text_muted;
    }
    FXNotificationBanner QPushButton#fxBannerClose {
        background: transparent;
        border: none;
        border-radius: 10px;
    }
    FXNotificationBanner QPushButton#fxBannerClose:hover {
        background: @surface_alt;
    }
    FXNotificationBanner QPushButton#fxBannerAction {
        background: transparent;
        color: @text_muted;
        border: 1px solid @border;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: bold;
        font-size: 12px;
    }
    FXNotificationBanner QPushButton#fxBannerAction:hover {
        background: @surface_alt;
    }
    FXNotificationBanner QPushButton#fxBannerAction[primary="true"] {
        background: @accent_primary;
        color: @text_on_accent_primary;
        border: none;
    }
    FXNotificationBanner QPushButton#fxBannerAction[primary="true"]:hover {
        background: @accent_secondary;
        color: @text_on_accent_secondary;
    }
    """
)


def _staying(parent: QWidget) -> list:
    """Return the banners shown on `parent` that are not leaving."""
    return [
        banner
        for banner in parent.findChildren(
            FXNotificationBanner, options=Qt.FindDirectChildrenOnly
        )
        if not banner.isHidden() and not banner._dismissing
    ]


class FXNotificationBanner(QFrame):
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
        action_text: Text for a single action button. Sugar for a one-entry
            `actions` whose callback emits `action_clicked`.
        actions: Buttons to put on the banner, as `{label: callback}`, left to
            right. The first one is styled as the primary. A banner with
            actions never auto-dismisses, and clicking one runs its callback
            then dismisses the banner.
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
        action_clicked: Emitted when the `action_text` button is clicked.

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
        >>>
        >>> # Interactive notification - waits for the artist to answer
        >>> banner = FXNotificationBanner(
        ...     parent=window,
        ...     message="Publish failed on 3 shots.",
        ...     severity_type=ERROR,
        ...     actions={"Retry": retry_publish, "Open log": open_log},
        ... )
        >>> banner.show()
    """

    closed = Signal()
    action_clicked = Signal()

    SEVERITY_ICONS = {level: kind.icon for level, kind in SEVERITIES.items()}
    SEVERITY_TITLES = {
        level: kind.title for level, kind in SEVERITIES.items()
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "",
        severity_type: Optional[int] = None,
        timeout: int = 5000,
        action_text: Optional[str] = None,
        actions: Optional[Mapping[str, Callable[[], None]]] = None,
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
        self.setProperty(
            "severity",
            severity(severity_type).feedback if severity_type in SEVERITIES
            else "",
        )

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
        self._icon_label = FXIconLabel(size=18)
        self._icon_label.setFixedSize(20, 20)
        header_layout.addWidget(self._icon_label)

        # Title (custom title, severity name, or default)
        display_title = (
            title
            if title is not None
            else self.SEVERITY_TITLES.get(severity_type, "Notification")
        )
        self._title_label = QLabel(display_title)
        self._title_label.setObjectName("fxBannerTitle")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        # Close button
        if closable:
            self._close_button = QPushButton()
            self._close_button.setObjectName("fxBannerClose")
            self._close_button.setFixedSize(20, 20)
            self._close_button.setFlat(True)
            self._close_button.setCursor(Qt.PointingHandCursor)
            self._close_button.clicked.connect(self.dismiss)
            header_layout.addWidget(self._close_button)

        main_layout.addLayout(header_layout)

        # Message label
        self._message_label = QLabel(message)
        self._message_label.setObjectName("fxBannerMessage")
        self._message_label.setTextFormat(Qt.RichText)
        self._message_label.setWordWrap(True)
        self._message_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        main_layout.addWidget(self._message_label)

        # Action buttons (optional) - the row is only built if one is added,
        # so a plain banner keeps its own bottom margin
        self._actions_layout: Optional[QHBoxLayout] = None
        self._action_buttons: list[QPushButton] = []

        # Setup slide animation (from right)
        self._slide_animation = QPropertyAnimation(self, b"pos", self)
        self._slide_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._slide_animation.setDuration(250)

        # Where the last slide was told to land, and whether we're leaving
        self._target_pos = QPoint()
        self._dismissing = False
        self._slide_handler = None

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

        self._update_icons()

        if action_text:
            self.add_action(action_text, self.action_clicked.emit)
        for label, callback in (actions or {}).items():
            self.add_action(label, callback)

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

    def _resting_x(self) -> int:
        """The x the banner sits at once it has finished sliding in."""
        parent = self.parent()
        parent_width = parent.width() if parent else 0
        return parent_width - self._notification_width - self._margin

    def _animate_to(self, target: QPoint, on_finished=None) -> None:
        """Slide to `target`, replacing whatever the banner was doing.

        The animation object is shared between slide-in, slide-out and
        restacking, so any pending `finished` handler is dropped first: a
        handler left connected fires at the end of the *next* slide, which is
        how a dismissing banner ends up stopping mid-way then vanishing.

        Args:
            target: Position to slide to, in parent coordinates.
            on_finished: Called once, when this slide reaches `target`.
        """
        animation = self._slide_animation
        animation.stop()
        if self._slide_handler is not None:
            animation.finished.disconnect(self._slide_handler)
            self._slide_handler = None

        self._target_pos = target
        if on_finished is not None:
            animation.finished.connect(on_finished)
            self._slide_handler = on_finished
        animation.setStartValue(self.pos())
        animation.setEndValue(target)
        animation.start()

    def _update_position(self) -> None:
        """Update position when parent is resized."""
        if not self.parent() or self.isHidden() or self._dismissing:
            return

        self._target_pos = QPoint(self._resting_x(), self._target_pos.y())
        if self._slide_animation.state() == QPropertyAnimation.Running:
            self._slide_animation.setEndValue(self._target_pos)
        else:
            self.move(self._target_pos)

    def _update_icons(self) -> None:
        """Set the severity icon and the close icon, in theme ink tokens."""
        if self._severity_type is None:
            color, icon_name = "text", "notifications"
        else:
            kind = severity(self._severity_type)
            color = f"feedback_{kind.feedback}_foreground"
            icon_name = kind.icon
        icon_name = self._custom_icon or icon_name
        self._icon_label.setIcon(fxicons.get_icon(icon_name, color=color))
        if self._closable:
            fxicons.set_icon(self._close_button, "close", color="text_muted")

    def show(self) -> None:
        """Show the notification with slide-in animation from the right.

        Automatically calculates position based on other active notifications
        for the same parent widget, stacking them vertically with spacing.
        """
        # Ensure layout is calculated before showing
        self.adjustSize()

        super().show()

        log(self._logger, self._severity_type, self._message)

        parent = self.parent()
        if parent:
            # Below every banner already staying on this parent.
            y_offset = max(
                (
                    n._target_pos.y() + n.height() + self._spacing
                    for n in _staying(parent)
                    if n is not self
                ),
                default=self._margin,
            )
            self._dismissing = False
            self.move(parent.width(), y_offset)  # Off-screen, to the right
            self._animate_to(QPoint(self._resting_x(), y_offset))

        # Start auto-dismiss timer
        if self._timeout > 0:
            self._dismiss_timer.start(self._timeout)

    def dismiss(self) -> None:
        """Dismiss the notification with slide-out animation to the right."""
        if self._dismissing:
            return

        self._dismiss_timer.stop()
        self._dismissing = True

        # Slide out to the right
        parent = self.parent()
        if parent:
            self._animate_to(
                QPoint(parent.width(), self._target_pos.y()),
                self._on_slide_out_finished,
            )
        else:
            self._on_slide_out_finished()

    def _on_slide_out_finished(self) -> None:
        """Handle slide-out completion and reposition remaining notifications."""
        self.hide()
        if self.parent():
            self._reposition_notifications(self.parent())
        self.closed.emit()
        self.deleteLater()

    @classmethod
    def _reposition_notifications(cls, parent: QWidget) -> None:
        """Reposition all active notifications for a parent widget.

        Animates remaining notifications to fill gaps left by dismissed ones.

        Args:
            parent: The parent widget containing the notifications.
        """
        # Sort by where each banner is headed, not by its transient position
        staying = sorted(_staying(parent), key=lambda n: n._target_pos.y())
        y_offset = staying[0]._margin if staying else 16

        for notification in staying:
            target = QPoint(notification._resting_x(), y_offset)
            if notification._target_pos != target:
                notification._animate_to(target)
            y_offset += notification.height() + notification._spacing

    def add_action(
        self,
        text: str,
        callback: Optional[Callable[[], None]] = None,
    ) -> QPushButton:
        """Add an action button to the banner.

        A banner you are meant to answer must not disappear while you reach
        for it, so the first action cancels auto-dismiss: the banner then
        stays until an action or the close button is used. Clicking an action
        runs `callback`, then dismisses the banner.

        Args:
            text: The button label.
            callback: Called when the button is clicked, before the dismiss.

        Returns:
            QPushButton: The button, for callers who want to restyle it or
                wire extra signals.

        Examples:
            >>> banner.add_action("Retry", retry_publish)
        """
        if self._actions_layout is None:
            self._actions_layout = QHBoxLayout()
            self._actions_layout.setSpacing(8)
            self._actions_layout.addStretch()
            self.layout().addLayout(self._actions_layout)

        button = QPushButton(text, self)
        button.setObjectName("fxBannerAction")
        # The first one leads; the rest step back.
        button.setProperty("primary", not self._action_buttons)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda: self._run_action(callback))
        self._actions_layout.addWidget(button)
        self._action_buttons.append(button)

        # No timing out a banner that is waiting on an answer
        self._timeout = 0
        self._dismiss_timer.stop()

        # The banner just grew, so the ones stacked under it have moved
        self.adjustSize()
        if not self.isHidden() and self.parent():
            self._reposition_notifications(self.parent())

        return button

    def _run_action(self, callback: Optional[Callable[[], None]]) -> None:
        """Run an action's callback, then close the banner.

        Warning:
            This method is intended for internal use only.
        """
        if callback is not None:
            callback()
        self.dismiss()

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


def example() -> None:
    import sys
    from fxgui.fxwidgets._constants import DEBUG, ERROR, INFO, SUCCESS, WARNING
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

    interactive_btn = QPushButton("Interactive")
    interactive_btn.clicked.connect(
        lambda: FXNotificationBanner(
            parent=window.centralWidget(),
            message="Publish failed on 3 shots.",
            severity_type=ERROR,
            actions={
                "Retry": lambda: print("Retry"),
                "Open log": lambda: print("Open log"),
            },
        ).show()
    )
    buttons_layout.addWidget(interactive_btn)

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
