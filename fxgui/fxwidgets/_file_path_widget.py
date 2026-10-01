"""Path input with browse button and validation indicator."""

# Built-in
import os
import weakref
from typing import Optional

# Third-party
from qtpy.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
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
from fxgui._compat import is_valid as is_valid_object
from fxgui.fxwidgets._tips import apply_tip


def _path_is_valid(path: str, mode: str) -> bool:
    """Return whether `path` exists as `mode` asks."""
    if not path:
        return False
    if mode == "folder":
        return os.path.isdir(path)
    if mode == "save":
        return os.path.isdir(os.path.dirname(path))
    if mode == "files":
        paths = [p.strip() for p in path.split(";") if p.strip()]
        return bool(paths) and all(os.path.isfile(p) for p in paths)
    return os.path.isfile(path)


class _Relay(QObject):
    """Carries a pool check's result back to the UI thread."""

    finished = Signal(object, str, bool)


_relay: Optional[_Relay] = None


def _deliver(widget_ref, path: str, is_valid: bool) -> None:
    """Hand a result to its widget if the widget is still alive."""
    widget = widget_ref()
    if widget is not None and is_valid_object(widget):
        widget._on_validation_finished(path, is_valid)


class _PathCheck(QRunnable):
    """One path check on the global thread pool."""

    def __init__(self, widget_ref, path: str, mode: str):
        super().__init__()
        self._widget_ref = widget_ref
        self._path = path
        self._mode = mode

    def run(self) -> None:
        """Check the path and post the result to the UI thread."""
        _relay.finished.emit(
            self._widget_ref, self._path, _path_is_valid(self._path, self._mode)
        )


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

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Path input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.setAcceptDrops(True)
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
        self._browse_btn.setCursor(Qt.PointingHandCursor)

        # Set icon based on mode
        if mode == "folder":
            fxicons.set_icon(self._browse_btn, "folder_open")
        else:
            fxicons.set_icon(self._browse_btn, "file_open")

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

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Debounce timer for validation
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(300)  # ms
        self._validation_timer.timeout.connect(self._do_validation)

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
        # Restart debounce timer for validation
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

        # A share that does not answer stalls the check, never the UI.
        global _relay
        if _relay is None:
            _relay = _Relay()
            _relay.finished.connect(_deliver)
        QThreadPool.globalInstance().start(
            _PathCheck(weakref.ref(self), path, self._mode)
        )

    def _on_validation_finished(self, path: str, is_valid: bool) -> None:
        """Handle validation result from background thread."""
        # Only update if path hasn't changed
        if path == self._input.text():
            self._is_valid = is_valid
            self._update_indicator()
            self.path_valid.emit(self._is_valid)

    def _update_indicator(self) -> None:
        """Update the validation indicator icon."""
        if not self._validate:
            return

        if not self._input.text():
            icon, ink, tip = "remove", "text_disabled", "No path entered"
        elif self._is_valid:
            icon, ink, tip = (
                "check_circle", "feedback_success_foreground", "Path exists")
        else:
            icon, ink, tip = (
                "error", "feedback_error_foreground", "Path does not exist")
        fxicons.set_icon(self._indicator, icon, color=ink)
        self._indicator.setToolTip(tip)

    def dragEnterEvent(self, event) -> None:
        """Handle drag enter for file drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """Handle file drop."""
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        if self._mode == "files":
            paths = [p for p in paths if os.path.isfile(p)]
            if paths:
                self._input.setText(";".join(paths))
        elif paths and _path_is_valid(paths[0], self._mode):
            self._input.setText(paths[0])
