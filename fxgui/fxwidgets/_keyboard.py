"""A tree, a split button and a filtered tree a keyboard works fully."""

# Built-in
import contextlib
from typing import Callable, Iterator, Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, QRect, QSize, Qt, Slot
from qtpy.QtGui import QKeyEvent, QKeySequence
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLayout,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui._compat import is_valid
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._summary_row import FOOTER_PROPERTY, FXSummaryRow
from fxgui.fxwidgets._tips import apply_tip

# The actions are the tree card's footer: its surface, a rule on top.
fxstyle.register_widget_style(
    """
    QFrame#fxTreeActions {
        background-color: @surface_sunken;
        border: none;
        border-top: 1px solid @border;
        border-radius: 0px;
    }
    """
)

# Shift is absent: shifted characters are still typing.
_COMMAND_MODIFIERS = Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier

# Windows reports AltGr as Ctrl+Alt, so exactly those two (Shift allowed)
# with a printable character is typing: @ # { [ on AZERTY and QWERTZ.
_ALTGR = Qt.ControlModifier | Qt.AltModifier


def _is_typing(event: QKeyEvent) -> bool:
    """Return whether `event`'s modifiers leave it plain typing."""
    held = event.modifiers() & _COMMAND_MODIFIERS
    return held == Qt.NoModifier or held == _ALTGR

#: Qt's own tree commands: `+` opens, `-` closes, `*` opens all, Space
#: activates. Matched by character, so the keypad's count too.
TREE_KEYS = "+-* "


def _is_return(event: QKeyEvent) -> bool:
    return event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
        event.modifiers() & _COMMAND_MODIFIERS
    )


class FXKeyboardTree(QTreeWidget):
    """A tree whose rows a keyboard reaches as well as a mouse.

    - The Menu key and Shift+F10 emit `customContextMenuRequested` at the
      current row, so one handler builds every row menu.
    - Enter runs the primary act set with `set_primary_act`.
    - Typing goes to the field set with `type_into`, rather than Qt's
      keyboard search, which on a lazy tree finds only loaded rows.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._filter_field: Optional[QLineEdit] = None
        self._qt_keys = TREE_KEYS
        self._primary_act: Optional[Callable[[QTreeWidgetItem], None]] = None

    def type_into(self, field: QLineEdit, qt_keys: str = TREE_KEYS) -> None:
        """Send what is typed on this tree to `field`.

        Args:
            field: The filter field; focus moves there on the first key.
            qt_keys: The characters that stay Qt's own tree commands.
        """
        self._filter_field = field
        self._qt_keys = qt_keys

    def set_primary_act(
        self, act: Optional[Callable[[QTreeWidgetItem], None]]
    ) -> None:
        """Run `act` on the current row on Enter; `None` gives Enter back."""
        self._primary_act = act

    def open_current_menu(self) -> bool:
        """Ask for the current row's menu, as a right-click on it would.

        Returns:
            Whether there was a current row to ask about.
        """
        item = self.currentItem()
        if item is None:
            return False
        self.scrollToItem(item)
        self.customContextMenuRequested.emit(self.visualItemRect(item).center())
        return True

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Route the menu keys, Enter and typing, then let Qt have the rest."""
        menu_key = event.key() == Qt.Key_Menu or (
            event.key() == Qt.Key_F10
            and event.modifiers() == Qt.ShiftModifier
        )
        if menu_key and self.open_current_menu():
            return
        item = self.currentItem()
        if _is_return(event) and item is not None and self._primary_act:
            self._primary_act(item)
            return
        if self._typed_into_the_field(event):
            return
        super().keyPressEvent(event)

    def _typed_into_the_field(self, event: QKeyEvent) -> bool:
        field, text = self._filter_field, event.text()
        if field is None or not text or not text.isprintable():
            return False
        if text in self._qt_keys or not _is_typing(event):
            return False
        field.setFocus(Qt.ShortcutFocusReason)
        # Focus by shortcut selects the field's text; typing again from the
        # tree refines the filter, so the key goes after it, not over it.
        field.deselect()
        field.end(False)
        field.insert(text)
        return True


class FXSplitButton(QToolButton):
    """A split button whose click and dropdown both have keys.

    A plain `MenuButtonPopup` answers only Space. Enter clicks it, and
    `DROPDOWN_KEYS` open the menu through `popup`, since `showMenu` runs an
    event loop of its own.
    """

    DROPDOWN_KEYS = ("Alt+Down", "Menu")

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setPopupMode(QToolButton.MenuButtonPopup)

    def sizeHint(self) -> QSize:
        """Return Qt's width at a push button's height, or a compact one's."""
        width = super().sizeHint().width()
        if (self.toolButtonStyle() == Qt.ToolButtonTextBesideIcon
                and self.text() and not self.icon().isNull()):
            # Qt pads the text by two spaces: centred on a text-only button,
            # all after it beside an icon, against the arrow's divider.
            width -= 2 * self.fontMetrics().horizontalAdvance(" ")
        # Qt's stylesheet style adds 3 px to every QToolButton's height.
        if self.property(fxstyle.COMPACT_PROPERTY):
            return QSize(width, fxstyle.COMPACT_HEIGHT)
        return QSize(width, fxstyle.control_height(self))

    @classmethod
    def dropdown_hint(cls) -> str:
        """Return `DROPDOWN_KEYS` as the platform spells them, for a tip."""
        return " or ".join(
            QKeySequence(keys).toString(QKeySequence.NativeText)
            for keys in cls.DROPDOWN_KEYS
        )

    def settle(self, click: bool) -> None:
        """Leave the button only what it still has to do.

        Args:
            click: Whether a plain click still runs something. Without one a
                click opens the menu; without a menu the arrow goes; with
                neither the button hides.
        """
        menu = self.menu()
        listed = menu is not None and bool(menu.actions())
        if not listed:
            self.setMenu(None)
            self.setPopupMode(QToolButton.DelayedPopup)
        elif not click:
            self.setPopupMode(QToolButton.InstantPopup)
        if not (click or listed):
            # Never `setVisible(True)` elsewhere: a button outside a shown
            # layout would open as its own window.
            self.hide()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Click on Enter and open the menu on `DROPDOWN_KEYS`."""
        # The keypad's Enter carries the keypad modifier.
        if _is_return(event) and not event.modifiers() & ~Qt.KeypadModifier:
            self.click()
            return
        menu = self.menu()
        pressed = QKeySequence(event.keyCombination())
        if menu is not None and any(
            pressed == QKeySequence(keys) for keys in self.DROPDOWN_KEYS
        ):
            menu.popup(self.mapToGlobal(self.rect().bottomLeft()))
            return
        super().keyPressEvent(event)


class FXFilteredTree(QWidget):
    """A tree under a filter bar, with expand-all and collapse-all buttons.

    Typing on the tree goes to the bar, and the bar narrows the tree with
    `fxutils.filter_tree`: a match keeps its subtree and its ancestors.

    Args:
        tree: The tree to wrap; a new `FXKeyboardTree` when omitted.
        placeholder: What the empty filter bar says.
        actions: A row of buttons, if any: the tree card's footer, under
            its rows and any `FXSummaryRow`, inside the card's edge.
        parent: The parent widget.
    """

    def __init__(
        self,
        tree: Optional[FXKeyboardTree] = None,
        placeholder: str = "Filter",
        actions: Optional[QLayout] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.tree = FXKeyboardTree() if tree is None else tree
        self.filter_bar = FXSearchBar(placeholder=placeholder)
        self.expand_button = self._fold_button("chevrons-up-down", "Expand all")
        self.collapse_button = self._fold_button("chevrons-down-up", "Collapse all")
        self.expand_button.clicked.connect(self.tree.expandAll)
        self.collapse_button.clicked.connect(self.tree.collapseAll)
        self.filter_bar.search_changed.connect(self._filter)
        self.tree.type_into(self.filter_bar)

        # Set, not left to the style: inside a host the style is the host's.
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(fxstyle.PANE_GAP)
        bar.addWidget(self.filter_bar, 1)
        bar.addWidget(self.expand_button)
        bar.addWidget(self.collapse_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(fxstyle.PANE_GAP)
        layout.addLayout(bar)
        layout.addWidget(self.tree, 1)
        if actions is not None:
            _TreeFooter(self.tree, actions)

        # A flush tree (mark_flush, as a dock pane makes it) has no card
        # edge under the bar: a rule runs along its top instead. A child of
        # the tree, it reaches as far as the tree does.
        self._top_rule = QFrame(self.tree)
        self._top_rule.setFrameShape(QFrame.HLine)
        self.tree.installEventFilter(self)
        self._fit_top_rule()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Keep the top rule across the tree, shown while it is flush."""
        if watched is self.tree and event.type() in (
            QEvent.Resize, QEvent.Show, QEvent.DynamicPropertyChange
        ):
            self._fit_top_rule()
        return False

    def _fit_top_rule(self) -> None:
        rule = self._top_rule
        flush = bool(self.tree.property(fxstyle.FLUSH_PROPERTY))
        rule.setVisible(flush)
        if flush:
            rule.setGeometry(0, 0, self.tree.width(), 1)
            rule.raise_()

    def _filter(self, text: str) -> None:
        fxutils.filter_tree(self.tree, text)

    def refilter(self) -> None:
        """Filter the tree again by the bar's text, after refilling it."""
        self._filter(self.filter_bar.text())

    @contextlib.contextmanager
    def refill(self) -> Iterator[None]:
        """Refill the tree inside the block; its rows arrive, filtered.

        The old rows leave as the new ones fade in and rise into place
        (`fxstyle.arrive`), and the bar's filter applies to them.

        Examples:
            >>> with panel.refill():
            ...     panel.tree.clear()
            ...     panel.tree.addTopLevelItems(items)
        """
        with fxstyle.arrive(self.tree.viewport()):
            yield
            self.refilter()

    def _fold_button(self, icon: str, tip: str) -> QToolButton:
        button = QToolButton(self)
        button.setAutoRaise(True)
        fxicons.set_icon(button, icon)
        apply_tip(button, tip)
        # The bar sets the row's height, so the tree sits one gap below it.
        policy = button.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Ignored)
        button.setSizePolicy(policy)
        return button


class _TreeFooter(QFrame):
    """A tree card's footer: a row of actions under the rows and summary.

    It sits in the tree's bottom margin, under any `FXSummaryRow`, so the
    card's edge and round corners frame it with the rows. The scroll bars
    scroll the rows and the summary, so they end above it: Qt lays the
    horizontal one under the whole margin, and the footer moves it up.
    """

    def __init__(self, view: QTreeView, actions: QLayout):
        super().__init__(view)
        self.setObjectName("fxTreeActions")
        self._view = view
        # Its buttons' ends line up with the cells' text.
        lead = int(fxstyle.colors().cell_lead.rstrip("px"))
        gap = fxstyle.PANE_GAP
        actions.setContentsMargins(lead, gap, lead, gap)
        self.setLayout(actions)
        # The view resets its viewport margins on every geometry update,
        # and puts its scroll bars back wherever it lays itself out.
        view.viewport().installEventFilter(self)
        # Held for the footer's life: PySide 6.5 marks a scroll bar's own
        # wrapper deleted once a passing wrapper of its container is freed.
        self._boxes = (
            _bar_box(view.horizontalScrollBar()),
            _bar_box(view.verticalScrollBar()),
        )
        for box in self._boxes:
            box.installEventFilter(self)
        fxstyle.theme_changed.connect(self._fit)
        # Under the frame's round corners, which the theme draws on top.
        self.lower()
        view.viewport().lower()
        self.show()

    def event(self, event: QEvent) -> bool:
        """Refit when the actions ask for another height."""
        handled = super().event(event)
        if event.type() == QEvent.LayoutRequest:
            self._fit()
        return handled

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Keep the bottom margin, the scroll bars and the footer in place."""
        if event.type() in (
            QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Hide
        ):
            self._fit()
        return False

    @Slot()
    def _fit(self) -> None:
        """Reserve the footer's height under any summary row and sit in it."""
        view = self._view
        if not is_valid(view):
            return
        height = self.sizeHint().height()
        view.setProperty(FOOTER_PROPERTY, height)
        summary = view.findChild(FXSummaryRow, "", Qt.FindDirectChildrenOnly)
        above = 0 if summary is None or summary.isHidden() else (
            summary.height())
        margins = view.viewportMargins()
        if margins.bottom() != above + height:
            view.setViewportMargins(
                margins.left(), margins.top(), margins.right(), above + height)
        viewport = view.viewport().geometry()
        under = viewport.bottom() + 1 + above
        # Rows, summary, then the horizontal bar; the footer last, at the
        # card's foot across its whole width, the vertical bar beside the
        # rows and summary only.
        horizontal, vertical = self._boxes
        if horizontal is not view and horizontal.isVisible():
            _place(horizontal, horizontal.x(), under,
                   horizontal.width(), horizontal.height())
            under += horizontal.height()
        if vertical is not view and vertical.isVisible():
            _place(vertical, vertical.x(), vertical.y(), vertical.width(),
                   viewport.bottom() + 1 + above - vertical.y())
        _place(self, viewport.x(), under,
               view.width() - view.frameWidth() - viewport.x(), height)


def _bar_box(bar: QWidget) -> QWidget:
    """Return what a scroll area lays a scroll bar out in: its container."""
    return bar.parentWidget()


def _place(widget: QWidget, x: int, y: int, width: int, height: int) -> None:
    """Set `widget`'s geometry when it differs: each set re-enters `_fit`."""
    if widget.geometry() != QRect(x, y, width, height):
        widget.setGeometry(x, y, width, height)
