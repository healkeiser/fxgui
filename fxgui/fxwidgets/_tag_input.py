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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._flow_layout import FXFlowLayout


class FXTagChip(QFrame):
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

        self.setFrameShape(QFrame.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4 if removable else 8, 2)
        layout.setSpacing(fxstyle.PANE_GAP)

        self.label = QLabel(text)
        layout.addWidget(self.label)

        self.remove_button = None
        if removable:
            self.remove_button = QPushButton()
            self.remove_button.setFixedSize(16, 16)
            self.remove_button.setFlat(True)
            self.remove_button.setCursor(Qt.PointingHandCursor)
            self.remove_button.clicked.connect(self._on_remove)
            layout.addWidget(self.remove_button)
            fxicons.set_icon(
                self.remove_button, "close", color="icon_on_accent_primary")

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def text(self) -> str:
        """Return the tag text."""
        return self._text

    def _on_remove(self) -> None:
        """Handle remove button click."""
        self.removed.emit(self._text)


class FXTagInput(QWidget):
    """A field whose Enter turns the text into a chip; a chip's x removes it.

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

        # The chips are the one record of the tags, in order.
        self._chips: List[FXTagChip] = []
        self._max_tags = max_tags
        self._allow_duplicates = allow_duplicates

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(fxstyle.PANE_GAP)

        # Chips wrap onto new lines, so the field grows taller, never wider.
        self._tags_container = QWidget()
        self._tags_layout = FXFlowLayout(self._tags_container)

        self._input = QLineEdit()
        self._input.setObjectName("fx_tag_input_field")
        self._input.setPlaceholderText(placeholder)
        self._input.returnPressed.connect(self._on_return_pressed)

        main_layout.addWidget(self._tags_container)
        main_layout.addWidget(self._input)

        self._tags_container.setVisible(False)

    def tags(self) -> List[str]:
        """Return the current tags, in order."""
        return [chip.text() for chip in self._chips]

    def add_tag(self, tag: str) -> bool:
        """Add `tag`; return False for a blank, a duplicate or one too many."""
        if not self._add(tag):
            return False
        self.tags_changed.emit(self.tags())
        return True

    def remove_tag(self, tag: str) -> bool:
        """Remove the first chip reading `tag`; return whether one did."""
        for chip in self._chips:
            if chip.text() == tag:
                self._drop(chip)
                self.tags_changed.emit(self.tags())
                return True
        return False

    def clear_tags(self) -> None:
        """Remove all tags."""
        self.set_tags([])

    def set_tags(self, tags: List[str]) -> None:
        """Replace the tags, saying `tags_changed` once."""
        before = self.tags()
        for chip in list(self._chips):
            self._drop(chip)
        for tag in tags:
            self._add(tag)
        if self.tags() != before:
            self.tags_changed.emit(self.tags())

    def _add(self, tag: str) -> bool:
        """Add a chip for `tag` if it is allowed, and say `tag_added`."""
        tag = tag.strip()
        tags = self.tags()
        if (
            not tag
            or (not self._allow_duplicates and tag in tags)
            or (self._max_tags > 0 and len(tags) >= self._max_tags)
        ):
            return False
        chip = FXTagChip(tag, self._tags_container)
        chip.removed.connect(self._on_chip_removed)
        self._chips.append(chip)
        self._tags_layout.addWidget(chip)
        self._tags_container.setVisible(True)
        self.tag_added.emit(tag)
        return True

    def _drop(self, chip: FXTagChip) -> None:
        """Take `chip` out of the layout and delete it; say `tag_removed`."""
        self._chips.remove(chip)
        self._tags_layout.removeWidget(chip)
        chip.deleteLater()
        self._tags_container.setVisible(bool(self._chips))
        self.tag_removed.emit(chip.text())

    def _on_chip_removed(self, _tag: str) -> None:
        """Remove the chip whose button was clicked."""
        self._drop(self.sender())
        self.tags_changed.emit(self.tags())

    def _on_return_pressed(self) -> None:
        """Handle Enter key press in input field."""
        text = self._input.text().strip()
        if text and self.add_tag(text):
            self._input.clear()


fxstyle.register_widget_style("""
/* A primary button's fill, so its text reads at 4.5:1, and a button's
   edge, so it still reads on an accent row. */
FXTagChip {
    background-color: @primary_button;
    border: 1px solid @border_light;
    border-radius: @button_radius;
    padding: 2px 4px;
}
FXTagChip QLabel {
    color: @text_on_accent_primary;
    background: transparent;
}
FXTagChip QPushButton {
    background: transparent;
    border: none;
    border-radius: @button_radius;
}
FXTagChip QPushButton:hover {
    background: @primary_button_hover;
}
""")
