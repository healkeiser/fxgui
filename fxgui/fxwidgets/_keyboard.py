"""A tree, a split button and a filtered tree a keyboard works fully."""

# Built-in
from typing import Callable, Optional

# Third-party
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QKeyEvent, QKeySequence
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._tips import apply_tip

# Shift is absent: shifted characters are still typing.
_COMMAND_MODIFIERS = Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier

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
        if text in self._qt_keys or event.modifiers() & _COMMAND_MODIFIERS:
            return False
        field.setFocus(Qt.ShortcutFocusReason)
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
        """Return Qt's width at a push button's height."""
        # Qt's stylesheet style adds 3 px to every QToolButton's height.
        return QSize(super().sizeHint().width(), fxstyle.control_height(self))

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
        parent: The parent widget.
    """

    def __init__(
        self,
        tree: Optional[FXKeyboardTree] = None,
        placeholder: str = "Filter...",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.tree = FXKeyboardTree() if tree is None else tree
        self.filter_bar = FXSearchBar(placeholder=placeholder)
        self.expand_button = self._fold_button("unfold_more", "Expand all")
        self.collapse_button = self._fold_button("unfold_less", "Collapse all")
        self.expand_button.clicked.connect(self.tree.expandAll)
        self.collapse_button.clicked.connect(self.tree.collapseAll)
        self.filter_bar.search_changed.connect(self._filter)
        self.tree.type_into(self.filter_bar)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(self.filter_bar, 1)
        bar.addWidget(self.expand_button)
        bar.addWidget(self.collapse_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self.tree, 1)

    def _filter(self, text: str) -> None:
        fxutils.filter_tree(self.tree, text)

    def _fold_button(self, icon: str, tip: str) -> QToolButton:
        button = QToolButton(self)
        button.setAutoRaise(True)
        fxicons.set_icon(button, icon)
        apply_tip(button, tip)
        return button
