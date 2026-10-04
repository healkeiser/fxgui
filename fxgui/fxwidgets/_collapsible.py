"""Collapsible widget implementation."""

# Built-in
from typing import Optional, Union

# Third-party
from qtpy.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    Signal,
)
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._labels import FXIconLabel


class FXCollapsibleWidget(QWidget):
    """A widget that can expand or collapse its content.

    The widget consists of a header with a toggle button and a content area
    that can be shown or hidden with an animation effect.

    Args:
        parent: Parent widget.
        title: Title displayed in the header.
        icon: Optional icon to display before the title. Can be a
            QIcon, an icon name string (for fxicons), or None.
        animation_duration: Duration of expand/collapse animation in ms.
        max_content_height: Maximum height of the open content area;
            taller content scrolls. 0 means no limit.

    Signals:
        expanded: Emitted when the widget is expanded.
        collapsed: Emitted when the widget is collapsed.

    Examples:
        >>> from qtpy.QtWidgets import QLabel, QVBoxLayout
        >>> collapsible = FXCollapsibleWidget(title="Settings")
        >>> layout = QVBoxLayout()
        >>> layout.addWidget(QLabel("Option 1"))
        >>> layout.addWidget(QLabel("Option 2"))
        >>> collapsible.set_content_layout(layout)
        >>>
        >>> # With an icon
        >>> collapsible_with_icon = FXCollapsibleWidget(
        ...     title="Settings",
        ...     icon="settings"
        ... )
    """

    expanded = Signal()
    collapsed = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        icon: Optional[Union[QIcon, str]] = None,
        animation_duration: int = 150,
        max_content_height: int = 300,
    ):
        """Initialize the collapsible section."""
        super().__init__(parent=parent)

        # Store properties
        self._animation_duration = animation_duration
        self._max_content_height = max_content_height
        self._is_expanded = False

        # Create fixed header layout
        self._header = QFrame()
        self._header.setObjectName("fx_collapsible_header")
        self._header.setProperty("expanded", False)
        self._header.setFrameShape(QFrame.StyledPanel)
        self._header.setFrameShadow(QFrame.Raised)
        self._header.setCursor(Qt.PointingHandCursor)
        # A QFrame matches :hover only with hover events on.
        self._header.setAttribute(Qt.WA_Hover)
        self._header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._header.installEventFilter(self)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(fxstyle.PANE_GAP)

        # Toggle button (chevron icon)
        self._toggle_btn = QToolButton()
        self._toggle_btn.setObjectName("fx_collapsible_toggle")
        fxicons.set_icon(self._toggle_btn, "chevron_right")
        self._toggle_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Title icon label (optional)
        self._icon_label = FXIconLabel()
        self._icon_label.setObjectName("fx_collapsible_icon")
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setVisible(False)

        # Title label
        self._title_label = QLabel(str(title))
        self._title_label.setObjectName("fx_collapsible_title")
        self._title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Spacer to push content to the left, line spans remaining width
        header_layout.addWidget(self._toggle_btn)
        header_layout.addWidget(self._icon_label)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        # Content area: always with scrollbars when needed
        self._content_area = QScrollArea()
        self._content_area.setWidgetResizable(True)
        self._content_area.setFrameShape(QFrame.NoFrame)
        # Start with scrollbars off to prevent flicker on first animation
        self._content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content_area.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )

        # Initially collapsed
        self._content_area.setMaximumHeight(0)
        self._content_area.setMinimumHeight(0)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._header)
        main_layout.addWidget(self._content_area)

        # Size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Set minimum width to ensure visibility
        self.setMinimumWidth(150)

        # Setup animation with ease-out curve. Parented to this widget,
        # so it is destroyed with it: an unparented group keeps ticking
        # after the widget is gone, and a frame handler that reaches for
        # a destroyed widget is a crash in someone else's event loop.
        self._animation = QParallelAnimationGroup(self)

        max_height_anim = QPropertyAnimation(
            self._content_area, b"maximumHeight"
        )
        max_height_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.addAnimation(max_height_anim)

        min_height_anim = QPropertyAnimation(
            self._content_area, b"minimumHeight"
        )
        min_height_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.addAnimation(min_height_anim)

        # Connect signals
        self._toggle_btn.clicked.connect(self.toggle)
        self._animation.finished.connect(self._on_animation_finished)

        # Set icon if provided
        if icon is not None:
            self.set_icon(icon)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Toggle on a left click anywhere on the header."""
        if (
            watched is self._header
            and event.type() == QEvent.MouseButtonPress
            and event.button() == Qt.LeftButton
        ):
            self.toggle()
            return True
        return super().eventFilter(watched, event)

    def is_expanded(self) -> bool:
        """Return whether the widget is expanded."""
        return self._is_expanded

    def animation_duration(self) -> int:
        """Return the animation duration in milliseconds."""
        return self._animation_duration

    def set_animation_duration(self, value: int) -> None:
        """Set the animation duration in milliseconds."""
        self._animation_duration = value

    def max_content_height(self) -> int:
        """Return the open content area's cap; 0 means no limit."""
        return self._max_content_height

    def set_max_content_height(self, value: int) -> None:
        """Set the open content area's cap, at once if it is open."""
        self._max_content_height = value
        if self._is_expanded:
            self._move_to(self._target_height(), animate=False)

    def expand(self, animate: bool = True) -> None:
        """Expand the widget to show content.

        Args:
            animate: Whether to animate the expansion.
        """
        if self._is_expanded:
            return

        self._is_expanded = True
        fxicons.set_icon(self._toggle_btn, "expand_more")

        self._mark_expanded(True)

        self._move_to(self._target_height(), animate)
        self.expanded.emit()

    def collapse(self, animate: bool = True) -> None:
        """Collapse the widget to hide content.

        Args:
            animate: Whether to animate the collapse.
        """
        if not self._is_expanded:
            return

        self._is_expanded = False
        fxicons.set_icon(self._toggle_btn, "chevron_right")

        self._mark_expanded(False)

        self._move_to(0, animate)
        self.collapsed.emit()

    def _move_to(self, target_height: int, animate: bool) -> None:
        """Animate the content area to `target_height`.

        Always forwards, from the height on screen now: a group run
        backwards starts at its own end value and jumps. The height is
        read before stopping the animation, and from `height()`, since
        `maximumHeight` is released to the cap once an expansion ends.

        Args:
            target_height: Where the content area should end up.
            animate: Whether to get there over time, or at once.
        """
        reached = min(
            self._content_area.maximumHeight(), self._content_area.height()
        )
        self._animation.stop()

        if not animate:
            self._content_area.setMinimumHeight(target_height)
            self._content_area.setMaximumHeight(target_height)
            self._on_animation_finished()
            return

        for index in range(self._animation.animationCount()):
            animation = self._animation.animationAt(index)
            animation.setDuration(self._animation_duration)
            animation.setStartValue(reached)
            animation.setEndValue(target_height)
        self._animation.setDirection(QAbstractAnimation.Forward)
        self._animation.start()

    def toggle(self) -> None:
        """Toggle the expanded/collapsed state."""
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()

    def _target_height(self) -> int:
        """Return the open height: the content's own, under any cap."""
        # Measured on every call: content grows after it was set.
        content = self._content_area.widget()
        height = content.sizeHint().height() if content else 0
        if self._max_content_height > 0:
            height = min(height, self._max_content_height)
        return height

    def _on_animation_finished(self) -> None:
        """Settle the content area once a movement ends.

        `updateGeometry` is what makes the parent layouts give back the
        height of a section shut again; they cache it otherwise.
        """
        # Bars stay off while moving, so the animation does not flicker.
        policy = (
            Qt.ScrollBarAsNeeded if self._is_expanded else Qt.ScrollBarAlwaysOff
        )
        self._content_area.setVerticalScrollBarPolicy(policy)
        self._content_area.setHorizontalScrollBarPolicy(policy)
        if not self._is_expanded:
            self._content_area.setMinimumHeight(0)
            self._content_area.setMaximumHeight(0)
        else:
            self._content_area.setMinimumHeight(self._target_height())
            # Released from the animated height, or later rows clip; a
            # requested cap stays a cap.
            self._content_area.setMaximumHeight(
                self._max_content_height
                if self._max_content_height > 0
                else fxutils.NO_CAP
            )

        self.updateGeometry()

    def _mark_expanded(self, expanded: bool) -> None:
        """Let the header's QSS rules follow the expanded state."""
        self._header.setProperty("expanded", expanded)
        fxutils.repolish(self._header)
        fxutils.repolish(self._title_label)

    def set_content_layout(self, content_layout: QLayout) -> None:
        """Set the layout for the content area.

        Args:
            content_layout: The layout to set for the content area.
        """
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        self.set_content_widget(content_widget)

    def set_content_widget(self, widget: QWidget) -> None:
        """Set the content widget directly.

        Args:
            widget: The widget to display when expanded.
        """
        self._content_area.setWidget(widget)

    def set_icon(self, icon: Union[QIcon, str, None]) -> None:
        """Set an icon to display before the title.

        Args:
            icon: The icon to display. Can be:
                - A QIcon instance
                - A string icon name (resolved via fxicons.get_icon)
                - None to remove the icon

        Examples:
            >>> collapsible = FXCollapsibleWidget(title="Settings")
            >>> collapsible.set_icon("settings")  # Using icon name
            >>> collapsible.set_icon(QIcon("path/to/icon.png"))  # Using QIcon
            >>> collapsible.set_icon(None)  # Remove icon
        """
        if isinstance(icon, str):
            icon = fxicons.get_icon(icon)
        self._icon_label.setIcon(icon)
        # A null QIcon is no icon too: shown, it is an empty gap.
        self._icon_label.setVisible(icon is not None and not icon.isNull())

    def icon(self) -> Optional[QIcon]:
        """Return the current icon.

        Returns:
            The current icon, or None if no icon is set.
        """
        icon = self._icon_label.icon()
        return None if icon.isNull() else icon

    def set_title(self, title: str) -> None:
        """Set the title text.

        Args:
            title: The title text to display.
        """
        self._title_label.setText(str(title))

    def title(self) -> str:
        """Return the title text."""
        return self._title_label.text()


fxstyle.register_widget_style("""
FXCollapsibleWidget QFrame#fx_collapsible_header {
    border-radius: @button_radius;
}
FXCollapsibleWidget QFrame#fx_collapsible_header:hover {
    background-color: @state_hover;
}
FXCollapsibleWidget QToolButton#fx_collapsible_toggle {
    border: none;
    background: transparent;
}
FXCollapsibleWidget QLabel#fx_collapsible_icon {
    background: transparent;
}
FXCollapsibleWidget QLabel#fx_collapsible_title {
    background: transparent;
}
FXCollapsibleWidget
QFrame#fx_collapsible_header[expanded="true"] QLabel#fx_collapsible_title {
    font-weight: 600;
}
""")
