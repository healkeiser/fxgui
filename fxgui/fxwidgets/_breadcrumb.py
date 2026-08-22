"""Navigation breadcrumb widget."""

# Built-in
from typing import List, Optional

# Third-party
from qtpy.QtCore import QEvent, Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
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
from fxgui.fxwidgets._tips import apply_tip


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

    # Which theme colors the strip and the segments are drawn in, named
    # as tokens rather than hexes so a theme governs them, and named as
    # class attributes so a subclass with a house style of its own can
    # say which tokens without reimplementing any of the drawing.
    #
    # `STRIP_RESTING_TOKEN` must not be `surface`: in every theme fxgui
    # ships that is the window's own colour to the byte, so a strip
    # painted in it is a strip nobody can see.
    STRIP_RESTING_TOKEN = "state_hover"
    STRIP_HOVERED_TOKEN = "border_light"
    SEGMENT_HOVER_TOKEN = "accent_primary"

    # How much of that accent a hovered segment carries, 0-255. A tint
    # rather than a border or a bolder weight, because both of those
    # change the segment's own size and shift the text beside it on
    # hover, where a tint costs the layout nothing.
    SEGMENT_HOVER_ALPHA = 80

    # The corner the strip and a hovered segment are rounded by.
    RADIUS = 4

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
            apply_tip(
                self._back_button,
                "Back",
                "Navigate to previous location",
            )

            self._forward_button = QPushButton()
            self._forward_button.setCursor(Qt.PointingHandCursor)
            self._forward_button.setFixedSize(28, 28)
            fxicons.set_icon(self._forward_button, "arrow_forward")
            self._forward_button.clicked.connect(self.go_forward)
            apply_tip(
                self._forward_button,
                "Forward",
                "Navigate to next location",
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

        # Filled here as well as on every rebuild, so the widget is
        # already drawn correctly before the first event loop pass --
        # `FXThemeAware` applies the theme through a `singleShot(0)`.
        self._fill_strip(False)

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

    def _fill_strip(self, lit: bool) -> None:
        """Draw the strip as the field a double-click opens there.

        What a double-click opens is a line edit as wide as this whole
        widget, so what says where to double-click is that whole width
        filled: a surface, since it stands for a field about to appear
        rather than for one segment being pointed at.

        Painted on the container rather than on this widget, which is
        measured rather than chosen: the container covers the whole of
        this widget's own area, so a fill on the widget itself is
        painted and then painted over.

        Args:
            lit: Whether the pointer is over the widget, which is the
                brighter of the two fills.
        """
        colors = fxstyle.get_theme_colors()
        token = (
            self.STRIP_HOVERED_TOKEN if lit else self.STRIP_RESTING_TOKEN
        )
        self._container.setStyleSheet(
            f"background-color: {colors[token]};"
            f" border-radius: {self.RADIUS}px;"
        )

    def enterEvent(self, event) -> None:
        """Light the strip: the pointer is somewhere over the path.

        Answered here rather than by a `:hover` rule in the style,
        because such a rule can only ever light the widget the pointer
        is DIRECTLY over -- which, once the path is drawn, is a segment
        and never the container. Measured: this widget keeps the pointer
        through a move onto one of its own segments and reports it lost
        only when it leaves for good, which is exactly when the fill
        should drop.
        """
        super().enterEvent(event)
        self._fill_strip(True)

    def leaveEvent(self, event) -> None:
        """Drop the strip's fill: the pointer has left for good."""
        super().leaveEvent(event)
        self._fill_strip(False)

    def eventFilter(self, obj, event):
        """Handle escape key and focus loss to exit edit mode.

        While the editor is up this widget also filters the application,
        to catch a press that lands outside it: focus loss alone covers
        only a press that lands on something focusable, and a press on a
        heading, a tree's own header or the window's background moves no
        focus at all -- which left the editor open with the artist
        looking at a path they had already left.
        """
        if (
            self.is_editing()
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(obj, QWidget)
            and obj is not self
            and not self.isAncestorOf(obj)
        ):
            self._exit_edit_mode()
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
        # Watch the whole application while the editor is up, so a press
        # that moves no focus still closes it. Dropped again the moment
        # the editor closes, since this filter sees every event in the
        # process while it is installed.
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def _exit_edit_mode(self) -> None:
        """Switch back to breadcrumb mode."""
        self._stacked.setCurrentIndex(0)
        application = QApplication.instance()
        if application is not None:
            application.removeEventFilter(self)

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

    def exit_edit_mode(self) -> None:
        """Close the editor without submitting, as `Escape` does.

        Public because a window-level `Escape` shortcut is delivered
        BEFORE the focused widget sees the key, so this widget's own
        `Escape` handling never fires while such a shortcut exists. A
        window that has one asks `is_editing()` and hands the key over
        by calling this.
        """
        self._exit_edit_mode()

    def _rebuild_breadcrumb(self) -> None:
        """Rebuild the breadcrumb UI.

        The one hook every rebuild goes through, and the reason the
        segments' own marks are applied by `_add_segment` rather than
        after `set_path`: a path change is not the only thing that
        replaces those buttons -- a theme change rebuilds them too, to
        restyle them. Measured: marks applied after `set_path` were
        still on the button and gone one event loop pass later, the
        buttons having been replaced underneath.
        """
        # The container survives a rebuild, but the theme it was filled
        # from may not have, and a theme change arrives here.
        self._fill_strip(self.underMouse())

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

        # Minimal styling for flat segment buttons, plus the hover tint
        # that says a segment is the button it is. Every segment is a
        # `QPushButton` and none of them said so: flat text on the
        # window's own background, no cursor change, nothing under the
        # pointer, so the one control that walks the hierarchy read as a
        # label and an artist had no reason to try it.
        #
        # Declared in the segment's OWN stylesheet rather than in a rule
        # above it, because a widget that carries a style of its own
        # beats anything an ancestor writes for it.
        #
        # The last segment is where the path already is: it is not
        # connected to anything, so tinting it would promise a click
        # that does nothing.
        font_weight = "bold" if is_last else "normal"
        button.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                padding: 4px 6px;
                font-weight: {font_weight};
            }}
            {"" if is_last else self._segment_hover_rule()}
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

    def _segment_hover_rule(self) -> str:
        """The QSS rule that tints a clickable segment under the pointer.

        Read from the theme on every call rather than cached, since the
        running theme can change under a window and every rebuild comes
        back through here.

        Returns:
            str: A `QPushButton:hover` rule, ready to append to a
            segment's own stylesheet.
        """
        tint = QColor(fxstyle.get_theme_colors()[self.SEGMENT_HOVER_TOKEN])
        tint.setAlpha(self.SEGMENT_HOVER_ALPHA)
        return (
            "QPushButton:hover {"
            f" background-color: rgba({tint.red()}, {tint.green()},"
            f" {tint.blue()}, {tint.alpha()});"
            f" border-radius: {self.RADIUS}px; }}"
        )

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
