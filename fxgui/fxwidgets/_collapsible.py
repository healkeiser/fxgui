"""Collapsible widget implementation."""

from typing import Optional, Union

from qtpy.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
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

from fxgui import fxicons


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
        title_icon: Optional icon to display before the title. Can be a
            QIcon, an icon name string (for fxicons), or None.

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
        ...     title_icon="settings"
        ... )
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        animation_duration: int = 150,
        max_content_height: int = 300,
        title_icon: Optional[Union[QIcon, str]] = None,
    ):
        """Initialize the collapsible section."""
        super().__init__(parent=parent)

        # Store properties
        self.animation_duration = animation_duration
        self.max_content_height = max_content_height
        self._title = str(title)
        self._title_icon: Optional[QIcon] = None
        self._is_expanded = False
        self._has_been_expanded = False
        self._content_height = 0

        # Create fixed header layout
        self.header_widget = QFrame()
        self.header_widget.setFrameShape(QFrame.StyledPanel)
        self.header_widget.setFrameShadow(QFrame.Raised)
        self.header_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        # Header background is styled via the QSS stylesheet

        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(8)

        # Toggle button (chevron icon)
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet(
            "QToolButton { border: none; background: transparent; }"
        )
        self.toggle_button.setIcon(fxicons.get_icon("chevron_right"))
        self.toggle_button.setProperty("icon_name", "chevron_right")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Title icon label (optional)
        self.title_icon_label = QLabel()
        self.title_icon_label.setStyleSheet("background: transparent;")
        self.title_icon_label.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed
        )
        self.title_icon_label.setVisible(False)

        # Title label
        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet("background: transparent;")
        self.title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Spacer to push content to the left, line spans remaining width
        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.title_icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Content area: always with scrollbars when needed
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setFrameShape(QFrame.NoFrame)
        # Start with scrollbars off to prevent flicker on first animation
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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

        # Set minimum width to ensure visibility
        self.setMinimumWidth(150)

        # Setup animation with ease-out curve
        self.toggle_animation = QParallelAnimationGroup()

        max_height_anim = QPropertyAnimation(
            self.content_area, b"maximumHeight"
        )
        max_height_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggle_animation.addAnimation(max_height_anim)

        min_height_anim = QPropertyAnimation(
            self.content_area, b"minimumHeight"
        )
        min_height_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggle_animation.addAnimation(min_height_anim)

        # Connect signals
        self.toggle_button.clicked.connect(self._toggle_content)
        self.toggle_animation.finished.connect(self._on_animation_finished)

        # Set title icon if provided
        if title_icon is not None:
            self.set_title_icon(title_icon)

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

    def set_content_layout(self, content_layout: QLayout) -> None:
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

    def set_title_icon(self, icon: Union[QIcon, str, None]) -> None:
        """Set an icon to display before the title.

        Args:
            icon: The icon to display. Can be:
                - A QIcon instance
                - A string icon name (resolved via fxicons.get_icon)
                - None to remove the icon

        Examples:
            >>> collapsible = FXCollapsibleWidget(title="Settings")
            >>> collapsible.set_title_icon("settings")  # Using icon name
            >>> collapsible.set_title_icon(QIcon("path/to/icon.png"))  # Using QIcon
            >>> collapsible.set_title_icon(None)  # Remove icon
        """
        if icon is None:
            self._title_icon = None
            self.title_icon_label.setVisible(False)
            self.title_icon_label.setPixmap(QIcon().pixmap(16, 16))
        elif isinstance(icon, str):
            self._title_icon = fxicons.get_icon(icon)
            self.title_icon_label.setPixmap(self._title_icon.pixmap(16, 16))
            self.title_icon_label.setVisible(True)
        elif isinstance(icon, QIcon):
            self._title_icon = icon
            self.title_icon_label.setPixmap(icon.pixmap(16, 16))
            self.title_icon_label.setVisible(True)

    def get_title_icon(self) -> Optional[QIcon]:
        """Get the current title icon.

        Returns:
            The current title icon, or None if no icon is set.
        """
        return self._title_icon

    def set_title(self, title: str) -> None:
        """Set the title text.

        Args:
            title: The title text to display.
        """
        self._title = str(title)
        self.title_label.setText(self._title)

    def get_title(self) -> str:
        """Get the current title text.

        Returns:
            The current title text.
        """
        return self._title
