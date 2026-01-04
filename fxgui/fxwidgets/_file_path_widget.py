"""FXFilePathWidget - Path input with browse button."""

# Built-in
import os
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


class FXFilePathWidget(QWidget):
    """A line edit with integrated browse button for file/folder selection.

    This widget provides:
    - File or folder mode selection
    - Drag & drop support
    - Path validation indicator
    - Browse button with file dialog

    Args:
        parent: Parent widget.
        mode: Selection mode ('file', 'files', 'folder', 'save').
        placeholder: Placeholder text.
        file_filter: File filter for file dialogs (e.g., "Images (*.png *.jpg)").
        default_path: Default path for the file dialog.
        validate: Whether to show validation indicator.

    Signals:
        path_changed: Emitted when the path changes.
        path_valid: Emitted with True/False when validation state changes.

    Examples:
        >>> path_widget = FXFilePathWidget(mode='file', file_filter="Python (*.py)")
        >>> path_widget.path_changed.connect(lambda p: print(f"Path: {p}"))
        >>>
        >>> # Folder mode
        >>> folder_widget = FXFilePathWidget(mode='folder')
    """

    path_changed = Signal(str)
    path_valid = Signal(bool)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        mode: str = "file",
        placeholder: str = "Select path...",
        file_filter: str = "All Files (*)",
        default_path: Optional[str] = None,
        validate: bool = True,
    ):
        super().__init__(parent)

        self._mode = mode
        self._file_filter = file_filter
        self._default_path = default_path or os.path.expanduser("~")
        self._validate = validate
        self._is_valid = False

        # Get theme colors
        theme_colors = fxstyle.get_theme_colors()
        accent_colors = fxstyle.get_accent_colors()

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Path input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.setAcceptDrops(True)

        # Style
        self._input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {theme_colors['input']};
                border: 1px solid {theme_colors['border']};
                border-radius: 4px;
                padding: 6px 8px;
            }}
            QLineEdit:focus {{
                border-color: {accent_colors['primary']};
            }}
        """
        )
        layout.addWidget(self._input, 1)

        # Validation indicator
        if validate:
            self._indicator = QPushButton()
            self._indicator.setFixedSize(24, 24)
            self._indicator.setFlat(True)
            self._indicator.setStyleSheet(
                "background: transparent; border: none;"
            )
            self._update_indicator()
            layout.addWidget(self._indicator)

        # Browse button
        self._browse_btn = QPushButton()
        self._browse_btn.setToolTip("Browse...")
        self._browse_btn.setCursor(Qt.PointingHandCursor)

        # Set icon based on mode
        if mode == "folder":
            fxicons.set_icon(self._browse_btn, "folder_open")
        else:
            fxicons.set_icon(self._browse_btn, "file_open")

        self._browse_btn.setFixedSize(32, 32)
        self._browse_btn.clicked.connect(self._browse)
        layout.addWidget(self._browse_btn)

        # Enable drag and drop
        self.setAcceptDrops(True)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @property
    def path(self) -> str:
        """Return the current path."""
        return self._input.text()

    @path.setter
    def path(self, value: str) -> None:
        """Set the path."""
        self._input.setText(value)

    def get_path(self) -> str:
        """Return the current path."""
        return self._input.text()

    def set_path(self, path: str) -> None:
        """Set the path.

        Args:
            path: The file or folder path.
        """
        self._input.setText(path)

    def is_valid(self) -> bool:
        """Return whether the current path is valid."""
        return self._is_valid

    def clear(self) -> None:
        """Clear the path input."""
        self._input.clear()

    def set_mode(self, mode: str) -> None:
        """Set the selection mode.

        Args:
            mode: Selection mode ('file', 'files', 'folder', 'save').
        """
        self._mode = mode

        if mode == "folder":
            fxicons.set_icon(self._browse_btn, "folder_open")
        else:
            fxicons.set_icon(self._browse_btn, "file_open")

    def set_file_filter(self, filter_str: str) -> None:
        """Set the file filter.

        Args:
            filter_str: File filter string (e.g., "Images (*.png *.jpg)").
        """
        self._file_filter = filter_str

    def _browse(self) -> None:
        """Open the file/folder dialog."""
        start_path = self._input.text() or self._default_path

        if self._mode == "folder":
            path = QFileDialog.getExistingDirectory(
                self, "Select Folder", start_path, QFileDialog.ShowDirsOnly
            )
        elif self._mode == "files":
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Files", start_path, self._file_filter
            )
            path = ";".join(paths) if paths else ""
        elif self._mode == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save File", start_path, self._file_filter
            )
        else:  # file
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", start_path, self._file_filter
            )

        if path:
            self._input.setText(path)

    def _on_text_changed(self, text: str) -> None:
        """Handle text change."""
        self._validate_path(text)
        self.path_changed.emit(text)

    def _validate_path(self, path: str) -> None:
        """Validate the path and update indicator."""
        if not self._validate:
            return

        if not path:
            self._is_valid = False
        elif self._mode == "folder":
            self._is_valid = os.path.isdir(path)
        elif self._mode == "save":
            # For save mode, check if parent directory exists
            self._is_valid = (
                os.path.isdir(os.path.dirname(path)) if path else False
            )
        elif self._mode == "files":
            # Check all paths
            paths = path.split(";")
            self._is_valid = all(
                os.path.isfile(p.strip()) for p in paths if p.strip()
            )
        else:  # file
            self._is_valid = os.path.isfile(path)

        self._update_indicator()
        self.path_valid.emit(self._is_valid)

    def _update_indicator(self) -> None:
        """Update the validation indicator icon."""
        if not self._validate:
            return

        path = self._input.text()

        if not path:
            fxicons.set_icon(self._indicator, "remove", color="#888888")
            self._indicator.setToolTip("No path entered")
        elif self._is_valid:
            fxicons.set_icon(self._indicator, "check_circle", color="#4caf50")
            self._indicator.setToolTip("Path exists")
        else:
            fxicons.set_icon(self._indicator, "error", color="#f44336")
            self._indicator.setToolTip("Path does not exist")

    def dragEnterEvent(self, event) -> None:
        """Handle drag enter for file drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """Handle file drop."""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self._mode == "folder" and os.path.isdir(path):
                self._input.setText(path)
            elif self._mode != "folder" and os.path.isfile(path):
                self._input.setText(path)
            elif self._mode == "files":
                paths = [
                    url.toLocalFile()
                    for url in urls
                    if os.path.isfile(url.toLocalFile())
                ]
                self._input.setText(";".join(paths))


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    import os
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel, QGroupBox
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXFilePathWidget Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # File selection
    file_group = QGroupBox("Select File")
    file_layout = QVBoxLayout(file_group)
    file_widget = FXFilePathWidget(
        mode="file",
        filter="Images (*.png *.jpg);;All Files (*.*)",
        placeholder="Select an image file...",
    )
    file_layout.addWidget(file_widget)
    layout.addWidget(file_group)

    # Folder selection
    folder_group = QGroupBox("Select Folder")
    folder_layout = QVBoxLayout(folder_group)
    folder_widget = FXFilePathWidget(
        mode="folder", placeholder="Select a project folder..."
    )
    folder_layout.addWidget(folder_widget)
    layout.addWidget(folder_group)

    # Save file
    save_group = QGroupBox("Save As")
    save_layout = QVBoxLayout(save_group)
    save_widget = FXFilePathWidget(
        mode="save",
        filter="JSON Files (*.json);;All Files (*.*)",
        placeholder="Enter save location...",
        validate=False,
    )
    save_layout.addWidget(save_widget)
    layout.addWidget(save_group)

    info_label = QLabel("Select a path")

    def on_path_changed(path):
        info_label.setText(f"Path: {path}")

    file_widget.path_changed.connect(on_path_changed)
    folder_widget.path_changed.connect(on_path_changed)
    save_widget.path_changed.connect(on_path_changed)

    layout.addWidget(info_label)
    layout.addStretch()

    window.resize(500, 350)
    window.show()
    sys.exit(app.exec())
