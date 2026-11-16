"""A command palette: a search box over a window's commands, or its rows."""

# Built-in
import html
import re
from dataclasses import dataclass
from functools import partial
from typing import Callable, List, Optional, Sequence, Tuple

# Third-party
from qtpy.QtCore import QPoint, QRect, QSize, Qt, Signal
from qtpy.QtGui import (
    QColor,
    QFont,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QPalette,
    QPixmap,
)
from qtpy.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QLineEdit,
    QStyledItemDelegate,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui._compat import is_valid


fxstyle.register_widget_style(
    """
    /* A popup's frame, as a menu's, on the surface: Carmen's palette. */
    FXCommandPalette {
        background-color: @surface;
        border: 1px solid @border;
        border-radius: @card_radius;
    }
    /* Carmen's field: 48 px, no frame of its own, 16 px text, a hairline
       under it. Under keyboard focus the hairline takes the focus ink. */
    FXCommandPalette QLineEdit#fxPaletteField {
        background: transparent;
        border: none;
        border-bottom: 1px solid @border;
        border-radius: 0px;
        padding: 0px 8px;
        font-size: 16px;
        min-height: 47px;
        max-height: 47px;
    }
    /* The rows sit on the palette's own ground, 4 px from its edges. */
    FXCommandPalette QTreeView {
        background-color: @surface;
        border: none;
        padding: 4px 0px;
        font-size: 14px;
    }
    FXCommandPalette QTreeView::item {
        padding: 0px 5px;
        border-radius: @small_radius;
    }
    FXCommandPalette QTreeView::item:first,
    FXCommandPalette QTreeView::item:only-one {
        margin-left: 4px;
    }
    FXCommandPalette QTreeView::item:last,
    FXCommandPalette QTreeView::item:only-one {
        margin-right: 4px;
    }
    /* The current row is the pointer's: the neutral fill, not a selection. */
    FXCommandPalette QTreeView::item:hover,
    FXCommandPalette QTreeView::item:pressed,
    FXCommandPalette QTreeView::item:selected,
    FXCommandPalette QTreeView::item:selected:active,
    FXCommandPalette QTreeView::item:selected:!active,
    FXCommandPalette QTreeView::item:selected:hover {
        background: @state_hover;
        color: @text;
    }
    FXCommandPalette QLabel#fxPaletteHint {
        color: @text_muted;
        border-top: 1px solid @border;
        padding: 8px 12px;
    }
    /* Rounded per cell, a selected row shows a notch at each column. */
    FXCommandPalette QTreeView::item:first {
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
    }
    FXCommandPalette QTreeView::item:middle {
        border-radius: 0;
    }
    FXCommandPalette QTreeView::item:last {
        border-top-left-radius: 0;
        border-bottom-left-radius: 0;
    }
    """
)


@dataclass(frozen=True)
class FXCommand:
    """One row of the palette, and what picking it does.

    Args:
        label: What the row reads.
        run: Called when the row is picked; unused where `choices` is set.
        keys: Its shortcut, as `QKeySequence` reads it, shown at the right.
        section: The group it is listed under, below a label of that name,
            and matched by the search.
        enabled: False shows the row greyed; picking it shows `tip`.
        tip: Shown under the list while the row is current.
        icon: An icon's name, drawn left of the label: one of the default library, or
            `library:name` for another library, such as `brands:houdini_mark`.
        choices: Picking the row lists what this returns, in place, to pick
            one; a choice with its own `choices` steps in again.
        key: What the palette remembers the row by; the label where empty.
            Give one where the label changes, as "Show Log" and "Hide Log".
    """

    label: str
    run: Optional[Callable[[], None]] = None
    keys: str = ""
    section: str = ""
    enabled: bool = True
    tip: str = ""
    icon: str = ""
    choices: Optional[Callable[[], List["FXCommand"]]] = None
    key: str = ""


# Hands `load` a callback taking (row id, words) pairs.
GoTo = Callable[[Callable[[List[Tuple[str, str]]], None]], None]

# The FXCommand a row stands for, on its first column.
_COMMAND_ROLE = Qt.UserRole
# On a group's label row: True where a rule parts it from the group above.
_HEADER_ROLE = Qt.UserRole + 1

# Carmen's measures: a 28 px label, 32 px rows, a group set 4 px in.
_LABEL_HEIGHT = 28
_ROW_HEIGHT = 32
_GROUP_PAD = 4
# Text 8 px in from a group's edge, as a row's icon.
_TEXT_INSET = _GROUP_PAD + 8
# The least room the palette keeps from its window's edges.
_EDGE = 8


def _header_height(text: str, ruled: bool) -> int:
    """A label row's height: the rule and its padding, then the label."""
    return (2 * _GROUP_PAD + 1 if ruled else 0) + (_LABEL_HEIGHT if text else 0)


class _RowInk(QStyledItemDelegate):
    """Draw the keys muted, a disabled row disabled, and the group labels."""

    def initStyleOption(self, option, index) -> None:
        """Give the cell the theme's ink of the moment."""
        super().initStyleOption(option, index)
        first = index.siblingAtColumn(0)
        entry = first.data(_COMMAND_ROLE)
        if entry is None:
            # "Nothing matches" and "Loading" read muted, in the middle.
            if first.data(_HEADER_ROLE) is None:
                option.displayAlignment = Qt.AlignCenter
                option.palette.setColor(
                    QPalette.Text, QColor(fxstyle.colors().text_muted)
                )
            return
        if not entry.enabled:
            token = "text_disabled"
        elif index.column():
            token = "text_muted"
        else:
            return
        option.palette.setColor(
            QPalette.Text, QColor(getattr(fxstyle.colors(), token))
        )

    def sizeHint(self, option, index) -> QSize:
        """Rows are 32 px whatever the row size; a label row its own."""
        size = super().sizeHint(option, index)
        # The sheet's margin to the group's edge is not in Qt's measure.
        size.setWidth(size.width() + _GROUP_PAD)
        first = index.siblingAtColumn(0)
        ruled = first.data(_HEADER_ROLE)
        if ruled is None:
            size.setHeight(_ROW_HEIGHT)
        else:
            size.setHeight(_header_height(first.data(Qt.DisplayRole), ruled))
        return size

    def paint(self, painter, option, index) -> None:
        """Paint a group's label: 12 px, strong, muted; a rule above it."""
        ruled = index.siblingAtColumn(0).data(_HEADER_ROLE)
        if ruled is None:
            super().paint(painter, option, index)
            return
        colors = fxstyle.colors()
        rect = QRect(option.rect)
        painter.save()
        if ruled:
            line = rect.top() + _GROUP_PAD
            painter.fillRect(
                QRect(rect.left(), line, rect.width(), 1), QColor(colors.border)
            )
            rect.setTop(line + 1 + _GROUP_PAD)
        font = QFont(option.font)
        font.setPixelSize(12)
        font.setWeight(QFont.Weight(fxstyle.drawn_weight(fxstyle.STRONG_WEIGHT)))
        painter.setFont(font)
        painter.setPen(QColor(colors.text_muted))
        painter.drawText(
            rect.adjusted(_TEXT_INSET, 0, -_TEXT_INSET, 0),
            Qt.AlignLeft | Qt.AlignVCenter,
            index.data(Qt.DisplayRole),
        )
        painter.restore()


class FXCommandPalette(QFrame):
    """A frameless popup over `window`'s commands; Enter runs, Escape closes.

    Every typed word must appear, in order, in a row's label and section.
    Rows run lately come first, the latest on top, as in VS Code; then
    rows where the words start words. Rows are grouped under a label per
    section, as in Carmen: "Recently used" first, then each section in
    the order its best row ranks. A label is no row: the arrows, Enter and
    the counts pass it by.

    Args:
        window: The window the palette opens over.
        commands: Returns the commands each time the palette opens.
        recent: The keys run lately, the latest first, to start from.

    Signals:
        recent_changed: The keys run lately, the latest first, after a run;
            store them to keep the order across sessions.

    Examples:
        >>> palette = FXCommandPalette(window, lambda: [
        ...     FXCommand("Collapse all", tree.collapseAll, "Ctrl+-"),
        ... ])
        >>> palette.open_commands(position="top")
    """

    # Rows drawn per keystroke; thousands of rows stay typeable.
    SHOWN = 200
    WIDTH = 768
    # The list grows to this many 32 px rows' height, then scrolls.
    ROWS = 12
    FIELD_HEIGHT = 48
    ROW_HEIGHT = _ROW_HEIGHT
    ICON_SIZE = 20
    # The group label the rows run lately are listed under.
    RECENT_LABEL = "Recently used"
    POSITIONS = ("top", "center", "bottom")
    # Keys remembered; a longer list orders nothing a person returns to.
    RECENT = 50

    recent_changed = Signal(list)

    def __init__(
        self,
        window: QWidget,
        commands: Callable[[], List[FXCommand]],
        recent: Sequence[str] = (),
    ):
        super().__init__(window)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        # A NoFrame QFrame loses its border to the base sheet.
        self.setFrameShape(QFrame.StyledPanel)
        self._position = "center"
        self._window = window
        self._commands = commands
        self._command_rows: List[FXCommand] = []
        self._go_to: Optional[List[FXCommand]] = None
        self._going = False
        self._ticket = 0
        self._loading = ""
        self.recent: List[str] = list(recent)[: self.RECENT]
        # Where the rows shown are remembered: "" for the commands, the
        # picked keys joined by "/" in a choice step, None for go-to rows.
        self._scope: Optional[str] = ""
        # The key of each choice step taken to reach the rows shown.
        self._steps: List[str] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.field = QLineEdit()
        self.field.setObjectName("fxPaletteField")
        self.field.addAction(
            fxicons.get_icon("search"), QLineEdit.LeadingPosition
        )
        self.field.textChanged.connect(self._filter)
        self.field.returnPressed.connect(self._run_current)
        self.rows = QTreeWidget()
        self.rows.setColumnCount(3)
        self.rows.setHeaderHidden(True)
        self.rows.setRootIsDecorated(False)
        # A group's label row is shorter or taller than a row.
        self.rows.setUniformRowHeights(False)
        self.rows.setFocusPolicy(Qt.NoFocus)
        # The pointer's row is the current one, as in Carmen.
        self.rows.setMouseTracking(True)
        self.rows.itemEntered.connect(self._pointed)
        # Set, since a host's style gives a list 24 px icons.
        self.rows.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.rows.setItemDelegate(_RowInk(self.rows))
        header = self.rows.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        # The section is a group's label now, not a column; the column keeps
        # its text for code that reads it.
        self.rows.setColumnHidden(1, True)
        self.rows.currentItemChanged.connect(self._followed)
        self.rows.itemClicked.connect(self._run)
        self.hint = QLabel()
        self.hint.setObjectName("fxPaletteHint")
        self.hint.setWordWrap(True)
        # Every tip lays out as rich text: a plain label sets no leading
        # under its last line, so plain and rich tips sat differently.
        self.hint.setTextFormat(Qt.RichText)
        layout.addWidget(self.field)
        layout.addWidget(self.rows)
        layout.addWidget(self.hint)

    @staticmethod
    def rank(query: str, text: str) -> Optional[int]:
        """Return how well `query` matches `text`, lower first; None for no.

        Every word of `query` must appear in `text` in order, ignoring case;
        the rank counts the words that start no word of `text`.
        """
        text = text.lower()
        words = query.lower().split()
        at = 0
        for word in words:
            found = text.find(word, at)
            if found < 0:
                return None
            at = found + len(word)
        return sum(
            re.search(r"(?<![a-z0-9])" + re.escape(word), text) is None
            for word in words
        )

    def open_commands(
        self,
        placeholder: str = "Search, or type a command…",
        position: str = "center",
    ) -> None:
        """Open on the window's commands, at `position` in the window.

        Raises:
            ValueError: If `position` is not one of `POSITIONS`.
        """
        self._going = False
        self._open(placeholder, position)

    def open_go_to(
        self,
        load: GoTo,
        select: Callable[[str], None],
        placeholder: str = "Type a name, or > for a command",
        loading: str = "Loading",
        position: str = "center",
    ) -> None:
        """Open on the rows `load` hands back; picking one `select`s its id.

        A leading `>` switches to the commands. Until `load` calls back,
        the list reads `loading`.

        Args:
            load: Called once with a callback taking `(row id, words)`
                pairs; it may call back later, from this thread.
            select: Called with the picked row's id.
            placeholder: What the empty field says.
            loading: What the list says until the rows land.
            position: Where in the window it opens; one of `POSITIONS`.

        Raises:
            ValueError: If `position` is not one of `POSITIONS`.
        """
        self._going = True
        self._go_to = None
        self._loading = loading
        self._open(placeholder, position)
        self._scope = None
        ticket = self._ticket

        def landed(entries: List[Tuple[str, str]]) -> None:
            # A load that lands after a newer opening, or after the
            # palette is deleted, is out of date.
            if not is_valid(self) or ticket != self._ticket:
                return
            self._go_to = [
                FXCommand(words, partial(select, row_id))
                for row_id, words in entries
            ]
            self._filter(self.field.text())

        load(landed)

    def _open(self, placeholder: str, position: str) -> None:
        if position not in self.POSITIONS:
            raise ValueError(
                f"position must be one of {self.POSITIONS}, not {position!r}"
            )
        self._position = position
        self._ticket += 1
        self._scope = ""
        self._steps = []
        self.field.setPlaceholderText(placeholder)
        self._command_rows = self._commands()
        self.field.blockSignals(True)
        self.field.clear()
        self.field.blockSignals(False)
        width = min(self.WIDTH, self._window.width() - 4 * _EDGE)
        self.resize(width, self.height())
        self._filter("")
        self.show()
        self.field.setFocus()

    def _filter(self, text: str) -> None:
        self._fill(text)
        # The list is as tall as its rows, up to `ROWS` rows; the top stays put.
        rows = self.rows
        content = sum(
            rows.sizeHintForRow(at) for at in range(rows.topLevelItemCount())
        )
        # The sheet's 4 px above and below the rows, once it has set them.
        rows.ensurePolished()
        margins = rows.contentsMargins()
        frame = margins.top() + margins.bottom()
        rows.setFixedHeight(
            min(max(content, self.ROW_HEIGHT), self.ROWS * self.ROW_HEIGHT)
            + frame
        )
        self._fit()

    def _fit(self) -> None:
        layout = self.layout()
        layout.activate()
        # At the real width: a wrapped tip's size hint guesses a narrower
        # one, and the label then centres the text in the extra height.
        height = layout.totalHeightForWidth(self.width())
        # In a small window the list gives up height, and scrolls.
        over = height - (self._window.height() - 2 * _EDGE)
        if over > 0:
            rows = self.rows
            rows.setFixedHeight(max(self.ROW_HEIGHT, rows.minimumHeight() - over))
            layout.activate()
            height = layout.totalHeightForWidth(self.width())
        self.resize(self.width(), height)
        self._place()

    def _place(self) -> None:
        """Centre across the window, at `_position` in its content area."""
        window = self._window
        gap = _EDGE
        # Below the menu and the command rows, above the status bar.
        central = getattr(window, "centralWidget", lambda: None)()
        area = central.geometry() if central is not None else window.rect()
        area = area.adjusted(gap, gap, -gap, -gap)
        height = min(self.height(), window.height() - 2 * gap)
        if self._position == "top":
            top = area.top()
        elif self._position == "bottom":
            top = area.bottom() + 1 - height
        else:
            top = area.center().y() - height // 2
        # A small window: the palette keeps inside it rather than the area.
        top = max(gap, min(top, window.height() - gap - height))
        left = (window.width() - self.width()) // 2
        self.setGeometry(
            QRect(window.mapToGlobal(QPoint(left, top)), QSize(self.width(), height))
        )

    def _tell(self, text: str) -> None:
        """Say `text` under the list; with nothing to say, take no room."""
        if not Qt.mightBeRichText(text):
            text = html.escape(text).replace("\n", "<br>")
        self.hint.setText(text)
        self.hint.setVisible(bool(text))
        self._fit()

    def _fill(self, text: str) -> None:
        commands = not self._going or text.startswith(">")
        query = text[1:] if text.startswith(">") else text
        source = self._command_rows if commands else self._go_to
        scope = "" if self._going and text.startswith(">") else self._scope
        # A row to go to has no key.
        self.rows.setColumnHidden(2, not commands)
        self.rows.clear()
        if source is None:
            self._placeholder(self._loading)
            return
        late = {key: at for at, key in enumerate(self.recent)}
        never = len(late)

        def lately(entry: FXCommand) -> int:
            if scope is None:
                return never
            return late.get(self._key(scope, entry), never)

        ranked = sorted(
            (lately(entry), found, index)
            for index, entry in enumerate(source)
            if (found := self.rank(query, f"{entry.label} {entry.section}"))
            is not None
        )
        if not ranked:
            self._placeholder("Nothing matches" if source else "Nothing to pick")
            return
        shown = [source[index] for *_order, index in ranked[: self.SHOWN]]
        recent_count = sum(order < never for order, *_rest in ranked)
        # Each section gathers its rows, in the order its best row ranks.
        groups = {}
        for at, entry in enumerate(shown):
            group = self.RECENT_LABEL if at < recent_count else entry.section
            groups.setdefault(group, []).append(entry)
        # A row with no icon keeps its label in line with those that have one.
        blank = None
        if any(entry.icon for entry in shown):
            side = self.rows.iconSize().width()
            pixmap = QPixmap(side, side)
            pixmap.fill(Qt.transparent)
            blank = QIcon(pixmap)
        items = []
        for group, entries in groups.items():
            # The first group needs no rule, nor a label where it has none.
            if items or group:
                items.append(self._header(group, ruled=bool(items)))
            for entry in entries:
                keys = QKeySequence(entry.keys).toString(
                    QKeySequence.NativeText
                )
                item = QTreeWidgetItem([entry.label, group, keys])
                item.setData(0, _COMMAND_ROLE, entry)
                item.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
                if blank is not None:
                    item.setIcon(
                        0, self._icon(entry.icon) if entry.icon else blank
                    )
                if entry.tip:
                    for column in range(3):
                        item.setToolTip(column, entry.tip)
                items.append(item)
        self.rows.addTopLevelItems(items)
        for item in items:
            if item.data(0, _HEADER_ROLE) is not None:
                item.setFirstColumnSpanned(True)
        self.rows.setCurrentItem(
            next(item for item in items if self._entry(item) is not None)
        )

    @staticmethod
    def _header(text: str, ruled: bool) -> QTreeWidgetItem:
        """A group's label: no row to pick, read out as a heading."""
        item = QTreeWidgetItem([text])
        item.setData(0, _HEADER_ROLE, ruled)
        # Enabled, so a reader does not call it unavailable; not selectable.
        item.setFlags(Qt.ItemIsEnabled)
        item.setData(0, Qt.AccessibleDescriptionRole, "Heading")
        return item

    @staticmethod
    def _key(scope: str, entry: FXCommand) -> str:
        return f"{scope}{entry.key or entry.label}"

    def _leave_for_commands(self) -> None:
        """A leading `>` lists the commands: remember them as commands."""
        if self._going and self.field.text().startswith(">"):
            self._scope, self._steps = "", []

    def _remember(self, entry: FXCommand) -> None:
        """Put `entry`, and each step that led to it, first in `recent`."""
        if self._scope is None:
            return
        keys = [*self._steps, self._key(self._scope, entry)]
        self.recent = (
            keys[::-1] + [key for key in self.recent if key not in keys]
        )[: self.RECENT]
        self.recent_changed.emit(list(self.recent))

    @staticmethod
    def _icon(name: str) -> QIcon:
        library, _, icon_name = name.rpartition(":")
        if not library:
            return fxicons.get_icon(icon_name)
        # A library icon may be missing, as a DCC with no mark yet.
        return fxicons.get_icon(icon_name, library=library, fallback="layout-grid")

    def _placeholder(self, text: str) -> None:
        item = QTreeWidgetItem([text])
        item.setFlags(Qt.NoItemFlags)
        self.rows.addTopLevelItem(item)
        self._tell("")

    def _followed(
        self,
        item: Optional[QTreeWidgetItem],
        previous: Optional[QTreeWidgetItem] = None,
    ) -> None:
        # A click on a group's label makes it current: keep the row instead.
        if (
            item is not None
            and item.data(0, _HEADER_ROLE) is not None
            and self._entry(previous) is not None
        ):
            self.rows.setCurrentItem(previous)
            return
        entry = self._entry(item)
        self._tell(entry.tip if entry is not None else "")

    def _pointed(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        if self._entry(item) is not None:
            self.rows.setCurrentItem(item)

    def _entry(self, item: Optional[QTreeWidgetItem]) -> Optional[FXCommand]:
        return None if item is None else item.data(0, _COMMAND_ROLE)

    def _run_current(self) -> None:
        self._run(self.rows.currentItem())

    def _run(self, item: Optional[QTreeWidgetItem], _column: int = 0) -> None:
        entry = self._entry(item)
        if entry is None:
            return
        if not entry.enabled:
            self._tell(entry.tip)
            return
        if entry.choices is not None:
            self._choose(entry)
            return
        self._leave_for_commands()
        self._remember(entry)
        # Closed first, so a command that moves focus lands in the window.
        self.hide()
        if entry.run is not None:
            entry.run()

    def _choose(self, entry: FXCommand) -> None:
        """List `entry`'s choices in place of the rows, the field emptied."""
        self._leave_for_commands()
        if self._scope is not None:
            key = self._key(self._scope, entry)
            self._steps.append(key)
            self._scope = f"{key}/"
        self._going = True
        # A go-to load still in flight must not land over the choices.
        self._ticket += 1
        self._go_to = list(entry.choices())
        self.field.setPlaceholderText(f"{entry.label}: type to pick one")
        self.field.blockSignals(True)
        self.field.clear()
        self.field.blockSignals(False)
        self._filter("")

    def _step(self, by: int) -> None:
        """Move `by` rows, passing over the groups' labels."""
        rows = self.rows
        current = rows.currentItem()
        if self._entry(current) is None:
            return
        picks = [
            item
            for item in map(rows.topLevelItem, range(rows.topLevelItemCount()))
            if self._entry(item) is not None
        ]
        now = picks.index(current)
        rows.setCurrentItem(picks[max(0, min(len(picks) - 1, now + by))])

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Move with the arrows and pages; Escape closes."""
        steps = {
            Qt.Key_Down: 1,
            Qt.Key_Up: -1,
            Qt.Key_PageDown: 10,
            Qt.Key_PageUp: -10,
        }
        if event.key() in steps:
            self._step(steps[event.key()])
        elif event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
