"""Navigation breadcrumb widget."""

# Built-in
from typing import List, Optional

# Third-party
from qtpy.QtCore import QEvent, Qt, Signal
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._tooltip import FXTooltip


class FXBreadcrumb(fxstyle.FXThemeAware, QWidget):
    """A clickable breadcrumb trail for hierarchical navigation.

    This widget provides a navigation breadcrumb with clickable path
    segments, separator icons, and optional back/forward navigation.
    Double-click the breadcrumb to switch to edit mode for typing paths.

    Args:
        parent: Parent widget.
        separator: Icon name for separator between segments.
        home_icon: Icon name for the home/root segment.
        show_navigation: Show back/forward navigation buttons.
        path_separator: Character used to join path segments in edit mode.
        home_path: Path segments to navigate to when home is clicked.
            If None, navigates to the first segment only.

    Signals:
        segment_clicked: Emitted when a segment is clicked (index, path list).
        home_clicked: Emitted when the home segment is clicked.
        path_edited: Emitted when user submits a typed path (raw string).
        navigated_back: Emitted when navigating back in history.
        navigated_forward: Emitted when navigating forward in history.

    Examples:
        >>> breadcrumb = FXBreadcrumb(show_navigation=True)
        >>> breadcrumb.set_path(["Home", "Projects", "MyProject", "Assets"])
        >>> breadcrumb.segment_clicked.connect(
        ...     lambda idx, path: print(f"Navigate to: {'/'.join(path[:idx+1])}")
        ... )
        >>> breadcrumb.path_edited.connect(lambda text: print(f"User typed: {text}"))
    """

    segment_clicked = Signal(int, list)
    home_clicked = Signal()
    path_edited = Signal(str)
    navigated_back = Signal(list)
    navigated_forward = Signal(list)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        separator: str = "chevron_right",
        home_icon: str = "home",
        show_navigation: bool = False,
        path_separator: str = "/",
        home_path: Optional[List[str]] = None,
    ):
        super().__init__(parent)

        self._path: List[str] = []
        self._separator = separator
        self._home_icon = home_icon
        self._show_navigation = show_navigation
        self._path_separator = path_separator
        self._home_path = home_path

        # History tracking
        self._history: List[List[str]] = []
        self._history_index: int = -1

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Navigation buttons (optional)
        if self._show_navigation:
            self._back_button = QPushButton()
            self._back_button.setCursor(Qt.PointingHandCursor)
            self._back_button.setFixedSize(28, 28)
            fxicons.set_icon(self._back_button, "arrow_back")
            self._back_button.clicked.connect(self.go_back)
            self._back_button_tooltip = FXTooltip(
                parent=self._back_button,
                title="Back",
                description="Navigate to previous location",
            )

            self._forward_button = QPushButton()
            self._forward_button.setCursor(Qt.PointingHandCursor)
            self._forward_button.setFixedSize(28, 28)
            fxicons.set_icon(self._forward_button, "arrow_forward")
            self._forward_button.clicked.connect(self.go_forward)
            self._forward_button_tooltip = FXTooltip(
                parent=self._forward_button,
                title="Forward",
                description="Navigate to next location",
            )

            main_layout.addWidget(self._back_button)
            main_layout.addWidget(self._forward_button)

        # Stacked widget to switch between breadcrumb and edit mode
        self._stacked = QStackedWidget()
        self._stacked.setFixedHeight(28)

        # Scroll area for breadcrumb overflow
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.mouseDoubleClickEvent = self._on_double_click

        # Container widget for breadcrumb segments
        self._container = QWidget()
        self._container.mouseDoubleClickEvent = self._on_double_click
        self._layout = QHBoxLayout(self._container)
        self._layout.setContentsMargins(4, 0, 4, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch()

        self._scroll_area.setWidget(self._container)

        # Line edit for manual path entry
        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("Enter path...")
        self._line_edit.returnPressed.connect(self._on_path_submitted)
        self._line_edit.installEventFilter(self)

        self._stacked.addWidget(self._scroll_area)  # Index 0: Breadcrumb
        self._stacked.addWidget(self._line_edit)  # Index 1: Edit mode
        self._stacked.setCurrentIndex(0)

        main_layout.addWidget(self._stacked)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(32)

        if self._show_navigation:
            self._update_nav_buttons()

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        # Re-apply icons with current theme color
        if self._show_navigation:
            fxicons.set_icon(self._back_button, "arrow_back")
            fxicons.set_icon(self._forward_button, "arrow_forward")

        # Rebuild breadcrumb to apply new segment styles
        self._rebuild_breadcrumb()

    def eventFilter(self, obj, event):
        """Handle escape key and focus loss to exit edit mode."""
        if obj == self._line_edit:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self._exit_edit_mode()
                    return True
            elif event.type() == QEvent.Type.FocusOut:
                # Exit edit mode when clicking outside
                self._exit_edit_mode()
        return super().eventFilter(obj, event)

    def _on_double_click(self, event) -> None:
        """Handle double-click to enter edit mode."""
        self._enter_edit_mode()

    def _enter_edit_mode(self) -> None:
        """Switch to edit mode with the line edit visible."""
        # Build path string, stripping trailing slashes from segments
        # to handle Windows drive letters like 'C:\\'
        if self._path:
            parts = [p.rstrip("\\/") for p in self._path]
            path_str = self._path_separator.join(parts)
        else:
            path_str = ""
        self._line_edit.setText(path_str)
        self._stacked.setCurrentIndex(1)
        self._line_edit.setFocus()
        self._line_edit.selectAll()

    def _exit_edit_mode(self) -> None:
        """Switch back to breadcrumb mode."""
        self._stacked.setCurrentIndex(0)

    def _on_path_submitted(self) -> None:
        """Handle path submission from line edit."""
        text = self._line_edit.text().strip()
        if text:
            self.path_edited.emit(text)
        self._exit_edit_mode()

    def _update_nav_buttons(self) -> None:
        """Update the enabled state of navigation buttons."""
        if not self._show_navigation:
            return
        self._back_button.setEnabled(self._history_index > 0)
        self._forward_button.setEnabled(
            self._history_index < len(self._history) - 1
        )

    @property
    def path(self) -> List[str]:
        """Return the current path segments."""
        return self._path.copy()

    def set_path(self, path: List[str], record_history: bool = True) -> None:
        """Set the breadcrumb path.

        Args:
            path: List of path segment strings.
            record_history: Whether to record this path in navigation history.
        """
        self._path = path.copy()
        self._rebuild_breadcrumb()

        if record_history and path:
            # Truncate forward history when navigating to new path
            if self._history_index < len(self._history) - 1:
                self._history = self._history[: self._history_index + 1]
            # Avoid duplicates
            if not self._history or self._history[-1] != path:
                self._history.append(path.copy())
                self._history_index = len(self._history) - 1
            if self._show_navigation:
                self._update_nav_buttons()

    def append_segment(self, segment: str) -> None:
        """Append a segment to the path.

        Args:
            segment: The segment string to append.
        """
        self._path.append(segment)
        self.set_path(self._path)

    def pop_segment(self) -> Optional[str]:
        """Remove and return the last segment.

        Returns:
            The removed segment, or None if path is empty.
        """
        if self._path:
            segment = self._path.pop()
            self.set_path(self._path)
            return segment
        return None

    def navigate_to(self, index: int) -> None:
        """Navigate to a specific path index, removing subsequent segments.

        Args:
            index: The index to navigate to.
        """
        if 0 <= index < len(self._path):
            self._path = self._path[: index + 1]
            self._rebuild_breadcrumb()
            self.segment_clicked.emit(index, self._path)

    def clear(self) -> None:
        """Clear the breadcrumb path."""
        self._path.clear()
        self._rebuild_breadcrumb()

    def go_back(self) -> bool:
        """Navigate to the previous path in history.

        Returns:
            True if navigation occurred, False if at beginning of history.
        """
        if self._history_index > 0:
            self._history_index -= 1
            self._path = self._history[self._history_index].copy()
            self._rebuild_breadcrumb()
            if self._show_navigation:
                self._update_nav_buttons()
            self.navigated_back.emit(self._path)
            return True
        return False

    def go_forward(self) -> bool:
        """Navigate to the next path in history.

        Returns:
            True if navigation occurred, False if at end of history.
        """
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._path = self._history[self._history_index].copy()
            self._rebuild_breadcrumb()
            if self._show_navigation:
                self._update_nav_buttons()
            self.navigated_forward.emit(self._path)
            return True
        return False

    def can_go_back(self) -> bool:
        """Check if back navigation is available."""
        return self._history_index > 0

    def can_go_forward(self) -> bool:
        """Check if forward navigation is available."""
        return self._history_index < len(self._history) - 1

    def clear_history(self) -> None:
        """Clear the navigation history."""
        self._history.clear()
        self._history_index = -1
        if self._show_navigation:
            self._update_nav_buttons()

    def is_editing(self) -> bool:
        """Check if currently in edit mode."""
        return self._stacked.currentIndex() == 1

    def enter_edit_mode(self) -> None:
        """Programmatically enter edit mode."""
        self._enter_edit_mode()

    def _rebuild_breadcrumb(self) -> None:
        """Rebuild the breadcrumb UI."""
        # Clear existing widgets
        while self._layout.count() > 1:  # Keep stretch
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._path:
            return

        for i, segment in enumerate(self._path):
            # Add separator before segment (except first)
            if i > 0:
                self._add_separator()

            is_last = i == len(self._path) - 1
            is_home = i == 0
            self._add_segment(segment, i, is_home, is_last)

    def _add_segment(
        self, text: str, index: int, is_home: bool, is_last: bool
    ) -> None:
        """Add a segment button."""
        button = QPushButton()
        button.setCursor(
            Qt.PointingHandCursor if not is_last else Qt.ArrowCursor
        )
        button.setFlat(True)

        if is_home and self._home_icon:
            fxicons.set_icon(button, self._home_icon)
            button.setToolTip(text)
        else:
            button.setText(text)

        # Minimal styling for flat segment buttons
        font_weight = "bold" if is_last else "normal"
        button.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                padding: 4px 6px;
                font-weight: {font_weight};
            }}
        """
        )

        if not is_last:
            if is_home:
                # Home button only triggers home navigation, not segment click
                button.clicked.connect(self._on_home_clicked)
            else:
                button.clicked.connect(
                    lambda checked, idx=index: self._on_segment_clicked(idx)
                )

        # Enable double-click on button to enter edit mode
        button.mouseDoubleClickEvent = self._on_double_click

        # Insert before stretch
        self._layout.insertWidget(self._layout.count() - 1, button)

    def _add_separator(self) -> None:
        """Add a separator icon."""
        label = QLabel()
        icon = fxicons.get_icon(
            self._separator, color=self.theme.text_muted
        )
        label.setPixmap(icon.pixmap(12, 12))
        label.setStyleSheet("background: transparent;")
        label.setFixedSize(16, 16)
        label.setAlignment(Qt.AlignCenter)
        label.mouseDoubleClickEvent = self._on_double_click

        self._layout.insertWidget(self._layout.count() - 1, label)

    def _on_segment_clicked(self, index: int) -> None:
        """Handle segment click."""
        self.navigate_to(index)

    def _on_home_clicked(self) -> None:
        """Handle home segment click."""
        self.home_clicked.emit()
        if self._home_path is not None:
            self.set_path(self._home_path)
            # Emit segment_clicked so external code can handle navigation
            self.segment_clicked.emit(len(self._home_path) - 1, self._path)
        else:
            # Navigate to first segment if no home_path set
            self.navigate_to(0)

    @property
    def home_path(self) -> Optional[List[str]]:
        """Get the home path."""
        return self._home_path.copy() if self._home_path else None

    @home_path.setter
    def home_path(self, path: Optional[List[str]]) -> None:
        """Set the home path."""
        self._home_path = path.copy() if path else None


def example() -> None:
    import sys
    from pathlib import Path
    from qtpy.QtWidgets import (
        QVBoxLayout,
        QWidget,
        QLabel,
        QTreeView,
    )
    from qtpy.QtWidgets import QFileSystemModel
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXBreadcrumb Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Start from home directory
    home_path = Path.home()
    print(home_path)

    breadcrumb = FXBreadcrumb(
        show_navigation=True,
        home_path=list(home_path.parts),
    )
    info_label = QLabel()

    # File system model and tree view
    model = QFileSystemModel()
    model.setRootPath(str(home_path))

    tree_view = QTreeView()
    tree_view.setModel(model)
    tree_view.setRootIndex(model.index(str(home_path)))
    tree_view.setColumnWidth(0, 250)
    # Hide Size, Type, Date Modified columns for cleaner view
    tree_view.setHeaderHidden(False)
    for col in range(1, model.columnCount()):
        tree_view.hideColumn(col)

    def navigate_to_path(path: Path):
        """Navigate to a filesystem path."""
        if path.exists() and path.is_dir():
            tree_view.setRootIndex(model.index(str(path)))
            breadcrumb.set_path(list(path.parts))
            info_label.setText(f"Current: {path}")
        else:
            info_label.setText(f"Invalid path: {path}")

    def on_tree_double_clicked(index):
        """Handle double-click on a directory in tree view."""
        path = Path(model.filePath(index))
        if path.is_dir():
            tree_view.setRootIndex(index)
            breadcrumb.set_path(list(path.parts))
            info_label.setText(f"Current: {path}")

    def on_segment_clicked(index: int, segments: List[str]):
        """Handle segment click navigation."""
        if segments:
            path = Path(*segments)
            tree_view.setRootIndex(model.index(str(path)))
            info_label.setText(f"Current: {path}")

    def on_navigated_back(segments: List[str]):
        """Handle back navigation."""
        if segments:
            path = Path(*segments)
            tree_view.setRootIndex(model.index(str(path)))
            info_label.setText(f"Current: {path}")

    def on_navigated_forward(segments: List[str]):
        """Handle forward navigation."""
        if segments:
            path = Path(*segments)
            tree_view.setRootIndex(model.index(str(path)))
            info_label.setText(f"Current: {path}")

    def on_path_edited(text: str):
        """Handle manually typed path."""
        path = Path(text)
        navigate_to_path(path)

    breadcrumb.segment_clicked.connect(on_segment_clicked)
    breadcrumb.navigated_back.connect(on_navigated_back)
    breadcrumb.navigated_forward.connect(on_navigated_forward)
    breadcrumb.path_edited.connect(on_path_edited)
    tree_view.doubleClicked.connect(on_tree_double_clicked)

    # Initialize
    breadcrumb.set_path(list(home_path.parts))
    info_label.setText(f"Current: {home_path}")

    layout.addWidget(breadcrumb)
    layout.addWidget(tree_view)
    layout.addWidget(info_label)

    window.resize(600, 500)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
