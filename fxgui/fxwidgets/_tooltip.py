"""Rich, theme-aware tooltip widget."""

# TODO: Peristent tooltip should follow their anchor when it moves
# TODO: Programmatic tooltip should close when the user clicks outside

# Built-in
import os
import weakref
from enum import IntEnum
from typing import Callable, Optional, Union

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from qtpy.QtGui import (
    QColor,
    QCursor,
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
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


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


class FXTooltip(fxstyle.FXThemeAware, QFrame):
    """A rich, theme-aware tooltip with advanced features.

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

        # Animation opacity
        self._opacity = 0.0

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

        # Connect to anchor for cleanup
        if self._anchor:
            self._anchor.destroyed.connect(self._on_anchor_destroyed)
            # Install event filter for hover detection (non-persistent)
            # or move tracking (persistent)
            self._anchor.installEventFilter(self)

        # Track mouse for hide delay
        self.setMouseTracking(True)

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
                self._icon_label = QLabel()
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
                self._shortcut_label = QLabel(self._shortcut)
                self._shortcut_label.setObjectName("FXTooltipShortcut")
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
        shadow = QGraphicsDropShadowEffect(self._content_widget)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self._content_widget.setGraphicsEffect(shadow)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        # Background and text colors - use surface_sunken for darker card
        bg_color = self.theme.surface_sunken
        text_color = self.theme.text
        text_muted = self.theme.text_muted
        border_color = self.theme.border
        accent = self.theme.accent_primary

        self._content_widget.setStyleSheet(
            f"""
            #FXTooltipContent {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #FXTooltipContent QLabel {{
                background: transparent;
            }}
            #FXTooltipTitle {{
                background: transparent;
                color: {text_color};
                font-size: 13px;
            }}
            #FXTooltipDescription {{
                background: transparent;
                color: {text_muted};
                font-size: 12px;
            }}
            #FXTooltipShortcut {{
                background-color: {border_color};
                color: {text_muted};
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
                font-family: monospace;
            }}
            #FXTooltipAction {{
                background-color: transparent;
                color: {accent};
                border: none;
                text-align: left;
                padding: 4px 0;
                font-size: 12px;
            }}
            #FXTooltipAction:hover {{
                text-decoration: underline;
            }}
            """
        )

        # Update icon with theme color
        if self._icon_name and hasattr(self, "_icon_label"):
            pixmap = fxicons.get_icon(self._icon_name, color=accent).pixmap(
                20, 20
            )
            self._icon_label.setPixmap(pixmap)

        # Store colors for painting
        self._bg_color = QColor(bg_color)
        self._border_color = QColor(border_color)

    def eventFilter(self, watched, event) -> bool:
        """Handle hover events on anchor widget and click-outside detection."""
        from qtpy.QtCore import QEvent

        # Handle click-outside when filtering app events
        if watched == QApplication.instance():
            if event.type() == QEvent.MouseButtonPress:
                # Check if click is outside the tooltip
                if self.isVisible():
                    global_pos = QCursor.pos()
                    if not self.geometry().contains(global_pos):
                        self.hide_tooltip()
            return False  # Don't consume app events

        if watched == self._anchor:
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
                    pos, _, arrow_offset = self._calculate_position()
                    self._arrow_offset = arrow_offset
                    self.move(pos)
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
        self.hide_tooltip()
        self.deleteLater()

    def _on_action_clicked(self) -> None:
        """Handle action button click."""
        self.action_clicked.emit()
        if self._action_callback:
            self._action_callback()
        self.hide_tooltip()

    def _calculate_position(self) -> tuple:
        """Calculate tooltip position and arrow placement."""
        if not self._anchor:
            return QCursor.pos(), FXTooltipPosition.TOP, 0

        # Get anchor geometry in global coordinates
        anchor_rect = self._anchor.rect()
        anchor_global = self._anchor.mapToGlobal(anchor_rect.topLeft())
        anchor_rect = QRect(
            anchor_global.x(),
            anchor_global.y(),
            anchor_rect.width(),
            anchor_rect.height(),
        )

        # Get screen geometry
        screen = QApplication.screenAt(anchor_global)
        if not screen:
            screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        # Calculate tooltip size
        self.adjustSize()
        tooltip_size = self.sizeHint()

        # Determine best position
        position = self._position
        if position == FXTooltipPosition.AUTO:
            position = self._find_best_position(
                anchor_rect, tooltip_size, screen_rect
            )

        # Calculate coordinates based on position
        x, y, arrow_offset = self._calculate_coordinates(
            position, anchor_rect, tooltip_size, screen_rect
        )

        return QPoint(x, y), position, arrow_offset

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
            arrow_polygon.append(QPoint(ax, ay - arrow_size))
            arrow_polygon.append(QPoint(ax - arrow_size, ay))
            arrow_polygon.append(QPoint(ax + arrow_size, ay))

        elif self._arrow_position == FXTooltipPosition.BOTTOM:
            # Arrow pointing down (tooltip above anchor)
            ax = self._arrow_offset
            ay = content_rect.bottom()
            arrow_polygon.append(QPoint(ax, ay + arrow_size))
            arrow_polygon.append(QPoint(ax - arrow_size, ay))
            arrow_polygon.append(QPoint(ax + arrow_size, ay))

        elif self._arrow_position == FXTooltipPosition.LEFT:
            # Arrow pointing left (tooltip right of anchor)
            ax = content_rect.left()
            ay = self._arrow_offset
            arrow_polygon.append(QPoint(ax - arrow_size, ay))
            arrow_polygon.append(QPoint(ax, ay - arrow_size))
            arrow_polygon.append(QPoint(ax, ay + arrow_size))

        elif self._arrow_position == FXTooltipPosition.RIGHT:
            # Arrow pointing right (tooltip left of anchor)
            ax = content_rect.right()
            ay = self._arrow_offset
            arrow_polygon.append(QPoint(ax + arrow_size, ay))
            arrow_polygon.append(QPoint(ax, ay - arrow_size))
            arrow_polygon.append(QPoint(ax, ay + arrow_size))

        # Fill arrow with background color
        if hasattr(self, "_bg_color"):
            path = QPainterPath()
            path.addPolygon(arrow_polygon)
            path.closeSubpath()
            painter.fillPath(path, self._bg_color)

            # Draw arrow border
            pen = QPen(self._border_color, 1)
            painter.setPen(pen)
            painter.drawPolyline(arrow_polygon)

    def _do_show(self) -> None:
        """Actually show the tooltip."""
        # Ensure theme styles are applied before showing
        if not hasattr(self, "_bg_color"):
            self._on_theme_changed()

        pos, arrow_pos, arrow_offset = self._calculate_position()
        self._arrow_offset = arrow_offset
        self.move(pos)

        # Reset and start fade animation
        self._fade_animation.stop()
        self.setWindowOpacity(0.0)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)

        # Install app-wide event filter for click-outside detection
        QApplication.instance().installEventFilter(self)

        self.show()
        self.raise_()
        self._fade_animation.start()

        # Start duration timer if set
        if self._duration > 0:
            self._duration_timer.start(self._duration)

        self.shown.emit()

    def _do_hide(self) -> None:
        """Actually hide the tooltip with fade out."""
        self._duration_timer.stop()

        # Fade out
        self._fade_animation.stop()
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self._on_fade_out_finished)
        self._fade_animation.start()

    def _on_fade_out_finished(self) -> None:
        """Handle fade out completion."""
        try:
            self._fade_animation.finished.disconnect(self._on_fade_out_finished)
        except (RuntimeError, TypeError):
            # Signal may already be disconnected or object deleted
            pass

        # Remove app-wide event filter
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)

        self.hide()
        self.hidden.emit()

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
            self._on_theme_changed()

    def set_anchor(self, widget: QWidget) -> None:
        """Change the anchor widget.

        Args:
            widget: New anchor widget.
        """
        # Remove old event filter
        if self._anchor:
            self._anchor.removeEventFilter(self)
            try:
                self._anchor.destroyed.disconnect(self._on_anchor_destroyed)
            except (RuntimeError, TypeError):
                # Signal may already be disconnected or anchor deleted
                pass

        # Set new anchor
        self._anchor = widget
        if widget and not self._persistent:
            widget.installEventFilter(self)
            widget.destroyed.connect(self._on_anchor_destroyed)

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

        # Ensure theme styles are applied
        if not hasattr(self, "_bg_color"):
            self._on_theme_changed()

        # Use provided position or fall back to instance position
        use_position = position if position is not None else self._position

        # Get screen geometry
        screen = QApplication.screenAt(rect.topLeft())
        if not screen:
            screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        # Calculate tooltip size
        self.adjustSize()
        tooltip_size = self.sizeHint()

        # Determine best position if AUTO
        if use_position == FXTooltipPosition.AUTO:
            use_position = self._find_best_position(
                rect, tooltip_size, screen_rect
            )

        # Calculate coordinates
        x, y, arrow_offset = self._calculate_coordinates(
            use_position, rect, tooltip_size, screen_rect
        )

        self._arrow_offset = arrow_offset
        self.move(QPoint(x, y))

        # Reset and start fade animation
        self._fade_animation.stop()
        self.setWindowOpacity(0.0)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)

        # Install app-wide event filter for click-outside detection
        QApplication.instance().installEventFilter(self)

        self.show()
        self.raise_()
        self._fade_animation.start()

        # Start duration timer if set
        if self._duration > 0:
            self._duration_timer.start(self._duration)

        self.shown.emit()

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
        self._pending_pos: Optional[QPoint] = None
        self._current_widget: Optional[weakref.ref] = None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Intercept tooltip events and show FXTooltip instead."""
        if event.type() == QEvent.ToolTip:
            # Get the widget that triggered the tooltip
            widget = watched
            if not isinstance(widget, QWidget):
                return False

            # Get tooltip text
            tooltip_text = widget.toolTip()
            if not tooltip_text:
                return True  # Block empty tooltips

            # Get the position from the event
            from qtpy.QtGui import QHelpEvent

            if isinstance(event, QHelpEvent):
                global_pos = event.globalPos()
            else:
                global_pos = QCursor.pos()

            # Check if we're already showing tooltip for this widget
            if (
                self._current_widget
                and self._current_widget() is widget
                and self._tooltip
                and self._tooltip.isVisible()
            ):
                return True  # Already showing, block the event

            # Cancel any pending hide
            self._hide_timer.stop()

            # Store pending tooltip data
            self._pending_widget = weakref.ref(widget)
            self._pending_pos = global_pos

            # Start show timer (or show immediately if already visible)
            if self._tooltip and self._tooltip.isVisible():
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

    def _do_show_tooltip(self) -> None:
        """Show the pending tooltip."""
        if not self._pending_widget:
            return

        widget = self._pending_widget()
        if not widget:
            return

        tooltip_text = widget.toolTip()
        if not tooltip_text:
            return

        # Hide any existing tooltip
        self._do_hide_tooltip()

        # Create widget rect in global coordinates
        widget_rect = widget.rect()
        global_top_left = widget.mapToGlobal(widget_rect.topLeft())
        global_rect = QRect(global_top_left, widget_rect.size())

        # Create and show tooltip
        self._tooltip = FXTooltip(
            parent=None,
            description=tooltip_text,
            show_delay=0,
            hide_delay=self._hide_delay,
            persistent=True,
            show_arrow=True,
            max_width=self._max_width,
        )
        self._tooltip.show_at_rect(global_rect)

        # Track current widget
        self._current_widget = self._pending_widget
        self._pending_widget = None
        self._pending_pos = None

    def _do_hide_tooltip(self) -> None:
        """Hide the current tooltip."""
        if self._tooltip:
            try:
                self._tooltip.hide_tooltip()
            except RuntimeError:
                pass  # Widget may have been deleted
            self._tooltip = None
        self._current_widget = None

    def _hide_tooltip_immediate(self) -> None:
        """Hide tooltip immediately without delay."""
        self._show_timer.stop()
        self._hide_timer.stop()
        self._do_hide_tooltip()
        self._pending_widget = None
        self._pending_pos = None

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
    """Event filter that handles tooltips for item-based widgets.

    This class manages tooltip display for QTreeWidgetItem, QListWidgetItem,
    and QTableWidgetItem by intercepting mouse events on the viewport.
    """

    def __init__(
        self,
        view: QAbstractItemView,
        item: Union[QTreeWidgetItem, QListWidgetItem, QTableWidgetItem],
        tooltip: FXTooltip,
        show_delay: int = 500,
    ):
        super().__init__(view)
        self._view = weakref.ref(view)
        self._item = weakref.ref(item)
        self._tooltip = tooltip
        self._show_delay = show_delay
        self._is_hovering = False

        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._do_show)

        self._pending_rect: Optional[QRect] = None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Handle mouse events to show/hide tooltip for the item."""
        view = self._view()
        item = self._item()

        if not view or not item:
            return False

        if event.type() == QEvent.MouseMove:
            from qtpy.QtGui import QMouseEvent

            if isinstance(event, QMouseEvent):
                pos = event.pos()
                hovered_item = self._get_item_at_pos(view, pos)

                if hovered_item is item:
                    # Mouse is over our item
                    if not self._is_hovering:
                        self._is_hovering = True
                        # Get item rect and start show timer
                        item_rect = self._get_item_rect(view, item)
                        if item_rect:
                            self._pending_rect = QRect(
                                view.viewport().mapToGlobal(
                                    item_rect.topLeft()
                                ),
                                item_rect.size(),
                            )
                            self._show_timer.start(self._show_delay)
                else:
                    # Mouse moved off our item
                    if self._is_hovering:
                        self._is_hovering = False
                        self._show_timer.stop()
                        if self._tooltip.isVisible():
                            self._tooltip.hide_tooltip()

        elif event.type() == QEvent.Leave:
            # Mouse left the viewport
            if self._is_hovering:
                self._is_hovering = False
                self._show_timer.stop()
                if self._tooltip.isVisible():
                    self._tooltip.hide_tooltip()

        return False  # Don't consume events

    def _do_show(self) -> None:
        """Show the tooltip at the pending rect."""
        if self._pending_rect and self._is_hovering:
            self._tooltip.show_at_rect(self._pending_rect)

    def _get_item_at_pos(
        self,
        view: QAbstractItemView,
        pos: QPoint,
    ) -> Optional[Union[QTreeWidgetItem, QListWidgetItem, QTableWidgetItem]]:
        """Get the item at the given position."""
        if isinstance(view, QTreeWidget):
            return view.itemAt(pos)
        elif isinstance(view, QListWidget):
            return view.itemAt(pos)
        elif isinstance(view, QTableWidget):
            return view.itemAt(pos)
        return None

    def _get_item_rect(
        self,
        view: QAbstractItemView,
        item: Union[QTreeWidgetItem, QListWidgetItem, QTableWidgetItem],
    ) -> Optional[QRect]:
        """Get the visual rect for the item."""
        if isinstance(view, QTreeWidget) and isinstance(item, QTreeWidgetItem):
            return view.visualItemRect(item)
        elif isinstance(view, QListWidget) and isinstance(
            item, QListWidgetItem
        ):
            return view.visualItemRect(item)
        elif isinstance(view, QTableWidget) and isinstance(
            item, QTableWidgetItem
        ):
            return view.visualItemRect(view.indexFromItem(item))
        return None


def set_tooltip(
    target: Union[QWidget, QTreeWidgetItem, QListWidgetItem, QTableWidgetItem],
    description: str = "",
    title: Optional[str] = None,
    icon: Optional[str] = None,
    shortcut: Optional[str] = None,
    position: FXTooltipPosition = FXTooltipPosition.AUTO,
    show_delay: int = 500,
    hide_delay: int = 200,
) -> FXTooltip:
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
        The created FXTooltip instance (kept internally to prevent GC).

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

        # Create tooltip without parent (will be positioned manually)
        tooltip = FXTooltip(
            parent=None,
            title=title,
            description=description,
            icon=icon,
            shortcut=shortcut,
            position=position,
            show_delay=show_delay,
            hide_delay=hide_delay,
            persistent=True,  # No hover detection on tooltip itself
        )

        # Create handler that manages tooltip for this item
        handler = _ItemTooltipHandler(view, target, tooltip, show_delay)
        view.viewport().installEventFilter(handler)
        view.viewport().setMouseTracking(True)

        # Store references to prevent garbage collection
        if not hasattr(view, "_fx_item_tooltip_handlers"):
            view._fx_item_tooltip_handlers = []
        view._fx_item_tooltip_handlers.append(handler)

        if not hasattr(view, "_fx_tooltips"):
            view._fx_tooltips = []
        view._fx_tooltips.append(tooltip)

        return tooltip

    # Handle regular QWidget
    elif isinstance(target, QWidget):
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


# Example usage
def example() -> None:
    import sys

    from qtpy.QtWidgets import (
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QPushButton,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXTooltip Demo")

    # Main content widget
    content_widget = QWidget()
    layout = QVBoxLayout(content_widget)
    layout.setSpacing(15)

    # Description
    desc = QLabel(
        "Hover over widgets and items to see tooltips. "
        "The set_tooltip() function works on both widgets and item views."
    )
    desc.setWordWrap(True)
    layout.addWidget(desc)

    ###### Widget tooltips group
    widget_group = QGroupBox("Widget Tooltips (using set_tooltip)")
    widget_layout = QVBoxLayout(widget_group)

    # Simple tooltip on button
    btn1 = QPushButton("Hover for Simple Tooltip")
    set_tooltip(btn1, "This is a simple tooltip description.")
    widget_layout.addWidget(btn1)

    # Rich tooltip on button
    btn2 = QPushButton("Hover for Rich Tooltip")
    set_tooltip(
        btn2,
        description="Save the current document to disk.",
        title="Save File",
        icon="save",
        shortcut="Ctrl+S",
    )
    widget_layout.addWidget(btn2)

    layout.addWidget(widget_group)

    ###### Item tooltips group
    item_group = QGroupBox("Item Tooltips (using set_tooltip)")
    item_layout = QHBoxLayout(item_group)

    # Tree widget with item tooltips
    tree = QTreeWidget()
    tree.setHeaderLabel("Tree Items")
    tree.setMinimumHeight(120)

    tree_item1 = QTreeWidgetItem(tree, ["Project Files"])
    set_tooltip(
        tree_item1,
        description="Contains all project source files and assets.",
        title="Project Files",
        icon="folder",
    )

    tree_item2 = QTreeWidgetItem(tree, ["Settings"])
    set_tooltip(
        tree_item2,
        description="Application configuration and preferences.",
        title="Settings",
        icon="settings",
        shortcut="Ctrl+,",
    )

    tree_item3 = QTreeWidgetItem(tree, ["Export"])
    set_tooltip(
        tree_item3,
        description="Export your project to various formats.",
        title="Export Options",
        icon="upload",
    )

    tree.expandAll()
    item_layout.addWidget(tree)

    # List widget with item tooltips
    list_widget = QListWidget()
    list_widget.setMinimumHeight(120)

    list_item1 = QListWidgetItem("Recent File 1")
    list_widget.addItem(list_item1)
    set_tooltip(
        list_item1,
        description="Last modified: 2 hours ago",
        title="document.txt",
        icon="description",
    )

    list_item2 = QListWidgetItem("Recent File 2")
    list_widget.addItem(list_item2)
    set_tooltip(
        list_item2,
        description="Last modified: Yesterday",
        title="image.png",
        icon="image",
    )

    list_item3 = QListWidgetItem("Recent File 3")
    list_widget.addItem(list_item3)
    set_tooltip(
        list_item3,
        description="Last modified: 3 days ago",
        title="script.py",
        icon="code",
    )

    item_layout.addWidget(list_widget)

    layout.addWidget(item_group)

    ###### Click tooltips group
    click_group = QGroupBox("Click Tooltips (programmatic)")
    click_layout = QVBoxLayout(click_group)

    # Button with persistent tooltip
    btn3 = QPushButton("Click for Persistent Tooltip")
    tooltip3 = FXTooltip(
        parent=btn3,
        title="Did you know?",
        description="You can drag and drop files directly into this window.",
        icon="info",
        persistent=True,
        show_delay=0,
    )
    btn3.clicked.connect(tooltip3.show_tooltip)
    click_layout.addWidget(btn3)

    # Programmatic tooltip
    btn4 = QPushButton("Show Tooltip Programmatically")

    # Keep reference to prevent garbage collection
    active_tooltips = []

    def show_programmatic():
        tooltip = FXTooltip.show_for_widget(
            btn4,
            title="Success!",
            description="Operation completed successfully.",
            icon="check_circle",
            duration=3000,
        )
        active_tooltips.append(tooltip)
        tooltip.hidden.connect(
            lambda: (
                active_tooltips.remove(tooltip)
                if tooltip in active_tooltips
                else None
            )
        )

    btn4.clicked.connect(show_programmatic)
    click_layout.addWidget(btn4)

    layout.addWidget(click_group)
    layout.addStretch()

    window.setCentralWidget(content_widget)
    window.resize(500, 550)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
