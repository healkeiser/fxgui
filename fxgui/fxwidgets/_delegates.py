"""Item delegates for tree and list views."""

# Built-in
import functools
import os
import time
from typing import Dict, NamedTuple, Optional, Tuple

# Third-party
from qtpy.QtCore import (
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from qtpy.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QPixmapCache,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
    QWidget,
)

# Internal
from fxgui import _compat, fxconstants, fxicons, fxstyle, fxutils
from fxgui.fxwidgets import _roles

_FALLBACK_THUMBNAIL = fxconstants.IMAGES_ROOT / "missing_image.png"

# A thumbnail's mtime is trusted this long before the share is asked again.
_STAT_SECONDS = 2.0
# ponytail: one entry per path ever shown, never pruned; bound it if a view
# ever walks millions of files.
_stamps: Dict[str, Tuple[float, Optional[float]]] = {}

_OWNS_ROW = "fxOwnsRow"

# The delegate paints the row's fill, selection and hover itself.
fxstyle.register_widget_style(
    f"""
    QAbstractItemView[{_OWNS_ROW}="true"] {{
        selection-background-color: transparent;
    }}
    QAbstractItemView[{_OWNS_ROW}="true"]::item,
    QAbstractItemView[{_OWNS_ROW}="true"]::item:hover,
    QAbstractItemView[{_OWNS_ROW}="true"]::item:selected,
    QTreeView[{_OWNS_ROW}="true"]::branch,
    QTreeView[{_OWNS_ROW}="true"]::branch:hover,
    QTreeView[{_OWNS_ROW}="true"]::branch:selected {{
        background: transparent;
    }}
    """
)


def _hover_on(card: Optional[QColor]) -> str:
    """Return the hover fill that reads on `card`, or on the view for None."""
    hover = fxstyle.colors().state_hover
    if card is None:
        return hover
    return _hover_reading(card.name(), hover, fxstyle.get_theme())


@functools.lru_cache(maxsize=256)
def _hover_reading(ground: str, hover: str, theme: str) -> str:
    """Return `hover`, stepped until it reads on `ground` in `theme`."""
    floor = fxstyle.state_contrast(theme)

    def reads(color: str) -> bool:
        return fxstyle.get_contrast_ratio(color, ground) >= floor

    if reads(hover):
        return hover
    pole = max(("#000000", "#ffffff"),
               key=lambda end: fxstyle.get_contrast_ratio(end, ground))
    return fxstyle.step_toward(ground, pole, reads)


def _mtime(path: str) -> Optional[float]:
    """Return a file's mtime, asking the disk at most once per window."""
    now = time.monotonic()
    seen = _stamps.get(path)
    if seen is not None and now - seen[0] < _STAT_SECONDS:
        return seen[1]
    try:
        stamp = os.path.getmtime(path)
    except (OSError, TypeError):
        stamp = None
    _stamps[path] = (now, stamp)
    return stamp


def _style(widget: Optional[QWidget]) -> QStyle:
    """Return the widget's style, or the application's without one."""
    return widget.style() if widget is not None else QApplication.style()


def _smaller(font: QFont, pixels: int) -> QFont:
    """Return `font` `pixels` px smaller, in its own unit, 8 px at least."""
    font = QFont(font)
    if font.pointSizeF() > 0:
        # 96 dpi: 1 px is 0.75 pt.
        font.setPointSizeF(max(6.0, font.pointSizeF() - 0.75 * pixels))
    else:
        font.setPixelSize(max(8, font.pixelSize() - pixels))
    return font


def _draw_elided(
    painter: QPainter, rect: QRect, alignment, text: str
) -> None:
    """Draw `text` in `rect`, ending in an ellipsis when it does not fit."""
    fitted = painter.fontMetrics().elidedText(
        text, Qt.ElideRight, max(0, rect.width())
    )
    painter.drawText(rect, alignment, fitted)


def _paint_icon(
    painter: QPainter, icon: QIcon, rect: QRect, state
) -> None:
    """Paint an icon in Selected mode on a selected row, else Normal.

    A hovered row keeps its Normal ink: its fill is neutral, not an accent.
    """
    if state & QStyle.State_Selected:
        icon.paint(painter, rect, Qt.AlignCenter, QIcon.Selected, QIcon.On)
    else:
        icon.paint(painter, rect)


def _draw_overlay_disc(
    painter: QPainter, center: QPointF, radius: float
) -> None:
    """Paint the translucent disc an overlay icon sits on."""
    theme = fxstyle.colors()
    fill = QColor(theme.surface)
    fill.setAlpha(220)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(fill))
    painter.setPen(QPen(QColor(theme.border_light), 1))
    painter.drawEllipse(center, radius, radius)


@functools.lru_cache(maxsize=1)
def _fallback_source() -> QPixmap:
    """Return the image shown for a missing thumbnail, loaded once."""
    return QPixmap(str(_FALLBACK_THUMBNAIL))


@functools.lru_cache(maxsize=None)
def _mark(name: str, token: str) -> QIcon:
    """Return a check box mark; its token is read each time it is drawn."""
    return fxicons.get_icon(name, color=token)


class _DelegateOwnsTheRow(fxstyle.FXProxyStyle):
    """fxgui's style, leaving the row panel and focus rect to the delegate.

    Windows 11 paints an accent pill and a focus rectangle there, under the
    delegate's own ring, and no stylesheet rule reaches either.
    """

    _SKIP = frozenset(
        {
            QStyle.PrimitiveElement.PE_FrameFocusRect,
        }
    )

    def drawPrimitive(self, element, option, painter, widget=None):
        """Draw `element` unless the delegate owns it.

        A tree's indentation reaches here as a row panel with no index; the
        row is found by position and its delegate fills it.
        """
        if element == QStyle.PrimitiveElement.PE_PanelItemViewRow:
            _paint_indent(option, painter, widget)
            return
        if element in self._SKIP:
            return
        super().drawPrimitive(element, option, painter, widget)


def _paint_indent(option, painter: QPainter, view: Optional[QWidget]) -> None:
    """Fill a tree row's indentation through its delegate, if it owns one."""
    if not isinstance(view, QTreeView):
        return
    beside = QPoint(option.rect.right() + 1, option.rect.center().y())
    index = view.indexAt(beside)
    if not index.isValid():
        return
    cell = view.visualRect(index)
    # Only the area left of the first cell: the cells paint themselves.
    if cell.left() != beside.x() or option.rect.left() >= cell.left():
        return
    delegate = view.itemDelegateForIndex(index)
    if isinstance(delegate, FXThumbnailDelegate):
        delegate.paint_indent(painter, option, index)


class _ColumnFloor(QObject):
    """Snaps one header section back up to its content's floor.

    `QHeaderView` has no per-section minimum. Parented to the view, so Qt
    owns it; the floor is measured again after the view's model, its rows
    or its expansion change.
    """

    def __init__(self, view: QWidget, column: int, floor: int):
        super().__init__(view)
        self.column = column
        self._minimum = floor
        self._floor: Optional[int] = None
        self._model = None
        self._snapping = False
        view.header().sectionResized.connect(self._enforce)
        for name in ("expanded", "collapsed"):
            if hasattr(view, name):
                getattr(view, name).connect(self._stale)
        floor = self.floor()
        if floor and view.header().sectionSize(column) < floor:
            view.header().resizeSection(column, floor)

    def release(self) -> None:
        """Stop guarding the section."""
        self.parent().header().sectionResized.disconnect(self._enforce)
        self.setParent(None)
        self.deleteLater()

    # Declared slots: as bare methods, PySide raised "Slot not found" on a
    # live floor once another floor had died.
    @Slot()
    def _stale(self) -> None:
        self._floor = None

    def floor(self) -> int:
        """Return the width the section may not go below."""
        model = self.parent().model()
        if model is not self._model:
            # The old model's signals stay connected; a stale mark is free.
            self._model = model
            self._floor = None
            if model is not None:
                for signal in (
                    model.dataChanged,
                    model.rowsInserted,
                    model.rowsRemoved,
                    model.modelReset,
                    model.layoutChanged,
                ):
                    signal.connect(self._stale)
        if self._floor is None:
            self._floor = max(
                self._minimum,
                FXThumbnailDelegate._measure_minimum_width(
                    self.parent(), self.column
                ),
            )
        return self._floor

    @Slot(int, int, int)
    def _enforce(self, index: int, _old_size: int, new_size: int) -> None:
        if index != self.column or self._snapping:
            return
        floor = self.floor()
        if new_size >= floor:
            return
        # Our own resize re-enters sectionResized.
        self._snapping = True
        try:
            self.parent().header().resizeSection(self.column, floor)
        finally:
            self._snapping = False


class _Indicators(NamedTuple):
    """What a row's status pill and dot take, and the colours they wear."""

    label_width: int
    dot_width: int
    footprint: int
    label_color: QColor
    dot_color: QColor
    label_text: str
    label_icon: str = ""


class FXThumbnailDelegate(QStyledItemDelegate):
    """Paint rows as a thumbnail, a title, a description and status marks.

    Column 0 is laid out from both edges: the thumbnail (or the decoration
    icon) at the left, then the title and the description (Markdown,
    shown as plain text), and the status label and dot anchored to the
    right edge with the child count under them. The text stops short of
    all three. A row is flat, edge to edge, its indentation included, with
    a hairline under it; a `Qt.BackgroundRole` fills it as a band.

    Note:
        Item roles:
        - `Qt.BackgroundRole` (`QColor`, `QBrush` or token name): the
          band's fill.
        - `Qt.DecorationRole` (`QIcon`): the icon of a row without a
          thumbnail, or an overlay on the thumbnail.
        - `THUMBNAIL_VISIBLE_ROLE` (`bool`), `THUMBNAIL_PATH_ROLE` (`str`).
        - `DESCRIPTION_ROLE` (`str`, Markdown).
        - `STATUS_DOT_COLOR_ROLE`, `STATUS_LABEL_COLOR_ROLE` (`QColor` or
          token name), `STATUS_LABEL_TEXT_ROLE` (`str`).
        - `STATUS_DOT_VISIBLE_ROLE`, `STATUS_LABEL_VISIBLE_ROLE`,
          `CHILD_COUNT_VISIBLE_ROLE` (`bool`).
        - `PICKER_TEXT_ROLE` (`str`), `PICKER_CHOICES_ROLE`
          (`Sequence[str]`), `PICKER_UNAVAILABLE_ROLE` (`Mapping[str, str]`,
          a listed choice that cannot be picked, to its reason).

        A view that stamps roles of its own on the same items derives them
        from `FIRST_FREE_ROLE`.

    Note:
        An element shows when its delegate flag (`show_thumbnail`,
        `show_status_dot`, `show_status_label`) is True and its per-item
        visible role is not False.

    Note:
        The right-anchored marks walk left as column 0 narrows.
        `apply_minimum_thumbnail_width(view)` stops the column before they
        reach the thumbnail; `sizeHint` reports the same floor.

    Examples:
        >>> tree = QTreeWidget()
        >>> tree.setItemDelegate(fxwidgets.FXThumbnailDelegate())
        >>> item = QTreeWidgetItem(tree, ["My Item"])
        >>> item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, path)
        >>> item.setData(0, FXThumbnailDelegate.DESCRIPTION_ROLE, "**Bold**")
        >>> item.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, "feedback_success_foreground")
        >>> item.setData(0, Qt.BackgroundRole, "surface")
    """

    THUMBNAIL_VISIBLE_ROLE = _roles.THUMBNAIL_VISIBLE
    THUMBNAIL_PATH_ROLE = _roles.THUMBNAIL_PATH
    DESCRIPTION_ROLE = _roles.DESCRIPTION
    STATUS_DOT_COLOR_ROLE = _roles.STATUS_DOT_COLOR
    STATUS_LABEL_COLOR_ROLE = _roles.STATUS_LABEL_COLOR
    STATUS_LABEL_TEXT_ROLE = _roles.STATUS_LABEL_TEXT
    # An icon name drawn in the label's colour in place of its dot.
    STATUS_LABEL_ICON_ROLE = _roles.STATUS_LABEL_ICON
    STATUS_DOT_VISIBLE_ROLE = _roles.STATUS_DOT_VISIBLE
    STATUS_LABEL_VISIBLE_ROLE = _roles.STATUS_LABEL_VISIBLE
    CHILD_COUNT_VISIBLE_ROLE = _roles.CHILD_COUNT_VISIBLE
    PICKER_TEXT_ROLE = _roles.PICKER_TEXT
    PICKER_CHOICES_ROLE = _roles.PICKER_CHOICES
    PICKER_UNAVAILABLE_ROLE = _roles.PICKER_UNAVAILABLE
    #: The first item-data role no fxgui item view claims.
    FIRST_FREE_ROLE = _roles.FIRST_FREE

    #: A viewer chose a value from a row's picker. The delegate writes
    #: nothing: what a choice means belongs to whoever put the choices
    #: there.
    picked = Signal(QModelIndex, str)

    # Shared by the paint and sizeHint paths, so the space reserved for an
    # element and the space it paints in cannot drift. The thumbnail fills
    # the row the row size in force makes, at 16:9.
    _THUMBNAIL_MARGIN = 4
    _THUMBNAIL_BORDER = 2  # 1 px of frame on each side
    _OVERLAY_SIZE = 15
    _OVERLAY_MARGIN = 6
    _CONTENT_SPACING = 5
    _ICON_SIZE = 16
    _ICON_MARGIN = 6
    _TEXT_RIGHT_MARGIN = 10
    # The least room above and below a row's one line of text.
    _ROW_PADDING = 2
    _LINE_GAP = 2
    # A description shows only in a row at least this tall: two lines.
    _DESCRIPTION_FLOOR = 34
    # From this height up, the status band sits at the row's top and the
    # child count at its bottom; below it, both centre.
    _TALL_ROW = 48

    # The label and the dot share one band, anchored to the row's right
    # edge: the dot _INDICATOR_RIGHT_MARGIN in, the label
    # _INDICATOR_SPACING left of it, or at the margin when there is no dot.
    # The band centres in a one-line row and sits at the top of a taller
    # one, clear of the child count at its bottom.
    _INDICATOR_BAND_TOP = 4
    _INDICATOR_BAND_HEIGHT = 14
    _INDICATOR_RIGHT_MARGIN = 6
    _INDICATOR_SPACING = 8
    _DOT_SIZE = 8
    _LABEL_PADDING = 4
    # The status label's coloured mark, and its gap to the words.
    _LABEL_MARK = 8
    _LABEL_ICON = 14
    _LABEL_GAP = 5
    # Under every row, a share of `border`, so the rows read as one table:
    # more under a top-level row, which heads what nests in it.
    _RULE_ALPHA = 0.6
    _NESTED_RULE_ALPHA = 0.25
    # How long a row's hover fades once the pointer leaves it, in seconds.
    _HOVER_FADE = 0.15

    _CHILD_COUNT_HEIGHT = 14
    _CHILD_COUNT_MARGIN = 4
    _CHILD_COUNT_MIN_WIDTH = 18

    # A value and a chevron in one cell, anchored to its right edge.
    _PICKER_HEIGHT = 16
    _PICKER_PADDING = 6
    _PICKER_CHEVRON = 12
    _PICKER_SPACING = 2
    _PICKER_RIGHT_MARGIN = 4

    # Badges and labels, one derived font per base font key
    _badge_fonts: Dict[str, QFont] = {}
    _label_fonts: Dict[str, QFont] = {}

    _FOCUS_RINGS = ("row", "cell")

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        #: Whether rows show their thumbnail.
        self.show_thumbnail = True
        #: Whether rows show their status dot.
        self.show_status_dot = True
        #: Whether rows show their status label pill.
        self.show_status_label = True
        #: Which column paints a picker, or -1 for none. One column for the
        #: whole view: it is the same column on every row.
        self.picker_column = -1
        #: Whether a selected row is filled with the accent. Off, only the
        #: focus ring marks the current cell.
        self.paint_selection = True
        self._focus_ring = "row"
        # A row lights at once under the pointer and fades once it leaves:
        # the row under it, and each row fading, to when it left.
        self._hovered: Optional[QPersistentModelIndex] = None
        self._fading: Dict[QPersistentModelIndex, float] = {}
        self._fading_view: Optional[QWidget] = None
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(16)
        self._fade_timer.timeout.connect(self._fade_step)

    @property
    def focus_ring(self) -> str:
        """Whether the ring outlines the current `"row"` or `"cell"`."""
        return self._focus_ring

    @focus_ring.setter
    def focus_ring(self, mode: str) -> None:
        if mode not in self._FOCUS_RINGS:
            raise ValueError(f"focus_ring is 'row' or 'cell', not {mode!r}")
        self._focus_ring = mode

    @staticmethod
    def apply_transparent_selection(view: QWidget) -> None:
        """Hand a view's row fill, selection and hover to the delegate.

        Marks the view for the registered rule that clears Qt's own
        highlight, and installs a style that skips the native row panel and
        focus rect, which Windows 11 draws under the delegate's ring.

        Args:
            view: A view painted by `FXThumbnailDelegate`.
        """
        if view.findChild(_DelegateOwnsTheRow) is None:
            # No base on purpose: `QProxyStyle(view.style())` takes the shared
            # app style. Parented, since a style freed before its view crashes.
            style = _DelegateOwnsTheRow()
            style.setParent(view)
            view.setStyle(style)
            # The host window's no-focus-rect style it replaces goes too.
            for old in view.findChildren(
                fxstyle.FXProxyStyle, "", Qt.FindDirectChildrenOnly
            ):
                if old is style:
                    continue
                old.setParent(None)
                old.deleteLater()
        view.setProperty(_OWNS_ROW, True)
        fxutils.repolish(view)

    @classmethod
    def apply_minimum_thumbnail_width(
        cls, view: QWidget, column: int = 0, floor: int = 0
    ) -> None:
        """Keep one column from being dragged below what its rows need.

        The floor is the thumbnail's span plus the widest status marks the
        laid-out rows show. `setMinimumSectionSize` cannot serve: it applies
        to every section. A second call on the same column replaces the
        first.

        Args:
            view: The tree view whose header is guarded.
            column: The column to guard.
            floor: A width the column never goes below, even when empty.

        Examples:
            >>> tree.setItemDelegate(fxwidgets.FXThumbnailDelegate())
            >>> fxwidgets.FXThumbnailDelegate.apply_minimum_thumbnail_width(
            ...     tree, floor=300
            ... )
        """
        if getattr(view, "header", None) is None:
            return
        for guard in view.findChildren(
            _ColumnFloor, options=Qt.FindDirectChildrenOnly
        ):
            if guard.column == column:
                guard.release()
        # ponytail: a show_* toggle does not mark the floor stale; it catches
        # up at the next model or expansion change.
        _ColumnFloor(view, column, floor)

    @classmethod
    def _measure_minimum_width(cls, view: QWidget, column: int) -> int:
        """Return the widest floor among the view's laid-out rows, or 0."""
        model = view.model()
        if model is None:
            return 0
        delegate = None
        if hasattr(view, "itemDelegateForColumn"):
            delegate = view.itemDelegateForColumn(column)
        if not isinstance(delegate, FXThumbnailDelegate):
            delegate = view.itemDelegate()
        if not isinstance(delegate, FXThumbnailDelegate):
            return 0

        # A null rect starts at x 0, so the row floors come out as offsets
        base = QStyleOptionViewItem()
        base.font = view.font()
        base.widget = view
        can_expand = hasattr(view, "isExpanded")

        floor = 0
        parents = [QModelIndex()]
        while parents:
            parent = parents.pop()
            for row in range(model.rowCount(parent)):
                index = model.index(row, column, parent)
                option = delegate._init(base, index)
                floor = max(
                    floor,
                    delegate._row_minimum_width(
                        option, index, delegate._has_thumbnail(index)
                    ),
                )
                if (
                    can_expand
                    and model.hasChildren(index)
                    and view.isExpanded(index)
                ):
                    parents.append(index)
        return floor

    @property
    def _THUMBNAIL_HEIGHT(self) -> int:
        """The picture's height: the row's, less its margins and frame."""
        return (
            fxstyle.row_height()
            - self._THUMBNAIL_MARGIN * 2
            - self._THUMBNAIL_BORDER
        )

    @property
    def _THUMBNAIL_WIDTH(self) -> int:
        """The picture's width, 16:9 against its height."""
        return round(self._THUMBNAIL_HEIGHT * 16 / 9)

    @property
    def _THUMBNAIL_SPAN(self) -> int:
        """The room a thumbnail takes across the row, margins included."""
        return (
            self._THUMBNAIL_WIDTH
            + self._THUMBNAIL_BORDER
            + self._THUMBNAIL_MARGIN * 2
        )

    @property
    def _THUMBNAIL_ROW_HEIGHT(self) -> int:
        """The height of a row with a thumbnail: the row size's."""
        return fxstyle.row_height()

    def _init(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QStyleOptionViewItem:
        """Return a copy of `option` filled in for `index`, its font included."""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        return opt

    @staticmethod
    def _text_color(option: QStyleOptionViewItem) -> QColor:
        """Return the text colour for the row's selection; hover keeps it."""
        if option.state & QStyle.State_Selected:
            return option.palette.highlightedText().color()
        return option.palette.text().color()

    @staticmethod
    def _title_font(option: QStyleOptionViewItem) -> QFont:
        """Return the item's font at weight 600."""
        font = QFont(option.font)
        font.setWeight(QFont.DemiBold)
        return font

    @staticmethod
    def _description_font(option: QStyleOptionViewItem) -> QFont:
        """Return the item's font 1 px smaller, the metadata rank."""
        return _smaller(option.font, 1)

    def _description(self, index: QModelIndex) -> str:
        """Return the row's description as plain text, or "".

        "" as well in a row too short for a second line.
        """
        text = index.data(self.DESCRIPTION_ROLE)
        if not text or text == "-":
            return ""
        if fxstyle.row_height() < self._DESCRIPTION_FLOOR:
            return ""
        return fxutils.markdown_to_plain_text(str(text))

    def _content_text_width(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        title_font: QFont,
    ) -> int:
        """Return the width the stacked title and description want."""
        title = index.data(Qt.DisplayRole) or ""
        width = QFontMetrics(title_font).horizontalAdvance(str(title))
        description = self._description(index)
        if description:
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
        """Return the x the text stops at, clear of the marks and the badge.

        Measured from the rect's exclusive right edge, not `QRect.right()`,
        which is one pixel inside it.
        """
        return (
            option.rect.left()
            + option.rect.width()
            - right_margin
            - self._child_count_width(index, option)
            - self._indicator_metrics(index, option, fit=True).footprint
        )

    def _text_rects(
        self,
        option: QStyleOptionViewItem,
        left: int,
        right: int,
        title_font: QFont,
        has_description: bool,
    ) -> Tuple[QRect, Optional[QRect]]:
        """Return the title's rect and the description's, centred as a block."""
        width = max(0, right - left)
        rect = option.rect
        if not has_description:
            return QRect(left, rect.top(), width, rect.height()), None
        title_height = QFontMetrics(title_font).height()
        description_height = QFontMetrics(
            self._description_font(option)
        ).height()
        block = title_height + self._LINE_GAP + description_height
        top = rect.top() + (rect.height() - block) // 2
        return (
            QRect(left, top, width, title_height),
            QRect(
                left,
                top + title_height + self._LINE_GAP,
                width,
                description_height,
            ),
        )

    def _row_height(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> int:
        """Return the row's height: the row size's, or its text's if taller."""
        has_thumbnail = self._has_thumbnail(index)
        has_description = bool(self._description(index.siblingAtColumn(0)))
        title_font = (
            self._title_font(option)
            if has_thumbnail or has_description
            else option.font
        )
        text = QFontMetrics(title_font).height()
        if has_description:
            text += (
                self._LINE_GAP
                + QFontMetrics(self._description_font(option)).height()
            )
        # Padding only past the row size: two lines that fit keep every row
        # of a size one height.
        size = fxstyle.row_height()
        return size if text <= size else text + self._ROW_PADDING * 2

    @classmethod
    def _badge_font(cls, option: QStyleOptionViewItem) -> QFont:
        """Return the item's font 2 px smaller at 600, cached per font."""
        base = option.font
        key = base.key()
        font = cls._badge_fonts.get(key)
        if font is None:
            font = _smaller(base, 2)
            font.setWeight(QFont.DemiBold)
            cls._badge_fonts[key] = font
        return font

    @classmethod
    def _label_font(cls, option: QStyleOptionViewItem) -> QFont:
        """Return the item's font 1 px smaller at 500, cached per font."""
        base = option.font
        key = base.key()
        font = cls._label_fonts.get(key)
        if font is None:
            font = _smaller(base, 1)
            font.setWeight(QFont.Medium)
            cls._label_fonts[key] = font
        return font

    def _mark_size(self, icon: str) -> int:
        """Return the side of the label's mark: its icon's, or its dot's."""
        return self._LABEL_ICON if icon else self._LABEL_MARK

    def _status_label_width(
        self, label_text: str, option: QStyleOptionViewItem, icon: str = ""
    ) -> int:
        """Return the width of the status mark and its words."""
        return (
            self._mark_size(icon)
            + self._LABEL_GAP
            + QFontMetrics(self._label_font(option)).horizontalAdvance(
                label_text.upper()
            )
        )

    def _indicator_metrics(
        self,
        index: QModelIndex,
        option: QStyleOptionViewItem,
        fit: bool = False,
    ) -> _Indicators:
        """Measure the status marks the row paints, and check their colours.

        A mark is measured only if it is painted: its flag is True, its
        visible role is not False, and it has a usable colour (and text,
        for the pill). `footprint` is how far in from the row's right edge
        the leftmost mark reaches, 0 when neither shows.
        """
        label_color = fxstyle.qcolor(index.data(self.STATUS_LABEL_COLOR_ROLE))
        label_text = index.data(self.STATUS_LABEL_TEXT_ROLE)
        label_icon = str(index.data(self.STATUS_LABEL_ICON_ROLE) or "")
        dot_color = fxstyle.qcolor(index.data(self.STATUS_DOT_COLOR_ROLE))

        show_label = bool(
            self.show_status_label
            and index.data(self.STATUS_LABEL_VISIBLE_ROLE) is not False
            and label_text
            and label_color.isValid()
        )
        label_width = (
            self._status_label_width(str(label_text), option, label_icon)
            if show_label
            else 0
        )
        show_dot = bool(
            self.show_status_dot
            and index.data(self.STATUS_DOT_VISIBLE_ROLE) is not False
            and dot_color.isValid()
        )
        dot_width = self._DOT_SIZE if show_dot else 0
        # Painting only: a measured width must never depend on the width.
        if fit and label_width and self._title_squeezed(
            index, option, label_width, dot_width
        ):
            # The title wins: the label keeps its coloured mark alone.
            label_width, label_text = self._mark_size(label_icon), ""

        # `+ 1` turns an inset from the inclusive right edge into a width
        label_inset, dot_inset = self._indicator_insets(label_width, dot_width)
        footprint = 0
        if label_width:
            footprint = label_inset + 1
        elif dot_width:
            footprint = dot_inset + 1
        return _Indicators(
            label_width,
            dot_width,
            footprint,
            label_color,
            dot_color,
            str(label_text or ""),
            label_icon,
        )

    def _title_squeezed(
        self,
        index: QModelIndex,
        option: QStyleOptionViewItem,
        label_width: int,
        dot_width: int,
    ) -> bool:
        """Whether the title would be cut beside the label's words."""
        has_thumbnail = self._has_thumbnail(index)
        title_font = (
            self._title_font(option)
            if has_thumbnail or self._description(index)
            else option.font
        )
        title = str(index.data(Qt.DisplayRole) or "")
        label_inset, dot_inset = self._indicator_insets(label_width, dot_width)
        right_margin = (
            self._TEXT_RIGHT_MARGIN if has_thumbnail else self._ICON_MARGIN
        )
        room = (
            option.rect.left()
            + option.rect.width()
            - right_margin
            - self._child_count_width(index, option)
            - (label_inset + 1)
            - self._text_left(option, index, has_thumbnail)
        )
        return room < QFontMetrics(title_font).horizontalAdvance(title)

    def _indicator_insets(
        self, label_width: int, dot_width: int
    ) -> Tuple[int, int]:
        """Return how far in from the row's right edge the pill and dot start.

        The one place the band's arithmetic lives, so the paint path and
        the reservation cannot disagree. Either inset is meaningless when
        its width is 0.
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
        """Return the left edges of the pill and the dot."""
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
        """Return the first x clear of the thumbnail, or of the icon."""
        if has_thumbnail:
            return option.rect.left() + self._THUMBNAIL_SPAN
        left = option.rect.left() + self._ICON_MARGIN
        if self._has_icon(option):
            left += self._ICON_SIZE + self._ICON_MARGIN
        return left

    @staticmethod
    def _has_icon(option: QStyleOptionViewItem) -> bool:
        """Whether the filled-in option carries a decoration icon."""
        # `option.icon`: Qt turns a QColor or QPixmap decoration into one.
        return not option.icon.isNull()

    def _text_left(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        has_thumbnail: bool,
    ) -> int:
        """Return the x the title and description start at."""
        left = self._content_left(option, index, has_thumbnail)
        return left + self._CONTENT_SPACING if has_thumbnail else left

    def _row_minimum_width(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        has_thumbnail: bool,
    ) -> int:
        """Return the narrowest column 0 this row can be laid out in.

        The check box, the thumbnail's span (or the icon's), and the room
        the row's own marks take; below it the marks reach the thumbnail.
        """
        content_left = (
            self._check_width(option, index)
            + self._content_left(option, index, has_thumbnail)
            - option.rect.left()
        )
        footprint = self._indicator_metrics(index, option).footprint
        if not footprint:
            return content_left
        return content_left + self._CONTENT_SPACING + footprint

    def _child_count_badge_width(
        self, count: int, option: QStyleOptionViewItem
    ) -> int:
        """Return the width of the child count badge."""
        text_width = QFontMetrics(self._badge_font(option)).horizontalAdvance(
            str(count)
        )
        return max(
            text_width + self._LABEL_PADDING * 2, self._CHILD_COUNT_MIN_WIDTH
        )

    def _child_count_width(
        self, index: QModelIndex, option: QStyleOptionViewItem
    ) -> int:
        """Return the room the child count badge takes, or 0 without one."""
        if index.data(self.CHILD_COUNT_VISIBLE_ROLE) is False:
            return 0
        model = index.model()
        count = model.rowCount(index) if model is not None else 0
        if count <= 0:
            return 0
        return (
            self._child_count_badge_width(count, option)
            + self._CHILD_COUNT_MARGIN * 2
        )

    def _draw_status_dot(
        self,
        painter: QPainter,
        item_rect: QRect,
        dot_x: int,
        left_limit: int,
        color: QColor,
        tall: bool = False,
    ) -> None:
        """Draw the status dot centred in the band, unless past `left_limit`."""
        if dot_x < left_limit:
            return
        dot_y = (
            self._band_top(item_rect, tall)
            + (self._INDICATOR_BAND_HEIGHT - self._DOT_SIZE) // 2
        )
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QRect(dot_x, dot_y, self._DOT_SIZE, self._DOT_SIZE))

    def _band_top(self, item_rect: QRect, tall: bool = False) -> int:
        """Return the top of the status band: centred, or a tall row's top.

        A `tall` row's band sits at its top, clear of the child count.
        """
        if not tall:
            return item_rect.top() + (
                item_rect.height() - self._INDICATOR_BAND_HEIGHT) // 2
        return item_rect.top() + self._INDICATOR_BAND_TOP

    def _is_tall(self, item_rect: QRect, has_thumbnail: bool) -> bool:
        """Whether a row stacks its marks: a thumbnail row of `_TALL_ROW`."""
        return has_thumbnail and item_rect.height() >= self._TALL_ROW

    def _draw_status_label(
        self,
        painter: QPainter,
        item_rect: QRect,
        label_x: int,
        label_width: int,
        left_limit: int,
        color: QColor,
        text: str,
        font: QFont,
        tall: bool = False,
        icon: str = "",
    ) -> None:
        """Draw the status mark and its words, unless past `left_limit`.

        The colour is on the mark only, so a bright status never sets a loud
        block of colour in the row.
        """
        if label_x < left_limit:
            return
        top = self._band_top(item_rect, tall)
        side = self._mark_size(icon)
        mark = QRectF(
            label_x,
            top + (self._INDICATOR_BAND_HEIGHT - side) / 2,
            side,
            side,
        )
        painter.setRenderHint(QPainter.Antialiasing)
        if icon:
            fxicons.get_icon(icon, color=color.name()).paint(
                painter, mark.toRect()
            )
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(mark)
        if not text:
            return
        words = QRect(
            label_x + side + self._LABEL_GAP,
            top,
            label_width - side - self._LABEL_GAP,
            self._INDICATOR_BAND_HEIGHT,
        )
        painter.setPen(QColor(fxstyle.colors().text_muted))
        painter.setFont(font)
        painter.drawText(words, Qt.AlignVCenter | Qt.AlignLeft, text.upper())

    @staticmethod
    def _row_ends(
        option: QStyleOptionViewItem, index: QModelIndex
    ) -> Tuple[bool, bool]:
        """Return whether the cell is drawn first and last in its row.

        Read in visual order from the header, so a dragged header keeps the
        ends on the cells drawn at the edges. `viewItemPosition` cannot
        serve: Qt starts the row at the tree column wherever it sits. A
        view without a header (a list) has cells that are both.
        """
        header = getattr(option.widget, "header", None)
        header = header() if callable(header) else None
        if header is None:
            return True, True
        shown = [
            visual
            for visual in range(header.count())
            if not header.isSectionHidden(header.logicalIndex(visual))
        ]
        if not shown:
            return True, True
        mine = header.visualIndex(index.column())
        return mine == shown[0], mine == shown[-1]

    @staticmethod
    def _row_outline(
        rect_f: QRectF, radius: float, ends: Tuple[bool, bool]
    ) -> QPainterPath:
        """Return the row's rounded outline, run past the cell's inner edges."""
        reach = radius + 2
        first, last = ends
        outline = QRectF(rect_f).adjusted(
            0 if first else -reach, 0, 0 if last else reach, 0
        )
        path = QPainterPath()
        path.addRoundedRect(outline, radius, radius)
        return path

    def _custom_background(self, index: QModelIndex) -> Optional[QColor]:
        """Return the row's band fill from column 0, or None for no band."""
        data = index.siblingAtColumn(0).data(Qt.BackgroundRole)
        if isinstance(data, QBrush):
            color = data.color()
        else:
            # A QColor, or a token name read now so the card follows
            # every theme switch.
            color = fxstyle.qcolor(data)
        return color if color.isValid() and color.alpha() > 0 else None

    def _has_thumbnail(self, index: QModelIndex) -> bool:
        """Whether the row paints a thumbnail."""
        visible = index.siblingAtColumn(0).data(self.THUMBNAIL_VISIBLE_ROLE)
        return visible is not False and self.show_thumbnail

    def _draw_row_fill(
        self,
        painter: QPainter,
        rect: QRect,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        band: Optional[QColor] = None,
        nested: bool = False,
    ) -> None:
        """Fill `rect` edge to edge, then draw the hairline under it.

        The fill is the selection, the hover, the row's own `band`, or the
        view's ground; a row the pointer just left fades to its own. The
        hairline is fainter under a `nested` row. On a `band` too near
        `state_hover`, the hover is the band stepped off it by the theme's
        `fxstyle.state_contrast`.
        """
        hover = self._hover_amount(option, index)
        ground = band if band is not None else option.palette.color(
            QPalette.Base)
        if option.state & QStyle.State_Selected:
            fill = QColor(fxstyle.colors().selection)
        elif hover > 0:
            fill = QColor(fxstyle.mix(ground, _hover_on(band), hover))
        else:
            fill = ground
        painter.fillRect(rect, fill)
        ink = QColor(fxstyle.colors().border)
        ink.setAlphaF(self._NESTED_RULE_ALPHA if nested else self._RULE_ALPHA)
        painter.fillRect(
            QRect(rect.left(), rect.bottom(), rect.width(), 1), ink
        )

    def _hover_amount(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> float:
        """Return how much of the hover fill `index`'s row wears, 0 to 1.

        1 under the pointer; after it leaves, less and less for
        `_HOVER_FADE` seconds, eased out.
        """
        row = QPersistentModelIndex(index.siblingAtColumn(0))
        now = time.monotonic()
        if option.state & QStyle.State_MouseOver or self._pointer_on_row(
            option.widget, index
        ):
            if self._hovered != row:
                self._leave(self._hovered, now, option.widget)
                self._hovered = row
            self._fading.pop(row, None)
            return 1.0
        if row == self._hovered:
            # The pointer left the view from this row.
            self._leave(row, now, option.widget)
            self._hovered = None
        left = self._fading.get(row)
        if left is None or not fxstyle.motion():
            return 0.0
        done = (now - left) / self._HOVER_FADE
        return 0.0 if done >= 1.0 else (1.0 - done) ** 2

    @staticmethod
    def _pointer_on_row(view: Optional[QWidget], index: QModelIndex) -> bool:
        """Whether the pointer is over any cell of `index`'s row.

        Qt marks only the hovered cell where a view selects cells: read
        alone, the row's other cells would leave and re-enter on each paint.
        """
        if not isinstance(view, QAbstractItemView):
            return False
        viewport = view.viewport()
        if not viewport.underMouse():
            return False
        under = view.indexAt(viewport.mapFromGlobal(QCursor.pos()))
        return under.isValid() and (
            under.siblingAtColumn(0) == index.siblingAtColumn(0)
        )

    def _leave(
        self,
        row: Optional[QPersistentModelIndex],
        now: float,
        view: Optional[QWidget],
    ) -> None:
        """Start `row` fading, and the timer that repaints it."""
        if row is None or not row.isValid():
            return
        self._fading[row] = now
        self._fading_view = view
        if not self._fade_timer.isActive():
            self._fade_timer.start()

    @Slot()
    def _fade_step(self) -> None:
        """Drop the rows done fading; repaint the view while any is not."""
        now = time.monotonic()
        self._fading = {
            row: left for row, left in self._fading.items()
            if row.isValid() and now - left < self._HOVER_FADE
        }
        view = self._fading_view
        if view is not None and _compat.is_valid(view):
            target = getattr(view, "viewport", None)
            (target() if callable(target) else view).update()
        if not self._fading:
            self._fade_timer.stop()

    def paint_indent(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Fill the indentation left of `index`'s row, as its cells are.

        The tree's own branch area: the row runs under it to the view's
        edge, and the chevron is drawn over it afterwards.
        """
        self._draw_row_fill(
            painter,
            option.rect,
            option,
            index,
            self._custom_background(index),
            index.parent().isValid(),
        )


    def has_focus_ring(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> bool:
        """Whether the focus ring is drawn on this cell.

        `State_HasFocus` is only set on the view's current cell, so the
        row is read from the view instead.

        Returns:
            True when focus came by keyboard and the cell sits in the
            current row, or is the current cell with `focus_ring` "cell".
        """
        view = option.widget
        if view is None or not hasattr(view, "currentIndex"):
            return bool(option.state & QStyle.State_HasFocus)
        if not fxstyle.focus_visible(view):
            return False
        current = view.currentIndex()
        if self._focus_ring == "cell":
            return current == index
        # Row numbers repeat under different parents
        return (
            current.isValid()
            and current.row() == index.row()
            and current.parent() == index.parent()
        )

    def _draw_focus_indicator(
        self,
        painter: QPainter,
        rect: QRect,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        ends: Tuple[bool, bool],
    ) -> None:
        """Outline the row, or the cell, the keyboard is on.

        A `::item:focus` rule matches nothing, so the delegate draws it,
        inside the cell so the row keeps its height. A selected row gets no
        ring: its accent fill already marks it.
        """
        if not self.has_focus_ring(option, index):
            return
        if option.state & QStyle.State_Selected:
            return
        if self._focus_ring == "cell":
            ends = (True, True)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        # A 1 px pen straddles its coordinate; half a pixel in lands it inside
        inset = QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setClipRect(rect, Qt.IntersectClip)
        painter.setPen(QPen(QColor(fxstyle.colors().accent_primary), 1))
        painter.setBrush(Qt.NoBrush)
        # Square, as the row it rings.
        painter.drawPath(self._row_outline(inset, 0, ends))
        painter.restore()

    def _draw_status_indicators(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        has_thumbnail: bool,
    ) -> None:
        """Draw the label and the dot, skipping one that would reach the image."""
        marks = self._indicator_metrics(index, option, fit=True)
        label_x, dot_x = self._indicator_left(
            option.rect, marks.label_width, marks.dot_width
        )
        left_limit = self._content_left(option, index, has_thumbnail)
        tall = self._is_tall(option.rect, has_thumbnail)
        if marks.label_width:
            self._draw_status_label(
                painter,
                option.rect,
                label_x,
                marks.label_width,
                left_limit,
                marks.label_color,
                marks.label_text,
                self._label_font(option),
                tall,
                marks.label_icon,
            )
        if marks.dot_width:
            self._draw_status_dot(
                painter, option.rect, dot_x, left_limit, marks.dot_color, tall
            )

    def _draw_child_count(
        self,
        painter: QPainter,
        item_rect: QRect,
        count: int,
        option: QStyleOptionViewItem,
        tall: bool = False,
        inset: int = 0,
    ) -> None:
        """Draw the child count at the row's right edge, as muted text.

        At a `tall` row's bottom, under the status band; else centred,
        `inset` further in, left of the status marks it shares the line with.
        """
        width = self._child_count_badge_width(count, option)
        margin = self._CHILD_COUNT_MARGIN
        if not tall:
            top = item_rect.top() + (
                item_rect.height() - self._CHILD_COUNT_HEIGHT) // 2
        else:
            top = item_rect.bottom() - self._CHILD_COUNT_HEIGHT - margin
        rect = QRectF(
            item_rect.right() - width - margin - (0 if tall else inset),
            top,
            width,
            self._CHILD_COUNT_HEIGHT,
        )
        painter.setPen(QColor(fxstyle.colors().text_muted))
        painter.setFont(self._badge_font(option))
        painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, str(count))

    def _bordered_thumbnail(self, path: Optional[str], ratio: float) -> QPixmap:
        """Return the framed thumbnail for a path at a pixel ratio, cached.

        Keyed by path, mtime, ratio, size and the two tokens it is drawn
        in, so an edited file, a row size or a theme switch builds afresh.
        """
        theme = fxstyle.colors()
        stamp = _mtime(path) if path else None
        key = (
            f"fxgui.thumbnail|{path}|{stamp}|{ratio}"
            f"|{self._THUMBNAIL_WIDTH}x{self._THUMBNAIL_HEIGHT}"
            f"|{theme.surface_sunken}|{theme.border_light}"
        )
        cached = _compat.find_pixmap(key)
        if cached is not None:
            return cached

        source = QPixmap(str(path)) if stamp is not None else QPixmap()
        if source.isNull():
            source = _fallback_source()
        width, height = self._THUMBNAIL_WIDTH, self._THUMBNAIL_HEIGHT
        source = source.scaled(
            round(width * ratio),
            round(height * ratio),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        source.setDevicePixelRatio(ratio)
        outer_width = width + self._THUMBNAIL_BORDER
        outer_height = height + self._THUMBNAIL_BORDER

        framed = QPixmap(round(outer_width * ratio), round(outer_height * ratio))
        framed.setDevicePixelRatio(ratio)
        framed.fill(Qt.transparent)
        frame = QRectF(0.5, 0.5, outer_width - 1, outer_height - 1)
        painter = QPainter(framed)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(theme.surface_sunken)))
        radius = fxstyle.SMALL_RADIUS
        painter.drawRoundedRect(frame, radius, radius)
        # The picture takes the frame's corners too.
        corners = QPainterPath()
        corners.addRoundedRect(frame, radius, radius)
        painter.setClipPath(corners)
        painter.drawPixmap(
            QPointF(
                1 + (width - source.width() / ratio) / 2,
                1 + (height - source.height() / ratio) / 2,
            ),
            source,
        )
        painter.setClipping(False)
        painter.setPen(QPen(QColor(theme.border_light), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(frame, radius, radius)
        painter.end()

        QPixmapCache.insert(key, framed)
        return framed

    def _draw_title_and_description(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        left: int,
        right: int,
        bold: bool,
    ) -> None:
        """Draw the title and, under it, the description, between two x's."""
        description = self._description(index)
        title_font = self._title_font(option) if bold else QFont(option.font)
        title_rect, description_rect = self._text_rects(
            option, left, right, title_font, bool(description)
        )
        color = self._text_color(option)
        # A row's name stands out in the strong ink, unless it is
        # selected or wears an ink of its own.
        plain = not option.state & QStyle.State_Selected and (
            index.data(Qt.ForegroundRole) is None)
        painter.setPen(
            QColor(fxstyle.colors().text_strong) if plain else color)
        painter.setFont(title_font)
        _draw_elided(
            painter,
            title_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            str(index.data(Qt.DisplayRole) or ""),
        )
        if description_rect is not None:
            # On a selected row the muted ink would sit on the accent.
            selected = option.state & QStyle.State_Selected
            painter.setPen(
                color if selected else QColor(fxstyle.colors().text_muted)
            )
            painter.setFont(self._description_font(option))
            _draw_elided(
                painter,
                description_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                description,
            )

    def _draw_thumbnail_content(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Draw column 0's thumbnail, its icon overlay, title and description."""
        ratio = painter.device().devicePixelRatioF()
        thumbnail = self._bordered_thumbnail(
            index.data(self.THUMBNAIL_PATH_ROLE), ratio
        )
        outer_width = self._THUMBNAIL_WIDTH + self._THUMBNAIL_BORDER
        outer_height = self._THUMBNAIL_HEIGHT + self._THUMBNAIL_BORDER
        x = option.rect.left() + self._THUMBNAIL_MARGIN
        y = option.rect.top() + (option.rect.height() - outer_height) // 2
        painter.drawPixmap(x, y, thumbnail)

        if self._has_icon(option):
            # Half the picture at most, so a small row's still shows.
            size = min(self._OVERLAY_SIZE, outer_height // 2)
            margin = min(self._OVERLAY_MARGIN, (outer_height - size) // 2)
            icon_rect = QRect(
                x + outer_width - size - margin,
                y + outer_height - size - margin,
                size,
                size,
            )
            _draw_overlay_disc(
                painter, QRectF(icon_rect).center(), size / 2 + 2
            )
            option.icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )

        self._draw_title_and_description(
            painter,
            option,
            index,
            self._text_left(option, index, True),
            self._content_right_limit(option, index, self._TEXT_RIGHT_MARGIN),
            bold=True,
        )

    def _check_rect(self, option: QStyleOptionViewItem) -> Optional[QRect]:
        """Where a tickable row's check box goes; None for a row without one.

        Asked of the style with the question `QStyledItemDelegate`'s own
        `editorEvent` asks before it toggles, so the painted box is the
        clickable one.
        """
        if not (option.features & QStyleOptionViewItem.HasCheckIndicator):
            return None
        return _style(option.widget).subElementRect(
            QStyle.SE_ItemViewItemCheckIndicator, option, option.widget
        )

    def _picker_text_inset(self) -> int:
        """How far a picker value's right edge sits from the cell's right.

        Plain text in the picker column ends here too, so values line up
        down the column whether a row has choices or not.
        """
        return (
            self._PICKER_RIGHT_MARGIN
            + self._PICKER_PADDING
            + self._PICKER_SPACING
            + self._PICKER_CHEVRON
        )

    def _picker_rect(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> Optional[QRect]:
        """Where this row's picker pill sits, or None where it has none."""
        if index.column() != self.picker_column:
            return None
        choices = index.data(self.PICKER_CHOICES_ROLE) or ()
        if len(choices) < 2:
            return None
        text = str(index.data(self.PICKER_TEXT_ROLE) or "")
        width = (
            QFontMetrics(option.font).horizontalAdvance(text)
            + self._PICKER_PADDING * 2
            + self._PICKER_SPACING
            + self._PICKER_CHEVRON
        )
        rect = option.rect
        top = rect.top() + (rect.height() - self._PICKER_HEIGHT) // 2
        left = max(
            rect.left(),
            rect.right() - self._PICKER_RIGHT_MARGIN - width,
        )
        return QRect(left, top, width, self._PICKER_HEIGHT)

    def editorEvent(self, event, model, option, index) -> bool:
        """Open a row's picker on a click inside its pill.

        Everything else goes to the base class, which toggles the painted
        check box.
        """
        if event.type() == QEvent.Type.MouseButtonRelease:
            rect = self._picker_rect(self._init(option, index), index)
            if rect is not None and rect.contains(event.pos()):
                self._open_picker(rect, index, option.widget)
                return True
        return super().editorEvent(event, model, option, index)

    def _open_picker(
        self,
        rect: QRect,
        index: QModelIndex,
        view: Optional[QWidget] = None,
    ) -> None:
        """Pop a menu of this row's choices under its picker pill.

        Args:
            rect: The pill, in the view's viewport coordinates.
            index: The row's model index.
            view: The view painting the row; parents the menu and maps
                `rect` to the screen.
        """
        menu = QMenu(view)
        anchor = rect.bottomLeft()
        if view is not None:
            surface = view.viewport() if hasattr(view, "viewport") else view
            anchor = surface.mapToGlobal(anchor)
        current = str(index.data(self.PICKER_TEXT_ROLE) or "")
        unavailable = index.data(self.PICKER_UNAVAILABLE_ROLE) or {}
        for choice in index.data(self.PICKER_CHOICES_ROLE) or ():
            reason = unavailable.get(str(choice))
            # QMenu right-aligns what follows a tab, in the shortcut column.
            label = f"{choice}\t{reason}" if reason else str(choice)
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(str(choice) == current)
            action.setEnabled(not reason)
        # `exec_` first: tests patch it, since `exec` is unpatchable on PySide
        runner = getattr(menu, "exec_", None) or menu.exec
        # The model may change while the menu runs its own event loop.
        row = QPersistentModelIndex(index)
        chosen = runner(anchor)
        text = chosen.text() if chosen is not None else None
        menu.deleteLater()
        if text is not None and row.isValid():
            self.picked.emit(QModelIndex(row), text)

    def _check_width(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> int:
        """How much of column 0 a tickable row's check box takes, or 0."""
        rect = self._check_rect(option)
        return 0 if rect is None else rect.right() + 1 - option.rect.left()

    def _draw_check_indicator(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        rect: QRect,
    ) -> None:
        """Paint a tickable row's check box in the delegate's own palette.

        Not the style's `PE_IndicatorItemViewItemCheck`: that fills a solid
        Base-coloured box over the selection, and on Windows ticks in the
        OS accent colour. A `QTreeView::indicator` rule does not reach it.
        """
        selected = bool(option.state & QStyle.State_Selected)
        theme = fxstyle.colors()
        box = QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 3.0
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        if option.checkState == Qt.Unchecked:
            edge = theme.text_on_selection if selected else theme.border_light
            painter.setPen(QPen(QColor(edge), 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(box, radius, radius)
        else:
            fill = theme.text_on_selection if selected else theme.accent_primary
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(fill)))
            painter.drawRoundedRect(box, radius, radius)
            name = "remove" if option.checkState == Qt.PartiallyChecked else "check"
            token = "selection" if selected else "text_on_accent_primary"
            _mark(name, token).paint(painter, rect)
        painter.restore()

    def _icon_rect(self, rect: QRect) -> QRect:
        """Return where a decoration icon sits at the left of `rect`."""
        return QRect(
            rect.left() + self._ICON_MARGIN,
            rect.top() + (rect.height() - self._ICON_SIZE) // 2,
            self._ICON_SIZE,
            self._ICON_SIZE,
        )

    def _draw_icon_and_text(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Draw column 0's icon, title and description, without a thumbnail."""
        if self._has_icon(option):
            _paint_icon(
                painter,
                option.icon,
                self._icon_rect(option.rect),
                option.state,
            )
        self._draw_title_and_description(
            painter,
            option,
            index,
            self._text_left(option, index, False),
            self._content_right_limit(option, index, self._ICON_MARGIN),
            bold=bool(self._description(index)),
        )

    def _draw_text(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Draw the icon and text of a column other than 0."""
        text_x = option.rect.left() + self._ICON_MARGIN
        if self._has_icon(option):
            icon_rect = self._icon_rect(option.rect)
            _paint_icon(painter, option.icon, icon_rect, option.state)
            text_x = icon_rect.right() + 1 + self._ICON_MARGIN

        text = index.data(Qt.DisplayRole)
        if not text:
            return
        # Beside a row's name, its other columns are quieter.
        plain = not option.state & QStyle.State_Selected and (
            index.data(Qt.ForegroundRole) is None)
        painter.setPen(
            QColor(fxstyle.colors().text_muted) if plain
            else self._text_color(option))
        painter.setFont(option.font)
        alignment = Qt.AlignLeft | Qt.AlignVCenter
        right_inset = self._ICON_MARGIN
        if index.column() == self.picker_column:
            alignment = Qt.AlignRight | Qt.AlignVCenter
            right_inset = self._picker_text_inset()
        text_rect = QRect(
            text_x,
            option.rect.top(),
            option.rect.right() - text_x - right_inset,
            option.rect.height(),
        )
        _draw_elided(painter, text_rect, alignment, str(text))

    def _draw_picker(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        rect: QRect,
        index: QModelIndex,
    ) -> None:
        """Draw a row's picker pill: a value and a chevron in one control."""
        theme = fxstyle.colors()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(theme.border_light), 1))
        painter.setBrush(QBrush(QColor(theme.surface)))
        painter.drawRoundedRect(
            QRectF(rect), fxstyle.SMALL_RADIUS, fxstyle.SMALL_RADIUS)

        chevron = self._PICKER_CHEVRON
        # From the far edge, not right(): right() is one pixel short of it.
        chevron_left = (
            rect.left() + rect.width() - self._PICKER_PADDING - chevron)
        text_left = rect.left() + self._PICKER_PADDING
        text_rect = QRect(
            text_left,
            rect.top(),
            chevron_left - self._PICKER_SPACING - text_left,
            rect.height(),
        )
        painter.setPen(QColor(theme.text_muted))
        painter.setFont(option.font)
        _draw_elided(
            painter,
            text_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            str(index.data(self.PICKER_TEXT_ROLE) or ""),
        )
        _mark("expand_more", "text_muted").paint(
            painter,
            QRect(
                chevron_left,
                rect.top() + (rect.height() - chevron) // 2,
                chevron,
                chevron,
            ),
        )

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> QSize:
        """Return the row's size, measured with the item's own font."""
        opt = self._init(option, index)
        base = super().sizeHint(option, index)
        height = self._row_height(opt, index)

        # Only column 0 lays out a thumbnail, marks and a description;
        # another column lays out a picker or plain text
        if index.column() != 0:
            picker = self._picker_rect(opt, index)
            width = base.width()
            if picker is not None:
                width = max(width, picker.width() + self._PICKER_RIGHT_MARGIN * 2)
            return QSize(width, height)

        has_thumbnail = self._has_thumbnail(index)
        has_description = bool(self._description(index))
        title_font = (
            self._title_font(opt)
            if has_thumbnail or has_description
            else QFont(opt.font)
        )
        right_margin = (
            self._TEXT_RIGHT_MARGIN if has_thumbnail else self._ICON_MARGIN
        )
        total = (
            self._check_width(opt, index)
            + self._text_left(opt, index, has_thumbnail)
            - opt.rect.left()
            + self._content_text_width(opt, index, title_font)
            + right_margin
            + self._child_count_width(index, opt)
            + self._indicator_metrics(index, opt).footprint
        )
        # Never a width the row cannot be laid out in
        floor = self._row_minimum_width(opt, index, has_thumbnail)
        return QSize(max(base.width(), total, floor), height)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the cell: its fill, rule, content and focus ring."""
        opt = self._init(option, index)
        if not self.paint_selection:
            opt.state &= ~QStyle.State_Selected

        # The check box narrows opt.rect below; the row keeps this one
        row_rect = QRect(opt.rect)

        painter.save()
        painter.setClipRect(row_rect)
        # Also covers any selection Qt drew before calling the delegate.
        self._draw_row_fill(
            painter,
            row_rect,
            opt,
            index,
            self._custom_background(index),
            index.parent().isValid(),
        )
        painter.restore()
        ends = self._row_ends(opt, index)
        rect = row_rect

        painter.save()
        painter.setClipRect(opt.rect)
        if index.column() == 0:
            # Everything below reads its left edge off `opt.rect`, so
            # narrowing it moves the row over to the right of the box.
            check_rect = self._check_rect(opt)
            if check_rect is not None:
                self._draw_check_indicator(painter, opt, check_rect)
                opt.rect.setLeft(check_rect.right() + 1)
            has_thumbnail = self._has_thumbnail(index)
            if has_thumbnail:
                self._draw_thumbnail_content(painter, opt, index)
            else:
                self._draw_icon_and_text(painter, opt, index)
            self._draw_status_indicators(painter, opt, index, has_thumbnail)
            if self._child_count_width(index, opt):
                self._draw_child_count(
                    painter,
                    opt.rect,
                    index.model().rowCount(index),
                    opt,
                    self._is_tall(opt.rect, has_thumbnail),
                    self._indicator_metrics(index, opt, fit=True).footprint,
                )
        else:
            picker = self._picker_rect(opt, index)
            if picker is None:
                self._draw_text(painter, opt, index)
            else:
                self._draw_picker(painter, opt, picker, index)
        painter.restore()

        # The focus ring goes on last so no content can paint over it
        painter.save()
        painter.setClipRect(row_rect)
        self._draw_focus_indicator(painter, rect, opt, index, ends)
        painter.restore()
