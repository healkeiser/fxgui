"""Drag and drop zone widget for file and folder selection."""

# Built-in
import os
from pathlib import Path
from typing import List, Optional, Set

# Third-party
from qtpy.QtCore import QEvent, Qt, QTimer, Signal
from qtpy.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


class FXDropZone(fxstyle.FXThemeAware, QWidget):
    """A drag and drop zone widget for file and folder selection.

    This widget provides a visual drop target for files and folders with:
    - Drag and drop support with visual feedback
    - Optional browse and clear buttons (external to drop area)
    - Customizable accepted extensions with display
    - Support for files, folders, or both
    - Visual states: default, hover, drag-active

    Args:
        parent: Parent widget.
        title: Main title text displayed in the drop zone.
        description: Description text displayed below the title.
        accept_mode: What to accept - 'files', 'folders', or 'both'.
        extensions: Set of allowed file extensions (e.g., {'.png', '.jpg'}).
            If None, all extensions are accepted.
        multiple: Whether to allow multiple file/folder selection.
        icon_name: Icon name to display (default: 'upload_file').
        show_formats: Whether to display accepted formats below title.
        show_buttons: Whether to show Browse/Clear buttons.

    Signals:
        files_dropped: Emitted when files/folders are dropped or selected.
            Passes a list of Path objects.
        files_cleared: Emitted when files are cleared.
        drag_entered: Emitted when a valid drag enters the drop zone.
        drag_left: Emitted when a drag leaves the drop zone.

    Examples:
        >>> # Accept image files only
        >>> drop_zone = FXDropZone(
        ...     title="Drop Images Here",
        ...     description="or use the Browse Files... button below",
        ...     extensions={'.png', '.jpg', '.exr'}
        ... )
        >>> drop_zone.files_dropped.connect(lambda paths: print(paths))
        >>>
        >>> # Accept folders only
        >>> folder_zone = FXDropZone(
        ...     title="Drop Project Folder",
        ...     accept_mode='folders'
        ... )
    """

    files_dropped = Signal(list)
    files_cleared = Signal()
    drag_entered = Signal()
    drag_left = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Drag and Drop Files Here",
        description: str = "or use the Browse Files... button below",
        accept_mode: str = "files",
        extensions: Optional[Set[str]] = None,
        multiple: bool = True,
        icon_name: str = "upload_file",
        show_formats: bool = True,
        show_buttons: bool = True,
    ):
        super().__init__(parent)

        self._title = title
        self._description = description
        self._accept_mode = accept_mode
        self._extensions = extensions
        self._multiple = multiple
        self._icon_name = icon_name
        self._show_formats = show_formats
        self._show_buttons = show_buttons
        self._is_drag_active = False
        self._has_files = False

        self._init_ui()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Drop area container
        self._drop_area = QWidget()
        self._drop_area.setAcceptDrops(True)
        self._drop_area.setObjectName("FXDropZoneArea")
        # Install event filter to handle drag/drop on the container
        self._drop_area.installEventFilter(self)

        drop_layout = QVBoxLayout(self._drop_area)
        drop_layout.setContentsMargins(20, 20, 20, 20)
        drop_layout.setSpacing(8)

        # Add stretch before content to center vertically
        drop_layout.addStretch(1)

        # Icon label - centered horizontally
        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setObjectName("FXDropZoneIcon")
        self._icon_label.setMinimumSize(64, 64)
        self._icon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        drop_layout.addWidget(self._icon_label, 0, Qt.AlignCenter)

        # Title label
        self._title_label = QLabel(self._title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setWordWrap(True)
        self._title_label.setObjectName("FXDropZoneTitle")
        drop_layout.addWidget(self._title_label)

        # Formats label (shows accepted extensions)
        self._formats_label = QLabel()
        self._formats_label.setAlignment(Qt.AlignCenter)
        self._formats_label.setWordWrap(True)
        self._formats_label.setObjectName("FXDropZoneFormats")
        self._update_formats_label()
        drop_layout.addWidget(self._formats_label)

        # Description label
        self._description_label = QLabel(self._description)
        self._description_label.setAlignment(Qt.AlignCenter)
        self._description_label.setWordWrap(True)
        self._description_label.setObjectName("FXDropZoneDescription")
        drop_layout.addWidget(self._description_label)

        # Add stretch after content to center vertically
        drop_layout.addStretch(1)

        main_layout.addWidget(self._drop_area, 1)

        # Button container (outside the drop area)
        if self._show_buttons:
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(8)

            # Clear button (left side)
            self._clear_btn = QPushButton("Clear All")
            self._clear_btn.setCursor(Qt.PointingHandCursor)
            self._clear_btn.setFocusPolicy(Qt.NoFocus)
            self._clear_btn.setEnabled(False)
            self._clear_btn.clicked.connect(self._on_clear_clicked)
            fxicons.set_icon(self._clear_btn, "clear")
            button_layout.addWidget(self._clear_btn)

            button_layout.addStretch()

            # Browse button (right side)
            self._browse_btn = QPushButton("Browse Files...")
            self._browse_btn.setCursor(Qt.PointingHandCursor)
            self._browse_btn.setFocusPolicy(Qt.NoFocus)
            self._browse_btn.clicked.connect(self._browse)
            self._browse_icon_name = (
                "folder_open" if self._accept_mode == "folders" else "file_open"
            )
            fxicons.set_icon(self._browse_btn, self._browse_icon_name)
            button_layout.addWidget(self._browse_btn)

            main_layout.addWidget(button_container)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        self._update_styles()
        self._update_icon()
        # Button icons are automatically refreshed by fxicons.set_icon registration

    def _update_styles(self) -> None:
        """Update widget styles based on current state."""
        if self._is_drag_active:
            self._apply_drag_active_style()
        else:
            self._apply_default_style()

    def _apply_default_style(self) -> None:
        """Apply default (non-drag) style."""
        self._drop_area.setStyleSheet(
            f"QWidget#FXDropZoneArea {{"
            f"  border: 2px dashed {self.theme.border};"
            f"  border-radius: 8px;"
            f"  background-color: {self.theme.surface_sunken};"
            f"}}"
            f"QWidget#FXDropZoneArea:hover {{"
            f"  border-color: {self.theme.border_light};"
            f"  background-color: {self.theme.state_hover};"
            f"}}"
        )

        self._icon_label.setStyleSheet("background: transparent; border: none;")

        self._title_label.setStyleSheet(
            f"color: {self.theme.text};"
            f"font-size: 12px;"
            f"font-weight: bold;"
            f"background: transparent;"
            f"border: none;"
        )

        self._formats_label.setStyleSheet(
            f"color: {self.theme.accent_primary};"
            f"font-size: 11px;"
            f"background: transparent;"
            f"border: none;"
        )

        self._description_label.setStyleSheet(
            f"color: {self.theme.text_muted};"
            f"font-size: 11px;"
            f"background: transparent;"
            f"border: none;"
        )

    def _apply_drag_active_style(self) -> None:
        """Apply drag-active style."""
        self._drop_area.setStyleSheet(
            f"QWidget#FXDropZoneArea {{"
            f"  border: 2px dashed {self.theme.accent_primary};"
            f"  border-radius: 8px;"
            f"  background-color: {self.theme.state_hover};"
            f"}}"
        )

    def _apply_feedback_style(self, feedback_type: str) -> None:
        """Apply feedback style (success/error).

        Args:
            feedback_type: Either 'success' or 'error'.
        """
        feedback = fxstyle.get_feedback_colors()
        color = feedback.get(feedback_type, {}).get(
            "foreground", self.theme.accent_primary
        )

        self._drop_area.setStyleSheet(
            f"QWidget#FXDropZoneArea {{"
            f"  border: 2px dashed {color};"
            f"  border-radius: 8px;"
            f"  background-color: {self.theme.state_hover};"
            f"}}"
        )
        self._update_icon(color)

    def _flash_feedback(self, feedback_type: str, duration: int = 800) -> None:
        """Flash feedback color then return to default.

        Args:
            feedback_type: Either 'success' or 'error'.
            duration: Duration in milliseconds.
        """
        self._apply_feedback_style(feedback_type)
        QTimer.singleShot(duration, self._reset_to_default)

    def _reset_to_default(self) -> None:
        """Reset to default style after feedback flash."""
        self._apply_default_style()
        self._update_icon()

    def _update_icon(self, color: Optional[str] = None) -> None:
        """Update the icon with theme colors.

        Args:
            color: Optional color override for the icon.
        """
        if color:
            # Use explicit color
            pixmap = fxicons.get_icon(self._icon_name, color=color).pixmap(
                64, 64
            )
        else:
            # Use theme icon color
            pixmap = fxicons.get_icon(self._icon_name).pixmap(64, 64)
        self._icon_label.setPixmap(pixmap)

    def _update_formats_label(self) -> None:
        """Update the formats label text."""
        if self._extensions:
            # Format extensions nicely (e.g., ".png, .jpg, .exr")
            ext_list = sorted(self._extensions)
            ext_str = ", ".join(ext_list)
            self._formats_label.setText(f"Accepted formats: {ext_str}")
            self._formats_label.setVisible(self._show_formats)
        else:
            self._formats_label.setVisible(False)

    def _browse(self) -> None:
        """Open file/folder browser dialog."""
        if self._accept_mode == "folders":
            path = QFileDialog.getExistingDirectory(
                self, "Select Folder", os.path.expanduser("~")
            )
            if path:
                self._on_files_added([Path(path)])
        else:
            # Build filter string from extensions
            if self._extensions:
                ext_str = " ".join(f"*{ext}" for ext in self._extensions)
                filter_str = f"Allowed Files ({ext_str});;All Files (*)"
            else:
                filter_str = "All Files (*)"

            if self._multiple:
                paths, _ = QFileDialog.getOpenFileNames(
                    self, "Select Files", os.path.expanduser("~"), filter_str
                )
                if paths:
                    self._on_files_added([Path(p) for p in paths])
            else:
                path, _ = QFileDialog.getOpenFileName(
                    self, "Select File", os.path.expanduser("~"), filter_str
                )
                if path:
                    self._on_files_added([Path(path)])

    def _on_files_added(self, paths: List[Path], flash: bool = True) -> None:
        """Handle files being added (from drop or browse).

        Args:
            paths: List of paths that were added.
            flash: Whether to flash success feedback.
        """
        self._has_files = True
        if self._show_buttons:
            self._clear_btn.setEnabled(True)
        if flash:
            self._flash_feedback("success")
        self.files_dropped.emit(paths)

    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        self._has_files = False
        if self._show_buttons:
            self._clear_btn.setEnabled(False)
        self.files_cleared.emit()

    def _is_valid_drop(self, paths: List[Path]) -> bool:
        """Check if the dropped paths are valid.

        Args:
            paths: List of dropped paths.

        Returns:
            True if at least one path is valid, False otherwise.
        """
        for path in paths:
            if not path.exists():
                continue

            if self._accept_mode == "files":
                if path.is_file():
                    if self._extensions is None:
                        return True
                    if path.suffix.lower() in self._extensions:
                        return True
            elif self._accept_mode == "folders":
                if path.is_dir():
                    return True
            else:  # both
                if path.is_dir():
                    return True
                if path.is_file():
                    if self._extensions is None:
                        return True
                    if path.suffix.lower() in self._extensions:
                        return True

        return False

    def eventFilter(self, obj, event) -> bool:
        """Filter events for the drop area."""
        if obj == self._drop_area:
            event_type = event.type()
            if event_type == QEvent.DragEnter:
                self._handle_drag_enter(event)
                return True
            elif event_type == QEvent.DragLeave:
                self._handle_drag_leave(event)
                return True
            elif event_type == QEvent.DragMove:
                self._handle_drag_move(event)
                return True
            elif event_type == QEvent.Drop:
                self._handle_drop(event)
                return True
        return super().eventFilter(obj, event)

    def _handle_drag_enter(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    paths.append(Path(url.toLocalFile()))

            if paths and self._is_valid_drop(paths):
                event.acceptProposedAction()
                self._is_drag_active = True
                self._update_styles()
                self.drag_entered.emit()
                return

        event.ignore()

    def _handle_drag_leave(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave events."""
        self._is_drag_active = False
        self._update_styles()
        self.drag_left.emit()
        event.accept()

    def _handle_drag_move(self, event) -> None:
        """Handle drag move events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _handle_drop(self, event: QDropEvent) -> None:
        """Handle drop events."""
        self._is_drag_active = False
        self._update_styles()

        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    if path.exists():
                        paths.append(path)

            if paths:
                # Filter based on accept mode and extensions
                valid_paths = []
                for path in paths:
                    if self._accept_mode == "files" and path.is_file():
                        if (
                            self._extensions is None
                            or path.suffix.lower() in self._extensions
                        ):
                            valid_paths.append(path)
                    elif self._accept_mode == "folders" and path.is_dir():
                        valid_paths.append(path)
                    elif self._accept_mode == "both":
                        if path.is_dir():
                            valid_paths.append(path)
                        elif path.is_file():
                            if (
                                self._extensions is None
                                or path.suffix.lower() in self._extensions
                            ):
                                valid_paths.append(path)

                if valid_paths:
                    if not self._multiple:
                        valid_paths = valid_paths[:1]
                    self._on_files_added(valid_paths)
                    event.acceptProposedAction()
                    return
                else:
                    # Files were dropped but none were valid
                    self._flash_feedback("error")

        event.ignore()

    # Public API

    @property
    def title(self) -> str:
        """Return the title text."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Set the title text."""
        self._title = value
        self._title_label.setText(value)

    @property
    def description(self) -> str:
        """Return the description text."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        """Set the description text."""
        self._description = value
        self._description_label.setText(value)

    @property
    def accept_mode(self) -> str:
        """Return the accept mode."""
        return self._accept_mode

    @accept_mode.setter
    def accept_mode(self, value: str) -> None:
        """Set the accept mode ('files', 'folders', or 'both')."""
        self._accept_mode = value
        # Update browse button icon if it exists
        if self._show_buttons:
            self._browse_icon_name = (
                "folder_open" if value == "folders" else "file_open"
            )
            fxicons.set_icon(self._browse_btn, self._browse_icon_name)

    @property
    def extensions(self) -> Optional[Set[str]]:
        """Return the accepted extensions."""
        return self._extensions

    @extensions.setter
    def extensions(self, value: Optional[Set[str]]) -> None:
        """Set the accepted extensions."""
        self._extensions = value
        self._update_formats_label()

    @property
    def multiple(self) -> bool:
        """Return whether multiple selection is enabled."""
        return self._multiple

    @multiple.setter
    def multiple(self, value: bool) -> None:
        """Set whether multiple selection is enabled."""
        self._multiple = value

    @property
    def has_files(self) -> bool:
        """Return whether files have been added."""
        return self._has_files

    def set_icon(self, icon_name: str) -> None:
        """Set the icon displayed in the drop zone.

        Args:
            icon_name: Name of the icon (from fxicons).
        """
        self._icon_name = icon_name
        self._update_icon()

    def set_has_files(self, has_files: bool) -> None:
        """Update the has_files state (useful for external state management).

        Args:
            has_files: Whether files are currently selected.
        """
        self._has_files = has_files
        if self._show_buttons:
            self._clear_btn.setEnabled(has_files)

    def clear(self) -> None:
        """Clear the drop zone state (programmatic clear)."""
        self._on_clear_clicked()


def example() -> None:
    """Demonstrate the FXDropZone widget."""
    import sys
    from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QWidget, QLabel
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXDropZone Demo")

    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Audio files drop zone (like LS Publisher)
    audio_group = QGroupBox("Files")
    audio_layout = QVBoxLayout(audio_group)
    audio_drop = FXDropZone(
        title="Drag and Drop Audio Files Here",
        description="or use the Browse Files... button below",
        extensions={".mp3", ".wav"},
        show_formats=True,
    )
    audio_layout.addWidget(audio_drop)
    layout.addWidget(audio_group)

    # Image files drop zone
    image_group = QGroupBox("Image Files")
    image_layout = QVBoxLayout(image_group)
    image_drop = FXDropZone(
        title="Drop Images Here",
        description="Supports PNG, JPG, EXR, and TIFF files",
        extensions={".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff"},
        show_formats=True,
    )
    image_layout.addWidget(image_drop)
    layout.addWidget(image_group)

    # Folder drop zone
    folder_group = QGroupBox("Project Folder")
    folder_layout = QVBoxLayout(folder_group)
    folder_drop = FXDropZone(
        title="Drop Project Folder",
        description="or click Browse to select",
        accept_mode="folders",
        icon_name="folder",
        show_formats=False,
    )
    folder_layout.addWidget(folder_drop)
    layout.addWidget(folder_group)

    # Status label
    status_label = QLabel("Drop files or folders to see paths")
    layout.addWidget(status_label)

    def on_files_dropped(paths):
        text = "Dropped:\n" + "\n".join(str(p) for p in paths[:5])
        if len(paths) > 5:
            text += f"\n... and {len(paths) - 5} more"
        status_label.setText(text)

    def on_files_cleared():
        status_label.setText("Files cleared")

    audio_drop.files_dropped.connect(on_files_dropped)
    audio_drop.files_cleared.connect(on_files_cleared)
    image_drop.files_dropped.connect(on_files_dropped)
    image_drop.files_cleared.connect(on_files_cleared)
    folder_drop.files_dropped.connect(on_files_dropped)
    folder_drop.files_cleared.connect(on_files_cleared)

    window.resize(500, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    if os.getenv("DEVELOPER_MODE") == "1":
        example()
