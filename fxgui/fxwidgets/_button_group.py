"""FXButtonGroup - Segmented button control widget."""

from typing import List, Optional, Union

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from fxgui import fxicons, fxstyle


class FXButtonGroup(QWidget):
    """A horizontal group of mutually exclusive buttons (segmented control).

    This widget provides a tab-bar-like control with styled active/inactive
    states and optional icons.

    Args:
        parent: Parent widget.
        buttons: List of button labels or (label, icon_name) tuples.
        exclusive: Whether only one button can be selected at a time.

    Signals:
        button_clicked: Emitted when a button is clicked (index).
        selection_changed: Emitted when the selection changes (index).

    Examples:
        >>> group = FXButtonGroup(buttons=["Day", "Week", "Month"])
        >>> group.selection_changed.connect(lambda i: print(f"Selected: {i}"))
        >>>
        >>> # With icons
        >>> group = FXButtonGroup(buttons=[
        ...     ("Grid", "grid_view"),
        ...     ("List", "view_list"),
        ...     ("Tree", "account_tree"),
        ... ])
    """

    button_clicked = Signal(int)
    selection_changed = Signal(int)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        buttons: Optional[List[Union[str, tuple]]] = None,
        exclusive: bool = True,
    ):
        super().__init__(parent)

        self._exclusive = exclusive
        self._buttons: List[QPushButton] = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(exclusive)

        # Get theme colors
        theme_colors = fxstyle.get_theme_colors()
        accent_colors = fxstyle.get_accent_colors()

        self._active_bg = accent_colors["primary"]
        self._inactive_bg = theme_colors["surface"]
        self._active_text = "#ffffff"
        self._inactive_text = theme_colors["text"]
        self._border_color = theme_colors["border"]

        # Main layout
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Add buttons if provided
        if buttons:
            for item in buttons:
                if isinstance(item, tuple):
                    self.add_button(item[0], item[1] if len(item) > 1 else None)
                else:
                    self.add_button(item)

        # Connect signals
        self._button_group.buttonClicked.connect(self._on_button_clicked)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def add_button(
        self,
        text: str,
        icon_name: Optional[str] = None,
        index: Optional[int] = None,
    ) -> QPushButton:
        """Add a button to the group.

        Args:
            text: Button label text.
            icon_name: Optional icon name.
            index: Position to insert at (None = append).

        Returns:
            The created QPushButton.
        """
        button = QPushButton(text)
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)

        if icon_name:
            button.setIcon(fxicons.get_icon(icon_name))

        # Determine position
        if index is None:
            index = len(self._buttons)

        self._buttons.insert(index, button)
        self._button_group.addButton(button, index)
        self._layout.insertWidget(index, button)

        # Update styling for all buttons
        self._update_button_styles()

        # Select first button by default
        if len(self._buttons) == 1:
            button.setChecked(True)

        return button

    def remove_button(self, index: int) -> None:
        """Remove a button by index.

        Args:
            index: The button index to remove.
        """
        if 0 <= index < len(self._buttons):
            button = self._buttons.pop(index)
            self._button_group.removeButton(button)
            self._layout.removeWidget(button)
            button.deleteLater()
            self._update_button_styles()

    def set_selected(self, index: int) -> None:
        """Set the selected button by index.

        Args:
            index: The button index to select.
        """
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
            self.selection_changed.emit(index)

    def get_selected(self) -> int:
        """Return the index of the selected button.

        Returns:
            The selected button index, or -1 if none selected.
        """
        for i, button in enumerate(self._buttons):
            if button.isChecked():
                return i
        return -1

    def set_button_enabled(self, index: int, enabled: bool) -> None:
        """Enable or disable a button.

        Args:
            index: The button index.
            enabled: Whether the button should be enabled.
        """
        if 0 <= index < len(self._buttons):
            self._buttons[index].setEnabled(enabled)

    def _update_button_styles(self) -> None:
        """Update button styles based on position and state."""
        count = len(self._buttons)

        for i, button in enumerate(self._buttons):
            # Determine border radius based on position
            if count == 1:
                radius = "4px"
            elif i == 0:
                radius = "4px 0 0 4px"
            elif i == count - 1:
                radius = "0 4px 4px 0"
            else:
                radius = "0"

            # Border styling
            if i == 0:
                border = f"1px solid {self._border_color}"
            else:
                border = f"1px solid {self._border_color}; border-left: none"

            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._inactive_bg};
                    color: {self._inactive_text};
                    border: {border};
                    border-radius: {radius};
                    padding: 6px 16px;
                    font-weight: normal;
                }}
                QPushButton:hover {{
                    background-color: {self._inactive_bg};
                    opacity: 0.8;
                }}
                QPushButton:checked {{
                    background-color: {self._active_bg};
                    color: {self._active_text};
                    font-weight: bold;
                }}
                QPushButton:disabled {{
                    opacity: 0.5;
                }}
            """)

    def _on_button_clicked(self, button: QPushButton) -> None:
        """Handle button click."""
        index = self._buttons.index(button)
        self.button_clicked.emit(index)
        if button.isChecked():
            self.selection_changed.emit(index)

    def __len__(self) -> int:
        """Return the number of buttons."""
        return len(self._buttons)

    def __getitem__(self, index: int) -> QPushButton:
        """Get a button by index."""
        return self._buttons[index]


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    import os
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXButtonGroup Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Single selection
    label1 = QLabel("Single Selection:")
    group1 = FXButtonGroup(["Left", "Center", "Right"])
    group1.set_selected(1)

    # Multi selection
    label2 = QLabel("Multi Selection:")
    group2 = FXButtonGroup(["Bold", "Italic", "Underline"], exclusive=False)
    group2.set_selected([0, 2])

    info_label = QLabel("Click a button")

    def on_selection1(index):
        info_label.setText(f"Single: Selected index {index}")

    def on_selection2(index):
        info_label.setText(f"Multi: Toggled index {index}")

    group1.selection_changed.connect(on_selection1)
    group2.button_clicked.connect(on_selection2)

    layout.addWidget(label1)
    layout.addWidget(group1)
    layout.addWidget(label2)
    layout.addWidget(group2)
    layout.addWidget(info_label)
    layout.addStretch()

    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())
