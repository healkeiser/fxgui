"""Rich, theme-aware tooltip widget."""

# Built-in
import html
import os
import weakref
from enum import IntEnum
from typing import Callable, Optional, Union

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from qtpy.QtGui import (
    QColor,
    QCursor,
    QHelpEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QTableWidgetItem,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui._compat import is_valid
from fxgui.fxwidgets._delegates import FXThumbnailDelegate
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._tips import FXKeycap

fxstyle.register_widget_style(
    """
    FXTooltip #FXTooltipContent {
        background-color: @surface_sunken;
        border: 1px solid @border;
        border-radius: @card_radius;
    }
    FXTooltip #FXTooltipContent QLabel {
        background: transparent;
    }
    FXTooltip #FXTooltipTitle {
        color: @text;
        font-size: 13px;
    }
    FXTooltip #FXTooltipDescription {
        color: @text_muted;
        font-size: 12px;
    }
    FXTooltip #FXTooltipAction {
        background-color: transparent;
        color: @accent_primary;
        border: none;
        text-align: left;
        padding: 4px 0;
        font-size: 12px;
    }
    FXTooltip #FXTooltipAction:hover {
        text-decoration: underline;
    }
    """
)

_EXPLICIT = "fx_has_explicit_tooltip"

# Shown tooltips, held until hidden: garbage-collecting a visible
# FXTooltip crashes Qt (access violation)
_SHOWN: set = set()


class FXTooltipPosition(IntEnum):
    """Tooltip position relative to anchor widget."""

    AUTO = 0  # Automatically determine best position
    TOP = 1
    BOTTOM = 2
    LEFT = 3
    RIGHT = 4
    TOP_LEFT = 5
    TOP_RIGHT = 6
    BOTTOM_LEFT = 7
    BOTTOM_RIGHT = 8


class FXTooltip(QFrame):
    """A rich, theme-aware tooltip with advanced features.

    The everyday path for tooltips is `fxwidgets.apply_tip`, which formats a
    small HTML string and hands it to Qt's own `setToolTip`. This class is for
    what a native tooltip cannot do: hosting live widgets (icons, images,
    action buttons), staying up while the pointer is over the tooltip itself,
    persistent and programmatic show/hide, and arrow-anchored placement.

    This widget provides an enhanced tooltip experience with:
    - Rich content: title, description, icon, images, shortcuts
    - Smart positioning with arrow pointing to anchor
    - Theme-aware styling
    - Fade in/out animations
    - Hover or programmatic trigger
    - Configurable delays
    - Optional action buttons
    - Persistent mode (stays until clicked away)

    Args:
        parent: Parent widget (anchor for positioning).
        title: Optional title text (bold).
        description: Main tooltip content.
        icon: Optional icon name (from fxicons).
        image: Optional QPixmap image to display.
        shortcut: Optional keyboard shortcut to display.
        action_text: Optional action button text.
        action_callback: Callback for action button click.
        position: Preferred position relative to anchor.
        show_delay: Delay in ms before showing (default 500).
        hide_delay: Delay in ms before hiding after mouse leaves (default 200).
        duration: Auto-hide duration in ms (0 = no auto-hide).
        persistent: If True, tooltip stays until explicitly closed.
        show_arrow: Whether to show the pointing arrow.
        max_width: Maximum width of the tooltip.

    Signals:
        shown: Emitted when the tooltip is shown.
        hidden: Emitted when the tooltip is hidden.
        action_clicked: Emitted when the action button is clicked.

    Examples:
        >>> # Simple tooltip attached to a button
        >>> tooltip = FXTooltip(
        ...     parent=my_button,
        ...     title="Save",
        ...     description="Save the current file to disk",
        ...     shortcut="Ctrl+S",
        ... )
        >>>
        >>> # Rich tooltip with image and action
        >>> tooltip = FXTooltip(
        ...     parent=my_widget,
        ...     title="New Feature!",
        ...     description="Click here to learn about the new export options.",
        ...     icon="lightbulb",
        ...     action_text="Learn More",
        ...     action_callback=lambda: show_help(),
        ...     persistent=True,
        ... )
        >>>
        >>> # Programmatic show/hide
        >>> tooltip.show_tooltip()
        >>> tooltip.hide_tooltip()
    """

    shown = Signal()
    hidden = Signal()
    action_clicked = Signal()

    # Arrow size
    ARROW_SIZE = 8

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None,
        description: str = "",
        icon: Optional[str] = None,
        image: Optional[QPixmap] = None,
        shortcut: Optional[str] = None,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        position: FXTooltipPosition = FXTooltipPosition.AUTO,
        show_delay: int = 500,
        hide_delay: int = 200,
        duration: int = 0,
        persistent: bool = False,
        show_arrow: bool = True,
        max_width: int = 300,
    ):
        # We use parent for positioning reference but tooltip is top-level
        super().__init__(None)  # No parent - we manage our own window

        self._anchor = parent
        self._title = title
        self._description = description
        self._icon_name = icon
        self._image = image
        self._shortcut = shortcut
        self._action_text = action_text
        self._action_callback = action_callback
        self._position = position
        self._show_delay = show_delay
        self._hide_delay = hide_delay
        self._duration = duration
        self._persistent = persistent
        self._show_arrow = show_arrow
        self._max_width = max_width

        # Computed arrow position
        self._arrow_position = FXTooltipPosition.TOP
        self._arrow_offset = 0  # Horizontal/vertical offset for arrow

        # A one-shot tooltip closes (and is deleted) once it has faded out
        self._one_shot = False
        self._watching_app = False
        self._previous_explicit = None

        # Timers
        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._do_show)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._do_hide)

        self._duration_timer = QTimer(self)
        self._duration_timer.setSingleShot(True)
        self._duration_timer.timeout.connect(self.hide_tooltip)


        # Setup window flags - use Window with FramelessWindowHint
        # Qt.Tool keeps it on top without taskbar entry
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)  # Ensure cleanup on close
        self.setAttribute(
            Qt.WA_QuitOnClose, False
        )  # Don't block app from quitting

        # Frame styling
        self.setFrameShape(QFrame.NoFrame)
        self.setMaximumWidth(max_width)

        # Setup UI
        self._setup_ui()

        # Fade animation using window opacity
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_animation.setDuration(150)
        self._fade_animation.finished.connect(self._on_fade_finished)

        self._anchor = None
        self._attach(parent)

        # Track mouse for hide delay
        self.setMouseTracking(True)

        # A parentless window is outside every themed root
        fxstyle.register_themed_root(self)

    def _setup_ui(self) -> None:
        """Setup the tooltip UI."""
        # Content container with padding for arrow
        self._content_widget = QFrame(self)
        self._content_widget.setObjectName("FXTooltipContent")

        # Main layout with margins for arrow space
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self.ARROW_SIZE, self.ARROW_SIZE, self.ARROW_SIZE, self.ARROW_SIZE
        )
        main_layout.addWidget(self._content_widget)

        # Content layout
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(6)

        # Header row (icon + title + shortcut)
        if self._title or self._icon_name or self._shortcut:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(8)

            # Icon
            if self._icon_name:
                self._icon_label = FXIconLabel(size=20)
                self._icon_label.setFixedSize(20, 20)
                header_layout.addWidget(self._icon_label)

            # Title
            if self._title:
                self._title_label = QLabel(self._title)
                self._title_label.setObjectName("FXTooltipTitle")
                font = self._title_label.font()
                font.setBold(True)
                self._title_label.setFont(font)
                header_layout.addWidget(self._title_label)

            header_layout.addStretch()

            # Shortcut badge
            if self._shortcut:
                self._shortcut_label = FXKeycap(self._shortcut)
                header_layout.addWidget(self._shortcut_label)

            content_layout.addLayout(header_layout)

        # Image
        if self._image:
            self._image_label = QLabel()
            self._image_label.setPixmap(
                self._image.scaledToWidth(
                    self._max_width - 40, Qt.SmoothTransformation
                )
            )
            self._image_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(self._image_label)

        # Description
        if self._description:
            self._desc_label = QLabel(self._description)
            self._desc_label.setObjectName("FXTooltipDescription")
            self._desc_label.setWordWrap(True)
            self._desc_label.setTextFormat(Qt.RichText)
            content_layout.addWidget(self._desc_label)

        # Action button
        if self._action_text:
            self._action_button = QPushButton(self._action_text)
            self._action_button.setObjectName("FXTooltipAction")
            self._action_button.setCursor(Qt.PointingHandCursor)
            self._action_button.clicked.connect(self._on_action_clicked)
            content_layout.addWidget(self._action_button)

        # Drop shadow on content
        fxutils.add_shadows(self._content_widget, self._content_widget)
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        """Give the header its icon, inked with the accent when drawn."""
        if self._icon_name and hasattr(self, "_icon_label"):
            self._icon_label.setIcon(
                fxicons.get_icon(self._icon_name, color="accent_primary")
            )

    def eventFilter(self, watched, event) -> bool:
        """Handle hover events on anchor widget and click-outside detection."""
        # The app-wide filter sees every press while the tooltip is shown
        if (
            self._watching_app
            and event.type() == QEvent.MouseButtonPress
            and self.isVisible()
        ):
            if hasattr(event, "globalPosition"):
                global_pos = event.globalPosition().toPoint()
            else:
                global_pos = event.globalPos()
            if not self.geometry().contains(global_pos):
                self.hide_tooltip()

        if watched == self._anchor:
            # A window closing hides its children without deleting them.
            if event.type() == QEvent.Hide and self.isVisible():
                self.hide_tooltip()
            # Handle hover for non-persistent tooltips
            if not self._persistent:
                if event.type() == QEvent.Enter:
                    self._hide_timer.stop()
                    if not self.isVisible():
                        self._show_timer.start(self._show_delay)
                elif event.type() == QEvent.Leave:
                    self._show_timer.stop()
                    # Check if mouse moved to tooltip
                    if not self.geometry().contains(QCursor.pos()):
                        self._hide_timer.start(self._hide_delay)

            # Handle move/resize events to reposition visible tooltip
            if event.type() in (QEvent.Move, QEvent.Resize):
                if self.isVisible():
                    self.move(self._place(self._anchor_rect(), self._position))
                    self.update()

        return super().eventFilter(watched, event)

    def enterEvent(self, event) -> None:
        """Handle mouse entering tooltip."""
        self._hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leaving tooltip."""
        if not self._persistent:
            self._hide_timer.start(self._hide_delay)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Handle click to dismiss persistent tooltip."""
        if self._persistent:
            self.hide_tooltip()
        super().mousePressEvent(event)

    def _on_anchor_destroyed(self) -> None:
        """Handle anchor widget being destroyed."""
        self._anchor = None
        self.close()

    def _on_action_clicked(self) -> None:
        """Handle action button click."""
        self.action_clicked.emit()
        if self._action_callback:
            self._action_callback()
        self.hide_tooltip()

    def _attach(self, widget: Optional[QWidget]) -> None:
        """Anchor to a widget: follow it, and mark it for the manager.

        The global FXTooltipManager stays silent on a marked anchor, so one
        hover never shows two tooltips; `_detach` restores the mark.
        """
        self._anchor = widget
        if widget is None:
            return
        widget.installEventFilter(self)
        # Not a bound method: dropping this tooltip can free the anchor, and
        # its destroyed signal would then call into the half-freed tooltip.
        tooltip = weakref.ref(self)

        def gone(*_args) -> None:
            alive = tooltip()
            # At exit Qt may delete the tooltip before its anchor.
            if alive is not None and is_valid(alive):
                alive._on_anchor_destroyed()

        self._anchor_gone = gone
        widget.destroyed.connect(gone)
        self._previous_explicit = widget.property(_EXPLICIT)
        widget.setProperty(_EXPLICIT, True)

    def _detach(self) -> None:
        """Let go of the anchor and hand its mark back."""
        if self._anchor is None:
            return
        self._anchor.removeEventFilter(self)
        self._anchor.setProperty(_EXPLICIT, self._previous_explicit)
        try:
            self._anchor.destroyed.disconnect(self._anchor_gone)
        except (RuntimeError, TypeError):
            pass
        self._anchor = None

    def _anchor_rect(self) -> QRect:
        """Return the anchor's global rect, or the cursor's point without one."""
        if not self._anchor:
            return QRect(QCursor.pos(), QSize(1, 1))
        return QRect(
            self._anchor.mapToGlobal(QPoint(0, 0)), self._anchor.size()
        )

    def _place(
        self, rect: QRect, position: FXTooltipPosition
    ) -> QPoint:
        """Return where the tooltip goes beside a global rect; aims the arrow."""
        screen = QApplication.screenAt(rect.topLeft())
        if not screen:
            screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        self.adjustSize()
        tooltip_size = self.sizeHint()
        if position == FXTooltipPosition.AUTO:
            position = self._find_best_position(
                rect, tooltip_size, screen_rect
            )
        x, y, self._arrow_offset = self._calculate_coordinates(
            position, rect, tooltip_size, screen_rect
        )
        return QPoint(x, y)

    def _find_best_position(
        self, anchor_rect: QRect, tooltip_size, screen_rect: QRect
    ) -> FXTooltipPosition:
        """Find the best position for the tooltip."""
        tw, th = tooltip_size.width(), tooltip_size.height()
        margin = 10

        # Check each position for available space
        space_below = screen_rect.bottom() - anchor_rect.bottom() - margin
        space_above = anchor_rect.top() - screen_rect.top() - margin
        space_right = screen_rect.right() - anchor_rect.right() - margin
        space_left = anchor_rect.left() - screen_rect.left() - margin

        # Prefer bottom, then top, then right, then left
        if space_below >= th:
            return FXTooltipPosition.BOTTOM
        elif space_above >= th:
            return FXTooltipPosition.TOP
        elif space_right >= tw:
            return FXTooltipPosition.RIGHT
        elif space_left >= tw:
            return FXTooltipPosition.LEFT
        else:
            # Default to bottom even if it doesn't fit perfectly
            return FXTooltipPosition.BOTTOM

    def _calculate_coordinates(
        self,
        position: FXTooltipPosition,
        anchor_rect: QRect,
        tooltip_size,
        screen_rect: QRect,
    ) -> tuple:
        """Calculate x, y coordinates and arrow offset."""
        tw, th = tooltip_size.width(), tooltip_size.height()
        margin = 8

        # Center of anchor
        anchor_cx = anchor_rect.center().x()
        anchor_cy = anchor_rect.center().y()

        if position in (
            FXTooltipPosition.BOTTOM,
            FXTooltipPosition.BOTTOM_LEFT,
            FXTooltipPosition.BOTTOM_RIGHT,
        ):
            y = anchor_rect.bottom() + margin
            if position == FXTooltipPosition.BOTTOM:
                x = anchor_cx - tw // 2
            elif position == FXTooltipPosition.BOTTOM_LEFT:
                x = anchor_rect.left()
            else:
                x = anchor_rect.right() - tw
            self._arrow_position = FXTooltipPosition.TOP

        elif position in (
            FXTooltipPosition.TOP,
            FXTooltipPosition.TOP_LEFT,
            FXTooltipPosition.TOP_RIGHT,
        ):
            y = anchor_rect.top() - th - margin
            if position == FXTooltipPosition.TOP:
                x = anchor_cx - tw // 2
            elif position == FXTooltipPosition.TOP_LEFT:
                x = anchor_rect.left()
            else:
                x = anchor_rect.right() - tw
            self._arrow_position = FXTooltipPosition.BOTTOM

        elif position == FXTooltipPosition.RIGHT:
            x = anchor_rect.right() + margin
            y = anchor_cy - th // 2
            self._arrow_position = FXTooltipPosition.LEFT

        elif position == FXTooltipPosition.LEFT:
            x = anchor_rect.left() - tw - margin
            y = anchor_cy - th // 2
            self._arrow_position = FXTooltipPosition.RIGHT

        else:
            x = anchor_cx - tw // 2
            y = anchor_rect.bottom() + margin
            self._arrow_position = FXTooltipPosition.TOP

        # Clamp to screen bounds
        x = max(
            screen_rect.left() + margin,
            min(x, screen_rect.right() - tw - margin),
        )
        y = max(
            screen_rect.top() + margin,
            min(y, screen_rect.bottom() - th - margin),
        )

        # Calculate arrow offset (how far from center the arrow should be)
        if self._arrow_position in (
            FXTooltipPosition.TOP,
            FXTooltipPosition.BOTTOM,
        ):
            # Arrow points horizontally toward anchor center
            arrow_target = anchor_cx - x
            arrow_offset = max(20, min(arrow_target, tw - 20))
        else:
            # Arrow points vertically toward anchor center
            arrow_target = anchor_cy - y
            arrow_offset = max(20, min(arrow_target, th - 20))

        return x, y, arrow_offset

    def paintEvent(self, event) -> None:
        """Paint the tooltip with arrow."""
        super().paintEvent(event)

        if not self._show_arrow:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Arrow dimensions
        arrow_size = self.ARROW_SIZE

        # Get content rect
        content_rect = self._content_widget.geometry()

        # Draw arrow based on position
        arrow_polygon = QPolygonF()

        if self._arrow_position == FXTooltipPosition.TOP:
            # Arrow pointing up (tooltip below anchor)
            ax = self._arrow_offset
            ay = content_rect.top()
            arrow_polygon.append(QPointF(ax, ay - arrow_size))
            arrow_polygon.append(QPointF(ax - arrow_size, ay))
            arrow_polygon.append(QPointF(ax + arrow_size, ay))

        elif self._arrow_position == FXTooltipPosition.BOTTOM:
            # Arrow pointing down (tooltip above anchor)
            ax = self._arrow_offset
            ay = content_rect.bottom()
            arrow_polygon.append(QPointF(ax, ay + arrow_size))
            arrow_polygon.append(QPointF(ax - arrow_size, ay))
            arrow_polygon.append(QPointF(ax + arrow_size, ay))

        elif self._arrow_position == FXTooltipPosition.LEFT:
            # Arrow pointing left (tooltip right of anchor)
            ax = content_rect.left()
            ay = self._arrow_offset
            arrow_polygon.append(QPointF(ax - arrow_size, ay))
            arrow_polygon.append(QPointF(ax, ay - arrow_size))
            arrow_polygon.append(QPointF(ax, ay + arrow_size))

        elif self._arrow_position == FXTooltipPosition.RIGHT:
            # Arrow pointing right (tooltip left of anchor)
            ax = content_rect.right()
            ay = self._arrow_offset
            arrow_polygon.append(QPointF(ax + arrow_size, ay))
            arrow_polygon.append(QPointF(ax, ay - arrow_size))
            arrow_polygon.append(QPointF(ax, ay + arrow_size))

        theme = fxstyle.colors()
        path = QPainterPath()
        path.addPolygon(arrow_polygon)
        path.closeSubpath()
        painter.fillPath(path, QColor(theme.surface_sunken))
        painter.setPen(QPen(QColor(theme.border), 1))
        painter.drawPolyline(arrow_polygon)

    def _fade_in_at(self, pos: QPoint) -> None:
        """Move to a global point, fade in and watch for clicks outside."""
        self.move(pos)
        self._fade_animation.stop()
        self.setWindowOpacity(0.0)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)

        QApplication.instance().installEventFilter(self)
        self._watching_app = True
        _SHOWN.add(self)

        self.show()
        self.raise_()
        self._fade_animation.start()

        if self._duration > 0:
            self._duration_timer.start(self._duration)

        self.shown.emit()

    def _do_show(self) -> None:
        """Actually show the tooltip."""
        self._fade_in_at(self._place(self._anchor_rect(), self._position))

    def _do_hide(self) -> None:
        """Actually hide the tooltip with fade out."""
        self._duration_timer.stop()
        if not self.isVisible():
            self._on_fade_finished_hidden()
            return
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self.windowOpacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.start()

    def _on_fade_finished(self) -> None:
        """Finish a fade out; a finished fade in needs nothing."""
        if self._fade_animation.endValue() == 0.0:
            self._on_fade_finished_hidden()

    def _on_fade_finished_hidden(self) -> None:
        """Hide, stop watching the app, and close a one-shot tooltip."""
        if self._watching_app:
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self)
            self._watching_app = False
        was_visible = self.isVisible()
        self.hide()
        if was_visible:
            self.hidden.emit()
        if self._one_shot:
            self.close()
        _SHOWN.discard(self)

    def closeEvent(self, event) -> None:
        """Hand the anchor back to the tooltip manager on close."""
        if self._watching_app:
            QApplication.instance().removeEventFilter(self)
            self._watching_app = False
        self._detach()
        _SHOWN.discard(self)
        super().closeEvent(event)

    def show_tooltip(self) -> None:
        """Programmatically show the tooltip."""
        self._hide_timer.stop()
        self._show_timer.stop()
        self._do_show()

    def hide_tooltip(self) -> None:
        """Programmatically hide the tooltip."""
        self._show_timer.stop()
        self._hide_timer.stop()
        self._do_hide()

    def set_content(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        shortcut: Optional[str] = None,
    ) -> None:
        """Update tooltip content dynamically.

        Args:
            title: New title text.
            description: New description text.
            icon: New icon name.
            shortcut: New shortcut text.
        """
        if title is not None and hasattr(self, "_title_label"):
            self._title_label.setText(title)
        if description is not None and hasattr(self, "_desc_label"):
            self._desc_label.setText(description)
        if shortcut is not None and hasattr(self, "_shortcut_label"):
            self._shortcut_label.setText(shortcut)
        if icon is not None:
            self._icon_name = icon
            self._refresh_icon()

    def set_anchor(self, widget: QWidget) -> None:
        """Change the anchor widget.

        Args:
            widget: New anchor widget.
        """
        self._detach()
        self._attach(widget)

    def show_at_rect(
        self,
        rect: QRect,
        position: Optional[FXTooltipPosition] = None,
    ) -> None:
        """Show tooltip positioned relative to a global rectangle.

        This is useful for showing tooltips relative to tree items, table cells,
        or other sub-widget regions that aren't QWidget instances.

        Args:
            rect: Rectangle in global (screen) coordinates to position relative to.
            position: Optional position override. Uses instance position if None.

        Examples:
            >>> # Show tooltip for a tree item
            >>> item_rect = tree.visualItemRect(item)
            >>> global_rect = QRect(
            ...     tree.viewport().mapToGlobal(item_rect.topLeft()),
            ...     item_rect.size()
            ... )
            >>> tooltip.show_at_rect(global_rect)
        """
        self._hide_timer.stop()
        self._show_timer.stop()
        if position is None:
            position = self._position
        self._fade_in_at(self._place(rect, position))

    def show_at_point(
        self,
        global_pos: QPoint,
        position: FXTooltipPosition = FXTooltipPosition.BOTTOM,
    ) -> None:
        """Show tooltip at a specific global position.

        The tooltip will be positioned relative to the given point,
        treating it as a zero-size anchor.

        Args:
            global_pos: Global (screen) coordinates where tooltip should appear.
            position: Which direction the tooltip should extend from the point.

        Examples:
            >>> # Show tooltip at cursor position
            >>> tooltip.show_at_point(QCursor.pos())
            >>>
            >>> # Show tooltip below a specific point
            >>> tooltip.show_at_point(some_global_point, FXTooltipPosition.BOTTOM)
        """
        # Create a small rect at the point
        rect = QRect(global_pos.x(), global_pos.y(), 1, 1)
        self.show_at_rect(rect, position)

    @staticmethod
    def show_for_widget(
        widget: QWidget,
        title: Optional[str] = None,
        description: str = "",
        icon: Optional[str] = None,
        shortcut: Optional[str] = None,
        duration: int = 3000,
        position: FXTooltipPosition = FXTooltipPosition.AUTO,
    ) -> "FXTooltip":
        """Convenience method to show a tooltip for a widget.

        Creates and shows a tooltip immediately, auto-hiding after duration.

        Args:
            widget: Widget to show tooltip for.
            title: Optional title.
            description: Tooltip description.
            icon: Optional icon name.
            shortcut: Optional shortcut text.
            duration: Auto-hide duration in ms.
            position: Tooltip position.

        Returns:
            The created FXTooltip instance.

        Examples:
            >>> FXTooltip.show_for_widget(
            ...     button,
            ...     title="Tip",
            ...     description="Click to save",
            ...     duration=2000
            ... )
        """
        tooltip = FXTooltip(
            parent=widget,
            title=title,
            description=description,
            icon=icon,
            shortcut=shortcut,
            duration=duration,
            position=position,
            persistent=True,  # Persistent=True means no hover detection
            show_delay=0,
        )
        tooltip._one_shot = True
        tooltip.show_tooltip()
        return tooltip

    @staticmethod
    def show_for_rect(
        rect: QRect,
        title: Optional[str] = None,
        description: str = "",
        icon: Optional[str] = None,
        shortcut: Optional[str] = None,
        duration: int = 3000,
        position: FXTooltipPosition = FXTooltipPosition.AUTO,
        max_width: int = 300,
    ) -> "FXTooltip":
        """Convenience method to show a tooltip for a screen rectangle.

        Creates and shows a tooltip immediately, auto-hiding after duration.
        Useful for tree items, table cells, or other non-widget regions.

        Args:
            rect: Rectangle in global (screen) coordinates.
            title: Optional title.
            description: Tooltip description.
            icon: Optional icon name.
            shortcut: Optional shortcut text.
            duration: Auto-hide duration in ms.
            position: Tooltip position.
            max_width: Maximum width of the tooltip.

        Returns:
            The created FXTooltip instance.

        Examples:
            >>> # Show tooltip for a tree item
            >>> item_rect = tree.visualItemRect(item)
            >>> global_rect = QRect(
            ...     tree.viewport().mapToGlobal(item_rect.topLeft()),
            ...     item_rect.size()
            ... )
            >>> FXTooltip.show_for_rect(
            ...     global_rect,
            ...     title="Item Info",
            ...     description="Details about this item",
            ...     duration=2000
            ... )
        """
        tooltip = FXTooltip(
            parent=None,
            title=title,
            description=description,
            icon=icon,
            shortcut=shortcut,
            duration=duration,
            position=position,
            persistent=True,  # Persistent=True means no hover detection
            show_delay=0,
            max_width=max_width,
        )
        tooltip._one_shot = True
        tooltip.show_at_rect(rect, position)
        return tooltip


class FXTooltipManager(QObject):
    """Global manager that intercepts standard Qt tooltips and shows FXTooltip instead.

    This allows you to use the standard `widget.setToolTip("text")` API
    and have FXTooltip displayed automatically.

    The manager installs an application-wide event filter that intercepts
    QEvent.ToolTip events and shows an FXTooltip with the widget's tooltip text.

    Args:
        parent: Parent QObject (typically QApplication.instance()).
        show_delay: Delay in ms before showing tooltip (default 500).
        hide_delay: Delay in ms before hiding tooltip after mouse leaves (default 200).
        max_width: Maximum width of tooltips (default 300).

    Examples:
        >>> # Install globally for the entire application
        >>> app = QApplication(sys.argv)
        >>> FXTooltipManager.install()
        >>>
        >>> # Now all setToolTip() calls will use FXTooltip
        >>> button = QPushButton("Click me")
        >>> button.setToolTip("This will show as an FXTooltip!")
        >>>
        >>> # Uninstall to restore default Qt tooltips
        >>> FXTooltipManager.uninstall()
    """

    _instance: Optional["FXTooltipManager"] = None

    def __init__(
        self,
        parent: Optional[QObject] = None,
        show_delay: int = 500,
        hide_delay: int = 200,
        max_width: int = 300,
    ):
        super().__init__(parent)

        self._show_delay = show_delay
        self._hide_delay = hide_delay
        self._max_width = max_width

        # Current tooltip instance
        self._tooltip: Optional[FXTooltip] = None

        # Timers for show/hide delays
        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._do_show_tooltip)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._do_hide_tooltip)

        # Track the widget we're showing tooltip for
        self._pending_widget: Optional[weakref.ref] = None
        self._pending_index: Optional[QPersistentModelIndex] = None
        self._pending_item_rect: Optional[QRect] = None
        self._current_widget: Optional[weakref.ref] = None
        self._current_index: Optional[QPersistentModelIndex] = None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Intercept tooltip events and show FXTooltip instead."""
        if event.type() == QEvent.ToolTip:
            widget = watched
            if not isinstance(widget, QWidget):
                return False
            # A widget anchoring its own FXTooltip: block both tooltips
            if widget.property(_EXPLICIT):
                return True

            showing = self._tooltip is not None and self._tooltip.isVisible()
            self._pending_item_rect = None
            self._pending_index = None
            view = widget.parent()
            if isinstance(view, QAbstractItemView):
                # The item's text is built only when the tooltip shows
                index = (
                    view.indexAt(event.pos())
                    if isinstance(event, QHelpEvent)
                    else QModelIndex()
                )
                if not index.isValid() or (
                    showing and self._current_index == index
                ):
                    return True
                item_rect = view.visualRect(index)
                self._pending_item_rect = QRect(
                    widget.mapToGlobal(item_rect.topLeft()), item_rect.size()
                )
                self._pending_index = QPersistentModelIndex(index)
            elif not widget.toolTip() or (
                showing
                and self._current_widget is not None
                and self._current_widget() is widget
            ):
                return True

            self._hide_timer.stop()
            self._pending_widget = weakref.ref(widget)
            if showing:
                self._do_show_tooltip()
            else:
                self._show_timer.start(self._show_delay)
            return True  # Block the standard Qt tooltip

        elif event.type() == QEvent.Leave:
            # Mouse left a widget - start hide timer
            if self._tooltip and self._tooltip.isVisible():
                self._show_timer.stop()
                self._hide_timer.start(self._hide_delay)

        elif event.type() == QEvent.MouseButtonPress:
            # Hide tooltip on click
            self._hide_tooltip_immediate()

        return False  # Don't consume other events

    def _get_item_view_tooltip(self, view, index):
        """Build tooltip HTML for an item view index.

        The item's own `Qt.ToolTipRole` is used as is when set. Otherwise
        the thumbnail, name, type and description are assembled, the text
        escaped.

        Args:
            view: The QAbstractItemView.
            index: The QModelIndex.

        Returns:
            HTML tooltip string, or None.
        """
        item_tooltip = index.data(Qt.ToolTipRole)
        if item_tooltip:
            return str(item_tooltip)

        parts = []

        thumbnail_path = index.data(FXThumbnailDelegate.THUMBNAIL_PATH_ROLE)
        # A missing file renders as a large broken-image glyph
        if thumbnail_path and os.path.isfile(str(thumbnail_path)):
            img_url = QUrl.fromLocalFile(str(thumbnail_path)).toString()
            parts.append(f'<img src="{html.escape(img_url)}" width="200">')

        entity_data = index.data(Qt.UserRole)
        description = index.data(FXThumbnailDelegate.DESCRIPTION_ROLE)

        entity_name = None
        entity_type = None
        if isinstance(entity_data, dict):
            entity_name = entity_data.get("name")
            entity_type = entity_data.get("type")
        if not entity_name:
            entity_name = index.data(Qt.DisplayRole)

        if entity_name:
            header = f"<b>{html.escape(str(entity_name))}</b>"
            if entity_type:
                header += f" ({html.escape(str(entity_type))})"
            if description and description != "-":
                plain = fxutils.markdown_to_plain_text(
                    str(description)
                )
                parts.append(f"{header}<br>{html.escape(plain)}")
            else:
                parts.append(header)

        return "<br>".join(parts) if parts else None

    def _do_show_tooltip(self) -> None:
        """Show the pending tooltip."""
        if not self._pending_widget:
            return

        widget = self._pending_widget()
        if not widget:
            return

        index = self._pending_index
        self._pending_index = None
        if index is not None:
            if not index.isValid():
                return
            tooltip_text = self._get_item_view_tooltip(
                widget.parent(), QModelIndex(index)
            )
        else:
            tooltip_text = widget.toolTip()
        if not tooltip_text:
            return

        # Hide any existing tooltip
        self._do_hide_tooltip()

        # Use item rect if available (for item views), else widget rect
        if self._pending_item_rect:
            global_rect = self._pending_item_rect
            self._pending_item_rect = None
        else:
            widget_rect = widget.rect()
            global_top_left = widget.mapToGlobal(widget_rect.topLeft())
            global_rect = QRect(global_top_left, widget_rect.size())

        # Optional rich fields carried as dynamic properties (see
        # set_rich_tooltip): lets a plain setToolTip() render the full
        # FXTooltip layout (bold title + shortcut badge) without the widget
        # owning a persistent FXTooltip instance.
        title = widget.property("fx_tooltip_title") or None
        shortcut = widget.property("fx_tooltip_shortcut") or None
        icon = widget.property("fx_tooltip_icon") or None

        # Create and show tooltip
        self._tooltip = FXTooltip(
            parent=None,
            title=title,
            description=tooltip_text,
            icon=icon,
            shortcut=shortcut,
            show_delay=0,
            hide_delay=self._hide_delay,
            persistent=True,
            show_arrow=True,
            max_width=self._max_width,
        )
        self._tooltip._one_shot = True
        self._tooltip.show_at_rect(global_rect)

        # Track current widget
        self._current_widget = self._pending_widget
        self._current_index = index
        self._pending_widget = None

    def _do_hide_tooltip(self) -> None:
        """Hide the current tooltip."""
        if self._tooltip:
            try:
                self._tooltip.hide_tooltip()
            except RuntimeError:
                pass  # Widget may have been deleted
            self._tooltip = None
        self._current_widget = None
        self._current_index = None

    def _hide_tooltip_immediate(self) -> None:
        """Hide tooltip immediately without delay."""
        self._show_timer.stop()
        self._hide_timer.stop()
        self._do_hide_tooltip()
        self._pending_widget = None
        self._pending_index = None

    @classmethod
    def install(
        cls,
        show_delay: int = 500,
        hide_delay: int = 200,
        max_width: int = 300,
    ) -> "FXTooltipManager":
        """Install the global tooltip manager.

        After calling this, all widgets using setToolTip() will display
        FXTooltip instead of the standard Qt tooltip.

        Args:
            show_delay: Delay in ms before showing tooltip.
            hide_delay: Delay in ms before hiding tooltip.
            max_width: Maximum width of tooltips.

        Returns:
            The installed FXTooltipManager instance.

        Examples:
            >>> FXTooltipManager.install()
            >>> button.setToolTip("Now uses FXTooltip!")
        """
        if cls._instance is not None:
            return cls._instance

        app = QApplication.instance()
        if not app:
            raise RuntimeError(
                "QApplication must be created before installing FXTooltipManager"
            )

        cls._instance = cls(
            parent=app,
            show_delay=show_delay,
            hide_delay=hide_delay,
            max_width=max_width,
        )
        app.installEventFilter(cls._instance)
        return cls._instance

    @classmethod
    def uninstall(cls) -> None:
        """Uninstall the global tooltip manager.

        Restores standard Qt tooltip behavior.

        Examples:
            >>> FXTooltipManager.uninstall()
        """
        if cls._instance is None:
            return

        app = QApplication.instance()
        if app:
            app.removeEventFilter(cls._instance)

        cls._instance._hide_tooltip_immediate()
        cls._instance.deleteLater()
        cls._instance = None

    @classmethod
    def is_installed(cls) -> bool:
        """Check if the tooltip manager is currently installed.

        Returns:
            True if installed, False otherwise.
        """
        return cls._instance is not None

    @classmethod
    def instance(cls) -> Optional["FXTooltipManager"]:
        """Get the current tooltip manager instance.

        Returns:
            The FXTooltipManager instance, or None if not installed.
        """
        return cls._instance


class _ItemTooltipHandler(QObject):
    """One viewport filter per item view, showing each item's FXTooltip.

    Items map to the keyword arguments of their tooltip; the FXTooltip is
    built when it shows and closed when the pointer leaves the item.
    """

    def __init__(self, view: QAbstractItemView):
        super().__init__(view)
        self._view = weakref.ref(view)
        # Keyed by id(): list and table items are unhashable. Holding the
        # item keeps its wrapper, so itemAt() hands back the same object.
        # ponytail: entries outlive deleted items; prune if views churn items
        self._entries: dict = {}
        self._hovered = None
        self._tooltip: Optional[FXTooltip] = None

        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._do_show)

        self._pending_rect: Optional[QRect] = None

    @classmethod
    def for_view(cls, view: QAbstractItemView) -> "_ItemTooltipHandler":
        """Return the view's handler, installing it on first use."""
        handler = view.findChild(cls)
        if handler is None:
            handler = cls(view)
            view.viewport().installEventFilter(handler)
            view.viewport().setMouseTracking(True)
        return handler

    def set_entry(self, item, show_delay: int, **tooltip_kwargs) -> None:
        """Store (or replace) the tooltip content for one item."""
        self._entries[id(item)] = (item, show_delay, tooltip_kwargs)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Track the hovered item and show or hide its tooltip."""
        view = self._view()
        if view is None:
            return False

        if event.type() == QEvent.MouseMove:
            entry = self._entries.get(id(view.itemAt(event.pos())))
            hovered = entry[0] if entry else None
            if hovered is not self._hovered:
                self._leave()
                self._hovered = hovered
                if entry:
                    item_rect = view.visualItemRect(hovered)
                    self._pending_rect = QRect(
                        view.viewport().mapToGlobal(item_rect.topLeft()),
                        item_rect.size(),
                    )
                    self._show_timer.start(entry[1])
        elif event.type() == QEvent.Leave:
            self._leave()
            self._hovered = None

        return False  # Don't consume events

    def _leave(self) -> None:
        """Stop a pending show and fade out the shown tooltip."""
        self._show_timer.stop()
        if self._tooltip is not None:
            try:
                self._tooltip.hide_tooltip()
            except RuntimeError:
                pass  # Already closed and deleted
            self._tooltip = None

    def _do_show(self) -> None:
        """Build and show the hovered item's tooltip."""
        if self._hovered is None or self._pending_rect is None:
            return
        _, _, kwargs = self._entries[id(self._hovered)]
        self._tooltip = FXTooltip(parent=None, persistent=True, **kwargs)
        self._tooltip._one_shot = True
        self._tooltip.show_at_rect(self._pending_rect)


def set_tooltip(
    target: Union[QWidget, QTreeWidgetItem, QListWidgetItem, QTableWidgetItem],
    description: str = "",
    title: Optional[str] = None,
    icon: Optional[str] = None,
    shortcut: Optional[str] = None,
    position: FXTooltipPosition = FXTooltipPosition.AUTO,
    show_delay: int = 500,
    hide_delay: int = 200,
) -> Optional[FXTooltip]:
    """Attach an FXTooltip to a widget or item with a simple API.

    This is a convenience function similar to `fxicons.set_icon()` that creates
    and attaches an FXTooltip to the given target. The tooltip is automatically
    shown on hover and hidden when the mouse leaves.

    Supports both QWidget subclasses and item-based widgets:
    - QWidget (buttons, labels, etc.)
    - QTreeWidgetItem
    - QListWidgetItem
    - QTableWidgetItem

    Args:
        target: The widget or item to attach the tooltip to.
        description: Main tooltip content text.
        title: Optional bold title text.
        icon: Optional icon name (from fxicons).
        shortcut: Optional keyboard shortcut to display.
        position: Preferred position relative to target.
        show_delay: Delay in ms before showing (default 500).
        hide_delay: Delay in ms before hiding after mouse leaves (default 200).

    Returns:
        None for items, whose tooltip is built on hover by one handler per
        view, and for widgets while the global FXTooltipManager is installed
        (the rich fields go to ``fx_tooltip_*`` dynamic properties). A
        widget without the manager gets the created FXTooltip instance.

    Examples:
        >>> # Simple tooltip on a button
        >>> set_tooltip(button, "Click to save the file")
        >>>
        >>> # Rich tooltip with all options
        >>> set_tooltip(
        ...     button,
        ...     description="Save the current document to disk.",
        ...     title="Save",
        ...     icon="save",
        ...     shortcut="Ctrl+S",
        ... )
        >>>
        >>> # Tooltip on a tree item
        >>> item = QTreeWidgetItem(tree, ["Item 1"])
        >>> set_tooltip(
        ...     item,
        ...     description="This is a tree item tooltip",
        ...     title="Item Info",
        ...     icon="info",
        ... )
    """
    # Handle item-based widgets
    if isinstance(target, (QTreeWidgetItem, QListWidgetItem, QTableWidgetItem)):
        # Get the parent view
        if isinstance(target, QTreeWidgetItem):
            view = target.treeWidget()
        elif isinstance(target, QListWidgetItem):
            view = target.listWidget()
        elif isinstance(target, QTableWidgetItem):
            view = target.tableWidget()
        else:
            view = None

        if not view:
            raise ValueError(
                f"Item {target} is not attached to a view widget. "
                "Add the item to a tree/list/table before calling set_tooltip()."
            )

        _ItemTooltipHandler.for_view(view).set_entry(
            target,
            title=title,
            description=description,
            icon=icon,
            shortcut=shortcut,
            position=position,
            show_delay=show_delay,
            hide_delay=hide_delay,
        )
        return None

    # Handle regular QWidget
    elif isinstance(target, QWidget):
        # With the global FXTooltipManager installed (FXMainWindow installs
        # it), no per-widget FXTooltip instance is needed: store the rich
        # fields as dynamic properties and let the manager build the tooltip
        # lazily on hover with the full layout (bold title, shortcut badge,
        # optional icon). This keeps zero persistent theme-aware objects
        # alive per widget.
        if FXTooltipManager.is_installed():
            target.setToolTip(description)
            if title is not None:
                target.setProperty("fx_tooltip_title", title)
            if shortcut is not None:
                target.setProperty("fx_tooltip_shortcut", shortcut)
            if icon is not None:
                target.setProperty("fx_tooltip_icon", icon)
            return None

        # No manager (app without FXMainWindow): legacy per-widget tooltip.
        tooltip = FXTooltip(
            parent=target,
            title=title,
            description=description,
            icon=icon,
            shortcut=shortcut,
            position=position,
            show_delay=show_delay,
            hide_delay=hide_delay,
        )

        # Store tooltip reference on the widget to prevent garbage collection
        if not hasattr(target, "_fx_tooltips"):
            target._fx_tooltips = []
        target._fx_tooltips.append(tooltip)

        return tooltip

    else:
        raise TypeError(
            f"set_tooltip() expects a QWidget or item type, got {type(target).__name__}"
        )
