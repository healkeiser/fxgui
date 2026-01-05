"""Custom item delegates for tree/list views."""

# Built-in
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

# Third-party
from qtpy.QtCore import QEvent, QMargins, QModelIndex, QRect, QSize, Qt
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QHelpEvent,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


class FXColorLabelDelegate(QStyledItemDelegate):
    """A custom delegate to paint items with specific colors and icons based
    on their text content."""

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
        theme_colors = fxstyle.get_theme_colors()
        background_color, border_color, text_icon_color, icon, color_icon = (
            QColor(theme_colors["surface"]),
            QColor(theme_colors["border_light"]),
            QColor(
                theme_colors["surface"]
                if fxstyle._theme == "dark"
                else "#ffffff"
            ),
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


class FXThumbnailDelegate(QStyledItemDelegate):
    """Custom item delegate for showing thumbnails in tree/list views.

    This delegate displays items with thumbnails, titles, descriptions,
    and status indicators. It supports Markdown formatting in descriptions
    and tooltips.

    Note:
        Store data in items using the following roles:
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

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the thumbnail delegate.

        Args:
            parent: The parent widget.
        """

        super().__init__(parent)
        self._show_thumbnail = True
        self._show_status_dot = True
        self._show_status_label = True

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

        # Check if ANY column in this row has a thumbnail
        # Respect both the delegate's show_thumbnail property and item's role
        has_thumbnail = False
        if index.model() and self._show_thumbnail:
            first_column_index = index.sibling(index.row(), 0)
            item_show_thumbnail = first_column_index.data(
                self.THUMBNAIL_VISIBLE_ROLE
            )
            has_thumbnail = item_show_thumbnail is None or item_show_thumbnail

        # Use consistent height based on whether this row has thumbnails
        fixed_height = 50 if has_thumbnail else 30

        # Only add thumbnail width for the first column
        if index.column() == 0:
            item_show_thumbnail = index.data(self.THUMBNAIL_VISIBLE_ROLE)
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
        """Paint the item at the given index.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
        """

        # Save painter state and set clipping to prevent overflow
        painter.save()
        painter.setClipRect(option.rect)

        # Use QStyle to draw the row background consistently
        # This ensures hover, selection, and alternating colors match other columns
        opt = QStyleOptionViewItem(option)
        opt.text = ""
        opt.icon = QIcon()
        opt.decorationSize = QSize(0, 0)
        style = opt.widget.style() if opt.widget else QApplication.style()
        # Draw the row background primitive (handles alternating, hover, selection)
        style.drawPrimitive(
            QStyle.PE_PanelItemViewRow, opt, painter, opt.widget
        )
        # Draw the item background (for selection/hover highlighting)
        style.drawPrimitive(
            QStyle.PE_PanelItemViewItem, opt, painter, opt.widget
        )

        # Initialize variables for thumbnail dimensions and offsets
        x_offset = 5
        thumbnail_width_with_padding = 0

        # Check if it's the first column and the thumbnail should be shown
        # Respect both the delegate's show_thumbnail property and item's role
        if index.column() == 0:
            item_show_thumbnail = index.data(self.THUMBNAIL_VISIBLE_ROLE)
            # Show thumbnail if: delegate allows AND (item role is True or None)
            show_thumbnail = self._show_thumbnail and (
                item_show_thumbnail is None or item_show_thumbnail
            )
            if show_thumbnail:
                thumbnail_path = index.data(self.THUMBNAIL_PATH_ROLE)
                thumbnail = (
                    QPixmap(thumbnail_path) if thumbnail_path else QPixmap()
                )

                # Use fallback if thumbnail is null/invalid
                if thumbnail.isNull():
                    # Try to use splash.png as fallback, or create a placeholder
                    fallback_path = (
                        Path(__file__).parent.parent / "images" / "splash.png"
                    )
                    if fallback_path.exists():
                        thumbnail = QPixmap(str(fallback_path))
                    else:
                        # Create a simple placeholder pixmap
                        thumbnail = QPixmap(70, 70)
                        thumbnail.fill(QColor(80, 80, 80))

                # Fixed thumbnail size
                thumbnail_size = 70
                if not thumbnail.isNull():
                    thumbnail = thumbnail.scaled(
                        thumbnail_size,
                        thumbnail_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )

                bordered_thumbnail = QPixmap(thumbnail.size() + QSize(2, 2))
                bordered_thumbnail.fill(Qt.transparent)

                painter_with_border = QPainter(bordered_thumbnail)
                painter_with_border.setRenderHint(QPainter.Antialiasing)

                # Draw the actual thumbnail image first
                painter_with_border.drawPixmap(1, 1, thumbnail)

                # Then draw the border on top
                painter_with_border.setPen(QPen(Qt.white, 1))
                painter_with_border.setBrush(Qt.NoBrush)
                radius = 2
                painter_with_border.drawRoundedRect(
                    bordered_thumbnail.rect().marginsRemoved(
                        QMargins(1, 1, 1, 1)
                    ),
                    radius,
                    radius,
                )
                painter_with_border.end()

                # Calculate the position to draw the thumbnail
                thumbnail_y = (
                    option.rect.top()
                    + (option.rect.height() - bordered_thumbnail.height()) // 2
                )

                # Draw the thumbnail
                thumbnail_x = option.rect.left() + x_offset
                painter.drawPixmap(
                    thumbnail_x,
                    thumbnail_y,
                    bordered_thumbnail,
                )

                # Update the width for the thumbnail with padding
                thumbnail_width_with_padding = (
                    bordered_thumbnail.width() + x_offset * 2
                )

                # Draw title and description text
                text_x = option.rect.left() + thumbnail_width_with_padding + 5
                text_y = option.rect.top() + 8
                text_width = (
                    option.rect.width() - thumbnail_width_with_padding - 10
                )

                # Get the item text (title) and description
                title = index.data(Qt.DisplayRole) or ""
                description = index.data(self.DESCRIPTION_ROLE) or ""

                # Convert Markdown description to plain text for display
                if description and description != "-":
                    description = self.markdown_to_plain_text(description)

                # Set up fonts
                title_font = QFont(option.font)
                title_font.setBold(True)

                description_font = QFont(option.font)
                description_font.setPointSize(
                    max(8, option.font.pointSize() - 1)
                )

                # Calculate text metrics
                title_metrics = QFontMetrics(title_font)
                description_metrics = QFontMetrics(description_font)

                title_height = title_metrics.height()
                description_height = (
                    description_metrics.height() if description else 0
                )

                # Set text color based on selection state
                if option.state & QStyle.State_Selected:
                    text_color = option.palette.highlightedText().color()
                else:
                    text_color = option.palette.text().color()

                painter.setPen(text_color)

                # Draw title
                painter.setFont(title_font)
                title_rect = QRect(text_x, text_y, text_width, title_height)
                painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignTop, title)

                # Draw description if available
                if description:
                    painter.setFont(description_font)
                    # Make description text slightly more transparent
                    description_color = QColor(text_color)
                    description_color.setAlpha(180)
                    painter.setPen(description_color)

                    description_rect = QRect(
                        text_x,
                        text_y + title_height + 2,
                        text_width,
                        description_height,
                    )

                    # Elide description text if it's too long
                    elided_description = description_metrics.elidedText(
                        description, Qt.ElideRight, text_width
                    )

                    painter.drawText(
                        description_rect,
                        Qt.AlignLeft | Qt.AlignTop,
                        elided_description,
                    )

            # Draw status indicators for first column with thumbnails
            if show_thumbnail is None or show_thumbnail:
                status_dot_color = index.data(self.STATUS_DOT_COLOR_ROLE)
                status_label_color = index.data(self.STATUS_LABEL_COLOR_ROLE)
                status_label_text = index.data(self.STATUS_LABEL_TEXT_ROLE)

                # Check per-item visibility (None = inherit from global)
                item_show_dot = index.data(self.STATUS_DOT_VISIBLE_ROLE)
                item_show_label = index.data(self.STATUS_LABEL_VISIBLE_ROLE)

                # Draw status label first (positioned left of status dot)
                # Show if: global enabled AND per-item not False AND has data
                show_label = (
                    self._show_status_label
                    and item_show_label is not False
                    and status_label_color
                    and status_label_text
                )
                if show_label:
                    self._draw_status_label(
                        painter,
                        option.rect,
                        status_label_color,
                        status_label_text,
                    )

                # Draw status dot
                # Show if: global enabled AND per-item not False AND has color
                show_dot = (
                    self._show_status_dot
                    and item_show_dot is not False
                    and status_dot_color
                )
                if show_dot:
                    self._draw_status_dot(
                        painter, option.rect, status_dot_color
                    )
                painter.restore()
                return

        # For first column when thumbnails are disabled, draw text ourselves
        # to maintain consistent styling, then draw status indicators on top
        if index.column() == 0:
            item_show_thumbnail = index.data(self.THUMBNAIL_VISIBLE_ROLE)
            # Thumbnails are disabled if: delegate disables OR item role is False
            thumbnails_disabled = (
                not self._show_thumbnail or item_show_thumbnail is False
            )
            if thumbnails_disabled:
                # Get text content
                title = index.data(Qt.DisplayRole) or ""
                description = index.data(self.DESCRIPTION_ROLE) or ""

                # Set text color based on selection state
                if option.state & QStyle.State_Selected:
                    text_color = option.palette.highlightedText().color()
                else:
                    text_color = option.palette.text().color()

                # Calculate layout - title on top, description below
                x_offset = 6
                content_rect = option.rect.adjusted(x_offset, 4, -x_offset, -4)

                if description:
                    # Two-line layout: title and description
                    title_font = QFont(option.font)
                    title_font.setBold(True)
                    title_metrics = QFontMetrics(title_font)
                    title_height = title_metrics.height()

                    description_font = QFont(option.font)
                    description_font.setPointSize(
                        max(8, option.font.pointSize() - 1)
                    )
                    description_metrics = QFontMetrics(description_font)

                    # Draw title
                    title_rect = QRect(
                        content_rect.x(),
                        content_rect.y(),
                        content_rect.width(),
                        title_height,
                    )
                    painter.setPen(text_color)
                    painter.setFont(title_font)
                    elided_title = title_metrics.elidedText(
                        title, Qt.ElideRight, title_rect.width()
                    )
                    painter.drawText(
                        title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title
                    )

                    # Draw description (convert Markdown to plain text)
                    description_plain = self.markdown_to_plain_text(description)
                    description_rect = QRect(
                        content_rect.x(),
                        content_rect.y() + title_height + 2,
                        content_rect.width(),
                        content_rect.height() - title_height - 2,
                    )
                    # Use slightly muted color for description
                    desc_color = QColor(text_color)
                    desc_color.setAlpha(180)
                    painter.setPen(desc_color)
                    painter.setFont(description_font)
                    elided_description = description_metrics.elidedText(
                        description_plain,
                        Qt.ElideRight,
                        description_rect.width(),
                    )
                    painter.drawText(
                        description_rect,
                        Qt.AlignLeft | Qt.AlignTop,
                        elided_description,
                    )
                else:
                    # Single-line layout: just title, vertically centered
                    painter.setPen(text_color)
                    painter.setFont(option.font)
                    painter.drawText(
                        content_rect, Qt.AlignLeft | Qt.AlignVCenter, title
                    )

                # Draw status indicators on top
                status_dot_color = index.data(self.STATUS_DOT_COLOR_ROLE)
                status_label_color = index.data(self.STATUS_LABEL_COLOR_ROLE)
                status_label_text = index.data(self.STATUS_LABEL_TEXT_ROLE)

                # Check per-item visibility (None = inherit from global)
                item_show_dot = index.data(self.STATUS_DOT_VISIBLE_ROLE)
                item_show_label = index.data(self.STATUS_LABEL_VISIBLE_ROLE)

                # Show if: global enabled AND per-item not False AND has data
                show_label = (
                    self._show_status_label
                    and item_show_label is not False
                    and status_label_color
                    and status_label_text
                )
                if show_label:
                    self._draw_status_label(
                        painter,
                        option.rect,
                        status_label_color,
                        status_label_text,
                    )

                show_dot = (
                    self._show_status_dot
                    and item_show_dot is not False
                    and status_dot_color
                )
                if show_dot:
                    self._draw_status_dot(
                        painter, option.rect, status_dot_color
                    )
                painter.restore()
                return

        # For other columns, use default painting
        super().paint(painter, option, index)
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
    colors = fxstyle.get_colors()
    feedback = colors["feedback"]

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

    ###### FXThumbnailDelegate
    layout.addWidget(QLabel("FXThumbnailDelegate:"))
    tree2 = QTreeWidget()
    tree2.setHeaderLabels(["Name", "Type"])
    tree2.setRootIsDecorated(False)

    delegate2 = FXThumbnailDelegate()
    delegate2.show_thumbnail = True
    delegate2.show_status_dot = True
    delegate2.show_status_label = True
    tree2.setItemDelegateForColumn(0, delegate2)

    # Sample items with thumbnails and status using feedback colors
    items_data = [
        (
            "Asset 001",
            "Character",
            QColor(feedback["success"]["foreground"]),
            "Ready",
            QColor(feedback["success"]["background"]),
        ),
        (
            "Asset 002",
            "Prop",
            QColor(feedback["warning"]["foreground"]),
            "Review",
            QColor(feedback["warning"]["background"]),
        ),
        (
            "Asset 003",
            "Environment",
            QColor(feedback["error"]["foreground"]),
            "WIP",
            QColor(feedback["error"]["background"]),
        ),
    ]

    for name, asset_type, dot_color, label_text, label_color in items_data:
        item = QTreeWidgetItem(tree2, [name, asset_type])
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
        item.setData(
            0,
            FXThumbnailDelegate.DESCRIPTION_ROLE,
            f"A **{asset_type.lower()}** asset",
        )
        item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, dot_color)
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, label_text)
        item.setData(
            0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, label_color
        )

    tree2.setColumnWidth(0, 300)
    layout.addWidget(tree2)

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
        lambda checked: setattr(delegate2, "show_status_dot", checked)
        or tree2.viewport().update()
    )
    controls_layout.addWidget(show_dot_cb)

    show_label_cb = QCheckBox("Show Status Label")
    show_label_cb.setChecked(True)
    show_label_cb.toggled.connect(
        lambda checked: setattr(delegate2, "show_status_label", checked)
        or tree2.viewport().update()
    )
    controls_layout.addWidget(show_label_cb)

    controls_layout.addStretch()
    layout.addWidget(controls)

    layout.addStretch()
    window.resize(500, 500)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
