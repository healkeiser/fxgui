"""FXColorPicker - Styled color selector widget."""

# Built-in
import os
from typing import List, Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QColorDialog,
    QFrame,
    QGridLayout,
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


class FXColorSwatch(QPushButton):
    """A clickable color swatch button.

    Args:
        color: The color to display.
        parent: Parent widget.
        size: Size of the swatch in pixels.

    Signals:
        color_selected: Emitted when the swatch is clicked.
    """

    color_selected = Signal(str)

    def __init__(
        self,
        color: str,
        parent: Optional[QWidget] = None,
        size: int = 24,
    ):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size

        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(color)

        self.clicked.connect(lambda: self.color_selected.emit(color))

        self._update_style()

    def _update_style(self) -> None:
        """Update the button style."""
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 1px solid rgba(0, 0, 0, 0.3);
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 2px solid {fxstyle.get_accent_colors()['primary']};
            }}
        """
        )

    def set_color(self, color: str) -> None:
        """Set the swatch color.

        Args:
            color: The color string.
        """
        self._color = QColor(color)
        self.setToolTip(color)
        self._update_style()


class FXColorPicker(QWidget):
    """A compact color picker widget with preset swatches and color input.

    This widget provides:
    - Preset color swatches
    - Hex color input
    - Recent colors history
    - Full color dialog button

    Args:
        parent: Parent widget.
        initial_color: Initial selected color.
        presets: List of preset color strings.
        max_recent: Maximum number of recent colors to remember.
        show_input: Whether to show the hex input field.
        show_dialog_button: Whether to show the full dialog button.

    Signals:
        color_changed: Emitted when the selected color changes.

    Examples:
        >>> picker = FXColorPicker(initial_color="#ff5500")
        >>> picker.color_changed.connect(lambda c: print(f"Color: {c}"))
    """

    color_changed = Signal(str)

    # Default preset colors (Material Design palette)
    DEFAULT_PRESETS = [
        "#f44336",
        "#e91e63",
        "#9c27b0",
        "#673ab7",
        "#3f51b5",
        "#2196f3",
        "#03a9f4",
        "#00bcd4",
        "#009688",
        "#4caf50",
        "#8bc34a",
        "#cddc39",
        "#ffeb3b",
        "#ffc107",
        "#ff9800",
        "#ff5722",
        "#795548",
        "#9e9e9e",
        "#607d8b",
        "#000000",
        "#ffffff",
        "#b71c1c",
        "#1a237e",
        "#004d40",
    ]

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_color: str = "#ffffff",
        presets: Optional[List[str]] = None,
        max_recent: int = 8,
        show_input: bool = True,
        show_dialog_button: bool = True,
    ):
        super().__init__(parent)

        self._color = QColor(initial_color)
        self._presets = presets or self.DEFAULT_PRESETS
        self._max_recent = max_recent
        self._recent_colors: List[str] = []

        # Get theme colors
        theme_colors = fxstyle.get_theme_colors()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Current color preview and input
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(8)

        # Color preview button
        self._preview = QPushButton()
        self._preview.setFixedSize(40, 40)
        self._preview.setCursor(Qt.PointingHandCursor)
        self._preview.setToolTip("Current color - Click to open color dialog")
        self._preview.clicked.connect(self._open_color_dialog)
        self._update_preview()
        preview_layout.addWidget(self._preview)

        # Hex input
        if show_input:
            self._input = QLineEdit()
            self._input.setPlaceholderText("#RRGGBB")
            self._input.setMaxLength(7)
            self._input.setText(self._color.name())
            self._input.setStyleSheet(
                f"""
                QLineEdit {{
                    background-color: {theme_colors['input']};
                    border: 1px solid {theme_colors['border']};
                    border-radius: 4px;
                    padding: 8px;
                    font-family: monospace;
                }}
            """
            )
            self._input.returnPressed.connect(self._on_input_changed)
            self._input.editingFinished.connect(self._on_input_changed)
            preview_layout.addWidget(self._input, 1)

        # Dialog button
        if show_dialog_button:
            self._dialog_button = QPushButton()
            fxicons.set_icon(self._dialog_button, "colorize")
            self._dialog_button.setFixedSize(40, 40)
            self._dialog_button.setToolTip("Open full color dialog")
            self._dialog_button.setCursor(Qt.PointingHandCursor)
            self._dialog_button.clicked.connect(self._open_color_dialog)
            preview_layout.addWidget(self._dialog_button)

        main_layout.addLayout(preview_layout)

        # Preset swatches grid
        self._presets_label = QLabel("Presets")
        self._presets_label.setStyleSheet(
            f"color: {theme_colors['text_secondary']};"
        )
        main_layout.addWidget(self._presets_label)

        presets_frame = QFrame()
        presets_frame.setFrameShape(QFrame.StyledPanel)
        presets_layout = QGridLayout(presets_frame)
        presets_layout.setContentsMargins(4, 4, 4, 4)
        presets_layout.setSpacing(4)

        cols = 8
        for i, color in enumerate(self._presets):
            swatch = FXColorSwatch(color, size=20)
            swatch.color_selected.connect(self._on_color_selected)
            presets_layout.addWidget(swatch, i // cols, i % cols)

        main_layout.addWidget(presets_frame)

        # Recent colors
        self._recent_label = QLabel("Recent")
        self._recent_label.setStyleSheet(
            f"color: {theme_colors['text_secondary']};"
        )
        self._recent_label.setVisible(False)
        main_layout.addWidget(self._recent_label)

        self._recent_layout = QHBoxLayout()
        self._recent_layout.setSpacing(4)
        self._recent_layout.addStretch()
        main_layout.addLayout(self._recent_layout)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    @property
    def color(self) -> str:
        """Return the current color as hex string."""
        return self._color.name()

    @color.setter
    def color(self, value: str) -> None:
        """Set the current color."""
        self._on_color_selected(value)

    def set_color(self, color: str) -> None:
        """Set the current color.

        Args:
            color: Color string (hex, rgb, etc.).
        """
        self._on_color_selected(color)

    def get_color(self) -> str:
        """Return the current color as hex string."""
        return self._color.name()

    def get_color_rgb(self) -> tuple:
        """Return the current color as RGB tuple."""
        return (self._color.red(), self._color.green(), self._color.blue())

    def _update_preview(self) -> None:
        """Update the preview button color."""
        # Determine text color based on luminance
        luminance = fxstyle.get_luminance(self._color)
        text_color = "#000000" if luminance > 0.5 else "#ffffff"

        self._preview.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 1px solid rgba(0, 0, 0, 0.3);
                border-radius: 4px;
                color: {text_color};
            }}
            QPushButton:hover {{
                border: 2px solid {fxstyle.get_accent_colors()['primary']};
            }}
        """
        )

    def _on_color_selected(self, color: str) -> None:
        """Handle color selection."""
        old_color = self._color.name()
        self._color = QColor(color)

        # Update UI
        self._update_preview()
        if hasattr(self, "_input"):
            self._input.setText(self._color.name())

        # Add to recent colors
        if old_color != color:
            self._add_to_recent(color)

        # Emit signal
        self.color_changed.emit(self._color.name())

    def _on_input_changed(self) -> None:
        """Handle hex input change."""
        text = self._input.text().strip()
        if not text.startswith("#"):
            text = "#" + text

        if QColor(text).isValid():
            self._on_color_selected(text)
        else:
            # Reset to current color
            self._input.setText(self._color.name())

    def _open_color_dialog(self) -> None:
        """Open the full color dialog."""
        color = QColorDialog.getColor(
            self._color, self, "Select Color", QColorDialog.ShowAlphaChannel
        )
        if color.isValid():
            self._on_color_selected(color.name())

    def _add_to_recent(self, color: str) -> None:
        """Add a color to recent history."""
        # Remove if already exists
        if color in self._recent_colors:
            self._recent_colors.remove(color)

        # Add to front
        self._recent_colors.insert(0, color)

        # Trim to max
        self._recent_colors = self._recent_colors[: self._max_recent]

        # Rebuild recent swatches
        self._rebuild_recent()

    def _rebuild_recent(self) -> None:
        """Rebuild the recent colors row."""
        # Clear existing
        while self._recent_layout.count() > 1:  # Keep stretch
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Show/hide label
        self._recent_label.setVisible(bool(self._recent_colors))

        # Add swatches
        for color in self._recent_colors:
            swatch = FXColorSwatch(color, size=20)
            swatch.color_selected.connect(self._on_color_selected)
            self._recent_layout.insertWidget(
                self._recent_layout.count() - 1, swatch
            )


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXColorPicker Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    picker = FXColorPicker(show_alpha=True)
    selected_label = QLabel("No color selected")

    def on_color_selected(color):
        selected_label.setText(f"Selected: {color}")
        selected_label.setStyleSheet(
            f"background-color: {color}; padding: 8px;"
        )

    picker.color_selected.connect(on_color_selected)

    layout.addWidget(picker)
    layout.addWidget(selected_label)
    layout.addStretch()

    window.resize(350, 400)
    window.show()
    sys.exit(app.exec())
