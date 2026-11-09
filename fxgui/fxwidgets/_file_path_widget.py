"""Path input with browse button and validation indicator."""

# Built-in
import os
import queue
import threading
import weakref
from typing import Callable, List, Optional, Tuple

# Third-party
from qtpy.QtCore import QObject, Qt, QTimer, Signal
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
    if mode == "files":
        paths = [p.strip() for p in path.split(";") if p.strip()]
        return bool(paths) and all(os.path.isfile(p) for p in paths)
    return os.path.isfile(path)


def _droppable(paths: List[str], mode: str) -> List[str]:
    """Return the dropped paths the field takes in `mode`."""
    if mode == "files":
        return [p for p in paths if os.path.isfile(p)]
    return paths[:1] if paths and _path_is_valid(paths[0], mode) else []


class _Relay(QObject):
    """Carries a worker's result back to the UI thread."""

    finished = Signal(object, str, object)


_relay: Optional[_Relay] = None
_jobs: "queue.SimpleQueue" = queue.SimpleQueue()
_workers: List[threading.Thread] = []
# A share that does not answer holds a worker; two keep a second share
# checking without flooding the process with stuck threads.
_WORKER_COUNT = 2


def _deliver(widget_ref, slot: str, args: tuple) -> None:
    """Hand a result to its widget if the widget is still alive."""
    widget = widget_ref()
    if widget is not None and is_valid_object(widget):
        getattr(widget, slot)(*args)


def _work() -> None:
    """Run disk checks forever, posting each result to the UI thread."""
    while True:
        widget_ref, slot, check = _jobs.get()
        try:
            args = check()
        except Exception:  # noqa: BLE001 - a failed check must not kill the worker
            continue
        _relay.finished.emit(widget_ref, slot, args)


def _check_off_thread(
    widget: QWidget, slot: str, check: Callable[[], Tuple]
) -> None:
    """Run `check` on a daemon worker and call `widget.slot(*result)`.

    Not the host's `QThreadPool`: a stuck check would starve it and hold
    its quit; a daemon thread never delays the process exit.
    """
    global _relay
    if _relay is None:
        _relay = _Relay()
        _relay.finished.connect(_deliver)
    _jobs.put((weakref.ref(widget), slot, check))
    if len(_workers) < _WORKER_COUNT:
        worker = threading.Thread(target=_work, name="fxgui-path-check", daemon=True)
        _workers.append(worker)
        worker.start()


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
        mode = self._mode
        _check_off_thread(
            self,
            "_on_validation_finished",
            lambda: (path, _path_is_valid(path, mode)),
        )

    def _on_validation_finished(self, path: str, is_valid: bool) -> None:
        """Handle validation result from background thread."""
        if path == self._input.text():
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
        _check_off_thread(
            self, "_on_drop_checked", lambda: (_droppable(paths, mode),)
        )

    def _on_drop_checked(self, paths: List[str]) -> None:
        """Show the dropped paths that passed the check."""
        if paths:
            self._input.setText(";".join(paths))
