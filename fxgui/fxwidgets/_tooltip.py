"""Rich, theme-aware tooltip widget."""

# TODO: Find a way to use the FXTooltip by default for standard Qt tooltips?
# TODO: Peristent tooltip should follow their anchor when it moves
# TODO: Programmatic tooltip should close when the user clicks outside

# Built-in
import os
from enum import IntEnum
from typing import Callable, Optional

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
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
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        text_secondary = self.theme.text_secondary
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
                color: {text_secondary};
                font-size: 12px;
            }}
            #FXTooltipShortcut {{
                background-color: {border_color};
                color: {text_secondary};
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


# Example usage
def example() -> None:
    import sys

    from qtpy.QtWidgets import (
        QVBoxLayout,
        QWidget,
        QPushButton,
        QGroupBox,
        QLabel,
    )
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXTooltip Demo")

    # Main content widget
    content_widget = QWidget()
    layout = QVBoxLayout(content_widget)
    layout.setSpacing(20)

    # Description
    desc = QLabel(
        "Hover over buttons to see tooltips, or click for programmatic ones."
    )
    desc.setWordWrap(True)
    layout.addWidget(desc)

    # Hover tooltips group
    hover_group = QGroupBox("Hover Tooltips")
    hover_layout = QVBoxLayout(hover_group)

    # Button with simple tooltip
    btn1 = QPushButton("Hover for Simple Tooltip")
    # XXX: Variable assigned to prevent Python's garbage collection
    tooltip1 = FXTooltip(
        parent=btn1,
        title="Save File",
        description="Save the current document to disk.",
        shortcut="Ctrl+S",
        icon="save",
    )
    hover_layout.addWidget(btn1)

    # Button with rich tooltip
    btn2 = QPushButton("Hover for Rich Tooltip")
    # XXX: Variable assigned to prevent Python's garbage collection
    tooltip2 = FXTooltip(
        parent=btn2,
        title="New Feature!",
        description="We've added <b>batch export</b> functionality. "
        "You can now export multiple items at once.",
        icon="lightbulb",
        action_text="Learn More →",
        action_callback=lambda: print("Learn more clicked!"),
    )
    hover_layout.addWidget(btn2)

    layout.addWidget(hover_group)

    # Click tooltips group
    click_group = QGroupBox("Click Tooltips")
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
    window.resize(450, 400)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
