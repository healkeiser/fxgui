"""Collapsible widget implementation."""

# Built-in
from typing import Optional, Union

# Third-party
from qtpy.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
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
from fxgui import fxicons, fxstyle


class FXCollapsibleWidget(fxstyle.FXThemeAware, QWidget):
    """A widget that can expand or collapse its content.

    The widget consists of a header with a toggle button and a content area
    that can be shown or hidden with an animation effect.

    Args:
        parent: Parent widget.
        title: Title displayed in the header.
        icon: Optional icon to display before the title. Can be a
            QIcon, an icon name string (for fxicons), or None.
        animation_duration: Duration of expand/collapse animation in ms.
        max_content_height: Maximum height for content area when
            expanded (0 = no limit).

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
        self._title = str(title)
        self._icon: Optional[QIcon] = None
        self._icon_name: Optional[str] = None
        self._is_expanded = False
        self._has_been_expanded = False
        self._content_height = 0

        # Create fixed header layout
        self._header = QFrame()
        self._header.setFrameShape(QFrame.StyledPanel)
        self._header.setFrameShadow(QFrame.Raised)
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Make header clickable
        self._header.mousePressEvent = lambda e: self.toggle()

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(8)

        # Toggle button (chevron icon)
        self._toggle_btn = QToolButton()
        self._toggle_btn.setStyleSheet(
            "QToolButton { border: none; background: transparent; }"
        )
        fxicons.set_icon(self._toggle_btn, "chevron_right")
        self._toggle_btn.setProperty("icon_name", "chevron_right")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(False)
        self._toggle_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Title icon label (optional)
        self._icon_label = QLabel()
        self._icon_label.setStyleSheet("background: transparent;")
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setVisible(False)

        # Title label
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet(
            "background: transparent; font-weight: bold;"
        )
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

        # Setup animation with ease-out curve
        self._animation = QParallelAnimationGroup()

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
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        self._animation.finished.connect(self._on_animation_finished)

        # Set icon if provided
        if icon is not None:
            self.set_icon(icon)

    @property
    def is_expanded(self) -> bool:
        """Return whether the widget is expanded."""
        return self._is_expanded

    @property
    def title(self) -> str:
        """Return the title text."""
        return self._title

    @property
    def animation_duration(self) -> int:
        """Return the animation duration in milliseconds."""
        return self._animation_duration

    @animation_duration.setter
    def animation_duration(self, value: int) -> None:
        """Set the animation duration in milliseconds."""
        self._animation_duration = value

    @property
    def max_content_height(self) -> int:
        """Return the maximum content height."""
        return self._max_content_height

    @max_content_height.setter
    def max_content_height(self, value: int) -> None:
        """Set the maximum content height."""
        self._max_content_height = value

    def expand(self, animate: bool = True) -> None:
        """Expand the widget to show content.

        Args:
            animate: Whether to animate the expansion.
        """
        if self._is_expanded:
            return

        self._is_expanded = True
        self._toggle_btn.setChecked(True)
        fxicons.set_icon(self._toggle_btn, "expand_more")
        self._toggle_btn.setProperty("icon_name", "expand_more")

        # Update header background based on expanded state
        self._on_theme_changed()

        # First time expansion: measure content
        if not self._has_been_expanded:
            if self._content_area.widget():
                self._content_height = (
                    self._content_area.widget().sizeHint().height()
                )
            self._has_been_expanded = True

        target_height = self._calculate_content_height()

        if animate:
            self._animation.stop()
            for i in range(self._animation.animationCount()):
                anim = self._animation.animationAt(i)
                anim.setDuration(self._animation_duration)
                anim.setStartValue(0)
                anim.setEndValue(target_height)
            self._animation.setDirection(QAbstractAnimation.Forward)
            self._animation.start()
        else:
            self._content_area.setMinimumHeight(target_height)
            self._content_area.setMaximumHeight(target_height)
            self._on_animation_finished()

        self.expanded.emit()

    def collapse(self, animate: bool = True) -> None:
        """Collapse the widget to hide content.

        Args:
            animate: Whether to animate the collapse.
        """
        if not self._is_expanded:
            return

        self._is_expanded = False
        self._toggle_btn.setChecked(False)
        fxicons.set_icon(self._toggle_btn, "chevron_right")
        self._toggle_btn.setProperty("icon_name", "chevron_right")

        # Update header background based on expanded state
        self._on_theme_changed()

        if animate:
            self._animation.stop()
            for i in range(self._animation.animationCount()):
                anim = self._animation.animationAt(i)
                anim.setDuration(self._animation_duration)
                anim.setStartValue(0)
                anim.setEndValue(self._calculate_content_height())
            self._animation.setDirection(QAbstractAnimation.Backward)
            self._animation.start()
        else:
            self._content_area.setMinimumHeight(0)
            self._content_area.setMaximumHeight(0)
            self._on_animation_finished()

        self.collapsed.emit()

    def toggle(self) -> None:
        """Toggle the expanded/collapsed state."""
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()

    def _on_toggle_clicked(self, checked: bool) -> None:
        """Handle toggle button click."""
        if checked:
            self.expand()
        else:
            self.collapse()

    def _calculate_content_height(self) -> int:
        """Calculate appropriate content height based on constraints."""
        if not self._content_area.widget():
            return 0

        # Get raw content height
        content_height = self._content_height

        # Apply max_content_height if specified
        if self._max_content_height > 0:
            content_height = min(content_height, self._max_content_height)

        return content_height

    def _on_animation_finished(self) -> None:
        """Handle animation completion."""
        if not self._is_expanded:
            # When collapsed, ensure content is hidden
            self._content_area.setMinimumHeight(0)
            self._content_area.setMaximumHeight(0)
            self._content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._content_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff
            )
        else:
            # When expanded, ensure scrollbars appear as needed
            height = self._calculate_content_height()
            self._content_area.setMinimumHeight(height)
            self._content_area.setMaximumHeight(height)

            # Enable scrollbars only if content exceeds visible area
            if self._content_area.widget():
                widget_width = self._content_area.widget().sizeHint().width()
                widget_height = self._content_area.widget().sizeHint().height()

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

                self._content_area.setHorizontalScrollBarPolicy(h_policy)
                self._content_area.setVerticalScrollBarPolicy(v_policy)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        if self._is_expanded:
            # Use hover state color when expanded
            self._header.setStyleSheet(
                f"QFrame {{ background-color: {self.theme.state_hover}; }}"
            )
        else:
            # Use default (transparent) when collapsed
            self._header.setStyleSheet("")

        # Update title icon with new theme colors
        if self._icon_name:
            self._icon = fxicons.get_icon(self._icon_name)
            self._icon_label.setPixmap(self._icon.pixmap(16, 16))

    def set_content_layout(self, content_layout: QLayout) -> None:
        """Set the layout for the content area.

        Args:
            content_layout: The layout to set for the content area.
        """
        # Create content widget
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        self._content_area.setWidget(content_widget)

        # Measure content height
        self._content_height = content_widget.sizeHint().height()

        # Initially collapsed
        self._content_area.setMaximumHeight(0)
        self._content_area.setMinimumHeight(0)

    def set_content_widget(self, widget: QWidget) -> None:
        """Set the content widget directly.

        Args:
            widget: The widget to display when expanded.
        """
        self._content_area.setWidget(widget)
        # Calculate content height
        self._content_height = widget.sizeHint().height()

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
        if icon is None:
            self._icon = None
            self._icon_name = None
            self._icon_label.setVisible(False)
            self._icon_label.setPixmap(QIcon().pixmap(16, 16))
        elif isinstance(icon, str):
            self._icon_name = icon
            self._icon = fxicons.get_icon(icon)
            self._icon_label.setPixmap(self._icon.pixmap(16, 16))
            self._icon_label.setVisible(True)
        elif isinstance(icon, QIcon):
            self._icon = icon
            self._icon_name = None
            self._icon_label.setPixmap(icon.pixmap(16, 16))
            self._icon_label.setVisible(True)

    def get_icon(self) -> Optional[QIcon]:
        """Get the current icon.

        Returns:
            The current icon, or None if no icon is set.
        """
        return self._icon

    def set_title(self, title: str) -> None:
        """Set the title text.

        Args:
            title: The title text to display.
        """
        self._title = str(title)
        self._title_label.setText(self._title)

    def get_title(self) -> str:
        """Get the current title text.

        Returns:
            The current title text.
        """
        return self._title

    # Backward compatibility aliases
    @property
    def header_widget(self) -> QFrame:
        """Return the header widget (deprecated, use _header)."""
        return self._header

    @property
    def content_area(self) -> QScrollArea:
        """Return the content area (deprecated, use _content_area)."""
        return self._content_area

    @property
    def toggle_button(self) -> QToolButton:
        """Return the toggle button (deprecated, use _toggle_btn)."""
        return self._toggle_btn

    @property
    def title_label(self) -> QLabel:
        """Return the title label (deprecated, use _title_label)."""
        return self._title_label

    @property
    def title_icon_label(self) -> QLabel:
        """Return the icon label (deprecated, use _icon_label)."""
        return self._icon_label

    def set_title_icon(self, icon: Union[QIcon, str, None]) -> None:
        """Set the title icon (deprecated, use set_icon)."""
        self.set_icon(icon)

    def get_title_icon(self) -> Optional[QIcon]:
        """Get the title icon (deprecated, use get_icon)."""
        return self.get_icon()


def example() -> None:
    import sys
    from qtpy.QtWidgets import QPushButton, QCheckBox
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXCollapsibleWidget Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Basic collapsible section
    collapsible1 = FXCollapsibleWidget(title="Basic Settings")
    content_layout1 = QVBoxLayout()
    content_layout1.addWidget(QLabel("Option 1"))
    content_layout1.addWidget(QLabel("Option 2"))
    content_layout1.addWidget(QCheckBox("Enable feature"))
    collapsible1.set_content_layout(content_layout1)
    layout.addWidget(collapsible1)

    # Collapsible with icon
    collapsible2 = FXCollapsibleWidget(title="Advanced Settings", icon="settings")
    content_layout2 = QVBoxLayout()
    content_layout2.addWidget(QLabel("Advanced option 1"))
    content_layout2.addWidget(QLabel("Advanced option 2"))
    content_layout2.addWidget(QPushButton("Apply"))
    collapsible2.set_content_layout(content_layout2)
    layout.addWidget(collapsible2)

    # Collapsible with more content
    collapsible3 = FXCollapsibleWidget(
        title="Info", icon="info", max_content_height=150
    )
    content_layout3 = QVBoxLayout()
    for i in range(10):
        content_layout3.addWidget(QLabel(f"Info line {i + 1}"))
    collapsible3.set_content_layout(content_layout3)
    layout.addWidget(collapsible3)

    layout.addStretch()

    window.resize(400, 400)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
