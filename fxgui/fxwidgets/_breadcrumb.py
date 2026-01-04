"""FXBreadcrumb - Navigation breadcrumb widget."""

from typing import List, Optional

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from fxgui import fxicons, fxstyle


class FXBreadcrumb(QWidget):
    """A clickable breadcrumb trail for hierarchical navigation.

    This widget provides a navigation breadcrumb with clickable path
    segments, separator icons, and overflow handling.

    Args:
        parent: Parent widget.
        separator: Separator string or icon name between segments.
        home_icon: Icon name for the home/root segment.
        max_visible: Maximum visible segments before truncation (0 = no limit).

    Signals:
        segment_clicked: Emitted when a segment is clicked (index, path list).
        home_clicked: Emitted when the home segment is clicked.

    Examples:
        >>> breadcrumb = FXBreadcrumb()
        >>> breadcrumb.set_path(["Home", "Projects", "MyProject", "Assets"])
        >>> breadcrumb.segment_clicked.connect(
        ...     lambda idx, path: print(f"Navigate to: {'/'.join(path[:idx+1])}")
        ... )
    """

    segment_clicked = Signal(int, list)
    home_clicked = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        separator: str = "chevron_right",
        home_icon: str = "home",
        max_visible: int = 0,
    ):
        super().__init__(parent)

        self._path: List[str] = []
        self._separator = separator
        self._home_icon = home_icon
        self._max_visible = max_visible

        # Get theme colors
        theme_colors = fxstyle.get_theme_colors()
        accent_colors = fxstyle.get_accent_colors()

        self._text_color = theme_colors["text"]
        self._text_secondary = theme_colors["text_secondary"]
        self._accent_color = accent_colors["primary"]

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for overflow
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setFixedHeight(28)

        # Container widget
        self._container = QWidget()
        self._layout = QHBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch()

        self._scroll_area.setWidget(self._container)
        main_layout.addWidget(self._scroll_area)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @property
    def path(self) -> List[str]:
        """Return the current path segments."""
        return self._path.copy()

    def set_path(self, path: List[str]) -> None:
        """Set the breadcrumb path.

        Args:
            path: List of path segment strings.
        """
        self._path = path.copy()
        self._rebuild_breadcrumb()

    def append_segment(self, segment: str) -> None:
        """Append a segment to the path.

        Args:
            segment: The segment string to append.
        """
        self._path.append(segment)
        self._rebuild_breadcrumb()

    def pop_segment(self) -> Optional[str]:
        """Remove and return the last segment.

        Returns:
            The removed segment, or None if path is empty.
        """
        if self._path:
            segment = self._path.pop()
            self._rebuild_breadcrumb()
            return segment
        return None

    def navigate_to(self, index: int) -> None:
        """Navigate to a specific path index, removing subsequent segments.

        Args:
            index: The index to navigate to.
        """
        if 0 <= index < len(self._path):
            self._path = self._path[:index + 1]
            self._rebuild_breadcrumb()
            self.segment_clicked.emit(index, self._path)

    def clear(self) -> None:
        """Clear the breadcrumb path."""
        self._path.clear()
        self._rebuild_breadcrumb()

    def _rebuild_breadcrumb(self) -> None:
        """Rebuild the breadcrumb UI."""
        # Clear existing widgets
        while self._layout.count() > 1:  # Keep stretch
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._path:
            return

        # Determine which segments to show
        segments_to_show = self._path
        start_index = 0
        show_ellipsis = False

        if self._max_visible > 0 and len(self._path) > self._max_visible:
            # Show home + ellipsis + last (max_visible - 2) segments
            segments_to_show = [self._path[0], "...", *self._path[-(self._max_visible - 2):]]
            start_index = len(self._path) - (self._max_visible - 2)
            show_ellipsis = True

        for i, segment in enumerate(segments_to_show):
            # Calculate actual index in path
            if show_ellipsis:
                if i == 0:
                    actual_index = 0
                elif segment == "...":
                    actual_index = -1  # Ellipsis, not clickable
                else:
                    actual_index = start_index + (i - 2)
            else:
                actual_index = i

            # Add separator before segment (except first)
            if i > 0:
                self._add_separator()

            # Add segment
            if segment == "...":
                self._add_ellipsis()
            else:
                is_last = (i == len(segments_to_show) - 1)
                is_home = (actual_index == 0)
                self._add_segment(segment, actual_index, is_home, is_last)

    def _add_segment(
        self, text: str, index: int, is_home: bool, is_last: bool
    ) -> None:
        """Add a segment button."""
        button = QPushButton()
        button.setCursor(Qt.PointingHandCursor if not is_last else Qt.ArrowCursor)
        button.setFlat(True)

        if is_home and self._home_icon:
            button.setIcon(fxicons.get_icon(self._home_icon))
            button.setToolTip(text)
        else:
            button.setText(text)

        # Style based on position
        if is_last:
            color = self._text_color
            hover_bg = "transparent"
        else:
            color = self._text_secondary
            hover_bg = "rgba(128, 128, 128, 0.2)"

        button.setStyleSheet(f"""
            QPushButton {{
                color: {color};
                background: transparent;
                border: none;
                padding: 4px 6px;
                border-radius: 3px;
                font-weight: {'bold' if is_last else 'normal'};
            }}
            QPushButton:hover {{
                background: {hover_bg};
                color: {self._accent_color if not is_last else color};
            }}
        """)

        if not is_last:
            button.clicked.connect(
                lambda checked, idx=index: self._on_segment_clicked(idx)
            )
            if is_home:
                button.clicked.connect(lambda: self.home_clicked.emit())

        # Insert before stretch
        self._layout.insertWidget(self._layout.count() - 1, button)

    def _add_separator(self) -> None:
        """Add a separator icon."""
        label = QLabel()
        label.setPixmap(
            fxicons.get_icon(
                self._separator, color=self._text_secondary
            ).pixmap(12, 12)
        )
        label.setStyleSheet("background: transparent;")
        label.setFixedSize(16, 16)
        label.setAlignment(Qt.AlignCenter)

        self._layout.insertWidget(self._layout.count() - 1, label)

    def _add_ellipsis(self) -> None:
        """Add an ellipsis indicator."""
        label = QLabel("...")
        label.setStyleSheet(f"""
            QLabel {{
                color: {self._text_secondary};
                background: transparent;
                padding: 4px 2px;
            }}
        """)
        self._layout.insertWidget(self._layout.count() - 1, label)

    def _on_segment_clicked(self, index: int) -> None:
        """Handle segment click."""
        self.navigate_to(index)


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    import os
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXBreadcrumb Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    breadcrumb = FXBreadcrumb()
    breadcrumb.set_segments(["Home", "Projects", "My Project", "Assets", "Textures"])

    info_label = QLabel("Click on a segment to navigate")

    def on_navigate(index, segment):
        info_label.setText(f"Navigated to: {segment} (index {index})")

    breadcrumb.navigated.connect(on_navigate)

    layout.addWidget(breadcrumb)
    layout.addWidget(info_label)
    layout.addStretch()

    window.resize(500, 150)
    window.show()
    sys.exit(app.exec())
