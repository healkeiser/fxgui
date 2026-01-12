"""Custom item delegates for tree/list views."""

# Built-in
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

# Third-party
from qtpy.QtCore import QEvent, QMargins, QModelIndex, QRect, QRectF, QSize, Qt
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QHelpEvent,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


class FXColorLabelDelegate(fxstyle.FXThemeAware, QStyledItemDelegate):
    """A custom delegate to paint items with specific colors and icons based
    on their text content.

    Note:
        This delegate automatically refreshes when the theme changes, ensuring
        that default colors (for items without explicit color mappings) stay
        in sync with the current theme.
    """

    # Custom role to skip delegate
    SKIP_DELEGATE_ROLE = Qt.UserRole + 5

    def __init__(
        self,
        colors_icons: Dict[str, Tuple[QColor, QColor, QColor, QIcon, bool]],
        parent: Optional[QWidget] = None,
        margin_left: int = 2,
        margin_top: Optional[int] = None,
        margin_bottom: Optional[int] = None,
    ):
        """Initializes the delegate with a dictionary of colors and icons.

        Args:
            colors_icons: A dictionary where keys are text patterns and values
                are tuples containing background color, border color,
                text/icon color, icon, and a boolean indicating if the icon
                should be colored.
            parent: The parent object.
            margin_left: The left margin for the text and icon. Defaults to 2.
            margin_top: The top margin for the text and icon. Defaults to
                `margin_left`.
            margin_bottom: The bottom margin for the text and icon. Defaults to
                `margin_left`.
        """

        super().__init__(parent)

        # Dictionary mapping item texts to (background_color, border_color,
        # text_icon_color, icon, color_icon)
        self.colors_icons = colors_icons

        # Margins
        self.margin_left = margin_left
        self.margin_top = self.margin_left if margin_top is None else margin_top
        self.margin_bottom = (
            self.margin_left if margin_bottom is None else margin_bottom
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paints the item with the specified colors and icons.

        Args:
            painter: The painter used to draw the item.
            option: The style options for the item.
            index: The model index of the item.
        """

        # Check if the delegate should skip drawing
        skip_delegate = index.data(FXColorLabelDelegate.SKIP_DELEGATE_ROLE)
        if skip_delegate:
            super().paint(painter, option, index)
            return

        # Retrieve the text and associated colors and icon
        text = index.data()
        if not text:
            return  # No need to paint anything if there's no text

        # Create a copy of the option to modify to clear the text and icon
        # XXX: Not working, need to investigate
        option_modified = QStyleOptionViewItem(option)
        option_modified.text = ""
        option_modified.icon = QIcon()

        # Call the base class paint method to draw selection and hover effects
        super().paint(painter, option_modified, index)

        # Set the default colors and icon (theme-aware)
        background_color, border_color, text_icon_color, icon, color_icon = (
            QColor(self.theme.surface),
            QColor(self.theme.border_light),
            QColor(self.theme.text),
            fxicons.get_icon("drag_indicator"),
            False,  # Default to not coloring the icon
        )

        # Find the best match for the text in the colors_icons dictionary
        best_match_length = 0
        best_match = None

        for key, value in self.colors_icons.items():
            if key in text.lower() and len(key) > best_match_length:
                best_match = value
                best_match_length = len(key)

        if best_match:
            (
                background_color,
                border_color,
                text_icon_color,
                icon,
                color_icon,
            ) = best_match

        # Adjust colors based on item state
        if option.state & QStyle.State_Selected:
            background_color = background_color.lighter(125)
            border_color = border_color.lighter(125)
        elif option.state & QStyle.State_MouseOver:
            background_color = background_color.darker(125)
            border_color = border_color.darker(125)

        # Save painter state
        painter.save()

        # Anti-aliasing for smoother rendering
        painter.setRenderHint(QPainter.Antialiasing)

        # Set the clipping region to the column's rectangle
        painter.setClipRect(option.rect)

        # Adjust the rectangle to be away from the border using margins
        rect = option.rect.adjusted(
            self.margin_left,
            self.margin_top,
            -self.margin_left,
            -self.margin_bottom,
        )

        # Use the default font and measure text size
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        # Define the rectangle around the text, aligned to the left
        icon_size = QSize(14, 14)  # Icon size
        text_rect = QRect(
            rect.left() + icon_size.width() + 2,  # Space between icon and text
            rect.top() + (rect.height() - text_height) // 2,
            text_width + 10,
            text_height + 0,
        )

        # Draw custom label with border and background colors from the mapping
        painter.setBrush(background_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(
            text_rect.adjusted(-icon_size.width() - 2, 0, 0, 0), 2, 2
        )

        # Draw the icon inside the rectangle, on the left of the text
        icon_rect = QRect(
            rect.left() + 2,
            rect.top() + (rect.height() - icon_size.height()) // 2,
            icon_size.width(),
            icon_size.height(),
        )

        if color_icon:
            # Convert the icon to a QPixmap and apply the text/icon color
            colored_pixmap = fxicons.change_pixmap_color(
                icon.pixmap(icon_size), text_icon_color
            )
            painter.drawPixmap(icon_rect, colored_pixmap)
        else:
            # Draw the original icon without coloring
            icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )

        # Draw the text inside the rectangle
        painter.setPen(text_icon_color)
        painter.drawText(text_rect, Qt.AlignCenter, text)

        # Restore painter state
        painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        """Provides the size hint for the item.

        Args:
            option: The style options for the item.
            index: The model index of the item.

        Returns:
            The size hint for the item.
        """

        text = index.data()
        if not text:
            return QSize()
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        icon_size = 14
        width = (
            text_width
            + icon_size
            + 20
            + self.margin_left * 2  # Add horizontal margins
        )
        height = (
            max(text_height, icon_size)
            + 2
            + self.margin_top
            + self.margin_bottom  # Add vertical margins
        )
        return QSize(width, height)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme change by triggering a repaint of the parent view."""
        parent = self.parent()
        if parent and hasattr(parent, "viewport"):
            parent.viewport().update()
        elif parent and hasattr(parent, "update"):
            parent.update()


class FXThumbnailDelegate(fxstyle.FXThemeAware, QStyledItemDelegate):
    """Custom item delegate for showing thumbnails in tree/list views.

    This delegate displays items with thumbnails, titles, descriptions,
    and status indicators. It supports Markdown formatting in descriptions
    and tooltips. Additionally, it supports custom background colors via
    Qt.BackgroundRole with rounded corners and borders for visual hierarchy.

    Note:
        Store data in items using the following roles:
        - `Qt.BackgroundRole` (`QColor/QBrush`): Custom background color
          with rounded corners and border.
        - `Qt.DecorationRole` (`QIcon`): Icon for items without thumbnails.
        - `Qt.UserRole + 1` (`bool`): Whether to show the thumbnail.
        - `Qt.UserRole + 2` (`str`): Path to the thumbnail image.
        - `Qt.UserRole + 3` (`str`): Description text (supports Markdown).
        - `Qt.UserRole + 4` (`QColor`): Status dot indicator color.
        - `Qt.UserRole + 5` (`QColor`): Status label background color.
        - `Qt.UserRole + 6` (`str`): Status label text.
        - `Qt.UserRole + 7` (`bool`): Whether to show the status dot.
        - `Qt.UserRole + 8` (`bool`): Whether to show the status label.

    Properties:
        show_thumbnail: Whether to show thumbnails globally.
        show_status_dot: Whether to show the status dot indicator globally.
        show_status_label: Whether to show the status label globally.

    Note:
        Global properties and per-item roles work together:
        - An element is shown only if BOTH global property is True AND
          per-item role is True (or None/unset).
        - Setting per-item role to False hides that element for that item.

    Note:
        When using custom backgrounds (Qt.BackgroundRole), call
        `FXThumbnailDelegate.apply_transparent_selection(view)` to disable the
        native Qt selection/hover highlighting, allowing the delegate's custom
        highlighting to be visible.

    Examples:
        >>> from fxgui import fxwidgets
        >>> from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem
        >>> from qtpy.QtCore import Qt
        >>> from qtpy.QtGui import QColor
        >>>
        >>> tree = QTreeWidget()
        >>> delegate = fxwidgets.FXThumbnailDelegate()
        >>> delegate.show_thumbnail = True
        >>> delegate.show_status_dot = True
        >>> delegate.show_status_label = True
        >>> tree.setItemDelegate(delegate)
        >>>
        >>> item = QTreeWidgetItem(tree, ["My Item"])
        >>> item.setData(0, fxwidgets.FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
        >>> item.setData(0, fxwidgets.FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, "/path/to/image.png")
        >>> item.setData(0, fxwidgets.FXThumbnailDelegate.DESCRIPTION_ROLE, "**Bold** description")
        >>> item.setData(0, fxwidgets.FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, QColor("green"))
        >>> # Hide status dot for this specific item
        >>> item.setData(0, fxwidgets.FXThumbnailDelegate.STATUS_DOT_VISIBLE_ROLE, False)
        >>> # Custom background color with rounded corners and border
        >>> item.setBackground(0, QColor("#252424"))
    """

    # Role constants for easier access
    THUMBNAIL_VISIBLE_ROLE = Qt.UserRole + 1
    THUMBNAIL_PATH_ROLE = Qt.UserRole + 2
    DESCRIPTION_ROLE = Qt.UserRole + 3
    STATUS_DOT_COLOR_ROLE = Qt.UserRole + 4
    STATUS_LABEL_COLOR_ROLE = Qt.UserRole + 5
    STATUS_LABEL_TEXT_ROLE = Qt.UserRole + 6
    STATUS_DOT_VISIBLE_ROLE = Qt.UserRole + 7
    STATUS_LABEL_VISIBLE_ROLE = Qt.UserRole + 8

    # Stylesheet constant is no longer used - apply_transparent_selection
    # now sets the stylesheet directly on the widget
    TRANSPARENT_SELECTION_STYLE = ""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the thumbnail delegate.

        Args:
            parent: The parent widget.
        """

        super().__init__(parent)
        self._show_thumbnail = True
        self._show_status_dot = True
        self._show_status_label = True

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme change by triggering a repaint of the parent view."""
        parent = self.parent()
        if parent and hasattr(parent, "viewport"):
            parent.viewport().update()
        elif parent and hasattr(parent, "update"):
            parent.update()

    @property
    def show_thumbnail(self) -> bool:
        """Whether thumbnails are shown globally.

        Individual items can override via THUMBNAIL_VISIBLE_ROLE.
        """
        return self._show_thumbnail

    @show_thumbnail.setter
    def show_thumbnail(self, value: bool) -> None:
        """Set whether thumbnails are shown globally."""
        self._show_thumbnail = value

    @property
    def show_status_dot(self) -> bool:
        """Whether the status dot is shown."""
        return self._show_status_dot

    @show_status_dot.setter
    def show_status_dot(self, value: bool) -> None:
        """Set whether the status dot is shown."""
        self._show_status_dot = value

    @property
    def show_status_label(self) -> bool:
        """Whether the status label is shown."""
        return self._show_status_label

    @show_status_label.setter
    def show_status_label(self, value: bool) -> None:
        """Set whether the status label is shown."""
        self._show_status_label = value

    # Stylesheet to disable default QTreeWidget selection (delegate handles it)
    TRANSPARENT_SELECTION_STYLE = """
        QTreeWidget {
            selection-background-color: transparent;
        }
        QTreeWidget::item {
            background: transparent;
        }
        QTreeWidget::item:selected {
            background: transparent;
            background-color: transparent;
            selection-background-color: transparent;
        }
        QTreeWidget::item:selected:active {
            background: transparent;
            background-color: transparent;
        }
        QTreeWidget::item:selected:!active {
            background: transparent;
            background-color: transparent;
        }
        QTreeWidget::item:hover {
            background: transparent;
            background-color: transparent;
        }
        QTreeView {
            selection-background-color: transparent;
        }
        QTreeView::item:selected {
            background: transparent;
            background-color: transparent;
        }
        QTreeView::item:selected:active {
            background: transparent;
            background-color: transparent;
        }
        QTreeView::item:selected:!active {
            background: transparent;
            background-color: transparent;
        }
        QTreeView::item:hover {
            background: transparent;
            background-color: transparent;
        }
        QTreeView::branch:selected {
            background: transparent;
        }
        QTreeView::branch:hover {
            background: transparent;
        }
    """

    @staticmethod
    def apply_transparent_selection(view: QWidget) -> None:
        """Apply transparent selection stylesheet to a tree view widget.

        This method disables the default Qt selection/hover backgrounds by
        applying a comprehensive stylesheet directly to the widget. The
        delegate handles all selection and hover highlighting itself.

        Call this on QTreeView/QTreeWidget instances that use custom
        backgrounds with FXThumbnailDelegate.

        Args:
            view: The tree view widget to apply transparent selection to.
        """
        current_style = view.styleSheet()
        view.setStyleSheet(
            current_style + FXThumbnailDelegate.TRANSPARENT_SELECTION_STYLE
        )

    @staticmethod
    def markdown_to_html(text: str) -> str:
        """Convert Markdown text to HTML.

        Args:
            text: Markdown-formatted text.

        Returns:
            HTML-formatted text.
        """

        if not text or text == "-":
            return text

        try:
            import markdown

            return markdown.markdown(text, extensions=["extra", "nl2br"])
        except ImportError:
            # Fallback if markdown is not installed
            return text

    @staticmethod
    def markdown_to_plain_text(text: str) -> str:
        """Convert Markdown text to plain text by removing formatting.

        Args:
            text: Markdown-formatted text.

        Returns:
            Plain text with Markdown formatting removed.
        """

        if not text or text == "-":
            return text

        try:
            import markdown
            from html.parser import HTMLParser

            class _HTMLStripper(HTMLParser):
                """Simple HTML tag stripper."""

                def __init__(self):
                    super().__init__()
                    self.reset()
                    self.strict = False
                    self.convert_charrefs = True
                    self.text = []

                def handle_data(self, d):
                    self.text.append(d)

                def get_data(self):
                    return "".join(self.text)

            # Convert Markdown to HTML first
            html = markdown.markdown(text, extensions=["extra", "nl2br"])

            # Remove HTML tags to get plain text
            stripper = _HTMLStripper()
            stripper.feed(html)
            plain_text = stripper.get_data()

            # Clean up extra whitespace
            plain_text = " ".join(plain_text.split())

            return plain_text
        except ImportError:
            # Fallback if markdown is not installed
            return text

    def helpEvent(
        self,
        event: QHelpEvent,
        view: QAbstractItemView,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        """Provide Markdown-formatted tooltips.

        Args:
            event (QHelpEvent): The help event.
            view (QAbstractItemView): The view widget.
            option (QStyleOptionViewItem): Style options.
            index (QModelIndex): The model index.

        Returns:
            True if the event was handled.
        """

        from qtpy.QtWidgets import QToolTip

        if event.type() == QEvent.ToolTip:
            # Get the entity data and description
            entity_data = index.data(Qt.UserRole)
            description = index.data(self.DESCRIPTION_ROLE)

            if entity_data and description and description != "-":
                # Convert Markdown to HTML for tooltip
                html_description = self.markdown_to_html(description)

                # Get entity name and type
                entity_name = entity_data.get("name", "Unknown")
                entity_type = entity_data.get("type", "Entity")

                # Create a formatted tooltip
                tooltip = (
                    f"<b>{entity_name}</b> ({entity_type})<hr>"
                    f"{html_description}"
                )

                QToolTip.showText(event.globalPos(), tooltip, view)
                return True

        return super().helpEvent(event, view, option, index)

    def _draw_status_dot(
        self,
        painter: QPainter,
        item_rect: QRect,
        status_color: QColor,
    ) -> None:
        """Draw a status indicator dot on the top-right corner.

        Args:
            painter: The painter to use for drawing.
            item_rect: The rectangle of the entire item.
            status_color: The color of the status dot.
        """

        if not status_color or not status_color.isValid():
            return

        # Status dot properties
        dot_size = 8
        dot_margin = 4

        # Calculate dot position (top-right corner of item)
        dot_x = item_rect.right() - dot_size - dot_margin
        dot_y = item_rect.top() + dot_margin

        # Don't draw if dot would go past left boundary
        if dot_x < item_rect.left() + dot_margin:
            return

        # Create dot rectangle
        dot_rect = QRect(dot_x, dot_y, dot_size, dot_size)

        # Draw the status dot with antialiasing
        painter.setRenderHint(QPainter.Antialiasing)
        # Use a darker border that contrasts with both light and dark backgrounds
        border_color = status_color.darker(150)
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(QBrush(status_color))
        painter.drawEllipse(dot_rect)

    def _draw_status_label(
        self,
        painter: QPainter,
        item_rect: QRect,
        label_color: QColor,
        label_text: str,
    ) -> None:
        """Draw a status label next to the status dot.

        Args:
            painter: The painter to use for drawing.
            item_rect: The rectangle of the entire item.
            label_color: The background color of the status label.
            label_text: The text to display in the status label.
        """

        if not label_color or not label_color.isValid() or not label_text:
            return

        # Status dot properties (for positioning reference)
        dot_size = 8
        dot_margin = 4

        # Label properties
        label_height = 14
        label_margin = 6
        label_padding = 4

        # Set up font for label text
        label_font = QFont()
        label_font.setPointSize(7)
        label_font.setBold(True)
        label_metrics = QFontMetrics(label_font)

        # Calculate label width based on text
        text_width = label_metrics.horizontalAdvance(label_text)
        label_width = text_width + (label_padding * 2)

        # Calculate label position (left of the status dot)
        dot_x = item_rect.right() - dot_size - dot_margin
        label_x = dot_x - label_width - label_margin
        label_y = item_rect.top() + dot_margin

        # Don't draw if label would go past left boundary
        if label_x < item_rect.left() + 4:
            return

        # Create label rectangle
        label_rect = QRect(label_x, label_y, label_width, label_height)

        # Draw the label background with rounded corners
        painter.setRenderHint(QPainter.Antialiasing)
        # Add a subtle border for visibility on selection
        border_color = label_color.darker(130)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(label_color))
        painter.drawRoundedRect(label_rect, 2, 2)

        # Draw the label text
        # Calculate appropriate text color based on background
        text_color = Qt.white if label_color.lightness() < 128 else Qt.black
        painter.setPen(text_color)
        painter.setFont(label_font)

        # Center the text in the label
        text_rect = QRect(
            label_x + label_padding, label_y, text_width, label_height
        )
        painter.drawText(text_rect, Qt.AlignCenter, label_text)

    def _get_column_position(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> Tuple[bool, bool]:
        """Determine if this is the first and/or last visible column.

        Args:
            option: Style options containing the widget reference.
            index: Model index to check.

        Returns:
            Tuple of (is_first_column, is_last_column).
        """

        is_first_column = index.column() == 0
        is_last_column = False

        view = option.widget
        if view and hasattr(view, "header"):
            header = view.header()
            if header:
                for col in range(header.count() - 1, -1, -1):
                    if not header.isSectionHidden(col):
                        is_last_column = index.column() == col
                        break

        return is_first_column, is_last_column

    def _create_rounded_path(
        self,
        rect_f: QRectF,
        radius: float,
        is_first_column: bool,
        is_last_column: bool,
    ) -> QPainterPath:
        """Create a QPainterPath for a rounded rectangle based on column position.

        Args:
            rect_f: The rectangle to create the path for.
            radius: The corner radius.
            is_first_column: Whether this is the first column.
            is_last_column: Whether this is the last column.

        Returns:
            A QPainterPath with appropriate rounded corners.
        """

        path = QPainterPath()

        if is_first_column and is_last_column:
            # Single column - all corners rounded
            path.addRoundedRect(rect_f, radius, radius)
        elif is_first_column:
            # First column - left corners rounded
            path.moveTo(rect_f.topRight())
            path.lineTo(rect_f.topLeft() + QRectF(radius, 0, 0, 0).topLeft())
            path.arcTo(
                QRectF(rect_f.left(), rect_f.top(), radius * 2, radius * 2),
                90,
                90,
            )
            path.lineTo(rect_f.bottomLeft() - QRectF(0, radius, 0, 0).topLeft())
            path.arcTo(
                QRectF(
                    rect_f.left(),
                    rect_f.bottom() - radius * 2,
                    radius * 2,
                    radius * 2,
                ),
                180,
                90,
            )
            path.lineTo(rect_f.bottomRight())
            path.lineTo(rect_f.topRight())
        elif is_last_column:
            # Last column - right corners rounded
            path.moveTo(rect_f.topLeft())
            path.lineTo(rect_f.topRight() - QRectF(radius, 0, 0, 0).topLeft())
            path.arcTo(
                QRectF(
                    rect_f.right() - radius * 2,
                    rect_f.top(),
                    radius * 2,
                    radius * 2,
                ),
                90,
                -90,
            )
            path.lineTo(
                rect_f.bottomRight() - QRectF(0, radius, 0, 0).topLeft()
            )
            path.arcTo(
                QRectF(
                    rect_f.right() - radius * 2,
                    rect_f.bottom() - radius * 2,
                    radius * 2,
                    radius * 2,
                ),
                0,
                -90,
            )
            path.lineTo(rect_f.bottomLeft())
            path.lineTo(rect_f.topLeft())
        else:
            # Middle column - no rounded corners
            path.addRect(rect_f)

        return path

    def _get_custom_background(
        self, index: QModelIndex, col0_index: Optional[QModelIndex] = None
    ) -> tuple:
        """Check if the item has a custom background color.

        Args:
            index: The model index to check.
            col0_index: Optional pre-computed column 0 index to avoid
                redundant sibling() calls.

        Returns:
            Tuple of (has_custom_background, bg_color).
        """

        if col0_index is None:
            col0_index = (
                index if index.column() == 0 else index.sibling(index.row(), 0)
            )
        background_data = col0_index.data(Qt.BackgroundRole)

        if background_data is not None:
            if isinstance(background_data, QBrush):
                bg_color = background_data.color()
                if bg_color.isValid() and bg_color.alpha() > 0:
                    return True, bg_color
            elif isinstance(background_data, QColor):
                if background_data.isValid() and background_data.alpha() > 0:
                    return True, background_data
        return False, None

    def _has_thumbnail(
        self, index: QModelIndex, col0_index: Optional[QModelIndex] = None
    ) -> bool:
        """Check if the item should show a thumbnail.

        Args:
            index: The model index to check.
            col0_index: Optional pre-computed column 0 index to avoid
                redundant sibling() calls.

        Returns:
            True if the item should show a thumbnail.
        """

        if col0_index is None:
            col0_index = (
                index if index.column() == 0 else index.sibling(index.row(), 0)
            )
        thumbnail_visible = col0_index.data(self.THUMBNAIL_VISIBLE_ROLE)
        return thumbnail_visible is not False and self._show_thumbnail

    def _draw_background_and_border(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        bg_color: QColor,
        column_position: Optional[Tuple[bool, bool]] = None,
    ) -> QRect:
        """Draw custom background with rounded corners and border.

        Args:
            painter: The painter to use.
            option: Style options.
            index: Model index.
            bg_color: Background color.
            column_position: Optional pre-computed (is_first, is_last) tuple.

        Returns:
            The adjusted rectangle used for drawing.
        """

        radius = 4  # Corner radius

        # Use pre-computed column position or calculate it
        if column_position is None:
            is_first_column, is_last_column = self._get_column_position(
                option, index
            )
        else:
            is_first_column, is_last_column = column_position

        # Adjust the rectangle based on position
        # Use consistent 1px inset on all sides for proper spacing
        if is_first_column:
            rect = option.rect.adjusted(1, 1, 0, -1)
        elif is_last_column:
            rect = option.rect.adjusted(0, 1, -1, -1)
        else:
            rect = option.rect.adjusted(0, 1, 0, -1)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Create path for rounded rectangle
        rect_f = QRectF(rect)
        path = self._create_rounded_path(
            rect_f, radius, is_first_column, is_last_column
        )

        # Fill background
        painter.fillPath(path, QBrush(bg_color))

        # Draw border
        border_color = bg_color.lighter(160)
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

        painter.restore()

        return rect

    def _draw_hover_selection(
        self,
        painter: QPainter,
        rect: QRect,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        column_position: Optional[Tuple[bool, bool]] = None,
    ) -> None:
        """Draw consistent hover/selection highlighting using theme colors.

        Args:
            painter: The painter to use.
            rect: The rectangle to fill.
            option: Style options containing state.
            index: Model index for determining rounded corners.
            column_position: Optional pre-computed (is_first, is_last) tuple.
        """

        if not (
            option.state & (QStyle.State_Selected | QStyle.State_MouseOver)
        ):
            return

        accent_color = QColor(self.theme.accent_primary)

        if option.state & QStyle.State_Selected:
            fill_color = accent_color
        else:
            # Use same accent color but with transparency for hover
            fill_color = QColor(accent_color)
            fill_color.setAlpha(80)  # ~30% opacity

        # Use pre-computed column position or calculate it
        radius = 4
        if column_position is None:
            is_first_column, is_last_column = self._get_column_position(
                option, index
            )
        else:
            is_first_column, is_last_column = column_position

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Create path for rounded rectangle matching background
        rect_f = QRectF(rect)
        path = self._create_rounded_path(
            rect_f, radius, is_first_column, is_last_column
        )

        painter.fillPath(path, QBrush(fill_color))
        painter.restore()

    def _draw_status_indicators(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Draw status dot and label indicators.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
        """

        status_dot_color = index.data(self.STATUS_DOT_COLOR_ROLE)
        status_label_color = index.data(self.STATUS_LABEL_COLOR_ROLE)
        status_label_text = index.data(self.STATUS_LABEL_TEXT_ROLE)

        item_show_dot = index.data(self.STATUS_DOT_VISIBLE_ROLE)
        item_show_label = index.data(self.STATUS_LABEL_VISIBLE_ROLE)

        show_label = (
            self._show_status_label
            and item_show_label is not False
            and status_label_color
            and status_label_text
        )
        if show_label:
            self._draw_status_label(
                painter, option.rect, status_label_color, status_label_text
            )

        show_dot = (
            self._show_status_dot
            and item_show_dot is not False
            and status_dot_color
        )
        if show_dot:
            self._draw_status_dot(painter, option.rect, status_dot_color)

    def _draw_thumbnail_content(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Draw thumbnail, title, and description for column 0.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
        """

        thumbnail_path = index.data(self.THUMBNAIL_PATH_ROLE)
        thumbnail = QPixmap(thumbnail_path) if thumbnail_path else QPixmap()

        # Use fallback if thumbnail is null/invalid
        if thumbnail.isNull():
            fallback_path = (
                Path(__file__).parent.parent / "images" / "missing_image.png"
            )
            if fallback_path.exists():
                thumbnail = QPixmap(str(fallback_path))
            else:
                # Create a simple placeholder pixmap
                thumbnail = QPixmap(70, 70)
                thumbnail.fill(QColor(80, 80, 80))

        # Fixed thumbnail size
        thumbnail_size = 70
        x_offset = 5

        if not thumbnail.isNull():
            thumbnail = thumbnail.scaled(
                thumbnail_size,
                thumbnail_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

        # Create bordered thumbnail
        bordered_thumbnail = QPixmap(thumbnail.size() + QSize(2, 2))
        bordered_thumbnail.fill(Qt.transparent)

        painter_with_border = QPainter(bordered_thumbnail)
        painter_with_border.setRenderHint(QPainter.Antialiasing)
        painter_with_border.drawPixmap(1, 1, thumbnail)
        painter_with_border.setPen(QPen(Qt.white, 1))
        painter_with_border.setBrush(Qt.NoBrush)
        painter_with_border.drawRoundedRect(
            bordered_thumbnail.rect().marginsRemoved(QMargins(1, 1, 1, 1)), 2, 2
        )
        painter_with_border.end()

        # Draw the thumbnail
        thumbnail_y = (
            option.rect.top()
            + (option.rect.height() - bordered_thumbnail.height()) // 2
        )
        thumbnail_x = option.rect.left() + x_offset
        painter.drawPixmap(thumbnail_x, thumbnail_y, bordered_thumbnail)

        # Draw title and description
        thumbnail_width_with_padding = bordered_thumbnail.width() + x_offset * 2
        text_x = option.rect.left() + thumbnail_width_with_padding + 5
        text_y = option.rect.top() + 8
        text_width = option.rect.width() - thumbnail_width_with_padding - 10

        title = index.data(Qt.DisplayRole) or ""
        description = index.data(self.DESCRIPTION_ROLE) or ""

        if description and description != "-":
            description = self.markdown_to_plain_text(description)

        # Set up fonts
        title_font = QFont(option.font)
        title_font.setBold(True)
        description_font = QFont(option.font)
        description_font.setPointSize(max(8, option.font.pointSize() - 1))

        title_metrics = QFontMetrics(title_font)
        description_metrics = QFontMetrics(description_font)
        title_height = title_metrics.height()

        # Set text color
        if option.state & QStyle.State_Selected:
            text_color = option.palette.highlightedText().color()
        else:
            text_color = option.palette.text().color()

        painter.setPen(text_color)

        # Draw title
        painter.setFont(title_font)
        title_rect = QRect(text_x, text_y, text_width, title_height)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignTop, title)

        # Draw description
        if description:
            painter.setFont(description_font)
            description_color = QColor(text_color)
            description_color.setAlpha(180)
            painter.setPen(description_color)

            description_rect = QRect(
                text_x,
                text_y + title_height + 2,
                text_width,
                description_metrics.height(),
            )
            elided_description = description_metrics.elidedText(
                description, Qt.ElideRight, text_width
            )
            painter.drawText(
                description_rect, Qt.AlignLeft | Qt.AlignTop, elided_description
            )

    def _draw_icon_and_text(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Draw icon and text for column 0 items without thumbnails.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
        """

        icon = index.data(Qt.DecorationRole)
        description = index.data(self.DESCRIPTION_ROLE) or ""

        icon_size = 16
        icon_margin = 6
        text_x = option.rect.left() + icon_margin

        if icon is not None and not icon.isNull():
            icon_x = option.rect.left() + icon_margin
            icon_y = option.rect.top() + (option.rect.height() - icon_size) // 2
            icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)
            icon.paint(painter, icon_rect, Qt.AlignCenter)
            text_x = icon_x + icon_size + icon_margin

        # Set text color
        if option.state & QStyle.State_Selected:
            text_color = option.palette.highlightedText().color()
        else:
            text_color = option.palette.text().color()

        title = index.data(Qt.DisplayRole) or ""

        if description and description != "-":
            # Two-line layout
            title_font = QFont(option.font)
            title_font.setBold(True)
            title_metrics = QFontMetrics(title_font)
            title_height = title_metrics.height()

            description_font = QFont(option.font)
            description_font.setPointSize(max(8, option.font.pointSize() - 1))
            description_metrics = QFontMetrics(description_font)

            content_width = (
                option.rect.width()
                - (text_x - option.rect.left())
                - icon_margin
            )

            # Draw title
            title_rect = QRect(
                text_x, option.rect.top() + 4, content_width, title_height
            )
            painter.setPen(text_color)
            painter.setFont(title_font)
            elided_title = title_metrics.elidedText(
                title, Qt.ElideRight, content_width
            )
            painter.drawText(
                title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title
            )

            # Draw description
            description_plain = self.markdown_to_plain_text(description)
            description_rect = QRect(
                text_x,
                option.rect.top() + title_height + 6,
                content_width,
                description_metrics.height(),
            )
            desc_color = QColor(text_color)
            desc_color.setAlpha(180)
            painter.setPen(desc_color)
            painter.setFont(description_font)
            elided_desc = description_metrics.elidedText(
                description_plain, Qt.ElideRight, content_width
            )
            painter.drawText(
                description_rect, Qt.AlignLeft | Qt.AlignTop, elided_desc
            )
        else:
            # Single-line layout
            painter.setPen(text_color)
            painter.setFont(option.font)
            text_rect = QRect(
                text_x,
                option.rect.top(),
                option.rect.width()
                - (text_x - option.rect.left())
                - icon_margin,
                option.rect.height(),
            )
            painter.drawText(
                text_rect, Qt.AlignLeft | Qt.AlignVCenter, str(title)
            )

    def _draw_text(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Draw text for non-column-0 items.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
        """

        text = index.data(Qt.DisplayRole)
        if text:
            if option.state & QStyle.State_Selected:
                text_color = option.palette.highlightedText().color()
            else:
                text_color = option.palette.text().color()
            painter.setPen(text_color)
            painter.setFont(option.font)
            text_rect = option.rect.adjusted(6, 0, -6, 0)
            painter.drawText(
                text_rect, Qt.AlignLeft | Qt.AlignVCenter, str(text)
            )

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> QSize:
        """Return the size hint for the item at the given index.

        Args:
            option: The style options for the item.
            index: The model index of the item.

        Returns:
            The size hint for the item.
        """

        original_size = super().sizeHint(option, index)

        # Get column 0 index once (avoid redundant sibling calls)
        is_col0 = index.column() == 0
        col0_index = index if is_col0 else index.sibling(index.row(), 0)

        # Check if ANY column in this row has a thumbnail
        # Respect both the delegate's show_thumbnail property and item's role
        has_thumbnail = False
        item_show_thumbnail = None
        if index.model() and self._show_thumbnail:
            item_show_thumbnail = col0_index.data(self.THUMBNAIL_VISIBLE_ROLE)
            has_thumbnail = item_show_thumbnail is None or item_show_thumbnail

        # Check if the item has a description (needs more height)
        description = (
            col0_index.data(self.DESCRIPTION_ROLE) if index.model() else None
        )
        has_description = bool(description and description != "-")

        # Use consistent height based on content:
        # - Thumbnail items: 50px (thumbnail + title + description)
        # - Non-thumbnail with description: 40px (title + description)
        # - Simple items: 30px (title only)
        if has_thumbnail:
            fixed_height = 50
        elif has_description:
            fixed_height = 40
        else:
            fixed_height = 30

        # Only add thumbnail width for the first column
        if is_col0:
            show_thumbnail = self._show_thumbnail and (
                item_show_thumbnail is None or item_show_thumbnail
            )
            if show_thumbnail:
                # Add thumbnail width + padding to the original width
                thumbnail_size = 70
                x_offset = 5
                thumbnail_width_with_padding = (
                    thumbnail_size + 2 + (x_offset * 2)
                )
                additional_spacing = 10

                # Calculate width needed for text content
                title = index.data(Qt.DisplayRole) or ""
                description = index.data(self.DESCRIPTION_ROLE) or ""

                # Set up fonts
                title_font = QFont(option.font)
                title_font.setBold(True)
                title_metrics = QFontMetrics(title_font)
                title_width = (
                    title_metrics.horizontalAdvance(title) if title else 0
                )

                description_width = 0
                if description:
                    description_font = QFont(option.font)
                    description_font.setPointSize(
                        max(8, option.font.pointSize() - 1)
                    )
                    description_metrics = QFontMetrics(description_font)
                    description_width = description_metrics.horizontalAdvance(
                        description
                    )

                # Use the wider of title or description
                text_width = max(title_width, description_width)

                # Add space for status dot
                dot_size = 8
                dot_margin = 4
                status_dot_width = dot_size + dot_margin

                # Add space for status label if present
                status_label_text = index.data(self.STATUS_LABEL_TEXT_ROLE)
                status_label_width = 0
                if status_label_text:
                    label_font = QFont()
                    label_font.setPointSize(7)
                    label_font.setBold(True)
                    label_metrics = QFontMetrics(label_font)
                    label_text_width = label_metrics.horizontalAdvance(
                        status_label_text
                    )
                    label_padding = 4
                    label_margin = 2
                    status_label_width = (
                        label_text_width + (label_padding * 2) + label_margin
                    )

                # Calculate total width needed
                total_width = (
                    thumbnail_width_with_padding
                    + text_width
                    + additional_spacing
                    + status_dot_width
                    + status_label_width
                )

                return QSize(
                    max(original_size.width(), total_width), fixed_height
                )
            else:
                return QSize(original_size.width(), fixed_height)
        else:
            return QSize(original_size.width(), fixed_height)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the item with custom background, border, and hover/selection.

        This method handles all painting consistently across all items and
        columns, ensuring hover and selection highlighting looks the same
        everywhere. It supports custom background colors via Qt.BackgroundRole
        with rounded corners and borders.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
        """

        # Initialize style option properly to get consistent font/state
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        painter.save()
        painter.setClipRect(opt.rect)

        # Pre-compute column 0 index and column position once for reuse
        is_col0 = index.column() == 0
        col0_index = index if is_col0 else index.sibling(index.row(), 0)

        # Check for custom background (pass col0_index to avoid redundant call)
        has_custom_background, bg_color = self._get_custom_background(
            index, col0_index
        )
        has_thumbnail = self._has_thumbnail(index, col0_index)

        rect = opt.rect

        # Pre-compute column position for background/hover drawing
        column_position = None
        if has_custom_background:
            column_position = self._get_column_position(opt, index)

        # Draw background
        if has_custom_background:
            # Fill with surface_sunken first to ensure consistent gap color
            # between items (matches non-custom-background items)
            surface_color = QColor(self.theme.surface_sunken)
            painter.fillRect(opt.rect, surface_color)

            # Draw custom background with border
            rect = self._draw_background_and_border(
                painter, opt, index, bg_color, column_position
            )
        else:
            # Fill with theme surface color for items without custom background
            # This covers any selection Qt drew before calling delegate
            surface_color = QColor(self.theme.surface_sunken)
            painter.fillRect(opt.rect, surface_color)

        # Draw hover/selection overlay (consistent for all items)
        self._draw_hover_selection(painter, rect, opt, index, column_position)

        painter.restore()

        # Draw content
        painter.save()
        painter.setClipRect(opt.rect)

        if is_col0:
            if has_thumbnail:
                self._draw_thumbnail_content(painter, opt, index)
            else:
                self._draw_icon_and_text(painter, opt, index)
            # Draw status indicators for column 0
            self._draw_status_indicators(painter, opt, index)
        else:
            self._draw_text(painter, opt, index)

        painter.restore()


def example() -> None:
    import sys
    from qtpy.QtWidgets import (
        QHBoxLayout,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
        QCheckBox,
        QLabel,
    )
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXDelegates Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Get feedback colors from theme
    feedback = fxstyle.get_feedback_colors()

    ###### FXColorLabelDelegate
    layout.addWidget(QLabel("FXColorLabelDelegate:"))
    tree1 = QTreeWidget()
    tree1.setHeaderLabels(["Status"])
    tree1.setRootIsDecorated(False)

    # Define colors and icons for different statuses using feedback colors
    colors_icons = {
        "success": (
            QColor(feedback["success"]["background"]),
            QColor(feedback["success"]["foreground"]),
            QColor(feedback["success"]["foreground"]),
            fxicons.get_icon("check_circle"),
            True,
        ),
        "warning": (
            QColor(feedback["warning"]["background"]),
            QColor(feedback["warning"]["foreground"]),
            QColor(feedback["warning"]["foreground"]),
            fxicons.get_icon("warning"),
            True,
        ),
        "error": (
            QColor(feedback["error"]["background"]),
            QColor(feedback["error"]["foreground"]),
            QColor(feedback["error"]["foreground"]),
            fxicons.get_icon("error"),
            True,
        ),
        "info": (
            QColor(feedback["info"]["background"]),
            QColor(feedback["info"]["foreground"]),
            QColor(feedback["info"]["foreground"]),
            fxicons.get_icon("info"),
            True,
        ),
    }
    delegate1 = FXColorLabelDelegate(colors_icons)
    tree1.setItemDelegate(delegate1)

    for status in ["Success", "Warning", "Error", "Info", "Unknown"]:
        QTreeWidgetItem(tree1, [status])
    tree1.setMaximumHeight(150)
    layout.addWidget(tree1)

    ###### FXThumbnailDelegate - With Thumbnails and Custom Backgrounds

    layout.addWidget(
        QLabel("FXThumbnailDelegate (thumbnails + custom backgrounds):")
    )
    tree2 = QTreeWidget()
    tree2.setHeaderLabels(["Name", "Type", "Status"])
    tree2.setRootIsDecorated(False)

    delegate2 = FXThumbnailDelegate()
    delegate2.show_thumbnail = True
    delegate2.show_status_dot = True
    delegate2.show_status_label = True
    # Apply delegate to all columns for consistent styling
    tree2.setItemDelegate(delegate2)
    # Apply transparent selection style for custom backgrounds
    FXThumbnailDelegate.apply_transparent_selection(tree2)

    # Thumbnail image path
    thumbnail_path = str(
        Path(__file__).parent.parent / "images" / "missing_image.png"
    )

    # Sample items with thumbnails - we'll set backgrounds via helper function
    items_data = [
        ("Asset 001", "Character", "Ready", "success"),
        ("Asset 002", "Prop", "Review", "warning"),
        ("Asset 003", "Environment", "WIP", "error"),
    ]

    for name, asset_type, label_text, feedback_key in items_data:
        item = QTreeWidgetItem(tree2, [name, asset_type, label_text])
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, thumbnail_path)
        item.setData(
            0,
            FXThumbnailDelegate.DESCRIPTION_ROLE,
            f"A **{asset_type.lower()}** asset",
        )
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, label_text)
        # Store the feedback key for dynamic color updates
        item.setData(0, Qt.UserRole + 100, feedback_key)

    tree2.setColumnWidth(0, 300)
    layout.addWidget(tree2)

    ###### FXThumbnailDelegate - With Custom Backgrounds

    layout.addWidget(QLabel("FXThumbnailDelegate (custom backgrounds):"))
    tree3 = QTreeWidget()
    tree3.setHeaderLabels(["Name", "Type", "Status"])
    tree3.setRootIsDecorated(False)

    delegate3 = FXThumbnailDelegate()
    delegate3.show_thumbnail = False  # No thumbnails, show icons instead
    delegate3.show_status_dot = True
    delegate3.show_status_label = True
    tree3.setItemDelegate(delegate3)
    # Apply transparent selection style for custom backgrounds
    FXThumbnailDelegate.apply_transparent_selection(tree3)

    # Items with custom backgrounds - we'll set backgrounds via helper function
    items_with_bg = [
        ("Project Alpha", "Feature", "In Progress", "info", "folder"),
        ("Bug Fix #123", "Bug", "Testing", "warning", "bug_report"),
        ("Documentation", "Task", "Done", "success", "description"),
        ("API Refactor", "Enhancement", "Review", "error", "code"),
    ]

    for name, item_type, status, feedback_key, icon_name in items_with_bg:
        item = QTreeWidgetItem(tree3, [name, item_type, status])
        # Set icon for column 0
        item.setIcon(0, fxicons.get_icon(icon_name))
        # Set description
        item.setData(
            0,
            FXThumbnailDelegate.DESCRIPTION_ROLE,
            f"A {item_type.lower()} item",
        )
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, status)
        # Store the feedback key for dynamic color updates
        item.setData(0, Qt.UserRole + 100, feedback_key)
        # Disable thumbnails for this item
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)

    tree3.setColumnWidth(0, 250)
    tree3.setColumnWidth(1, 100)
    layout.addWidget(tree3)

    ###### Theme awareness for custom backgrounds
    # Theme-aware custom backgrounds: Update colors when theme changes
    #
    # This helper function updates all item backgrounds and status colors
    # based on the current theme. Call it at startup and connect it to the
    # theme_changed signal to keep colors in sync with the active theme

    # Define custom color palettes for dark and light themes
    # These are semantic colors that adapt to the theme
    CUSTOM_COLORS = {
        "dark": {
            "red": QColor("#4a2020"),  # Dark red for dark theme
            "blue": QColor("#1a3a5c"),  # Dark blue for dark theme
            "green": QColor("#1a3a1a"),  # Dark green for dark theme
            "purple": QColor("#3a1a4a"),  # Dark purple for dark theme
        },
        "light": {
            "red": QColor("#ffcccc"),  # Light red/pink for light theme
            "blue": QColor("#cce5ff"),  # Light blue for light theme
            "green": QColor("#ccffcc"),  # Light green for light theme
            "purple": QColor("#e5ccff"),  # Light purple for light theme
        },
    }

    # Assign a color key to each item for theme-aware backgrounds
    color_keys = ["red", "blue", "green", "purple"]

    def update_item_colors(_theme_name: str = None) -> None:
        """Update item backgrounds and status colors based on current theme.

        This function demonstrates how to make custom BackgroundRole colors
        theme-aware. It reads the current theme colors and applies them to
        all items in the tree widgets.

        Args:
            _theme_name: The name of the new theme (unused, provided by signal).
        """
        # Get fresh theme colors
        theme = fxstyle.FXThemeColors(fxstyle.get_theme_colors())
        feedback = fxstyle.get_feedback_colors()
        palette_key = "light" if fxstyle.is_light_theme() else "dark"

        # Update tree2 items (with thumbnails) - uses custom colors
        for i in range(tree2.topLevelItemCount()):
            item = tree2.topLevelItem(i)
            feedback_key = item.data(0, Qt.UserRole + 100)
            if feedback_key and feedback_key in feedback:
                # Set status colors from feedback
                item.setData(
                    0,
                    FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE,
                    QColor(feedback[feedback_key]["foreground"]),
                )
                item.setData(
                    0,
                    FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE,
                    QColor(feedback[feedback_key]["background"]),
                )
            # Set background color from custom palette (cycles through colors)
            color_key = color_keys[i % len(color_keys)]
            bg_color = CUSTOM_COLORS[palette_key][color_key]
            item.setBackground(0, bg_color)
            item.setBackground(1, bg_color)
            item.setBackground(2, bg_color)

        # Update tree3 items (without thumbnails) - uses surface variations
        base_surface = QColor(theme.surface_sunken)
        for i in range(tree3.topLevelItemCount()):
            item = tree3.topLevelItem(i)
            feedback_key = item.data(0, Qt.UserRole + 100)
            if feedback_key and feedback_key in feedback:
                # Set status colors from feedback
                status_color = QColor(feedback[feedback_key]["foreground"])
                item.setData(
                    0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, status_color
                )
                item.setData(
                    0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, status_color
                )
            # Set background color (darker variations of base surface)
            darkness = 105 + (i % 4) * 5  # 105, 110, 115, 120
            bg_color = base_surface.darker(darkness)
            item.setBackground(0, bg_color)
            item.setBackground(1, bg_color)
            item.setBackground(2, bg_color)

        # Trigger repaint
        tree2.viewport().update()
        tree3.viewport().update()

    # Apply initial colors
    update_item_colors()

    # Connect to theme changes so colors update when user switches theme
    fxstyle.theme_manager.theme_changed.connect(update_item_colors)

    # Controls
    controls = QWidget()
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(0, 0, 0, 0)

    show_thumb_cb = QCheckBox("Show Thumbnails")
    show_thumb_cb.setChecked(True)
    show_thumb_cb.toggled.connect(
        lambda checked: setattr(delegate2, "show_thumbnail", checked)
        or tree2.viewport().update()
    )
    controls_layout.addWidget(show_thumb_cb)

    show_dot_cb = QCheckBox("Show Status Dot")
    show_dot_cb.setChecked(True)
    show_dot_cb.toggled.connect(
        lambda checked: (
            setattr(delegate2, "show_status_dot", checked),
            setattr(delegate3, "show_status_dot", checked),
            tree2.viewport().update(),
            tree3.viewport().update(),
        )
    )
    controls_layout.addWidget(show_dot_cb)

    show_label_cb = QCheckBox("Show Status Label")
    show_label_cb.setChecked(True)
    show_label_cb.toggled.connect(
        lambda checked: (
            setattr(delegate2, "show_status_label", checked),
            setattr(delegate3, "show_status_label", checked),
            tree2.viewport().update(),
            tree3.viewport().update(),
        )
    )
    controls_layout.addWidget(show_label_cb)

    controls_layout.addStretch()
    layout.addWidget(controls)

    layout.addStretch()
    window.resize(600, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
