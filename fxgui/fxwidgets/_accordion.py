"""Multi-section collapsible widget."""

from typing import List, Optional, Union

from qtpy.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    Signal,
)
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from fxgui import fxicons, fxstyle


class FXAccordionSection(fxstyle.FXThemeAware, QWidget):
    """A single section of the accordion.

    Args:
        parent: Parent widget.
        title: Section title.
        icon: Optional icon name for the section header.
        animation_duration: Duration of expand/collapse animation in ms.

    Signals:
        expanded: Emitted when the section is expanded.
        collapsed: Emitted when the section is collapsed.
    """

    expanded = Signal()
    collapsed = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        icon: Optional[str] = None,
        animation_duration: int = 150,
    ):
        super().__init__(parent)

        self._title = title
        self._icon_name = icon
        self._animation_duration = animation_duration
        self._is_expanded = False
        self._has_been_expanded = False
        self._content_height = 0

        # Header
        self._header = QFrame()
        self._header.setFrameShape(QFrame.StyledPanel)
        self._header.setCursor(Qt.PointingHandCursor)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        # Toggle button
        self._toggle_btn = QToolButton()
        self._toggle_btn.setStyleSheet(
            "QToolButton { border: none; background: transparent; }"
        )
        fxicons.set_icon(self._toggle_btn, "chevron_right")
        self._toggle_btn.setCheckable(True)
        header_layout.addWidget(self._toggle_btn)

        # Section icon
        if icon:
            self._icon_label = QLabel()
            self._icon_label.setPixmap(fxicons.get_icon(icon).pixmap(16, 16))
            self._icon_label.setStyleSheet("background: transparent;")
            header_layout.addWidget(self._icon_label)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(
            "background: transparent; font-weight: bold;"
        )
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        # Content area
        self._content_area = QScrollArea()
        self._content_area.setWidgetResizable(True)
        self._content_area.setFrameShape(QFrame.NoFrame)
        # Start with scrollbars off to prevent flicker on first animation
        self._content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content_area.setMaximumHeight(0)
        self._content_area.setMinimumHeight(0)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._header)
        main_layout.addWidget(self._content_area)

        # Animation - use QParallelAnimationGroup like FXCollapsibleWidget
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

        # Connections
        self._toggle_btn.clicked.connect(self._on_toggle)
        self._header.mousePressEvent = lambda e: self._on_toggle()
        self._animation.finished.connect(self._on_animation_finished)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @property
    def is_expanded(self) -> bool:
        """Return whether the section is expanded."""
        return self._is_expanded

    @property
    def title(self) -> str:
        """Return the section title."""
        return self._title

    def set_content_widget(self, widget: QWidget) -> None:
        """Set the content widget for this section.

        Args:
            widget: The widget to display when expanded.
        """
        self._content_area.setWidget(widget)
        # Calculate content height
        self._content_height = min(300, widget.sizeHint().height())

    def set_content_layout(self, layout) -> None:
        """Set the content layout for this section.

        Args:
            layout: The layout to use for content.
        """
        container = QWidget()
        container.setLayout(layout)
        self.set_content_widget(container)

    def expand(self, animate: bool = True) -> None:
        """Expand the section.

        Args:
            animate: Whether to animate the expansion.
        """
        if self._is_expanded:
            return

        self._is_expanded = True
        self._toggle_btn.setChecked(True)
        fxicons.set_icon(self._toggle_btn, "expand_more")

        # Update header background based on expanded state
        self._apply_theme_styles()

        # First time expansion: measure content
        if not self._has_been_expanded:
            if self._content_area.widget():
                self._content_height = min(
                    300, self._content_area.widget().sizeHint().height()
                )
            self._has_been_expanded = True

        if animate:
            self._animation.stop()
            for i in range(self._animation.animationCount()):
                anim = self._animation.animationAt(i)
                anim.setDuration(self._animation_duration)
                anim.setStartValue(0)
                anim.setEndValue(self._content_height)
            self._animation.setDirection(QAbstractAnimation.Forward)
            self._animation.start()
        else:
            self._content_area.setMinimumHeight(self._content_height)
            self._content_area.setMaximumHeight(self._content_height)

        self.expanded.emit()

    def collapse(self, animate: bool = True) -> None:
        """Collapse the section.

        Args:
            animate: Whether to animate the collapse.
        """
        if not self._is_expanded:
            return

        self._is_expanded = False
        self._toggle_btn.setChecked(False)
        fxicons.set_icon(self._toggle_btn, "chevron_right")

        # Update header background based on expanded state
        self._apply_theme_styles()

        if animate:
            self._animation.stop()
            for i in range(self._animation.animationCount()):
                anim = self._animation.animationAt(i)
                anim.setDuration(self._animation_duration)
                anim.setStartValue(0)
                anim.setEndValue(self._content_height)
            self._animation.setDirection(QAbstractAnimation.Backward)
            self._animation.start()
        else:
            self._content_area.setMinimumHeight(0)
            self._content_area.setMaximumHeight(0)

        self.collapsed.emit()

    def toggle(self) -> None:
        """Toggle the section state."""
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()

    def _on_toggle(self) -> None:
        """Handle toggle button click."""
        self.toggle()

    def _on_animation_finished(self) -> None:
        """Handle animation completion."""
        if not self._is_expanded:
            # When collapsed, ensure content is hidden and scrollbars off
            self._content_area.setMinimumHeight(0)
            self._content_area.setMaximumHeight(0)
            self._content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._content_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff
            )
        else:
            # When expanded, enable scrollbars as needed
            self._content_area.setMinimumHeight(self._content_height)
            self._content_area.setMaximumHeight(self._content_height)

            # Enable scrollbars only if content exceeds visible area
            if self._content_area.widget():
                widget_height = self._content_area.widget().sizeHint().height()
                v_policy = (
                    Qt.ScrollBarAsNeeded
                    if widget_height > self._content_height
                    else Qt.ScrollBarAlwaysOff
                )
                self._content_area.setVerticalScrollBarPolicy(v_policy)
                self._content_area.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarAlwaysOff
                )

    def _apply_theme_styles(self) -> None:
        """Apply theme-aware styling to the header."""
        colors = fxstyle.get_theme_colors()
        if self._is_expanded:
            # Use hover state color when expanded
            self._header.setStyleSheet(
                f"QFrame {{ background-color: {colors['state_hover']}; }}"
            )
        else:
            # Use default (transparent) when collapsed
            self._header.setStyleSheet("")


class FXAccordion(QWidget):
    """A multi-section collapsible accordion widget.

    Like FXCollapsibleWidget but for multiple mutually-exclusive sections
    (only one section open at a time by default).

    Args:
        parent: Parent widget.
        exclusive: If True, only one section can be open at a time.
        animation_duration: Duration of expand/collapse animation in ms.

    Signals:
        section_expanded: Emitted when a section is expanded (section index).
        section_collapsed: Emitted when a section is collapsed (section index).

    Examples:
        >>> accordion = FXAccordion()
        >>> accordion.add_section("General", general_content)
        >>> accordion.add_section("Advanced", advanced_content)
        >>> accordion.add_section("Settings", settings_content)
    """

    section_expanded = Signal(int)
    section_collapsed = Signal(int)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        exclusive: bool = True,
        animation_duration: int = 150,
    ):
        super().__init__(parent)

        self._exclusive = exclusive
        self._animation_duration = animation_duration
        self._sections: List[FXAccordionSection] = []

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self._layout.addStretch()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def add_section(
        self,
        title: str,
        content: Optional[Union[QWidget, QVBoxLayout]] = None,
        icon: Optional[str] = None,
    ) -> FXAccordionSection:
        """Add a new section to the accordion.

        Args:
            title: Section title.
            content: Content widget or layout.
            icon: Optional icon name for the header.

        Returns:
            The created FXAccordionSection.
        """
        section = FXAccordionSection(
            self, title, icon, self._animation_duration
        )

        if content:
            if isinstance(content, QWidget):
                section.set_content_widget(content)
            else:
                section.set_content_layout(content)

        # Connect signals
        index = len(self._sections)
        section.expanded.connect(
            lambda idx=index: self._on_section_expanded(idx)
        )
        section.collapsed.connect(
            lambda idx=index: self._on_section_collapsed(idx)
        )

        self._sections.append(section)

        # Insert before stretch
        self._layout.insertWidget(self._layout.count() - 1, section)

        return section

    def remove_section(self, index: int) -> None:
        """Remove a section by index.

        Args:
            index: The section index to remove.
        """
        if 0 <= index < len(self._sections):
            section = self._sections.pop(index)
            self._layout.removeWidget(section)
            section.deleteLater()

    def get_section(self, index: int) -> Optional[FXAccordionSection]:
        """Get a section by index.

        Args:
            index: The section index.

        Returns:
            The FXAccordionSection or None if index is invalid.
        """
        if 0 <= index < len(self._sections):
            return self._sections[index]
        return None

    def expand_section(self, index: int) -> None:
        """Expand a section by index.

        Args:
            index: The section index to expand.
        """
        if 0 <= index < len(self._sections):
            self._sections[index].expand()

    def collapse_section(self, index: int) -> None:
        """Collapse a section by index.

        Args:
            index: The section index to collapse.
        """
        if 0 <= index < len(self._sections):
            self._sections[index].collapse()

    def collapse_all(self) -> None:
        """Collapse all sections."""
        for section in self._sections:
            section.collapse()

    def expand_all(self) -> None:
        """Expand all sections (only works if not exclusive)."""
        if not self._exclusive:
            for section in self._sections:
                section.expand()

    def _on_section_expanded(self, index: int) -> None:
        """Handle section expansion."""
        if self._exclusive:
            # Collapse all other sections
            for i, section in enumerate(self._sections):
                if i != index and section.is_expanded:
                    section.collapse()

        self.section_expanded.emit(index)

    def _on_section_collapsed(self, index: int) -> None:
        """Handle section collapse."""
        self.section_collapsed.emit(index)

    def __len__(self) -> int:
        """Return the number of sections."""
        return len(self._sections)

    def __iter__(self):
        """Iterate over sections."""
        return iter(self._sections)


def example() -> None:
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXAccordion Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    accordion = FXAccordion(exclusive=True)

    # Section 1
    section1_content = QLabel("Content of Section 1")
    section1_content.setStyleSheet("padding: 8px;")
    accordion.add_section("Section 1", section1_content, icon="folder")

    # Section 2
    section2_content = QLabel("Content of Section 2")
    section2_content.setStyleSheet("padding: 8px;")
    accordion.add_section("Section 2", section2_content, icon="settings")

    # Section 3
    section3_content = QLabel("Content of Section 3")
    section3_content.setStyleSheet("padding: 8px;")
    accordion.add_section("Section 3", section3_content, icon="info")

    layout.addWidget(accordion)

    window.resize(400, 300)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
