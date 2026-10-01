"""Toast/banner notification widget."""

# Built-in
import logging
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
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._constants import CRITICAL, ERROR
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._severity import SEVERITIES, log, severity


fxstyle.register_widget_style(
    """
    FXNotificationBanner {
        background-color: @surface_sunken;
        border: 1px solid @border;
        border-radius: @card_radius;
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
        border-radius: @button_radius;
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
            Defaults to 5000, and to 0 for ERROR and CRITICAL: an error
            waits for the artist to read it.
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
        timeout: Optional[int] = None,
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
        if timeout is None:
            timeout = 0 if severity_type in (ERROR, CRITICAL) else 5000
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
        self._shadow_effect = fxutils.add_shadows(self, self)

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

    def show(self, unique: bool = False) -> bool:
        """Show the notification with slide-in animation from the right.

        Automatically calculates position based on other active notifications
        for the same parent widget, stacking them vertically with spacing.

        Args:
            unique: If a banner on the same parent already says this
                message, show nothing and delete this one.

        Returns:
            bool: Whether the banner was shown.
        """
        parent = self.parent()
        if unique and parent and any(
            other is not self and other._message == self._message
            for other in _staying(parent)
        ):
            self.deleteLater()
            return False

        # Ensure layout is calculated before showing
        self.adjustSize()

        super().show()

        log(self._logger, self._severity_type, self._message)

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
        return True

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

    def message(self) -> str:
        """Return the message the banner says."""
        return self._message

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
