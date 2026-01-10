"""Tag/chip input widget."""

# Built-in
from typing import List, Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


class FXTagChip(fxstyle.FXThemeAware, QFrame):
    """A single removable tag chip.

    Args:
        text: The tag text.
        parent: Parent widget.
        removable: Whether the chip can be removed.

    Signals:
        removed: Emitted when the remove button is clicked.
    """

    removed = Signal(str)

    def __init__(
        self,
        text: str,
        parent: Optional[QWidget] = None,
        removable: bool = True,
    ):
        super().__init__(parent)
        self._text = text
        self._removable = removable

        # Setup styling
        self.setFrameShape(QFrame.StyledPanel)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4 if removable else 8, 2)
        layout.setSpacing(4)

        # Tag label
        self.label = QLabel(text)
        layout.addWidget(self.label)

        # Remove button
        self.remove_button = None
        if removable:
            self.remove_button = QPushButton()
            self.remove_button.setFixedSize(16, 16)
            self.remove_button.setFlat(True)
            self.remove_button.setCursor(Qt.PointingHandCursor)
            self.remove_button.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
            """
            )
            self.remove_button.clicked.connect(self._on_remove)
            layout.addWidget(self.remove_button)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        self.setStyleSheet(
            f"""
            FXTagChip {{
                background-color: {self.theme.accent_primary};
                border-radius: 12px;
                padding: 2px 4px;
            }}
        """
        )

        self.label.setStyleSheet(
            """
            QLabel {
                color: white;
                background: transparent;
                font-size: 11px;
            }
        """
        )

        if self.remove_button:
            fxicons.set_icon(self.remove_button, "close", color="#ffffff")

    @property
    def text(self) -> str:
        """Return the tag text."""
        return self._text

    def _on_remove(self) -> None:
        """Handle remove button click."""
        self.removed.emit(self._text)


class FXTagInput(fxstyle.FXThemeAware, QWidget):
    """A styled input widget that displays tags as removable chips.

    This widget provides an input field where users can type and press
    Enter to add tags. Tags are displayed as styled chips that can be
    removed by clicking the × button.

    Args:
        parent: Parent widget.
        placeholder: Placeholder text for the input field.
        max_tags: Maximum number of tags allowed (0 = unlimited).
        allow_duplicates: Whether duplicate tags are allowed.

    Signals:
        tags_changed: Emitted when tags are added or removed.
        tag_added: Emitted when a single tag is added.
        tag_removed: Emitted when a single tag is removed.

    Examples:
        >>> tag_input = FXTagInput(placeholder="Add tags...")
        >>> tag_input.tags_changed.connect(lambda tags: print(f"Tags: {tags}"))
        >>> tag_input.add_tag("python")
        >>> tag_input.add_tag("qt")
    """

    tags_changed = Signal(list)
    tag_added = Signal(str)
    tag_removed = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Add tag and press Enter...",
        max_tags: int = 0,
        allow_duplicates: bool = False,
    ):
        super().__init__(parent)

        self._tags: List[str] = []
        self._max_tags = max_tags
        self._allow_duplicates = allow_duplicates

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Tags container with scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setMaximumHeight(80)

        # Tags container widget
        self._tags_container = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(4)
        self._tags_layout.addStretch()

        self._scroll_area.setWidget(self._tags_container)

        # Input field
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.returnPressed.connect(self._on_return_pressed)

        main_layout.addWidget(self._scroll_area)
        main_layout.addWidget(self._input)

        # Hide scroll area initially if no tags
        self._scroll_area.setVisible(False)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        self._input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {self.theme.surface_sunken};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 6px 8px;
            }}
            QLineEdit:focus {{
                border-color: {self.theme.accent_primary};
            }}
        """
        )

    @property
    def tags(self) -> List[str]:
        """Return the list of current tags."""
        return self._tags.copy()

    def add_tag(self, tag: str) -> bool:
        """Add a tag to the input.

        Args:
            tag: The tag text to add.

        Returns:
            True if the tag was added, False otherwise.
        """
        tag = tag.strip()
        if not tag:
            return False

        if not self._allow_duplicates and tag in self._tags:
            return False

        if self._max_tags > 0 and len(self._tags) >= self._max_tags:
            return False

        self._tags.append(tag)

        # Create chip
        chip = FXTagChip(tag, self._tags_container)
        chip.removed.connect(self.remove_tag)

        # Insert before stretch
        self._tags_layout.insertWidget(self._tags_layout.count() - 1, chip)

        # Show scroll area
        self._scroll_area.setVisible(True)

        # Emit signals
        self.tag_added.emit(tag)
        self.tags_changed.emit(self._tags)

        return True

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the input.

        Args:
            tag: The tag text to remove.

        Returns:
            True if the tag was removed, False otherwise.
        """
        if tag not in self._tags:
            return False

        self._tags.remove(tag)

        # Find and remove the chip
        for i in range(self._tags_layout.count()):
            item = self._tags_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, FXTagChip) and widget.text == tag:
                    widget.deleteLater()
                    break

        # Hide scroll area if no tags
        if not self._tags:
            self._scroll_area.setVisible(False)

        # Emit signals
        self.tag_removed.emit(tag)
        self.tags_changed.emit(self._tags)

        return True

    def clear_tags(self) -> None:
        """Remove all tags."""
        for tag in self._tags.copy():
            self.remove_tag(tag)

    def set_tags(self, tags: List[str]) -> None:
        """Set the tags, replacing any existing tags.

        Args:
            tags: List of tag strings to set.
        """
        self.clear_tags()
        for tag in tags:
            self.add_tag(tag)

    def _on_return_pressed(self) -> None:
        """Handle Enter key press in input field."""
        text = self._input.text().strip()
        if text and self.add_tag(text):
            self._input.clear()


def example() -> None:
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXTagInput Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)
    tag_input = FXTagInput(placeholder="Add tags...", max_tags=5)
    tag_input.tags_changed.connect(lambda tags: print(f"Tags: {tags}"))
    layout.addWidget(tag_input)
    window.setLayout(layout)
    window.resize(400, 200)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
