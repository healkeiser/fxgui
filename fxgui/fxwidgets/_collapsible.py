"""Collapsible widget implementation."""

from typing import Optional

from qtpy.QtCore import (
    QAbstractAnimation,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
)
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
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

    Examples:
        >>> from qtpy.QtWidgets import QLabel, QVBoxLayout
        >>> collapsible = FXCollapsibleWidget(title="Settings")
        >>> layout = QVBoxLayout()
        >>> layout.addWidget(QLabel("Option 1"))
        >>> layout.addWidget(QLabel("Option 2"))
        >>> collapsible.setContentLayout(layout)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        animation_duration: int = 200,
        max_content_height: int = 300,
    ):
        """Initialize the collapsible section."""
        super().__init__(parent=parent)

        # Store properties
        self.animation_duration = animation_duration
        self.max_content_height = max_content_height
        self._title = str(title)
        self._is_expanded = False
        self._has_been_expanded = False
        self._content_height = 0

        # Create fixed header layout
        self.header_widget = QWidget()
        self.header_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )

        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setIcon(fxicons.get_icon("chevron_right"))
        self.toggle_button.setProperty("icon_name", "chevron_right")
        self.toggle_button.setText(self._title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)

        # Button won't get smaller than this
        button_width = max(120, self.toggle_button.sizeHint().width())
        self.toggle_button.setMinimumWidth(button_width)
        self.toggle_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Header line
        self.header_line = QFrame()
        self.header_line.setFrameShape(QFrame.HLine)
        self.header_line.setFrameShadow(QFrame.Sunken)
        self.header_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.header_line)

        # Content area: always with scrollbars when needed
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
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

        # Set minimum width to ensure button visibility
        min_width = max(150, button_width + 30)
        self.setMinimumWidth(min_width)

        # Setup animation
        self.toggle_animation = QParallelAnimationGroup()
        self.toggle_animation.addAnimation(
            QPropertyAnimation(self.content_area, b"maximumHeight")
        )
        self.toggle_animation.addAnimation(
            QPropertyAnimation(self.content_area, b"minimumHeight")
        )

        # Connect signals
        self.toggle_button.clicked.connect(self._toggle_content)
        self.toggle_animation.finished.connect(self._on_animation_finished)

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

    def setContentLayout(self, content_layout: QLayout) -> None:
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
