"""Tag/chip input widget."""

# Built-in
from typing import List, Optional, Union

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QPainter
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
from fxgui.fxwidgets._tips import apply_tip


# A chip's height, and its remove button's side.
_CHIP_HEIGHT = 28
_REMOVE_SIZE = 16


class _Dot(QWidget):
    """An 8 px dot in a token's colour, read when it paints."""

    def __init__(self, color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(8, 8)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        value = getattr(fxstyle.colors(), self._color, None) or self._color
        painter.setBrush(QColor(value))
        painter.drawEllipse(self.rect())


class FXTagChip(QFrame):
    """A single removable tag chip.

    Args:
        text: The tag text.
        parent: Parent widget.
        removable: Whether the chip can be removed.
        color: An 8 px dot before the text: a theme token name (such as
            "feedback_success_foreground") or any colour QColor reads.
            None (the default) draws no dot.

    Signals:
        removed: Emitted when the remove button is clicked.
    """

    removed = Signal(str)

    def __init__(
        self,
        text: str,
        parent: Optional[QWidget] = None,
        removable: bool = True,
        color: Optional[str] = None,
    ):
        super().__init__(parent)
        self._text = text
        self._removable = removable

        self.setFrameShape(QFrame.StyledPanel)

        # 28 px tall; the text starts 10 px in, and the x sits as far from
        # the end as from the top and bottom. The 1 px border is inside.
        self.setFixedHeight(_CHIP_HEIGHT)
        end = (_CHIP_HEIGHT - _REMOVE_SIZE) // 2 - 1 if removable else 9
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 0, end, 0)
        layout.setSpacing(6)

        self.dot = None
        if color:
            self.dot = _Dot(color, self)
            layout.addWidget(self.dot)
        self.label = QLabel(text)
        self.label.setTextFormat(Qt.PlainText)
        layout.addWidget(self.label)

        self.remove_button = None
        if removable:
            self.remove_button = QPushButton()
            self.remove_button.setFixedSize(_REMOVE_SIZE, _REMOVE_SIZE)
            self.remove_button.setFlat(True)
            self.remove_button.setCursor(Qt.PointingHandCursor)
            self.remove_button.clicked.connect(self._on_remove)
            layout.addWidget(self.remove_button)
            apply_tip(self.remove_button, "Remove", text)
            fxicons.set_icon(self.remove_button, "x", color="text_muted")

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
        """Replace the tags, saying `tags_changed` once if they changed.

        A chip whose tag stays is kept: only real removals and additions
        say `tag_removed` and `tag_added`.
        """
        before = self.tags()
        wanted: List[str] = []
        for tag in (tag.strip() for tag in tags):
            if (
                tag
                and (self._allow_duplicates or tag not in wanted)
                and not (self._max_tags > 0 and len(wanted) >= self._max_tags)
            ):
                wanted.append(tag)
        spare = list(self._chips)
        plan: List[Union[FXTagChip, str]] = []
        for tag in wanted:
            chip = next((chip for chip in spare if chip.text() == tag), None)
            if chip is None:
                plan.append(tag)
            else:
                spare.remove(chip)
                plan.append(chip)
        for chip in spare:
            self._drop(chip)
        self._chips = []
        for entry in plan:
            if isinstance(entry, str):
                self._add(entry)
            else:
                # Re-laid out in the new order.
                self._tags_layout.removeWidget(entry)
                self._tags_layout.addWidget(entry)
                self._chips.append(entry)
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
/* A neutral hairline chip on the page's fill, as the web look's: colour
   shows only as its dot. */
FXTagChip {
    background-color: @surface;
    border: 1px solid @border;
    border-radius: @button_radius;
    padding: 0px;
}
FXTagChip QLabel {
    color: @text;
    background: transparent;
    font-size: @font_size_small;
}
FXTagChip QPushButton {
    background: transparent;
    border: none;
    border-radius: @small_radius;
}
FXTagChip QPushButton:hover {
    background: @state_hover;
}
""")
