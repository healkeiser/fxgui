"""Navigation breadcrumb widget."""

# Built-in
import weakref
from functools import lru_cache
from typing import List, Optional

# Third-party
from qtpy.QtCore import QEvent, QRect, QRectF, Qt, Signal
from qtpy.QtGui import QColor, QPainter, QPen
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
    QToolBar,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._tips import apply_tip


fxstyle.register_widget_style(
    """
    QPushButton#fxBreadcrumbSegment,
    QPushButton#fxBreadcrumbSegment:hover,
    QPushButton#fxBreadcrumbSegment:pressed
    {
        background: transparent;
        border: 1px solid transparent;
        border-radius: @button_radius;
        padding: 3px 5px;
    }
    QPushButton#fxBreadcrumbSegment[fxFocusVisible="true"]:focus
    {
        border-color: @accent_primary;
    }
    """
)


def _ground(widget: QWidget) -> str:
    """Return the token of the colour `widget` sits on: frame or surface."""
    parent = widget.parentWidget()
    while parent is not None:
        if parent.property(fxstyle.FRAME_PROPERTY):
            return "frame"
        outer = parent.parentWidget()
        if isinstance(outer, QMainWindow):
            framed = bool(outer.property(fxstyle.FRAME_PROPERTY))
            on_bar = isinstance(parent, QToolBar)
            return "frame" if framed and on_bar else "surface"
        parent = outer
    return "surface"


def _strip_colors(ground: str, resting: str, hovered: str):
    """Return the strip's rest fill, hover fill, edge and ink on `ground`.

    The rest fill is `resting` or `surface`, whichever stands out more from
    the ground. The ink is `text` stepped until it reads at 4.5:1 on both
    fills, the edge `pane_border` stepped until it shows at
    `PANE_BORDER_MIN_CONTRAST` against the ground and both fills.
    """
    colors = fxstyle.colors()
    return _worked_out(
        getattr(colors, ground),
        getattr(colors, resting),
        colors.surface,
        getattr(colors, hovered),
        colors.text,
        colors.pane_border,
    )


# Keyed on the colours themselves, so a theme or colour file switch misses.
@lru_cache(maxsize=64)
def _worked_out(under, resting, surface, hover, text, pane_border):
    """Return the rest fill, hover fill, edge and ink from these colours."""
    rest = max(
        (resting, surface),
        key=lambda fill: fxstyle.get_contrast_ratio(fill, under),
    )
    ink = text
    for fill in (rest, hover):
        ink = fxstyle.readable_ink(fill, ink)
    edge = pane_border
    for other in (under, rest, hover):
        edge = fxstyle.readable_ink(
            other, edge, fxstyle.PANE_BORDER_MIN_CONTRAST
        )
    return rest, hover, edge, ink


class _Strip(QWidget):
    """The field behind the segments, painted from the theme each time."""

    def __init__(self, crumb: "FXBreadcrumb"):
        super().__init__()
        # A proxy: a strong reference to the parent is a cycle.
        self._crumb = weakref.proxy(crumb)

    def paintEvent(self, event) -> None:
        """Paint the strip's fill and edge."""
        rest, hover, edge, _ink = self._crumb._colors()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(edge), 1))
        painter.setBrush(QColor(hover if self._crumb._lit else rest))
        radius = fxstyle.BUTTON_RADIUS
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius
        )


class _Segment(QPushButton):
    """One path segment, its text in the strip's ink."""

    def __init__(self, crumb: "FXBreadcrumb", current: bool):
        super().__init__()
        self.setObjectName("fxBreadcrumbSegment")
        self.setFlat(True)
        # A proxy: a strong reference to the parent is a cycle.
        self._crumb = weakref.proxy(crumb)
        self._current = current
        if current:
            font = self.font()
            font.setBold(True)
            self.setFont(font)

    def paintEvent(self, event) -> None:
        """Paint the hover tint, the style's box, and the label in ink."""
        crumb = self._crumb
        painter = QStylePainter(self)
        if not self._current and self.underMouse():
            tint = QColor(getattr(fxstyle.colors(), crumb.SEGMENT_HOVER_TOKEN))
            tint.setAlpha(crumb.SEGMENT_HOVER_ALPHA)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(tint)
            painter.drawRoundedRect(
                QRectF(self.rect()),
                fxstyle.BUTTON_RADIUS,
                fxstyle.BUTTON_RADIUS,
            )
        option = QStyleOptionButton()
        self.initStyleOption(option)
        painter.drawControl(QStyle.CE_PushButtonBevel, option)
        contents = self.style().subElementRect(
            QStyle.SE_PushButtonContents, option, self
        )
        if self.icon().isNull():
            painter.setPen(QColor(crumb._colors()[3]))
            painter.drawText(contents, Qt.AlignCenter, self.text())
        else:
            box = QRect(contents.topLeft(), self.iconSize())
            box.moveCenter(contents.center())
            self.icon().paint(painter, box)


class FXBreadcrumb(QWidget):
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
        segments_focusable: Whether each segment takes a Tab stop. False
            leaves the path to the mouse; the back and forward buttons and
            the path editor keep theirs.

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

    # The theme tokens the strip and a hovered segment start from; a
    # subclass names its own. Not `surface` for the strip: in every theme
    # fxgui ships that is the window's own colour.
    STRIP_RESTING_TOKEN = "state_hover"
    STRIP_HOVERED_TOKEN = "border_light"
    SEGMENT_HOVER_TOKEN = "accent_primary"

    # A hovered segment's accent opacity, 0-255: a tint, which unlike a
    # border or a bolder weight shifts nothing beside it.
    SEGMENT_HOVER_ALPHA = 80

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        separator: str = "chevron_right",
        home_icon: str = "home",
        show_navigation: bool = False,
        path_separator: str = "/",
        home_path: Optional[List[str]] = None,
        segments_focusable: bool = True,
    ):
        super().__init__(parent)
        self._segments_focusable = segments_focusable
        self._lit = False

        self._path: List[str] = []
        self._separator = separator
        self._home_icon = home_icon
        self._show_navigation = show_navigation
        self._path_separator = path_separator
        self._home_path = list(home_path) if home_path else None

        # History tracking
        self._history: List[List[str]] = []
        self._history_index: int = -1

        # The buttons, the strip and the editor are a push button's height.
        side = fxstyle.control_height(self)

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Navigation buttons (optional)
        if self._show_navigation:
            self._back_button = QPushButton()
            self._back_button.setCursor(Qt.PointingHandCursor)
            self._back_button.setFixedSize(side, side)
            fxicons.set_icon(self._back_button, "arrow_back")
            self._back_button.clicked.connect(self.go_back)
            apply_tip(
                self._back_button,
                "Back",
                "Navigate to previous location",
            )

            self._forward_button = QPushButton()
            self._forward_button.setCursor(Qt.PointingHandCursor)
            self._forward_button.setFixedSize(side, side)
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
        self._stacked.setFixedHeight(side)

        # Scroll area for breadcrumb overflow
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # It never scrolls, so a Tab stop on it lands on nothing.
        self._scroll_area.setFocusPolicy(Qt.NoFocus)

        # Container widget for breadcrumb segments
        self._container = _Strip(self)
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
        # Installed last: the filter reads `_line_edit`.
        self._scroll_area.installEventFilter(self)
        self._container.installEventFilter(self)

        self._stacked.addWidget(self._scroll_area)  # Index 0: Breadcrumb
        self._stacked.addWidget(self._line_edit)  # Index 1: Edit mode
        self._stacked.setCurrentIndex(0)

        main_layout.addWidget(self._stacked)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(side)

        self._update_nav_buttons()

    def _colors(self):
        """Return the strip's rest fill, hover fill, edge and ink, now."""
        return _strip_colors(
            _ground(self),
            self.STRIP_RESTING_TOKEN,
            self.STRIP_HOVERED_TOKEN,
        )

    def set_edit_placeholder(self, text: str) -> None:
        """Set the hint the path editor shows while it is empty."""
        self._line_edit.setPlaceholderText(text)

    def enterEvent(self, event) -> None:
        """Brighten the strip while the pointer is anywhere over the path.

        Not a `:hover` rule: once the path is drawn, the widget directly
        under the pointer is a segment, never the strip.
        """
        super().enterEvent(event)
        self._lit = True
        self._container.update()

    def leaveEvent(self, event) -> None:
        """Return the strip to its resting fill."""
        super().leaveEvent(event)
        self._lit = False
        self._container.update()

    def eventFilter(self, obj, event):
        """Handle escape key and focus loss to exit edit mode.

        While the editor is up this widget also filters the application,
        to catch a press that lands outside it: focus loss alone covers
        only a press that lands on something focusable, and a press on a
        heading, a tree's own header or the window's background moves no
        focus at all -- which left the editor open with the artist
        looking at a path they had already left.
        """
        if event.type() == QEvent.Type.MouseButtonDblClick and (
            obj in (self._scroll_area, self._container)
            or (isinstance(obj, QWidget) and obj.parent() is self._container)
        ):
            self.enter_edit_mode()
            return True
        if (
            self.is_editing()
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(obj, QWidget)
            and obj is not self
            and not self.isAncestorOf(obj)
        ):
            self.exit_edit_mode()
        if obj == self._line_edit:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self.exit_edit_mode()
                    return True
            elif event.type() == QEvent.Type.FocusOut:
                # Exit edit mode when clicking outside
                self.exit_edit_mode()
        return super().eventFilter(obj, event)

    def enter_edit_mode(self) -> None:
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

    def exit_edit_mode(self) -> None:
        """Close the editor without submitting, as `Escape` does.

        Public: a window-level `Escape` shortcut fires before this widget
        sees the key, so such a window calls this itself.
        """
        self._stacked.setCurrentIndex(0)
        application = QApplication.instance()
        if application is not None:
            application.removeEventFilter(self)

    def _on_path_submitted(self) -> None:
        """Handle path submission from line edit."""
        text = self._line_edit.text().strip()
        if text:
            self.path_edited.emit(text)
        self.exit_edit_mode()

    def _update_nav_buttons(self) -> None:
        """Update the enabled state of navigation buttons."""
        if not self._show_navigation:
            return
        self._back_button.setEnabled(self._history_index > 0)
        self._forward_button.setEnabled(
            self._history_index < len(self._history) - 1
        )

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
            self.set_path(self._path[: index + 1])
            self.segment_clicked.emit(index, self.path())

    def clear(self) -> None:
        """Clear the breadcrumb path."""
        self._path.clear()
        self._rebuild_breadcrumb()

    def go_back(self) -> bool:
        """Navigate to the previous path in history.

        Returns:
            True if navigation occurred, False if at beginning of history.
        """
        return self._step(-1, self.navigated_back)

    def go_forward(self) -> bool:
        """Navigate to the next path in history.

        Returns:
            True if navigation occurred, False if at end of history.
        """
        return self._step(1, self.navigated_forward)

    def _step(self, by: int, signal) -> bool:
        """Move `by` places through history and announce it on `signal`."""
        index = self._history_index + by
        if not 0 <= index < len(self._history):
            return False
        self._history_index = index
        self._path = self._history[index].copy()
        self._rebuild_breadcrumb()
        self._update_nav_buttons()
        signal.emit(self.path())
        return True

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
        self._update_nav_buttons()

    def is_editing(self) -> bool:
        """Check if currently in edit mode."""
        return self._stacked.currentIndex() == 1

    def _rebuild_breadcrumb(self) -> None:
        """Rebuild the segments for the current path."""
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
        """Add a segment button; the last one is where the path already is."""
        button = _Segment(self, current=is_last)
        button.setCursor(
            Qt.PointingHandCursor if not is_last else Qt.ArrowCursor
        )
        if not self._segments_focusable:
            button.setFocusPolicy(Qt.NoFocus)

        if is_home and self._home_icon:
            fxicons.set_icon(button, self._home_icon)
            button.setToolTip(text)
        else:
            button.setText(text)

        if not is_last:
            if is_home:
                # Home button only triggers home navigation, not segment click
                button.clicked.connect(self._on_home_clicked)
            else:
                button.clicked.connect(
                    lambda _=False, idx=index: self.navigate_to(idx)
                )

        button.installEventFilter(self)

        # Insert before stretch
        self._layout.insertWidget(self._layout.count() - 1, button)

    def _add_separator(self) -> None:
        """Add a separator icon."""
        label = FXIconLabel(
            fxicons.get_icon(self._separator, color="text_muted"), size=12)
        label.setFixedSize(16, 16)
        label.setAlignment(Qt.AlignCenter)
        label.installEventFilter(self)

        self._layout.insertWidget(self._layout.count() - 1, label)

    def _on_home_clicked(self) -> None:
        """Go to the home path, or the first segment, and say home."""
        self.set_path(self._home_path or self._path[:1])
        self.home_clicked.emit()

    def home_path(self) -> Optional[List[str]]:
        """Return where a home click goes; None means the first segment."""
        return self._home_path.copy() if self._home_path else None

    def set_home_path(self, path: Optional[List[str]]) -> None:
        """Set the path a home click goes to; None means the first segment."""
        self._home_path = list(path) if path else None
