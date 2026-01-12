"""Multi-section collapsible widget (accordion)."""

# Built-in
import warnings
from typing import List, Optional, Union

# Third-party
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui.fxwidgets._collapsible import FXCollapsibleWidget


class FXAccordion(QWidget):
    """A multi-section collapsible accordion widget.

    Uses FXCollapsibleWidget for each section. By default, only one section
    can be open at a time (exclusive mode).

    Args:
        parent: Parent widget.
        exclusive: If True, only one section can be open at a time.
        animation_duration: Duration of expand/collapse animation in ms.

    Signals:
        section_expanded: Emitted when a section is expanded (section index).
        section_collapsed: Emitted when a section is collapsed (section index).

    Examples:
        >>> accordion = FXAccordion()
        >>> accordion.add_section("General", general_content, icon="settings")
        >>> accordion.add_section("Advanced", advanced_content, icon="tune")
        >>> accordion.add_section("Info", info_content, icon="info")
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
        self._sections: List[FXCollapsibleWidget] = []

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self._layout.addStretch()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    @property
    def exclusive(self) -> bool:
        """Return whether accordion is in exclusive mode."""
        return self._exclusive

    @exclusive.setter
    def exclusive(self, value: bool) -> None:
        """Set exclusive mode."""
        self._exclusive = value

    def add_section(
        self,
        title: str,
        content: Optional[Union[QWidget, QLayout]] = None,
        icon: Optional[str] = None,
    ) -> FXCollapsibleWidget:
        """Add a new section to the accordion.

        Args:
            title: Section title.
            content: Content widget or layout.
            icon: Optional icon name for the header.

        Returns:
            The created FXCollapsibleWidget.
        """
        section = FXCollapsibleWidget(
            parent=self,
            title=title,
            icon=icon,
            animation_duration=self._animation_duration,
        )

        if content:
            if isinstance(content, QWidget):
                section.set_content_widget(content)
            else:
                section.set_content_layout(content)

        # Connect signals
        index = len(self._sections)
        section.expanded.connect(lambda idx=index: self._on_section_expanded(idx))
        section.collapsed.connect(lambda idx=index: self._on_section_collapsed(idx))

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

    def get_section(self, index: int) -> Optional[FXCollapsibleWidget]:
        """Get a section by index.

        Args:
            index: The section index.

        Returns:
            The FXCollapsibleWidget or None if index is invalid.
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


# Backward compatibility alias
class FXAccordionSection(FXCollapsibleWidget):
    """Deprecated: Use FXCollapsibleWidget instead.

    This class is kept for backward compatibility only.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        icon: Optional[str] = None,
        animation_duration: int = 150,
    ):
        warnings.warn(
            "FXAccordionSection is deprecated. Use FXCollapsibleWidget instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            parent=parent,
            title=title,
            icon=icon,
            animation_duration=animation_duration,
        )


def example() -> None:
    import sys
    from qtpy.QtWidgets import QLabel, QVBoxLayout
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
