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
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._severity import (
    CRITICAL,
    ERROR,
    SEVERITIES,
    log,
    severity,
    severity_icon,
)


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
    }
    FXNotificationBanner QLabel#fxBannerMessage {
        color: @text_muted;
    }
    FXNotificationBanner QPushButton#fxBannerClose {
        background: transparent;
        border: none;
        border-radius: @button_radius;
    }
    FXNotificationBanner QPushButton#fxBannerClose:hover,
    FXNotificationBanner QPushButton#fxBannerAction:hover {
        background: @state_hover;
    }
    FXNotificationBanner QPushButton#fxBannerAction {
        background: transparent;
        color: @text_muted;
        border: 1px solid @border;
        border-radius: @button_radius;
        padding: 6px 16px;
        font-weight: 600;
    }
    FXNotificationBanner QPushButton#fxBannerAction[fxFocusVisible="true"]:focus {
        border-color: @accent_primary;
    }
    FXNotificationBanner QPushButton#fxBannerAction[primary="true"] {
        background: @primary_button;
        color: @text_on_accent_primary;
        border: 1px solid @primary_button;
    }
    FXNotificationBanner QPushButton#fxBannerAction[primary="true"]:hover {
        background: @primary_button_hover;
        color: @text_on_accent_secondary;
        border-color: @primary_button_hover;
    }
    FXNotificationBanner QPushButton#fxBannerAction[primary="true"]:pressed {
        background: @primary_button_pressed;
        color: @text_on_accent_primary;
        border-color: @primary_button_pressed;
    }
    FXNotificationBanner
    QPushButton#fxBannerAction[primary="true"][fxFocusVisible="true"]:focus {
        border-color: @text;
    }
    """
    + "".join(
        f'FXNotificationBanner[severity="{key}"] QLabel#fxBannerTitle '
        f"{{ color: @feedback_{key}_foreground; }} "
        for key in sorted({kind.feedback for kind in SEVERITIES.values()})
    )
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
    """A notification card that slides in at the parent's top right.

    Cards on one parent stack, and close up when one is dismissed.

    Args:
        parent: The widget the card sits on; it positions the card.
        message: The notification message, rich text.
        severity_type: CRITICAL, ERROR, WARNING, SUCCESS, INFO or DEBUG;
            None for a plain card with `title` and `icon`.
        timeout: Milliseconds before it dismisses itself; 0 never.
            Defaults to 5000, and to 0 for ERROR and CRITICAL: an error
            waits for the artist to read it.
        actions: Buttons as `{label: callback}`, left to right, the first
            styled primary. A card with actions never times out; a click
            runs the callback, then dismisses the card.
        closable: Whether to show a close button.
        width: The card's fixed width.
        logger: Logs the message when shown, at the severity's level.
        title: Replaces the severity's title.
        icon: An icon name replacing the severity's icon.
        margin: From the parent's right edge.
        top: From the parent's top to the first banner. Defaults to
            `margin`.
        spacing: Between stacked notifications; the pane gap.

    Signals:
        closed: Emitted when the banner is closed.

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

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "",
        severity_type: Optional[int] = None,
        timeout: Optional[int] = None,
        actions: Optional[Mapping[str, Callable[[], None]]] = None,
        closable: bool = True,
        width: int = 320,
        logger: Optional[logging.Logger] = None,
        title: Optional[str] = None,
        icon: Optional[str] = None,
        margin: int = 16,
        top: Optional[int] = None,
        spacing: int = fxstyle.PANE_GAP,
    ):
        super().__init__(parent)

        self._message = message
        self._severity_type = severity_type
        if timeout is None:
            timeout = 0 if severity_type in (ERROR, CRITICAL) else 5000
        self._timeout = timeout
        self._closable = closable
        self._logger = logger
        self._custom_icon = icon
        self._margin = margin
        self._top = margin if top is None else top
        self._spacing = spacing

        self.setFixedWidth(width)
        self.setProperty(
            "severity",
            severity(severity_type).feedback if severity_type in SEVERITIES
            else "",
        )

        self.setFrameShape(QFrame.StyledPanel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(fxstyle.PANE_GAP)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(fxstyle.PANE_GAP)
        self._icon_label = FXIconLabel(size=18)
        self._icon_label.setFixedSize(20, 20)
        header_layout.addWidget(self._icon_label)

        if title is None:
            title = (
                severity(severity_type).title
                if severity_type in SEVERITIES else "Notification"
            )
        self._title_label = QLabel(title)
        self._title_label.setObjectName("fxBannerTitle")
        fxstyle.mark_as_title(self._title_label, rank="section")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        if closable:
            self._close_button = QPushButton()
            self._close_button.setObjectName("fxBannerClose")
            self._close_button.setFixedSize(20, 20)
            self._close_button.setFlat(True)
            self._close_button.setCursor(Qt.PointingHandCursor)
            self._close_button.clicked.connect(self.dismiss)
            header_layout.addWidget(self._close_button)

        main_layout.addLayout(header_layout)

        self._message_label = QLabel(message)
        self._message_label.setObjectName("fxBannerMessage")
        self._message_label.setTextFormat(Qt.RichText)
        self._message_label.setWordWrap(True)
        self._message_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        main_layout.addWidget(self._message_label)

        # Built with the first action, so a plain banner keeps its margin.
        self._actions_layout: Optional[QHBoxLayout] = None
        self._action_buttons: list[QPushButton] = []

        # One animation slides in, out and restacks; ending the slide out
        # is the only end that does anything.
        self._slide_animation = QPropertyAnimation(self, b"pos", self)
        self._slide_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._slide_animation.setDuration(250)
        self._slide_animation.finished.connect(self._on_slide_finished)

        # Where the last slide was told to land, and whether we're leaving
        self._target_pos = QPoint()
        self._dismissing = False

        fxutils.add_shadow(self)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        self._update_icons()

        for label, callback in (actions or {}).items():
            self.add_action(label, callback)

        self.adjustSize()
        if parent:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        """Keep the banner at the parent's right edge as it resizes."""
        if obj == self.parent() and event.type() == QEvent.Resize:
            self._update_position()
        return super().eventFilter(obj, event)

    def _resting_x(self) -> int:
        """The x the banner sits at once it has finished sliding in."""
        parent = self.parent()
        parent_width = parent.width() if parent else 0
        return parent_width - self.width() - self._margin

    def _animate_to(self, target: QPoint) -> None:
        """Slide to `target`, in parent coordinates, from where it is now."""
        animation = self._slide_animation
        animation.stop()
        self._target_pos = target
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
            shown = fxicons.get_icon(
                self._custom_icon or "notifications", color="text")
        elif self._custom_icon:
            kind = severity(self._severity_type)
            shown = fxicons.get_icon(
                self._custom_icon, color=f"feedback_{kind.feedback}_foreground")
        else:
            shown = severity_icon(self._severity_type)
        self._icon_label.setIcon(shown)
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
            # Hidden now: a card waiting for its delete still stacks.
            self.hide()
            self.deleteLater()
            return False

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
                default=self._top,
            )
            self._dismissing = False
            self.move(parent.width(), y_offset)  # Off-screen, to the right
            self._animate_to(QPoint(self._resting_x(), y_offset))

        if self._timeout > 0:
            self._dismiss_timer.start(self._timeout)
        return True

    def dismiss(self) -> None:
        """Dismiss the notification with slide-out animation to the right."""
        if self._dismissing:
            return

        self._dismiss_timer.stop()
        self._dismissing = True

        parent = self.parent()
        if parent:
            self._animate_to(QPoint(parent.width(), self._target_pos.y()))
        else:
            self._leave()

    def _on_slide_finished(self) -> None:
        if self._dismissing:
            self._leave()

    def _leave(self) -> None:
        """Hide, let the banners below close up, then delete."""
        self.hide()
        if self.parent():
            self._reposition_notifications(self.parent())
        self.closed.emit()
        self.deleteLater()

    @staticmethod
    def _reposition_notifications(parent: QWidget) -> None:
        """Slide the banners staying on `parent` up into one stack."""
        # By where each is headed, not where a slide has it now.
        staying = sorted(_staying(parent), key=lambda n: n._target_pos.y())
        if not staying:
            return
        y_offset = staying[0]._top

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

        A banner with an action never times out. Clicking one runs its
        `callback`, then dismisses the banner.

        Returns:
            QPushButton: The button.

        Examples:
            >>> banner.add_action("Retry", retry_publish)
        """
        if self._actions_layout is None:
            self._actions_layout = QHBoxLayout()
            self._actions_layout.setSpacing(fxstyle.PANE_GAP)
            self._actions_layout.addStretch()
            self.layout().addLayout(self._actions_layout)

        button = QPushButton(text, self)
        button.setObjectName("fxBannerAction")
        # The first one leads; the rest step back.
        button.setProperty("primary", not self._action_buttons)
        button.setCursor(Qt.PointingHandCursor)
        # On the button, not in a lambda: a lambda holding self leaks it.
        button.callback = callback
        button.clicked.connect(self._action_clicked)
        self._actions_layout.addWidget(button)
        self._action_buttons.append(button)

        self._timeout = 0
        self._dismiss_timer.stop()

        self._refit()
        return button

    def _refit(self) -> None:
        """Fit the banner to its content and move the ones stacked under it."""
        self.adjustSize()
        if not self.isHidden() and self.parent():
            self._reposition_notifications(self.parent())

    def _action_clicked(self, _=False) -> None:
        """Run the clicked action's callback, then close the banner."""
        callback = self.sender().callback
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
        self._refit()

    def set_timeout(self, timeout: int) -> None:
        """Set the auto-dismiss timeout; a shown banner counts from now.

        Args:
            timeout: Timeout in milliseconds (0 = no auto-dismiss).
        """
        self._timeout = timeout
        self._dismiss_timer.stop()
        if timeout > 0 and not self.isHidden() and not self._dismissing:
            self._dismiss_timer.start(timeout)

    def set_top(self, top: int) -> None:
        """Set the first banner's distance from the parent's top."""
        self._top = top
