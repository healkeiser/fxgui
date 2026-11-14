"""Path input with browse button and validation indicator."""

# Built-in
import os
from typing import List, Optional

# Third-party
from qtpy.QtCore import Qt, QTimer, Signal
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
from fxgui.fxwidgets import _path_check
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._tips import apply_tip


MODES = ("file", "files", "folder", "save")


def _path_is_valid(path: str, mode: str) -> bool:
    """Return whether `path` exists as `mode` asks."""
    if not path:
        return False
    if mode == "folder":
        return os.path.isdir(path)
    if mode == "save":
        return os.path.isdir(os.path.dirname(path))
    return os.path.isfile(path)


def _droppable(paths: List[str], mode: str) -> List[str]:
    """Return the dropped paths the field takes in `mode`."""
    if mode == "files":
        return [p for p in paths if os.path.isfile(p)]
    return paths[:1] if paths and _path_is_valid(paths[0], mode) else []


class FXFilePathWidget(QWidget):
    """A path field with a Browse button, a drop target and a validity mark.

    The check runs on a worker thread, so a share that does not answer
    stalls the mark, never the window.

    Args:
        parent: Parent widget.
        mode: Selection mode: 'file', 'files', 'folder' or 'save'.
        placeholder: Placeholder text.
        file_filter: File filter for file dialogs (e.g., "Images (*.png *.jpg)").
        default_path: Default path for the file dialog.
        validate: Whether to show validation indicator.

    Raises:
        ValueError: `mode` is not one of `MODES`.

    Signals:
        path_changed: Emitted when the path changes.
        path_valid: Whether the path exists as the mode asks, after each
            check.

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

        self._file_filter = file_filter
        self._default_path = default_path or os.path.expanduser("~")
        self._validate = validate
        self._is_valid = False
        # Only the latest check's result lands; an earlier one may answer late.
        self._check_ticket = 0
        self._drop_ticket = 0
        # The list "files" mode showed last, so a ";" in a name survives.
        self._paths: List[str] = []

        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(300)  # ms
        self._validation_timer.timeout.connect(self._do_validation)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(fxstyle.PANE_GAP)

        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.textChanged.connect(self._on_text_changed)
        # A drop on the field reaches dropEvent, not the line edit's own
        # text drop.
        self._input.setAcceptDrops(False)
        layout.addWidget(self._input, 1)

        if validate:
            self._indicator = FXIconLabel()
            self._update_indicator()
            layout.addWidget(self._indicator)

        self._browse_btn = QPushButton()
        self._browse_btn.setCursor(Qt.PointingHandCursor)
        self.set_mode(mode)

        # A square as tall as a push button, beside a line edit as tall.
        side = fxstyle.control_height(self._browse_btn)
        self._browse_btn.setFixedSize(side, side)
        self._browse_btn.clicked.connect(self._browse)
        apply_tip(
            self._browse_btn,
            "Browse",
            "Open file browser to select a path",
        )
        layout.addWidget(self._browse_btn)

        self.setAcceptDrops(True)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def path(self) -> str:
        """Return the current path."""
        return self._input.text()

    def set_path(self, path: str) -> None:
        """Set the path shown."""
        self._input.setText(path)

    def paths(self) -> List[str]:
        """Return the paths in the field: several in "files" mode, else one.

        In "files" mode the field shows them joined by ";". A list given to
        `set_paths`, or picked or dropped, comes back whole even when a
        name holds a ";"; text typed by hand is split on ";".
        """
        text = self._input.text()
        if self._mode != "files":
            return [text] if text else []
        if self._paths and text == ";".join(self._paths):
            return list(self._paths)
        return [p.strip() for p in text.split(";") if p.strip()]

    def set_paths(self, paths: List[str]) -> None:
        """Show `paths`, joined by ";" in "files" mode.

        Raises:
            ValueError: More than one path outside "files" mode.
        """
        if self._mode != "files" and len(paths) > 1:
            raise ValueError(
                f"mode {self._mode!r} holds one path, got {len(paths)}")
        self._paths = list(paths)
        self._input.setText(";".join(paths))

    def is_valid(self) -> bool:
        """Return whether the current path is valid."""
        return self._is_valid

    def clear(self) -> None:
        """Clear the path input."""
        self._input.clear()

    def set_mode(self, mode: str) -> None:
        """Set the mode: 'file', 'files', 'folder' or 'save'.

        Raises:
            ValueError: `mode` is not one of `MODES`.
        """
        if mode not in MODES:
            raise ValueError(f"mode {mode!r} is not one of {MODES}")
        self._mode = mode
        fxicons.set_icon(
            self._browse_btn,
            "folder-open" if mode == "folder" else "file-input",
        )
        self._validation_timer.start()

    def set_file_filter(self, filter_str: str) -> None:
        """Set the dialogs' filter, such as "Images (*.png *.jpg)"."""
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
            if paths:
                self.set_paths(paths)
            return
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
        self._validation_timer.start()
        self.path_changed.emit(text)

    def _do_validation(self) -> None:
        """Start background validation (called after debounce)."""
        path = self._input.text()

        if not self._validate:
            return

        if not path:
            self._is_valid = False
            self._update_indicator()
            self.path_valid.emit(self._is_valid)
            return

        mode = self._mode
        paths = self.paths()
        self._check_ticket += 1
        ticket = self._check_ticket

        def check() -> tuple:
            if mode == "files":
                found = bool(paths) and all(
                    _path_is_valid(p, "file") for p in paths)
            else:
                found = _path_is_valid(path, mode)
            return ticket, path, found

        # Off the UI thread even when local: a local folder may link to a share.
        _path_check.run(
            self, "_on_validation_finished", check, paths, inline=False)

    def _on_validation_finished(
        self, ticket: int, path: str, is_valid: bool
    ) -> None:
        """Show the check's result if it is the latest, for the current text."""
        if ticket == self._check_ticket and path == self._input.text():
            self._is_valid = is_valid
            self._update_indicator()
            self.path_valid.emit(self._is_valid)

    def _update_indicator(self) -> None:
        """Update the validation indicator icon."""
        if not self._validate:
            return

        if not self._input.text():
            icon, ink, tip = "minus", "text_disabled", "No path entered"
        elif self._is_valid:
            icon, ink, tip = (
                "circle-check", "feedback_success_foreground", "Path exists")
        else:
            icon, ink, tip = (
                "circle-alert", "feedback_error_foreground", "Path does not exist")
        fxicons.set_icon(self._indicator, icon, color=ink)
        self._indicator.setToolTip(tip)

    def dragEnterEvent(self, event) -> None:
        """Handle drag enter for file drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """Take the dropped paths that exist, checked off the UI thread."""
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        mode = self._mode
        self._drop_ticket += 1
        ticket = self._drop_ticket
        _path_check.run(
            self,
            "_on_drop_checked",
            lambda: (ticket, _droppable(paths, mode)),
            paths,
        )

    def _on_drop_checked(self, ticket: int, paths: List[str]) -> None:
        """Show the dropped paths that passed the check, if still the latest."""
        if ticket == self._drop_ticket and paths:
            self.set_paths(paths)
