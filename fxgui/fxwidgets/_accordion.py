"""Multi-section collapsible widget (accordion)."""

# Built-in
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

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self._layout.addStretch()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def exclusive(self) -> bool:
        """Return whether only one section can be open at a time."""
        return self._exclusive

    def set_exclusive(self, value: bool) -> None:
        """Set whether only one section can be open at a time."""
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

        if content is not None:
            if isinstance(content, QWidget):
                section.set_content_widget(content)
            else:
                section.set_content_layout(content)

        # Bound methods, not lambdas holding `self`: that cycle lets Python's
        # collector delete a shown accordion mid-event.
        section.expanded.connect(self._on_section_expanded)
        section.collapsed.connect(self._on_section_collapsed)

        self._sections.append(section)

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
        """Expand all sections.

        Raises:
            RuntimeError: The accordion is exclusive.
        """
        if self._exclusive:
            raise RuntimeError("an exclusive accordion opens one section")
        for section in self._sections:
            section.expand()

    def _index_of(self, section: FXCollapsibleWidget) -> int:
        """Return the section's current index, or -1 once removed."""
        try:
            return self._sections.index(section)
        except ValueError:
            return -1

    def _on_section_expanded(self) -> None:
        """Collapse the others when exclusive, and say which opened."""
        # Looked up now: removals shift the indexes.
        index = self._index_of(self.sender())
        if index < 0:
            return
        if self._exclusive:
            # Collapse all other sections
            for i, section in enumerate(self._sections):
                if i != index and section.is_expanded():
                    section.collapse()

        self.section_expanded.emit(index)

    def _on_section_collapsed(self) -> None:
        """Say which section closed."""
        index = self._index_of(self.sender())
        if index >= 0:
            self.section_collapsed.emit(index)

    def __len__(self) -> int:
        """Return the number of sections."""
        return len(self._sections)

    def __iter__(self):
        """Iterate over sections."""
        return iter(self._sections)
