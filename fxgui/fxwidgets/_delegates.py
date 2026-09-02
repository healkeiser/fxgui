"""Custom item delegates for tree/list views."""

# Built-in
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

# Third-party
from qtpy.QtCore import (
    QMargins,
    QModelIndex,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
)
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from qtpy.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle


class FXItemDelegate(QStyledItemDelegate):
    """Minimal delegate that enables QIcon mode switching on hover/selection.

    Qt's default item view painting only uses QIcon.Selected for selected items.
    This delegate adds QIcon.Active support for hover states, making icons
    change color when items are hovered.

    This is a drop-in replacement for QStyledItemDelegate with no layout changes.
    Apply it to any QListView, QTreeView, or QTableView for icon color switching.

    Examples:
        >>> from fxgui import fxwidgets
        >>> list_widget = QListWidget()
        >>> list_widget.setItemDelegate(fxwidgets.FXItemDelegate())
    """

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        # Check if we need to handle icon mode switching
        icon = index.data(Qt.DecorationRole)
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hovered = bool(option.state & QStyle.State_MouseOver)

        if (
            icon is not None
            and not icon.isNull()
            and (is_selected or is_hovered)
        ):
            # Initialize option to get proper styling
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)

            # Get the style
            style = opt.widget.style() if opt.widget else QApplication.style()

            # Draw everything normally first (background, text, etc.)
            # but temporarily remove icon to prevent double-drawing
            saved_icon = opt.icon
            opt.icon = QIcon()
            style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)
            opt.icon = saved_icon

            # Get the decoration rect using the style's calculation
            icon_rect = style.subElementRect(
                QStyle.SE_ItemViewItemDecoration, opt, opt.widget
            )

            # Draw icon with appropriate mode
            mode = QIcon.Selected if is_selected else QIcon.Active
            icon.paint(painter, icon_rect, Qt.AlignCenter, mode, QIcon.On)
        else:
            # Default painting for items without icons or in normal state
            super().paint(painter, option, index)


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
    and status indicators. Descriptions may be written in Markdown, which is
    rendered as plain text. Additionally, it supports custom background colors
    via Qt.BackgroundRole with rounded corners and borders for visual
    hierarchy.

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
        - `Qt.UserRole + 9` (`QIcon`): Status label icon (displayed before text).

        This delegate claims `Qt.UserRole + 1` through `Qt.UserRole + 12`.
        A view that stamps roles of its own on the same items must derive
        them from `FIRST_FREE_ROLE` rather than guess a margin past that
        range.

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
        Column 0 is laid out from both edges. The thumbnail (or the decoration
        icon) sits at the left, the title and description follow it, and the
        status label pill and the status dot are anchored to the row's right
        edge, the pill left of the dot. The text stops short of both of them
        and of the child count badge in the bottom-right corner, so it never
        runs underneath any of the three.

    Note:
        Because the indicators are right-anchored, they walk left as the
        column narrows, and past a point they would reach the thumbnail.
        `apply_minimum_thumbnail_width(view)` stops the column there: it
        keeps column 0 at or above the thumbnail's full span plus whatever
        indicator space the rows actually show. `sizeHint` reports the same
        floor, so a view that sizes to contents already has the room.

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
    STATUS_LABEL_ICON_ROLE = Qt.UserRole + 9  # QIcon for status label
    CHILD_COUNT_VISIBLE_ROLE = Qt.UserRole + 10  # bool
    STARRED_ROLE = Qt.UserRole + 11  # bool
    STARRED_COLOR_ROLE = Qt.UserRole + 12  # QColor (default: gold)

    # The first item-data role this delegate does NOT claim. Derive your
    # own roles from it rather than guessing a margin past the roles
    # above: two studio repositories have now each picked a safe-looking
    # offset by hand, and one of them picked +10 first and collided with
    # `CHILD_COUNT_VISIBLE_ROLE`, which showed up as a child count
    # appearing on rows that had no children.
    #
    #   MY_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE
    #   MY_OTHER_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE + 1
    #
    # Roles added to this delegate go BELOW this line and move it up, so
    # a consumer that derived from it is moved along with it.
    FIRST_FREE_ROLE = Qt.UserRole + 13

    # Layout geometry, shared by the paint and sizeHint paths so that the
    # space reserved for an element and the space it paints in cannot drift
    _THUMBNAIL_WIDTH = 68  # 16:9 against _THUMBNAIL_HEIGHT
    _THUMBNAIL_HEIGHT = 38
    _THUMBNAIL_MARGIN = 5  # Margin around the bordered thumbnail
    _THUMBNAIL_BORDER = 2  # The bordered container adds 1px on each side
    _THUMBNAIL_SPAN = (
        _THUMBNAIL_WIDTH + _THUMBNAIL_BORDER + _THUMBNAIL_MARGIN * 2
    )
    _CONTENT_SPACING = 5  # Gap between the thumbnail and what follows it
    _ICON_SIZE = 16
    _ICON_MARGIN = 6
    _TEXT_RIGHT_MARGIN = 10

    # The status label pill and the status dot share one band at the row's
    # top, anchored to its right edge: the dot sits _INDICATOR_RIGHT_MARGIN in
    # from the edge and the pill sits _INDICATOR_SPACING left of the dot. A
    # row showing only the pill puts it at the margin instead, since there is
    # no dot to leave room for. The pill fills the band's height and the dot
    # is centered in it, so the two line up
    _INDICATOR_BAND_TOP = 4
    _INDICATOR_BAND_HEIGHT = 14
    _INDICATOR_RIGHT_MARGIN = 4
    _INDICATOR_SPACING = 6
    _DOT_SIZE = 8
    _LABEL_PADDING = 4
    _LABEL_ICON_SIZE = 12
    _LABEL_ICON_SPACING = 2

    # Child count badge, painted at the row's bottom-right corner
    _CHILD_COUNT_HEIGHT = 14
    _CHILD_COUNT_MARGIN = 4
    _CHILD_COUNT_MIN_WIDTH = 18

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
        self._show_child_count = True
        self._show_starred = True

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

    @property
    def show_child_count(self) -> bool:
        """Whether child count badges are shown."""
        return self._show_child_count

    @show_child_count.setter
    def show_child_count(self, value: bool) -> None:
        """Set whether child count badges are shown."""
        self._show_child_count = value

    @property
    def show_starred(self) -> bool:
        """Whether starred indicators are shown."""
        return self._show_starred

    @show_starred.setter
    def show_starred(self, value: bool) -> None:
        """Set whether starred indicators are shown."""
        self._show_starred = value

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

    @classmethod
    def apply_minimum_thumbnail_width(
        cls, view: QWidget, column: int = 0
    ) -> None:
        """Keep one column from shrinking below what its content needs.

        The status label pill and the status dot are anchored to the row's
        right edge, so they walk left as the column narrows and would end up
        on the thumbnail. This installs a floor on the given column: the
        thumbnail's full span plus the space the rows' indicators occupy plus
        the gap between the two. Dragging the section narrower than that snaps
        it back to the floor.

        A view opts in: the delegate cannot install this itself, since it is
        handed a rect and never sees the header. `sizeHint` already reports
        the same floor, which covers `resizeColumnToContents` and
        `ResizeToContents`, but a size hint does not stop a person dragging a
        section by hand. `QHeaderView.setMinimumSectionSize` cannot serve
        either: it applies to every section, so the wide floor column 0 needs
        would also be forced on the narrow columns beside it.

        The floor is measured from the model each time a resize would breach
        it, walking the rows that are laid out (expanded branches only), so it
        follows the widest pill the view currently shows.

        Args:
            view: The tree view whose header should be constrained.
            column: The column to constrain. Defaults to 0.

        Examples:
            >>> from fxgui import fxwidgets
            >>> from qtpy.QtWidgets import QTreeWidget
            >>> tree = QTreeWidget()
            >>> tree.setItemDelegate(fxwidgets.FXThumbnailDelegate())
            >>> fxwidgets.FXThumbnailDelegate.apply_minimum_thumbnail_width(
            ...     tree
            ... )
        """

        header = view.header() if hasattr(view, "header") else None
        if header is None:
            return

        # A resize of our own re-enters sectionResized, so the enforcement
        # has to be able to tell its own resize from the user's
        guard = {"busy": False}

        def _enforce(index: int, _old_size: int, new_size: int) -> None:
            if index != column or guard["busy"]:
                return
            floor = cls._measure_minimum_width(view, column)
            if new_size >= floor:
                return
            guard["busy"] = True
            try:
                header.resizeSection(column, floor)
            finally:
                guard["busy"] = False

        # The connection is the only reference to the closure, and the binding
        # a signal keeps is not something to rely on across Qt bindings. The
        # handlers are kept per column so a second call replaces its own
        # rather than stacking a duplicate on the signal
        installed = getattr(view, "_fxgui_minimum_section_guards", None)
        if installed is None:
            installed = {}
            view._fxgui_minimum_section_guards = installed
        previous = installed.get(column)
        if previous is not None:
            header.sectionResized.disconnect(previous)

        header.sectionResized.connect(_enforce)
        installed[column] = _enforce

        floor = cls._measure_minimum_width(view, column)
        if floor and header.sectionSize(column) < floor:
            header.resizeSection(column, floor)

    @classmethod
    def _measure_minimum_width(cls, view: QWidget, column: int) -> int:
        """Return the widest content floor among the view's laid-out rows.

        Every row has its own floor, since a row showing both indicators
        needs more room than one showing neither. The column has to satisfy
        all of them, so the widest wins.

        Args:
            view: The view holding the model and the delegate.
            column: The column to measure.

        Returns:
            The floor in pixels, or 0 when the view has no model or does not
            use this delegate for that column.
        """

        model = view.model()
        if model is None:
            return 0

        delegate = None
        if hasattr(view, "itemDelegateForColumn"):
            delegate = view.itemDelegateForColumn(column)
        if not isinstance(delegate, FXThumbnailDelegate) and hasattr(
            view, "itemDelegate"
        ):
            delegate = view.itemDelegate()
        if not isinstance(delegate, FXThumbnailDelegate):
            return 0

        # A null rect starts at x 0, so the row floors come out as offsets
        option = QStyleOptionViewItem()
        can_expand = hasattr(view, "isExpanded")

        floor = 0
        parents = [QModelIndex()]
        while parents:
            parent = parents.pop()
            for row in range(model.rowCount(parent)):
                index = model.index(row, column, parent)
                floor = max(
                    floor,
                    delegate._row_minimum_width(
                        option, index, delegate._has_thumbnail(index)
                    ),
                )
                if (
                    model.hasChildren(index)
                    and can_expand
                    and view.isExpanded(index)
                ):
                    parents.append(index)

        return floor

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

    @staticmethod
    def _as_color(value) -> QColor:
        """Coerce a color role value to a QColor.

        The color roles are documented as QColor, but strings are the obvious
        thing to store instead, so they are parsed here. Anything else yields
        an invalid QColor, which hides the element rather than raising in the
        middle of a paint or a size hint.

        Args:
            value: Whatever the model returned for a color role.

        Returns:
            The color, or an invalid QColor when there is none to be had.

        Examples:
            >>> FXThumbnailDelegate._as_color("#ff0000").isValid()
            True
            >>> FXThumbnailDelegate._as_color("not a color").isValid()
            False
            >>> FXThumbnailDelegate._as_color(None).isValid()
            False
        """

        if isinstance(value, QColor):
            return value
        if isinstance(value, str):
            return QColor(value)
        return QColor()

    def _title_font(self, option: QStyleOptionViewItem) -> QFont:
        """Return the font the title is painted with.

        Args:
            option: The style options for the item.

        Returns:
            The bold variant of the item's font.
        """

        font = QFont(option.font)
        font.setBold(True)
        return font

    def _description_font(self, option: QStyleOptionViewItem) -> QFont:
        """Return the font the description is painted with.

        Args:
            option: The style options for the item.

        Returns:
            The item's font, one point smaller and never below 8.
        """

        font = QFont(option.font)
        font.setPointSize(max(8, option.font.pointSize() - 1))
        return font

    def _content_text_width(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        title_font: QFont,
    ) -> int:
        """Return the width the title and description want.

        The two stack, so the wider of them is what the row needs. The
        description is measured as plain text, which is what gets painted.

        Args:
            option: The style options for the item.
            index: The model index of the item.
            title_font: The font the caller paints the title with.

        Returns:
            The natural text width, in pixels.
        """

        title = index.data(Qt.DisplayRole) or ""
        width = QFontMetrics(title_font).horizontalAdvance(str(title))

        description = index.data(self.DESCRIPTION_ROLE) or ""
        if description and description != "-":
            description = self.markdown_to_plain_text(description)
            width = max(
                width,
                QFontMetrics(
                    self._description_font(option)
                ).horizontalAdvance(description),
            )

        return width

    def _content_right_limit(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        right_margin: int,
    ) -> int:
        """Return the x the text must stop at.

        The right edge of the row belongs to the status indicators, the child
        count badge and the margin, so the text stops before all three. The
        indicators sit at the top of the row and the badge at the bottom, so
        subtracting both is more room than either line strictly needs, but it
        keeps one text width for the title and the description that stacks
        under it.

        Measured from the rect's exclusive right edge, not `QRect.right()`,
        which is one pixel inside it. Mixing the two is what made `sizeHint`
        reserve a pixel less than the paint path needed.

        Args:
            option: The style options for the item.
            index: The model index of the item.
            right_margin: The margin to keep past the text.

        Returns:
            The x coordinate the text ends at.
        """

        return (
            option.rect.left()
            + option.rect.width()
            - right_margin
            - self._child_count_width(index)
            - self._indicator_metrics(index)[2]
        )

    def _status_label_width(
        self, label_text: str, label_icon: Optional[QIcon] = None
    ) -> int:
        """Return the width of the status label pill.

        The pill grows with its text, plus horizontal padding and, when an
        icon is set, the icon and the gap that follows it.

        Args:
            label_text: The text displayed in the pill.
            label_icon: Optional icon displayed before the text.

        Returns:
            The pill width, in pixels.
        """

        label_font = QFont()
        label_font.setPointSize(7)
        label_font.setBold(True)
        label_metrics = QFontMetrics(label_font)

        icon_size = (
            self._LABEL_ICON_SIZE
            if label_icon and not label_icon.isNull()
            else 0
        )
        icon_spacing = self._LABEL_ICON_SPACING if icon_size > 0 else 0

        return (
            label_metrics.horizontalAdvance(label_text)
            + self._LABEL_PADDING * 2
            + icon_size
            + icon_spacing
        )

    def _indicator_metrics(self, index: QModelIndex) -> Tuple[int, int, int]:
        """Measure the indicator region for an item.

        An indicator is measured only if it is actually painted, so the
        reserved space always matches what is drawn: the delegate's global
        `show_*` property must be True and the per-item role must not be
        False, and the item must carry a usable color (and text, for the
        pill). A color role holding something unusable hides its indicator
        instead of raising, see `_as_color`.

        Args:
            index: The model index of the item.

        Returns:
            Tuple of (label_width, dot_width, footprint), in pixels. A width
            of 0 means the element is not shown. `footprint` is how far in
            from the row's right edge the leftmost indicator reaches, and is 0
            when neither indicator is shown.
        """

        label_color = self._as_color(index.data(self.STATUS_LABEL_COLOR_ROLE))
        label_text = index.data(self.STATUS_LABEL_TEXT_ROLE)
        label_icon = index.data(self.STATUS_LABEL_ICON_ROLE)
        dot_color = self._as_color(index.data(self.STATUS_DOT_COLOR_ROLE))

        item_show_label = index.data(self.STATUS_LABEL_VISIBLE_ROLE)
        item_show_dot = index.data(self.STATUS_DOT_VISIBLE_ROLE)

        show_label = bool(
            self._show_status_label
            and item_show_label is not False
            and label_text
            and label_color.isValid()
        )
        label_width = (
            self._status_label_width(label_text, label_icon)
            if show_label
            else 0
        )

        show_dot = bool(
            self._show_status_dot
            and item_show_dot is not False
            and dot_color.isValid()
        )
        dot_width = self._DOT_SIZE if show_dot else 0

        # Measured from the same insets the paint path places the indicators
        # at, so what is reserved is exactly what is drawn. `+ 1` turns an
        # inset (a distance in from the inclusive right edge) into a width
        label_inset, dot_inset = self._indicator_insets(label_width, dot_width)
        footprint = 0
        if label_width:
            footprint = label_inset + 1
        elif dot_width:
            footprint = dot_inset + 1

        return label_width, dot_width, footprint

    def _indicator_insets(
        self, label_width: int, dot_width: int
    ) -> Tuple[int, int]:
        """Return how far in from the row's right edge each indicator starts.

        The one place the indicator band's arithmetic lives: the paint path
        turns these into x coordinates and `_indicator_metrics` turns the
        leftmost of them into the width it reserves, so the two can never
        disagree about where an indicator is.

        The dot sits `_INDICATOR_RIGHT_MARGIN` in from the edge. The pill
        sits `_INDICATOR_SPACING` left of the dot when there is a dot, and
        takes the dot's own place at the margin when there is not: a row
        showing only a pill has no dot to leave room for, and leaving it
        anyway is a gap of empty pixels between the pill and the edge.

        Args:
            label_width: The pill width, or 0 when it is not shown.
            dot_width: The dot width, or 0 when it is not shown.

        Returns:
            Tuple of (label_inset, dot_inset), in pixels. Either is
            meaningless when the matching width is 0.
        """

        dot_inset = self._INDICATOR_RIGHT_MARGIN + self._DOT_SIZE
        if dot_width:
            label_inset = dot_inset + self._INDICATOR_SPACING + label_width
        else:
            label_inset = self._INDICATOR_RIGHT_MARGIN + label_width
        return label_inset, dot_inset

    def _indicator_left(
        self, item_rect: QRect, label_width: int, dot_width: int
    ) -> Tuple[int, int]:
        """Return the left edges of the pill and the dot.

        Both are anchored to the row's right edge, at the insets
        `_indicator_insets` gives them.

        Args:
            item_rect: The rectangle of the entire item.
            label_width: The pill width, or 0 when it is not shown.
            dot_width: The dot width, or 0 when it is not shown.

        Returns:
            Tuple of (label_x, dot_x). Either is meaningless when the matching
            width is 0.
        """

        label_inset, dot_inset = self._indicator_insets(label_width, dot_width)
        return (
            item_rect.right() - label_inset,
            item_rect.right() - dot_inset,
        )

    def _content_left(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        has_thumbnail: bool,
    ) -> int:
        """Return the first x that is clear of the thumbnail or the icon.

        This is the boundary the right-anchored indicators must not cross: the
        thumbnail's span including its margins, or the decoration icon and the
        gap after it on thumbnail-less rows.

        Args:
            option: The style options for the item.
            index: The model index of the item.
            has_thumbnail: Whether the row paints a thumbnail.

        Returns:
            The x coordinate the content area starts at.
        """

        if has_thumbnail:
            return option.rect.left() + self._THUMBNAIL_SPAN

        left = option.rect.left() + self._ICON_MARGIN
        icon = index.data(Qt.DecorationRole)
        if icon is not None and not icon.isNull():
            left += self._ICON_SIZE + self._ICON_MARGIN
        return left

    def _text_left(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        has_thumbnail: bool,
    ) -> int:
        """Return the x the title and description start at.

        Args:
            option: The style options for the item.
            index: The model index of the item.
            has_thumbnail: Whether the row paints a thumbnail.

        Returns:
            The x coordinate the text starts at.
        """

        left = self._content_left(option, index, has_thumbnail)
        return left + self._CONTENT_SPACING if has_thumbnail else left

    def _row_minimum_width(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        has_thumbnail: bool,
    ) -> int:
        """Return the narrowest column 0 this row can be laid out in.

        Below this the right-anchored indicators reach the thumbnail. It is
        the thumbnail's full span (or the icon's), the gap after it, and the
        space the row's own indicators take, so a row showing neither asks
        only for its thumbnail.

        Args:
            option: The style options for the item.
            index: The model index of the item.
            has_thumbnail: Whether the row paints a thumbnail.

        Returns:
            The floor width, in pixels.
        """

        content_left = (
            self._content_left(option, index, has_thumbnail)
            - option.rect.left()
        )
        footprint = self._indicator_metrics(index)[2]
        if not footprint:
            return content_left
        return content_left + self._CONTENT_SPACING + footprint

    def _child_count_badge_width(self, count: int) -> int:
        """Return the width of the child count badge.

        Args:
            count: The number of children.

        Returns:
            The badge width, in pixels.
        """

        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        text_width = QFontMetrics(font).horizontalAdvance(str(count))
        return max(
            text_width + self._LABEL_PADDING * 2, self._CHILD_COUNT_MIN_WIDTH
        )

    def _child_count_width(self, index: QModelIndex) -> int:
        """Return the horizontal space the child count badge occupies.

        The badge is painted at the row's bottom-right corner, so the text
        keeps this much room free on its right to avoid running under it.

        Args:
            index: The model index of the item.

        Returns:
            The badge width plus its margins, or 0 when no badge is painted.
        """

        if not self._show_child_count:
            return 0
        if index.data(self.CHILD_COUNT_VISIBLE_ROLE) is False:
            return 0

        model = index.model()
        if model is None:
            return 0
        count = model.rowCount(index)
        if count <= 0:
            return 0

        return (
            self._child_count_badge_width(count) + self._CHILD_COUNT_MARGIN * 2
        )

    def _draw_status_dot(
        self,
        painter: QPainter,
        item_rect: QRect,
        dot_x: int,
        left_limit: int,
        status_color: QColor,
    ) -> None:
        """Draw a status indicator dot at the given left edge.

        The dot is centered vertically in the indicator band, so it lines up
        with the middle of the status label pill. The band is fixed geometry,
        so a dot sits at the same height whether or not its row shows a pill.

        Args:
            painter: The painter to use for drawing.
            item_rect: The rectangle of the entire item.
            dot_x: The left edge of the dot.
            left_limit: The x the dot may not start before. On a column too
                narrow for it the dot is skipped rather than drawn over the
                thumbnail.
            status_color: The color of the status dot, as a QColor or a string.
        """

        status_color = self._as_color(status_color)
        if not status_color.isValid():
            return

        if dot_x < left_limit:
            return

        dot_y = (
            item_rect.top()
            + self._INDICATOR_BAND_TOP
            + (self._INDICATOR_BAND_HEIGHT - self._DOT_SIZE) // 2
        )
        dot_rect = QRect(dot_x, dot_y, self._DOT_SIZE, self._DOT_SIZE)

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
        label_x: int,
        label_width: int,
        left_limit: int,
        label_color: QColor,
        label_text: str,
        label_icon: QIcon = None,
    ) -> None:
        """Draw the status label pill at the given left edge.

        The pill fills the indicator band: it starts at `label_x`, spans
        `label_width` as measured by `_status_label_width` and is offset from
        the row's top by `_INDICATOR_BAND_TOP`.

        Args:
            painter: The painter to use for drawing.
            item_rect: The rectangle of the entire item.
            label_x: The left edge of the pill.
            label_width: The pill width, in pixels.
            left_limit: The x the pill may not start before. On a column too
                narrow for it the pill is skipped rather than drawn over the
                thumbnail.
            label_color: The background color of the status label, as a
                QColor or a string.
            label_text: The text to display in the status label.
            label_icon: Optional icon to display before the text.
        """

        label_color = self._as_color(label_color)
        if not label_color.isValid() or not label_text:
            return

        if label_x < left_limit:
            return

        label_y = item_rect.top() + self._INDICATOR_BAND_TOP
        label_rect = QRect(
            label_x, label_y, label_width, self._INDICATOR_BAND_HEIGHT
        )

        # Set up font for label text
        label_font = QFont()
        label_font.setPointSize(7)
        label_font.setBold(True)
        label_metrics = QFontMetrics(label_font)

        # Draw the label background with rounded corners
        painter.setRenderHint(QPainter.Antialiasing)
        # Add a subtle border for visibility on selection
        border_color = label_color.darker(130)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(label_color))
        painter.drawRoundedRect(label_rect, 2, 2)

        # Calculate appropriate text color based on background luminance
        text_color = Qt.white if label_color.lightness() < 128 else Qt.black

        # Draw the icon if provided (keep original colors for brand/DCC icons)
        content_x = label_x + self._LABEL_PADDING
        icon_size = (
            self._LABEL_ICON_SIZE
            if label_icon and not label_icon.isNull()
            else 0
        )
        if icon_size > 0:
            icon_y = label_y + (self._INDICATOR_BAND_HEIGHT - icon_size) // 2
            icon_rect = QRect(content_x, icon_y, icon_size, icon_size)
            label_icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )
            content_x += icon_size + self._LABEL_ICON_SPACING

        # Draw the label text
        painter.setPen(text_color)
        painter.setFont(label_font)

        # Position text after icon (if any)
        text_rect = QRect(
            content_x,
            label_y,
            label_metrics.horizontalAdvance(label_text),
            self._INDICATOR_BAND_HEIGHT,
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

    @staticmethod
    def _is_focus_row(
        option: QStyleOptionViewItem, index: QModelIndex
    ) -> bool:
        """Whether this cell belongs to the row the keyboard is on.

        `State_HasFocus` is only set on the view's current cell, never on the
        rest of that row, so a ring drawn from it alone would stop at the
        first column boundary. The row is read from the view instead, which
        also gives the answer for the columns that carry no focus state of
        their own.

        Args:
            option: Style options for the cell being painted.
            index: The model index of the cell being painted.

        Returns:
            True when the view holds keyboard focus and the cell sits in its
            current row.
        """

        view = option.widget
        if view is None or not hasattr(view, "currentIndex"):
            return bool(option.state & QStyle.State_HasFocus)

        if not view.hasFocus():
            return False

        current = view.currentIndex()
        # Row numbers repeat under different parents, so the parent has to
        # match as well
        return (
            current.isValid()
            and current.row() == index.row()
            and current.parent() == index.parent()
        )

    def _create_focus_path(
        self,
        rect_f: QRectF,
        radius: float,
        is_first_column: bool,
        is_last_column: bool,
    ) -> QPainterPath:
        """Create the stroke path for a row's focus ring.

        The ring belongs to the row, but a delegate is handed one cell at a
        time, so each cell contributes its own segment: the top and bottom
        edges always, and the outer vertical edge only where the row actually
        ends. Stroking a closed rectangle per cell would instead draw a line
        down every column boundary.

        Args:
            rect_f: The cell rectangle to stroke, already inset for the pen.
            radius: The corner radius, matching the selection fill.
            is_first_column: Whether this cell is in the first column.
            is_last_column: Whether this cell is in the last column.

        Returns:
            A path covering this cell's share of the row's outline.
        """

        if is_first_column and is_last_column:
            path = QPainterPath()
            path.addRoundedRect(rect_f, radius, radius)
            return path

        if is_first_column or is_last_column:
            # The closed per-column paths already round the outer corners in
            # the right places; the segment to drop is the one they close
            # with, which is the inner vertical edge
            path = self._create_rounded_path(
                rect_f, radius, is_first_column, is_last_column
            )
            elements = [path.elementAt(i) for i in range(path.elementCount())]
            open_path = QPainterPath()
            for element in elements[:-1]:
                if element.isMoveTo():
                    open_path.moveTo(element.x, element.y)
                elif element.isLineTo():
                    open_path.lineTo(element.x, element.y)
                else:
                    open_path.lineTo(element.x, element.y)
            return open_path

        # Middle column: the two horizontal edges and nothing else
        path = QPainterPath()
        path.moveTo(rect_f.topLeft())
        path.lineTo(rect_f.topRight())
        path.moveTo(rect_f.bottomLeft())
        path.lineTo(rect_f.bottomRight())
        return path

    def _draw_focus_indicator(
        self,
        painter: QPainter,
        rect: QRect,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        column_position: Optional[Tuple[bool, bool]] = None,
    ) -> None:
        """Outline the row the keyboard is on.

        The stylesheet cannot reach this: a `::item:focus` rule matches
        nothing, and `apply_transparent_selection` hands the row's whole
        appearance to the delegate anyway. Without this the current row is
        invisible, so keyboard navigation has nothing to follow.

        The ring is stroked inside the cell rect, so it costs no space and the
        row keeps the height `sizeHint` reported. On a selected row the fill
        is already `accent_primary`, so the ring switches to the token that
        exists to be read against it.

        Args:
            painter: The painter to use.
            rect: The rectangle to outline.
            option: Style options containing state.
            index: Model index, for the row check and corner rounding.
            column_position: Optional pre-computed (is_first, is_last) tuple.
        """

        if not self._is_focus_row(option, index):
            return

        if option.state & QStyle.State_Selected:
            ring_color = QColor(self.theme.text_on_accent_primary)
        else:
            ring_color = QColor(self.theme.accent_primary)

        if column_position is None:
            is_first_column, is_last_column = self._get_column_position(
                option, index
            )
        else:
            is_first_column, is_last_column = column_position

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # A 1px pen straddles the coordinate it is given, so the rect is
        # pulled in by half a pixel to land the stroke inside the row
        inset = QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
        path = self._create_focus_path(
            inset, 4, is_first_column, is_last_column
        )

        pen = QPen(ring_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.restore()

    def _draw_status_indicators(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        has_thumbnail: bool,
    ) -> None:
        """Draw the status label pill and the status dot side by side.

        Both are anchored to the row's right edge, the pill left of the dot.
        As the column narrows they walk left towards the thumbnail, and
        `apply_minimum_thumbnail_width` is what stops the column before they
        reach it. On a column narrower than that floor an indicator is skipped
        rather than painted over the image.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
            has_thumbnail: Whether the row paints a thumbnail.
        """

        label_width, dot_width, _ = self._indicator_metrics(index)
        label_x, dot_x = self._indicator_left(
            option.rect, label_width, dot_width
        )
        left_limit = self._content_left(option, index, has_thumbnail)

        if label_width:
            self._draw_status_label(
                painter,
                option.rect,
                label_x,
                label_width,
                left_limit,
                index.data(self.STATUS_LABEL_COLOR_ROLE),
                index.data(self.STATUS_LABEL_TEXT_ROLE),
                index.data(self.STATUS_LABEL_ICON_ROLE),
            )

        if dot_width:
            self._draw_status_dot(
                painter,
                option.rect,
                dot_x,
                left_limit,
                index.data(self.STATUS_DOT_COLOR_ROLE),
            )

    def _draw_starred_indicator(
        self,
        painter: QPainter,
        item_rect: QRect,
        color: QColor,
        has_thumbnail: bool = False,
    ) -> None:
        """Draw a star indicator.

        For thumbnail items: bottom-left of the thumbnail, mirroring
        the decoration icon overlay on the bottom-right.
        For non-thumbnail items: small star to the right of the icon.

        Args:
            painter: The painter to use for drawing.
            item_rect: The rectangle of the entire item.
            color: The color of the star.
            has_thumbnail: Whether the item shows a thumbnail.
        """
        from qtpy.QtGui import QPolygonF
        from qtpy.QtCore import QPointF
        import math

        painter.setRenderHint(QPainter.Antialiasing)

        if has_thumbnail:
            # Match decoration icon overlay dimensions exactly
            overlay_size = 15
            overlay_margin = 6

            # Thumbnail position (same constants as _draw_thumbnail_content)
            bordered_height = self._THUMBNAIL_HEIGHT + self._THUMBNAIL_BORDER
            thumbnail_x = item_rect.left() + self._THUMBNAIL_MARGIN
            thumbnail_y = (
                item_rect.top() + (item_rect.height() - bordered_height) // 2
            )

            # Bottom-left of thumbnail area
            overlay_x = thumbnail_x + overlay_margin
            overlay_y = (
                thumbnail_y + bordered_height - overlay_size - overlay_margin
            )
        else:
            # Tiny star on bottom-right corner of the icon
            overlay_size = 7
            icon_size = self._ICON_SIZE
            icon_y = item_rect.top() + (item_rect.height() - icon_size) // 2
            overlay_x = (
                item_rect.left()
                + self._ICON_MARGIN
                + icon_size
                - overlay_size
                + 1
            )
            overlay_y = icon_y + icon_size - overlay_size + 1

        cx = overlay_x + overlay_size / 2
        cy = overlay_y + overlay_size / 2

        # Background circle
        bg_color = QColor(self.theme.surface)
        bg_color.setAlpha(220)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(QColor(self.theme.border_light), 1))
        circle_r = overlay_size / 2 + 2
        painter.drawEllipse(QPointF(cx, cy), circle_r, circle_r)

        # Draw 5-point star
        outer_r = overlay_size / 2 - 1
        inner_r = outer_r * 0.4
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = outer_r if i % 2 == 0 else inner_r
            points.append(
                QPointF(
                    cx + r * math.cos(angle), cy + r * math.sin(angle)
                )
            )

        polygon = QPolygonF(points)
        painter.setPen(QPen(color.darker(130), 0.5))
        painter.setBrush(QBrush(color))
        painter.drawPolygon(polygon)

    def _draw_child_count(
        self,
        painter: QPainter,
        item_rect: QRect,
        count: int,
    ) -> None:
        """Draw a child count badge at the bottom-right corner.

        Args:
            painter: The painter to use for drawing.
            item_rect: The rectangle of the entire item.
            count: The number of children.
        """
        text = str(count)
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)

        badge_width = self._child_count_badge_width(count)
        badge_height = self._CHILD_COUNT_HEIGHT
        margin = self._CHILD_COUNT_MARGIN

        badge_x = item_rect.right() - badge_width - margin
        badge_y = item_rect.bottom() - badge_height - margin

        painter.setRenderHint(QPainter.Antialiasing)

        # Badge background — muted theme color
        bg_color = QColor(self.theme.surface)
        bg_color.setAlpha(200)
        badge_rect = QRectF(badge_x, badge_y, badge_width, badge_height)
        painter.setPen(QPen(QColor(self.theme.border_light), 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(badge_rect, 3, 3)

        # Badge text
        painter.setPen(QColor(self.theme.text_muted))
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignCenter, text)

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

        # Fixed thumbnail container size - 16:9 aspect ratio to match missing_image.png
        # Row height is 50px, with 5px margin top/bottom = 40px for bordered thumbnail
        # Bordered thumbnail adds 2px, so inner thumbnail is 38px height
        thumbnail_height = self._THUMBNAIL_HEIGHT
        thumbnail_width = self._THUMBNAIL_WIDTH
        x_offset = self._THUMBNAIL_MARGIN  # Consistent margin on all sides

        # Scale image to fit within container while keeping aspect ratio
        if not thumbnail.isNull():
            thumbnail = thumbnail.scaled(
                thumbnail_width,
                thumbnail_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

        # Create fixed-size bordered thumbnail container with background
        bordered_thumbnail = QPixmap(
            thumbnail_width + self._THUMBNAIL_BORDER,
            thumbnail_height + self._THUMBNAIL_BORDER,
        )
        bordered_thumbnail.fill(Qt.transparent)

        painter_with_border = QPainter(bordered_thumbnail)
        painter_with_border.setRenderHint(QPainter.Antialiasing)

        # Fill background with surface_sunken for visual separation
        bg_color = QColor(self.theme.surface_sunken)
        painter_with_border.setBrush(QBrush(bg_color))
        painter_with_border.setPen(Qt.NoPen)
        painter_with_border.drawRoundedRect(
            bordered_thumbnail.rect().marginsRemoved(QMargins(1, 1, 1, 1)), 2, 2
        )

        # Center the scaled image within the fixed-size container
        img_x = 1 + (thumbnail_width - thumbnail.width()) // 2
        img_y = 1 + (thumbnail_height - thumbnail.height()) // 2
        painter_with_border.drawPixmap(img_x, img_y, thumbnail)

        # Draw border around the full container
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

        # Draw decoration icon overlay on bottom-right corner of thumbnail
        decoration_icon = index.data(Qt.DecorationRole)
        if decoration_icon is not None and not decoration_icon.isNull():
            overlay_size = 15
            overlay_margin = 6
            overlay_x = (
                thumbnail_x
                + bordered_thumbnail.width()
                - overlay_size
                - overlay_margin
            )
            overlay_y = (
                thumbnail_y
                + bordered_thumbnail.height()
                - overlay_size
                - overlay_margin
            )

            # Draw a background circle for the icon
            painter.setRenderHint(QPainter.Antialiasing)
            bg_color = QColor(self.theme.surface)
            bg_color.setAlpha(220)
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(QColor(self.theme.border_light), 1))
            painter.drawEllipse(
                overlay_x - 2, overlay_y - 2, overlay_size + 4, overlay_size + 4
            )

            # Draw the icon
            icon_rect = QRect(overlay_x, overlay_y, overlay_size, overlay_size)
            decoration_icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )

        # Draw title and description, after the thumbnail and its gutter
        text_x = self._text_left(option, index, True)
        text_y = option.rect.top() + 8

        # Keep the text clear of the indicators and the child count badge
        text_width = max(
            0,
            self._content_right_limit(option, index, self._TEXT_RIGHT_MARGIN)
            - text_x,
        )

        title = index.data(Qt.DisplayRole) or ""
        description = index.data(self.DESCRIPTION_ROLE) or ""

        if description and description != "-":
            description = self.markdown_to_plain_text(description)

        # Set up fonts
        title_font = self._title_font(option)
        description_font = self._description_font(option)

        title_metrics = QFontMetrics(title_font)
        description_metrics = QFontMetrics(description_font)
        title_height = title_metrics.height()

        # Set text color
        if option.state & QStyle.State_Selected:
            text_color = option.palette.highlightedText().color()
        else:
            text_color = option.palette.text().color()

        painter.setPen(text_color)

        # Draw title, clipped to its rect rather than elided: a narrowing
        # column reveals less of it instead of collapsing to an ellipsis
        painter.setFont(title_font)
        title_rect = QRect(text_x, text_y, text_width, title_height)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignTop, str(title))

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
            painter.drawText(
                description_rect, Qt.AlignLeft | Qt.AlignTop, str(description)
            )

    def _check_rect(self, option: QStyleOptionViewItem) -> Optional[QRect]:
        """Where a tickable row's check box goes; None for a row without one.

        Asked of the style, with the very question `QStyledItemDelegate`'s
        own `editorEvent` asks before it decides whether a click landed on
        the box. That is what makes the box this delegate paints the box a
        click toggles: this delegate does not override `editorEvent`, so
        the base class handles the click, and the two agree on the rect
        because they read it from the same place.

        Args:
            option: The style option, already run through
                `initStyleOption` so `features` and `rect` are filled in.

        Returns:
            The check indicator's rect, or None when the item carries no
            `Qt.CheckStateRole`.
        """

        if not (option.features & QStyleOptionViewItem.HasCheckIndicator):
            return None
        widget = option.widget
        style = widget.style() if widget is not None else QApplication.style()
        return style.subElementRect(
            QStyle.SE_ItemViewItemCheckIndicator, option, widget
        )

    def _check_width(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> int:
        """How much of column 0 a tickable row's check box takes, or 0.

        For `sizeHint`, which is handed the view's raw option rather than
        an initialised one, so the features are filled in here first.
        """

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        rect = self._check_rect(opt)
        return 0 if rect is None else rect.width() + 1

    def _draw_check_indicator(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        rect: QRect,
    ) -> None:
        """Paint a tickable row's check box in the delegate's own palette.

        Drawn here rather than through the style's own
        `PE_IndicatorItemViewItemCheck`, which was the first version of
        this and looked wrong for two reasons. It fills a solid box in
        the palette's Base colour, so on a row this delegate has already
        painted a selection over, the box reads as a dark bar cut into
        the highlight. And on Windows the native check glyph is drawn in
        the OS accent colour, so a tick came out in whatever the artist
        set their system accent to -- orange on a machine that had never
        chosen it in this application -- rather than in the theme's own.
        A flat box in the delegate's tokens answers both: it sits on the
        selection instead of cutting a hole in it, and its colour is the
        theme's rather than the desktop's.

        The whole appearance is the delegate's, which is the same bargain
        the rest of column 0 already strikes: a themed
        `QTreeView::indicator` stylesheet rule no longer reaches it, and
        in exchange the box matches the card, the border and the
        selection this delegate draws around it.

        Args:
            painter: The painter to use.
            option: The style option, already initialised for the item.
            rect: Where the box goes, from `_check_rect`.
        """

        checked = option.checkState == Qt.Checked
        partial = option.checkState == Qt.PartiallyChecked
        selected = bool(option.state & QStyle.State_Selected)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        box = QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 3.0
        if checked or partial:
            fill = (
                QColor(self.theme.text_on_accent_primary)
                if selected
                else QColor(self.theme.accent_primary)
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(fill))
            painter.drawRoundedRect(box, radius, radius)
            mark = (
                QColor(self.theme.accent_primary)
                if selected
                else QColor(self.theme.text_on_accent_primary)
            )
            pen = QPen(mark)
            pen.setWidthF(1.6)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            if partial:
                mid_y = box.center().y()
                painter.drawLine(
                    QPointF(box.left() + box.width() * 0.28, mid_y),
                    QPointF(box.right() - box.width() * 0.28, mid_y),
                )
            else:
                # A tick as three points, in fractions of the box so it
                # scales with whatever size the style hands back.
                painter.drawPolyline(
                    [
                        QPointF(
                            box.left() + box.width() * 0.26,
                            box.top() + box.height() * 0.52,
                        ),
                        QPointF(
                            box.left() + box.width() * 0.44,
                            box.top() + box.height() * 0.70,
                        ),
                        QPointF(
                            box.left() + box.width() * 0.76,
                            box.top() + box.height() * 0.32,
                        ),
                    ]
                )
        else:
            edge = (
                QColor(self.theme.text_on_accent_primary)
                if selected
                else QColor(self.theme.border_light)
            )
            painter.setPen(QPen(edge, 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(box, radius, radius)
        painter.restore()

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

        icon_size = self._ICON_SIZE
        icon_margin = self._ICON_MARGIN

        # Determine text color based on selection state
        if option.state & QStyle.State_Selected:
            text_color = option.palette.highlightedText().color()
        else:
            text_color = option.palette.text().color()

        if icon is not None and not icon.isNull():
            icon_x = option.rect.left() + icon_margin
            icon_y = option.rect.top() + (option.rect.height() - icon_size) // 2
            icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)

            # Use QIcon's built-in modes for automatic color switching
            # Icons created with get_icon() have Selected/Active pixmaps
            if option.state & QStyle.State_Selected:
                icon.paint(
                    painter, icon_rect, Qt.AlignCenter, QIcon.Selected, QIcon.On
                )
            elif option.state & QStyle.State_MouseOver:
                icon.paint(
                    painter, icon_rect, Qt.AlignCenter, QIcon.Active, QIcon.On
                )
            else:
                icon.paint(painter, icon_rect)

        title = index.data(Qt.DisplayRole) or ""

        # The text follows the icon
        text_x = self._text_left(option, index, False)

        # Keep the text clear of the indicators and the child count badge
        content_width = max(
            0, self._content_right_limit(option, index, icon_margin) - text_x
        )

        if description and description != "-":
            # Two-line layout
            title_font = self._title_font(option)
            title_metrics = QFontMetrics(title_font)
            title_height = title_metrics.height()

            description_font = self._description_font(option)
            description_metrics = QFontMetrics(description_font)

            # Draw title
            title_rect = QRect(
                text_x, option.rect.top() + 4, content_width, title_height
            )
            painter.setPen(text_color)
            painter.setFont(title_font)
            painter.drawText(
                title_rect, Qt.AlignLeft | Qt.AlignVCenter, str(title)
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
            painter.drawText(
                description_rect, Qt.AlignLeft | Qt.AlignTop, description_plain
            )
        else:
            # Single-line layout
            painter.setPen(text_color)
            painter.setFont(option.font)
            text_rect = QRect(
                text_x,
                option.rect.top(),
                content_width,
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
        """Draw icon and text for non-column-0 items.

        Args:
            painter: The painter to use for drawing.
            option: The style options for the item.
            index: The model index of the item.
        """

        icon = index.data(Qt.DecorationRole)
        text = index.data(Qt.DisplayRole)

        icon_size = 16
        icon_margin = 6
        text_x = option.rect.left() + icon_margin

        # Draw icon if present
        if icon is not None and not icon.isNull():
            icon_x = option.rect.left() + icon_margin
            icon_y = option.rect.top() + (option.rect.height() - icon_size) // 2
            icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)

            # Use QIcon's built-in modes for automatic color switching
            # Icons created with get_icon() have Selected/Active pixmaps
            if option.state & QStyle.State_Selected:
                icon.paint(
                    painter, icon_rect, Qt.AlignCenter, QIcon.Selected, QIcon.On
                )
            elif option.state & QStyle.State_MouseOver:
                icon.paint(
                    painter, icon_rect, Qt.AlignCenter, QIcon.Active, QIcon.On
                )
            else:
                icon.paint(painter, icon_rect)
            text_x = icon_x + icon_size + icon_margin

        # Draw text
        if text:
            if option.state & QStyle.State_Selected:
                text_color = option.palette.highlightedText().color()
            else:
                text_color = option.palette.text().color()
            painter.setPen(text_color)
            painter.setFont(option.font)
            text_rect = QRect(
                text_x,
                option.rect.top(),
                option.rect.right() - text_x - icon_margin,
                option.rect.height(),
            )
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

        # Only column 0 lays out a thumbnail, indicators and a description
        if not is_col0:
            return QSize(original_size.width(), fixed_height)

        show_thumbnail = self._show_thumbnail and (
            item_show_thumbnail is None or item_show_thumbnail
        )

        # Everything left of the text, from the same helper the paint path
        # uses: the thumbnail and its gutter, or the decoration icon
        text_offset = (
            self._text_left(option, index, show_thumbnail)
            - option.rect.left()
        )

        # What the right-anchored indicators take out of the row (0 when the
        # item shows neither)
        _, _, footprint = self._indicator_metrics(index)

        # The text itself, measured with the fonts it is painted with. A
        # thumbnail row always bolds its title; a thumbnail-less row only
        # does when it splits into two lines for a description
        if show_thumbnail or has_description:
            title_font = self._title_font(option)
        else:
            title_font = QFont(option.font)
        text_width = self._content_text_width(option, index, title_font)

        # The margin the paint path keeps past the text, and the badge it
        # keeps clear of
        right_margin = (
            self._TEXT_RIGHT_MARGIN if show_thumbnail else self._ICON_MARGIN
        )
        child_count_width = self._child_count_width(index)

        starred_width = 0
        if self._show_starred and index.data(self.STARRED_ROLE):
            starred_width = 22  # star + circle + margin

        total_width = (
            self._check_width(option, index)
            + text_offset
            + text_width
            + right_margin
            + child_count_width
            + footprint
            + starred_width
        )

        # Never report a width the row cannot be laid out in, so anything
        # sizing to contents lands at or above the floor
        floor = self._row_minimum_width(option, index, show_thumbnail)

        return QSize(
            max(original_size.width(), total_width, floor), fixed_height
        )

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
            # A tickable row's box first, and the rest of the row laid
            # out to the right of it. Everything below reads its left
            # edge off `opt.rect`, so narrowing the rect is what moves
            # the icon, the thumbnail and the text over.
            check_rect = self._check_rect(opt)
            if check_rect is not None:
                self._draw_check_indicator(painter, opt, check_rect)
                opt.rect.setLeft(check_rect.right() + 1)
            if has_thumbnail:
                self._draw_thumbnail_content(painter, opt, index)
            else:
                self._draw_icon_and_text(painter, opt, index)
            # Draw status indicators for column 0, anchored to its right edge
            self._draw_status_indicators(painter, opt, index, has_thumbnail)

            # Draw starred indicator
            if self._show_starred:
                is_starred = index.data(self.STARRED_ROLE)
                if is_starred:
                    star_color = self._as_color(
                        index.data(self.STARRED_COLOR_ROLE)
                    )
                    if not star_color.isValid():
                        star_color = QColor("#FFD700")  # Gold
                    self._draw_starred_indicator(
                        painter, opt.rect, star_color, has_thumbnail
                    )

            # Draw child count badge
            if self._show_child_count:
                item_show_count = index.data(self.CHILD_COUNT_VISIBLE_ROLE)
                if item_show_count is not False:
                    child_count = index.model().rowCount(index)
                    if child_count > 0:
                        self._draw_child_count(
                            painter, opt.rect, child_count
                        )
        else:
            self._draw_text(painter, opt, index)

        painter.restore()

        # The focus ring goes on last so no content can paint over it
        painter.save()
        painter.setClipRect(opt.rect)
        self._draw_focus_indicator(painter, rect, opt, index, column_position)
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

    ###### FXColorLabelDelegate
    layout.addWidget(QLabel("FXColorLabelDelegate:"))
    tree1 = QTreeWidget()
    tree1.setHeaderLabels(["Status"])
    tree1.setRootIsDecorated(False)

    # Define colors and icons for different statuses using feedback colors
    # Store icon names for theme-aware updates instead of static icons
    status_icon_names = {
        "success": "check_circle",
        "warning": "warning",
        "error": "error",
        "info": "info",
    }

    def get_colors_icons():
        """Build colors_icons dict with current theme colors."""
        feedback = fxstyle.get_feedback_colors()
        return {
            status: (
                QColor(feedback[status]["background"]),
                QColor(feedback[status]["foreground"]),
                QColor(feedback[status]["foreground"]),
                fxicons.get_icon(icon_name),
                True,
            )
            for status, icon_name in status_icon_names.items()
        }

    colors_icons = get_colors_icons()
    delegate1 = FXColorLabelDelegate(colors_icons)
    tree1.setItemDelegate(delegate1)

    # Update colors_icons when theme changes for theme-aware icons
    def update_color_label_delegate(_theme_name: str = None):
        delegate1.colors_icons = get_colors_icons()
        tree1.viewport().update()

    fxstyle.theme_manager.theme_changed.connect(update_color_label_delegate)

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
    # Format: (name, asset_type, label_text, feedback_key, status_icon_name, overlay_icon_name)
    items_data = [
        (
            "Asset 001",
            "Character",
            "Ready",
            "success",
            "check_circle",
            "person",
        ),
        ("Asset 002", "Prop", "Review", "warning", "rate_review", "category"),
        (
            "Asset 003",
            "Environment",
            "WIP",
            "error",
            "construction",
            "landscape",
        ),
    ]

    # Custom roles for theme-aware icon updates, derived from the
    # delegate's own ceiling rather than guessed past it.
    FEEDBACK_KEY_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE
    STATUS_LABEL_ICON_NAME_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE + 1
    OVERLAY_ICON_NAME_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE + 2

    for (
        name,
        asset_type,
        label_text,
        feedback_key,
        status_icon,
        overlay_icon,
    ) in items_data:
        item = QTreeWidgetItem(tree2, [name, asset_type, label_text])
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, thumbnail_path)
        item.setData(
            0,
            FXThumbnailDelegate.DESCRIPTION_ROLE,
            f"A **{asset_type.lower()}** asset",
        )
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, label_text)
        # Set status label icon and store icon name for theme-aware updates
        item.setData(
            0,
            FXThumbnailDelegate.STATUS_LABEL_ICON_ROLE,
            fxicons.get_icon(status_icon),
        )
        item.setData(0, STATUS_LABEL_ICON_NAME_ROLE, status_icon)
        # Set overlay icon on thumbnail (via setIcon) and store name for theme updates
        item.setIcon(0, fxicons.get_icon(overlay_icon))
        item.setData(0, OVERLAY_ICON_NAME_ROLE, overlay_icon)
        # Store the feedback key for dynamic color updates
        item.setData(0, FEEDBACK_KEY_ROLE, feedback_key)

    tree2.setColumnWidth(0, 300)
    # Column 0 cannot be dragged narrower than its thumbnail and indicators
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree2)
    layout.addWidget(tree2)

    ###### FXThumbnailDelegate - With Custom Backgrounds

    layout.addWidget(QLabel("FXThumbnailDelegate (custom backgrounds):"))
    tree3 = QTreeWidget()
    tree3.setHeaderLabels(["Name", "Type", "Status"])
    tree3.setRootIsDecorated(False)

    delegate3 = FXThumbnailDelegate()
    delegate3.show_thumbnail = True
    delegate3.show_status_dot = True
    delegate3.show_status_label = True
    tree3.setItemDelegate(delegate3)
    # Apply transparent selection style for custom backgrounds
    FXThumbnailDelegate.apply_transparent_selection(tree3)

    # Items with custom backgrounds - we'll set backgrounds via helper function
    # Format: (name, item_type, status, feedback_key, dcc_status_icon, dcc_overlay_icon)
    # Using DCC library icons for both status labels and thumbnail overlays
    items_with_bg = [
        (
            "Project Alpha",
            "Feature",
            "In Progress",
            "info",
            "houdini",
            "houdini",
        ),
        ("Bug Fix #123", "Bug", "Testing", "warning", "maya", "maya"),
        ("Documentation", "Task", "Done", "success", "nuke", "nuke"),
        (
            "API Refactor",
            "Enhancement",
            "Review",
            "error",
            "blender",
            "blender",
        ),
    ]

    # Custom roles for theme-aware icon updates
    DCC_ICON_NAME_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE + 3
    DCC_OVERLAY_ICON_NAME_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE + 4

    for (
        name,
        item_type,
        status,
        feedback_key,
        dcc_status_icon,
        dcc_overlay_icon,
    ) in items_with_bg:
        item = QTreeWidgetItem(tree3, [name, item_type, status])
        # Enable thumbnail and set path
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, True)
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, thumbnail_path)
        # Set description
        item.setData(
            0,
            FXThumbnailDelegate.DESCRIPTION_ROLE,
            f"A {item_type.lower()} item",
        )
        item.setData(0, FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, status)
        # Set DCC icon for status label and store icon name for theme-aware updates
        item.setData(
            0,
            FXThumbnailDelegate.STATUS_LABEL_ICON_ROLE,
            fxicons.get_icon(dcc_status_icon, library="dcc"),
        )
        item.setData(0, DCC_ICON_NAME_ROLE, dcc_status_icon)
        # Set DCC overlay icon on thumbnail and store name for theme updates
        item.setIcon(0, fxicons.get_icon(dcc_overlay_icon, library="dcc"))
        item.setData(0, DCC_OVERLAY_ICON_NAME_ROLE, dcc_overlay_icon)
        # Store the feedback key for dynamic color updates
        item.setData(0, FEEDBACK_KEY_ROLE, feedback_key)

    tree3.setColumnWidth(0, 250)
    tree3.setColumnWidth(1, 100)
    # Column 0 cannot be dragged narrower than its thumbnail and indicators
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree3)
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
            feedback_key = item.data(0, FEEDBACK_KEY_ROLE)
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
            # Update status label icon with current theme color
            status_icon_name = item.data(0, STATUS_LABEL_ICON_NAME_ROLE)
            if status_icon_name:
                item.setData(
                    0,
                    FXThumbnailDelegate.STATUS_LABEL_ICON_ROLE,
                    fxicons.get_icon(status_icon_name),
                )
            # Update overlay icon with current theme color
            overlay_icon_name = item.data(0, OVERLAY_ICON_NAME_ROLE)
            if overlay_icon_name:
                item.setIcon(0, fxicons.get_icon(overlay_icon_name))
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
            feedback_key = item.data(0, FEEDBACK_KEY_ROLE)
            if feedback_key and feedback_key in feedback:
                # Set status colors from feedback
                status_color = QColor(feedback[feedback_key]["foreground"])
                item.setData(
                    0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, status_color
                )
                item.setData(
                    0, FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE, status_color
                )
            # Update DCC status label icon (theme-aware icons from dcc library)
            dcc_icon_name = item.data(0, DCC_ICON_NAME_ROLE)
            if dcc_icon_name:
                item.setData(
                    0,
                    FXThumbnailDelegate.STATUS_LABEL_ICON_ROLE,
                    fxicons.get_icon(dcc_icon_name, library="dcc"),
                )
            # Update DCC overlay icon (theme-aware icons from dcc library)
            dcc_overlay_icon_name = item.data(0, DCC_OVERLAY_ICON_NAME_ROLE)
            if dcc_overlay_icon_name:
                item.setIcon(
                    0, fxicons.get_icon(dcc_overlay_icon_name, library="dcc")
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
