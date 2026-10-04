"""Drag and drop zone widget for file and folder selection."""

# Built-in
import os
from pathlib import Path
from typing import Iterable, List, Optional, Set

# Third-party
from qtpy.QtCore import QLocale, Qt, QTimer, Signal
from qtpy.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._labels import FXIconLabel


ACCEPT_MODES = ("files", "folders", "both")


def _local_paths(event) -> List[Path]:
    """Return the existing local paths a drag or drop event carries."""
    paths = [
        Path(url.toLocalFile())
        for url in event.mimeData().urls()
        if url.isLocalFile()
    ]
    return [path for path in paths if path.exists()]


def _size_text(path: Path) -> str:
    """Return a file's size in Qt's own format, or "-" if it is unreadable."""
    try:
        size = path.stat().st_size
    except OSError:
        return "-"
    return QLocale().formattedDataSize(
        size, 1, QLocale.DataSizeTraditionalFormat)


class FXDropZone(QWidget):
    """A drag and drop zone widget for file and folder selection.

    The zone takes drops on its placeholder and on its file list alike:
    neither child accepts drops, so Qt hands them to the zone.

    Args:
        parent: Parent widget.
        title: Main title text displayed in the drop zone.
        description: Description text displayed below the title.
        accept_mode: What to accept: 'files', 'folders' or 'both'.
        extensions: Allowed file extensions, such as {'.png', '.JPG'}; case
            and a missing leading dot do not matter. None accepts all.
        multiple: Whether to allow multiple file/folder selection.
        icon_name: Icon name to display (default: 'upload_file').
        show_formats: Whether to display accepted formats below title.
        show_buttons: Whether to show Browse/Clear buttons.
        show_tree: Whether to show file tree after files are dropped.

    Raises:
        ValueError: `accept_mode` is not one of `ACCEPT_MODES`.

    Signals:
        files_dropped: Emitted when files/folders are dropped or selected.
            Passes a list of Path objects.
        files_cleared: Emitted when files are cleared.
        file_removed: Emitted when a single file is removed from the tree.
            Passes the Path that was removed.
        drag_entered: Emitted when a valid drag enters the drop zone.
        drag_left: Emitted when a drag leaves the drop zone.

    Examples:
        >>> # Accept image files only with tree view
        >>> drop_zone = FXDropZone(
        ...     title="Drop Images Here",
        ...     description="or use the Browse Files... button below",
        ...     extensions={'.png', '.jpg', '.exr'},
        ...     show_tree=True
        ... )
        >>> drop_zone.files_dropped.connect(lambda paths: print(paths))
        >>>
        >>> # Accept folders only (no tree)
        >>> folder_zone = FXDropZone(
        ...     title="Drop Project Folder",
        ...     accept_mode='folders',
        ...     show_tree=False
        ... )
    """

    files_dropped = Signal(list)
    files_cleared = Signal()
    file_removed = Signal(object)  # Path object
    drag_entered = Signal()
    drag_left = Signal()

    # How long a success or error edge shows after a drop, in ms.
    FLASH_MS = 800

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
        show_tree: bool = True,
    ):
        super().__init__(parent)

        self._multiple = multiple
        self._icon_name = icon_name
        self._show_formats = show_formats
        self._show_buttons = show_buttons
        self._show_tree = show_tree
        self._selected_files: List[Path] = []

        # One owned timer: a second flash restarts it, and it dies with us.
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._reset_to_default)

        self._init_ui(title, description)
        self.set_accept_mode(accept_mode)
        self.set_extensions(extensions)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _init_ui(self, title: str, description: str) -> None:
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(fxstyle.PANE_GAP)

        self._drop_area = QWidget()
        self._drop_area.setObjectName("FXDropZoneArea")
        self._drop_area.setAttribute(Qt.WA_StyledBackground, True)
        self._drop_area.setProperty("dropState", "idle")

        drop_layout = QVBoxLayout(self._drop_area)
        drop_layout.setContentsMargins(16, 16, 16, 16)
        drop_layout.setSpacing(fxstyle.PANE_GAP)
        drop_layout.addStretch(1)

        self._icon_label = FXIconLabel(size=64)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setObjectName("FXDropZoneIcon")
        self._icon_label.setMinimumSize(64, 64)
        self._icon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        drop_layout.addWidget(self._icon_label, 0, Qt.AlignCenter)

        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setWordWrap(True)
        self._title_label.setObjectName("FXDropZoneTitle")
        drop_layout.addWidget(self._title_label)

        self._formats_label = QLabel()
        self._formats_label.setAlignment(Qt.AlignCenter)
        self._formats_label.setWordWrap(True)
        self._formats_label.setObjectName("FXDropZoneFormats")
        drop_layout.addWidget(self._formats_label)

        self._description_label = QLabel(description)
        self._description_label.setAlignment(Qt.AlignCenter)
        self._description_label.setWordWrap(True)
        self._description_label.setObjectName("FXDropZoneDescription")
        drop_layout.addWidget(self._description_label)

        drop_layout.addStretch(1)
        main_layout.addWidget(self._drop_area, 1)

        if self._show_tree:
            self._file_tree = QTreeWidget()
            self._file_tree.setObjectName("FXDropZoneTree")
            self._file_tree.setSelectionMode(
                QAbstractItemView.ExtendedSelection
            )
            self._file_tree.setRootIsDecorated(False)
            self._file_tree.setHeaderLabels(["Name", "Type", "Size"])
            header = self._file_tree.header()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self._file_tree.setVisible(False)
            self._file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
            self._file_tree.customContextMenuRequested.connect(
                self._show_context_menu
            )
            main_layout.addWidget(self._file_tree, 1)

            self._count_label = QLabel()
            self._count_label.setObjectName("FXDropZoneCount")
            self._count_label.setVisible(False)
            main_layout.addWidget(self._count_label)

        if self._show_buttons:
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(fxstyle.PANE_GAP)

            self._clear_btn = QPushButton("Clear All")
            self._clear_btn.setCursor(Qt.PointingHandCursor)
            self._clear_btn.setFocusPolicy(Qt.NoFocus)
            self._clear_btn.setEnabled(False)
            self._clear_btn.clicked.connect(self.clear)
            fxicons.set_icon(self._clear_btn, "clear")
            button_layout.addWidget(self._clear_btn)

            button_layout.addStretch()

            self._browse_btn = QPushButton("Browse Files...")
            self._browse_btn.setCursor(Qt.PointingHandCursor)
            self._browse_btn.setFocusPolicy(Qt.NoFocus)
            self._browse_btn.clicked.connect(self._browse)
            button_layout.addWidget(self._browse_btn)

            main_layout.addWidget(button_container)

        self._update_icon()

    def _set_drop_state(self, state: str) -> None:
        """Set the drop area's state: idle, drag, success or error."""
        self._drop_area.setProperty("dropState", state)
        fxutils.repolish(self._drop_area)

    def _flash_feedback(self, feedback_type: str) -> None:
        """Edge the area in `feedback_type`, success or error, for FLASH_MS."""
        self._set_drop_state(feedback_type)
        self._update_icon(f"feedback_{feedback_type}_foreground")
        self._flash_timer.start(self.FLASH_MS)

    def _reset_to_default(self) -> None:
        """Reset to default style after feedback flash."""
        self._set_drop_state("idle")
        self._update_icon()

    def _update_icon(self, color: Optional[str] = None) -> None:
        """Draw the drop icon in `color`, a theme token, or the icon ink."""
        self._icon_label.setIcon(fxicons.get_icon(self._icon_name, color=color))

    def _update_file_tree(self) -> None:
        """Show the files: the list and its count, or the placeholder."""
        has_files = bool(self._selected_files)
        if self._show_buttons:
            self._clear_btn.setEnabled(has_files)
        if not self._show_tree:
            return

        self._file_tree.clear()
        for path in self._selected_files:
            item = QTreeWidgetItem()
            item.setText(0, path.name)
            item.setData(0, Qt.UserRole, path)
            if path.is_dir():
                item.setText(1, "Folder")
                item.setIcon(0, fxicons.get_icon("folder"))
                item.setText(2, "-")
            else:
                item.setText(1, path.suffix.upper().lstrip(".") or "File")
                item.setIcon(0, fxicons.get_icon("description"))
                item.setText(2, _size_text(path))
            self._file_tree.addTopLevelItem(item)

        count = len(self._selected_files)
        self._count_label.setText(
            "1 file selected" if count == 1 else f"{count} files selected"
        )
        self._drop_area.setVisible(not has_files)
        self._file_tree.setVisible(has_files)
        self._count_label.setVisible(has_files)

    def _show_context_menu(self, position) -> None:
        """Offer to remove the file under `position`, or all of them."""
        item = self._file_tree.itemAt(position)
        if not item:
            return
        path = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        menu.addAction(fxicons.get_icon("delete"), "Remove").triggered.connect(
            lambda _=False: self._remove_file(path)
        )
        if len(self._selected_files) > 1:
            menu.addSeparator()
            menu.addAction(
                fxicons.get_icon("clear"), "Remove All"
            ).triggered.connect(self.clear)
        at = self._file_tree.viewport().mapToGlobal(position)
        fxutils.popup_menu(menu, at)

    def _remove_file(self, path: Path) -> None:
        """Drop `path` from the selection and say `file_removed`."""
        if path in self._selected_files:
            self._selected_files.remove(path)
            self._update_file_tree()
            self.file_removed.emit(path)

            if not self._selected_files:
                self.files_cleared.emit()

    def _browse(self) -> None:
        """Open file/folder browser dialog."""
        home = os.path.expanduser("~")
        if self._accept_mode == "folders":
            path = QFileDialog.getExistingDirectory(self, "Select Folder", home)
            self._take([Path(path)] if path else [])
            return
        if self._extensions:
            patterns = " ".join(f"*{ext}" for ext in sorted(self._extensions))
            filter_str = f"Allowed Files ({patterns});;All Files (*)"
        else:
            filter_str = "All Files (*)"
        if self._multiple:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Files", home, filter_str
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", home, filter_str
            )
            paths = [path] if path else []
        self._take([Path(p) for p in paths])

    def _on_files_added(self, paths: Iterable[Path]) -> bool:
        """Add the paths not held yet, say which; return whether any were."""
        new_files = [p for p in paths if p not in self._selected_files]
        if not new_files:
            return False
        if self._multiple:
            self._selected_files.extend(new_files)
        else:
            # One file replaces the last; the signal names what was kept.
            new_files = new_files[:1]
            self._selected_files = list(new_files)
        self._update_file_tree()
        self.files_dropped.emit(list(new_files))
        return True

    def _take(self, paths: List[Path]) -> None:
        """Add paths the user gave; without a list, flash the area."""
        if self._on_files_added(paths) and not self._show_tree:
            self._flash_feedback("success")

    def _accepts(self, path: Path) -> bool:
        """Return whether this zone takes `path`, by mode and extension."""
        if self._accept_mode != "files" and path.is_dir():
            return True
        if self._accept_mode != "folders" and path.is_file():
            return (
                self._extensions is None
                or path.suffix.lower() in self._extensions
            )
        return False

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept a drag that carries a path the zone takes."""
        if any(self._accepts(path) for path in _local_paths(event)):
            event.acceptProposedAction()
            self._set_drop_state("drag")
            self.drag_entered.emit()
            return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Return the area to rest."""
        self._set_drop_state("idle")
        self.drag_left.emit()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Add the accepted paths; edge the area in error if none were."""
        self._set_drop_state("idle")
        paths = _local_paths(event)
        accepted = [path for path in paths if self._accepts(path)]
        if not accepted:
            if paths:
                self._flash_feedback("error")
            event.ignore()
            return
        self._take(accepted)
        event.acceptProposedAction()

    # Public API

    def title(self) -> str:
        """Return the title text."""
        return self._title_label.text()

    def set_title(self, value: str) -> None:
        """Set the title text."""
        self._title_label.setText(value)

    def description(self) -> str:
        """Return the description text."""
        return self._description_label.text()

    def set_description(self, value: str) -> None:
        """Set the description text."""
        self._description_label.setText(value)

    def accept_mode(self) -> str:
        """Return the accept mode: 'files', 'folders' or 'both'."""
        return self._accept_mode

    def set_accept_mode(self, value: str) -> None:
        """Set the accept mode: 'files', 'folders' or 'both'.

        Raises:
            ValueError: `value` is not one of `ACCEPT_MODES`.
        """
        if value not in ACCEPT_MODES:
            raise ValueError(
                f"accept_mode {value!r} is not one of {ACCEPT_MODES}"
            )
        self._accept_mode = value
        if self._show_buttons:
            fxicons.set_icon(
                self._browse_btn,
                "folder_open" if value == "folders" else "file_open",
            )

    def extensions(self) -> Optional[Set[str]]:
        """Return the accepted extensions, lowercase with a leading dot."""
        return None if self._extensions is None else set(self._extensions)

    def set_extensions(self, value: Optional[Iterable[str]]) -> None:
        """Set the accepted extensions; None or none at all accepts all."""
        self._extensions = {
            "." + ext.lower().lstrip(".") for ext in value or ()
        } or None
        if self._extensions:
            self._formats_label.setText(
                f"Accepted formats: {', '.join(sorted(self._extensions))}"
            )
        self._formats_label.setVisible(
            bool(self._extensions) and self._show_formats
        )

    def multiple(self) -> bool:
        """Return whether multiple selection is enabled."""
        return self._multiple

    def set_multiple(self, value: bool) -> None:
        """Set whether multiple selection is enabled."""
        self._multiple = value

    def has_files(self) -> bool:
        """Return whether files have been added."""
        return bool(self._selected_files)

    def selected_files(self) -> List[Path]:
        """Return the list of selected files."""
        return self._selected_files.copy()

    def file_tree(self) -> Optional[QTreeWidget]:
        """Return the file tree widget, or None without `show_tree`."""
        return self._file_tree if self._show_tree else None

    def set_icon(self, icon_name: str) -> None:
        """Show the fxicons icon `icon_name` in the area."""
        self._icon_name = icon_name
        self._update_icon()

    def set_files(self, paths: List[Path]) -> None:
        """Replace the selected files, saying nothing."""
        self._selected_files = list(paths)
        self._update_file_tree()

    def add_files(self, paths: List[Path]) -> None:
        """Add the paths not held yet, saying `files_dropped`."""
        self._on_files_added(paths)

    def clear(self) -> None:
        """Remove every file and say `files_cleared`."""
        self.set_files([])
        self.files_cleared.emit()


fxstyle.register_widget_style("""
FXDropZone QWidget#FXDropZoneArea {
    border: 2px dashed @border;
    border-radius: @card_radius;
    background-color: @surface_sunken;
}
FXDropZone QWidget#FXDropZoneArea:hover {
    border-color: @border_light;
    background-color: @state_hover;
}
FXDropZone QWidget#FXDropZoneArea[dropState="drag"] {
    border-color: @accent_primary;
    background-color: @state_hover;
}
FXDropZone QWidget#FXDropZoneArea[dropState="success"] {
    border-color: @feedback_success_foreground;
    background-color: @state_hover;
}
FXDropZone QWidget#FXDropZoneArea[dropState="error"] {
    border-color: @feedback_error_foreground;
    background-color: @state_hover;
}
FXDropZone QLabel#FXDropZoneIcon {
    background: transparent;
    border: none;
}
FXDropZone QLabel#FXDropZoneTitle {
    color: @text;
    font-weight: 600;
    background: transparent;
    border: none;
}
FXDropZone QLabel#FXDropZoneFormats {
    color: @accent_primary;
    background: transparent;
    border: none;
}
FXDropZone QLabel#FXDropZoneDescription {
    color: @text_muted;
    background: transparent;
    border: none;
}
FXDropZone QLabel#FXDropZoneCount {
    color: @text_muted;
}
""")
