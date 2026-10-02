"""A command palette: a search box over a window's commands, or its rows."""

# Built-in
import re
from dataclasses import dataclass
from functools import partial
from typing import Callable, List, Optional, Tuple

# Third-party
from qtpy.QtCore import QPoint, QRect, QSize, Qt
from qtpy.QtGui import QColor, QIcon, QKeyEvent, QKeySequence, QPalette, QPixmap
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


fxstyle.register_widget_style(
    """
    /* A popup's frame, as a menu's. */
    FXCommandPalette {
        background-color: @surface;
        border: 1px solid @border;
        border-radius: @card_radius;
    }
    FXCommandPalette QLabel#fxPaletteHint {
        color: @text_muted;
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
        run: Called when the row is picked.
        keys: Its shortcut, as `QKeySequence` reads it, shown at the right.
        section: The group it belongs to, shown beside the label and
            matched by the search.
        enabled: False shows the row greyed; picking it shows `tip`.
        tip: Shown under the list while the row is current.
        icon: A material icon's name, drawn left of the label.
    """

    label: str
    run: Callable[[], None]
    keys: str = ""
    section: str = ""
    enabled: bool = True
    tip: str = ""
    icon: str = ""


# Hands `load` a callback taking (row id, words) pairs.
GoTo = Callable[[Callable[[List[Tuple[str, str]]], None]], None]

# The FXCommand a row stands for, on its first column.
_COMMAND_ROLE = Qt.UserRole


class _RowInk(QStyledItemDelegate):
    """Draw the section and keys muted, a disabled row disabled, when shown."""

    def initStyleOption(self, option, index) -> None:
        """Give the cell the theme's ink of the moment."""
        super().initStyleOption(option, index)
        entry = index.siblingAtColumn(0).data(_COMMAND_ROLE)
        if entry is None:
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


class FXCommandPalette(QFrame):
    """A frameless popup over `window`'s commands; Enter runs, Escape closes.

    Every typed word must appear, in order, in a row's label and section.
    Rows where the words start words rank first.

    Args:
        window: The window the palette opens over.
        commands: Returns the commands each time the palette opens.

    Examples:
        >>> palette = FXCommandPalette(window, lambda: [
        ...     FXCommand("Collapse all", tree.collapseAll, "Ctrl+-"),
        ... ])
        >>> palette.open_commands(position="top")
    """

    # Rows drawn per keystroke; thousands of rows stay typeable.
    SHOWN = 200
    WIDTH = 640
    ROWS = 12
    POSITIONS = ("top", "center", "bottom")

    def __init__(
        self, window: QWidget, commands: Callable[[], List[FXCommand]]
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(fxstyle.PANE_GAP)
        self.field = QLineEdit()
        self.field.addAction(
            fxicons.get_icon("search"), QLineEdit.LeadingPosition
        )
        self.field.textChanged.connect(self._filter)
        self.field.returnPressed.connect(self._run_current)
        self.rows = QTreeWidget()
        self.rows.setColumnCount(3)
        self.rows.setHeaderHidden(True)
        self.rows.setRootIsDecorated(False)
        self.rows.setUniformRowHeights(True)
        self.rows.setFocusPolicy(Qt.NoFocus)
        # A host's style gives a list 24 px icons.
        self.rows.setIconSize(QSize(16, 16))
        self.rows.setItemDelegate(_RowInk(self.rows))
        header = self.rows.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.rows.currentItemChanged.connect(self._followed)
        self.rows.itemClicked.connect(self._run)
        self.hint = QLabel()
        self.hint.setObjectName("fxPaletteHint")
        self.hint.setWordWrap(True)
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
        self, placeholder: str = "Type a command", position: str = "center"
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
        ticket = self._ticket

        def landed(entries: List[Tuple[str, str]]) -> None:
            # A load that lands after a newer opening is out of date.
            if ticket != self._ticket:
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
        self.field.setPlaceholderText(placeholder)
        self._command_rows = self._commands()
        self.field.blockSignals(True)
        self.field.clear()
        self.field.blockSignals(False)
        margin = self.layout().contentsMargins().left()
        width = min(self.WIDTH, self._window.width() - 4 * margin)
        self.resize(width, self.height())
        self._filter("")
        self.show()
        self.field.setFocus()

    def _filter(self, text: str) -> None:
        self._fill(text)
        # The list is as tall as its rows, up to `ROWS`; the top stays put.
        row = self.rows.sizeHintForRow(0)
        count = min(max(1, self.rows.topLevelItemCount()), self.ROWS)
        self.rows.setFixedHeight(
            max(row, 1) * count + 2 * self.rows.frameWidth()
        )
        self._fit()

    def _fit(self) -> None:
        self.layout().activate()
        self.resize(self.width(), self.sizeHint().height())
        self._place()

    def _place(self) -> None:
        """Centre across the window, at `_position` in its content area."""
        window = self._window
        gap = self.layout().contentsMargins().left()
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
        self.hint.setText(text)
        self.hint.setVisible(bool(text))
        self._fit()

    def _fill(self, text: str) -> None:
        commands = not self._going or text.startswith(">")
        query = text[1:] if text.startswith(">") else text
        source = self._command_rows if commands else self._go_to
        # A row to go to has no section and no key.
        for column in (1, 2):
            self.rows.setColumnHidden(column, not commands)
        self.rows.clear()
        if source is None:
            self._placeholder(self._loading)
            return
        ranked = sorted(
            (found, index)
            for index, entry in enumerate(source)
            if (found := self.rank(query, f"{entry.label} {entry.section}"))
            is not None
        )
        if not ranked:
            self._placeholder("Nothing matches")
            return
        shown = [source[index] for _found, index in ranked[: self.SHOWN]]
        # A row with no icon keeps its label in line with those that have one.
        blank = None
        if any(entry.icon for entry in shown):
            side = self.rows.iconSize().width()
            pixmap = QPixmap(side, side)
            pixmap.fill(Qt.transparent)
            blank = QIcon(pixmap)
        items = []
        for entry in shown:
            keys = QKeySequence(entry.keys).toString(QKeySequence.NativeText)
            item = QTreeWidgetItem([entry.label, entry.section, keys])
            item.setData(0, _COMMAND_ROLE, entry)
            item.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
            if blank is not None:
                item.setIcon(
                    0, fxicons.get_icon(entry.icon) if entry.icon else blank)
            if entry.tip:
                for column in range(3):
                    item.setToolTip(column, entry.tip)
            items.append(item)
        self.rows.addTopLevelItems(items)
        self.rows.setCurrentItem(items[0])

    def _placeholder(self, text: str) -> None:
        item = QTreeWidgetItem([text])
        item.setFlags(Qt.NoItemFlags)
        self.rows.addTopLevelItem(item)
        self._tell("")

    def _followed(self, item: Optional[QTreeWidgetItem], *_) -> None:
        entry = self._entry(item)
        self._tell(entry.tip if entry is not None else "")

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
        # Closed first, so a command that moves focus lands in the window.
        self.hide()
        entry.run()

    def _step(self, by: int) -> None:
        current = self.rows.currentItem()
        if self._entry(current) is None:
            return
        now = self.rows.indexOfTopLevelItem(current)
        last = self.rows.topLevelItemCount() - 1
        self.rows.setCurrentItem(
            self.rows.topLevelItem(max(0, min(last, now + by)))
        )

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
