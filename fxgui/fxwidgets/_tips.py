"""Rich tooltips built on Qt's own `setToolTip`, and the keycap widget.

`apply_tip` is fxgui's one tooltip. A useful tooltip answers three things
at once: what the control is, what it does to the user's data, and how to
reach it without the mouse. Every string goes through `tip`, so the layout
is the same everywhere: title in the primary text, body dimmed, shortcut on
the right as keycaps, one per key.

`tip` writes the current theme's colours into the HTML, so `apply_tip`
rebuilds it each time Qt is about to show it: a tip set in one theme shows
in the theme in force. Rich text draws no rounded background: a keycap in a
tooltip is square; `FXKeycap`, the widget, is round.
"""

# Built-in
from html import escape
from typing import List, Optional

# Third-party
from qtpy.QtCore import QEvent, QKeyCombination, QObject, Qt, Slot
from qtpy.QtGui import QAction, QKeySequence
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QSizePolicy,
    QTableWidgetItem,
    QToolTip,
    QTreeWidgetItem,
    QWidget,
)

# Internal
from fxgui import fxstyle


# Where apply_tip keeps a tip's (title, body, shortcut): a property on a
# widget or action, an item role on a view's item.
_PARTS = "fxTipParts"
_PARTS_ROLE = Qt.ItemDataRole.UserRole + 0x7F1

# Gaps between keycaps: keys of one chord sit close, chords further apart.
_KEY_GAP = 2
_CHORD_GAP = 8
_KEY_GAP_HTML = "&nbsp;"
_CHORD_GAP_HTML = "&nbsp;&nbsp;&nbsp;"

_MODIFIERS = (
    Qt.KeyboardModifier.ControlModifier,
    Qt.KeyboardModifier.AltModifier,
    Qt.KeyboardModifier.ShiftModifier,
    Qt.KeyboardModifier.MetaModifier,
)

# An id outranks the base sheet's QFrame[frameShape="0"] border rule, which
# beats a type selector and would drop the cap's border and padding.
fxstyle.register_widget_style(
    """
    QLabel#fxKeycap {
        background: @state_hover;
        color: @text_muted;
        border: 1px solid @border;
        border-radius: @button_radius;
        padding: 1px 5px;
        font-family: @font_mono;
    }
    """
)


def _native(combination: QKeyCombination) -> str:
    return QKeySequence(combination).toString(
        QKeySequence.SequenceFormat.NativeText
    )


def _chords(keys: str) -> List[List[str]]:
    """Return each chord of `keys` as its key names, in the platform's words.

    A string Qt cannot parse comes back whole, as one key.
    """
    sequence = QKeySequence(keys)
    if not sequence.toString():
        return [[keys]] if keys else []
    chords = []
    for index in range(sequence.count()):
        combination = sequence[index]
        key = combination.key()
        name = _native(QKeyCombination(key))
        whole = _native(combination)
        held = combination.keyboardModifiers()
        # Qt names a modifier only beside a key; the key's name is cut off
        # the end, then the "+" Qt puts between them.
        modifiers = [
            _native(QKeyCombination(modifier, key))[: -len(name)].rstrip("+")
            for modifier in _MODIFIERS
            if held & modifier
        ]
        modifiers.sort(key=whole.find)
        chords.append(modifiers + [name])
    return chords


def keycap(keys: str) -> str:
    """Render a keyboard shortcut as rich text, one keycap per key.

    Args:
        keys: A Qt key sequence, such as `"Ctrl+S"`, `"F5"` or
            `"Ctrl+K, Ctrl+S"`.

    Returns:
        str: HTML for the keycaps, or an empty string when `keys` is empty.

    Examples:
        >>> button.setToolTip(f"Save {keycap('Ctrl+S')}")

    Note:
        The HTML holds the current theme's colours; a keycap on a window is
        an `FXKeycap`.
    """

    colors = fxstyle.colors()
    return _CHORD_GAP_HTML.join(
        _KEY_GAP_HTML.join(
            f'<span style="background:{colors.surface};'
            f' color:{colors.text_muted};">&nbsp;{escape(name)}&nbsp;</span>'
            for name in chord
        )
        for chord in _chords(keys)
    )


def tip(title: str, body: str = "", shortcut: str = "") -> str:
    """Build the HTML for a rich tooltip.

    Args:
        title: What the control is, in a couple of words. Sentence case, no
            trailing period, it is a label and not a sentence.
        body: What the control does, or why it is unavailable. One sentence.
            Defaults to `""`.
        shortcut: A Qt key sequence, such as `"Ctrl+S"`. Defaults to `""`.

    Returns:
        str: HTML to hand to `setToolTip`. An empty string when all three
            arguments are empty, so a caller can pass a missing value
            through without producing an empty floating box.

    Examples:
        >>> tip("", "", "")
        ''
        >>> button.setToolTip(
        ...     tip("Save", "Write the scene to disk", "Ctrl+S")
        ... )

    Note:
        The HTML holds the current theme's colours: call it when the tip
        shows, as a model's `data(ToolTipRole)` does, or use `apply_tip`.
        Every caller string is HTML-escaped, so a path or a name holding
        `&` or `<` reaches the user as text instead of corrupting the markup.
        Qt ignores `max-width` and applies a table `width` as a fixed width,
        so there is no width cap: the tooltip wraps itself, up to 440 px.
    """

    if not (title or body or shortcut):
        return ""

    head = f"<b>{escape(title)}</b>" if title else ""

    rows = []
    if shortcut:
        # A spacer cell pushes the keycaps to the right edge; Qt rich text
        # offers no other way to right-align part of a line.
        rows.append(
            '<table width="100%" cellspacing="0" cellpadding="0"><tr>'
            f"<td>{head}</td>"
            f'<td align="right">{keycap(shortcut)}</td>'
            "</tr></table>"
        )
    elif head:
        rows.append(head)

    if body:
        muted = fxstyle.colors().text_muted
        rows.append(f'<span style="color:{muted};">{escape(body)}</span>')

    blocks = f"<div>{rows[0]}</div>"
    for row in rows[1:]:
        blocks += f'<div style="margin-top:3px;">{row}</div>'
    return blocks


class FXKeycap(QWidget):
    """A keyboard shortcut drawn as keys, one cap per key.

    Each cap is round at the button radius, and its look is a registered
    rule, so it follows every theme switch.

    Examples:
        >>> row.addWidget(FXKeycap("Ctrl+S"))
    """

    def __init__(self, keys: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._keys = ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(_KEY_GAP)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_keys(keys)

    def keys(self) -> str:
        """Return the key sequence as it was given."""
        return self._keys

    def set_keys(self, keys: str) -> None:
        """Show `keys`, a Qt key sequence, as one cap per key."""
        self._keys = keys
        layout = self.layout()
        while layout.count():
            widget = layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for index, chord in enumerate(_chords(keys)):
            if index:
                layout.addSpacing(_CHORD_GAP - _KEY_GAP * 2)
            for name in chord:
                cap = QLabel(name, self)
                cap.setObjectName("fxKeycap")
                layout.addWidget(cap)


class _TipRefresh(QObject):
    """Rebuild an `apply_tip` tooltip as Qt is about to show it."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.ToolTip:
            return False
        view = watched.parent()
        if isinstance(view, QAbstractItemView) and watched is view.viewport():
            index = view.indexAt(event.pos())
            parts = index.data(_PARTS_ROLE)
            if not parts:
                return False
            QToolTip.showText(
                event.globalPos(), tip(*parts), watched, view.visualRect(index)
            )
            return True
        parts = watched.property(_PARTS)
        if parts:
            watched.setToolTip(tip(*parts))
        return False

    @Slot()
    def refresh_action(self) -> None:
        """Rebuild the hovered action's tooltip."""
        action = self.sender()
        action.setToolTip(tip(*action.property(_PARTS)))


_REFRESH = _TipRefresh()


def _view_of(item) -> QAbstractItemView:
    """Return the view showing `item`, or raise if it is in none yet."""
    if isinstance(item, QTreeWidgetItem):
        view = item.treeWidget()
    elif isinstance(item, QListWidgetItem):
        view = item.listWidget()
    else:
        view = item.tableWidget()
    if view is None:
        raise ValueError("Add the item to its view before apply_tip.")
    return view


def apply_tip(
    target,
    title: str,
    body: str = "",
    shortcut: str = "",
) -> None:
    """Set a rich tooltip on `target`, plus a markup-free status tip.

    The tooltip is rebuilt each time it shows, in the theme in force.

    Args:
        target: A widget, an action, or an item already in its list, tree
            or table widget; a tree item gets the tip on every column.
        title: What the control is, in a couple of words.
        body: What the control does. Defaults to `""`.
        shortcut: A Qt key sequence, such as `"Ctrl+S"`. Defaults to `""`.

    Raises:
        ValueError: `target` is an item not yet added to a view.

    Examples:
        >>> apply_tip(
        ...     button,
        ...     "Save",
        ...     "Write the scene to disk",
        ...     "Ctrl+S",
        ... )

    Note:
        The status tip carries the same words without markup. Qt shows it in
        the window's status bar on hover, which is where a person looks for
        "what is this" before a tooltip has had time to appear.
    """

    parts = [title, body, shortcut]
    html = tip(*parts)
    plain = f"{title} - {body}" if body else title

    if isinstance(target, (QTreeWidgetItem, QListWidgetItem, QTableWidgetItem)):
        _view_of(target).viewport().installEventFilter(_REFRESH)
        if isinstance(target, QTreeWidgetItem):
            for column in range(max(target.columnCount(), 1)):
                target.setData(column, _PARTS_ROLE, parts)
                target.setToolTip(column, html)
                target.setStatusTip(column, plain)
        else:
            target.setData(_PARTS_ROLE, parts)
            target.setToolTip(html)
            target.setStatusTip(plain)
        return

    if isinstance(target, QAction):
        # A tool button or menu reads the action's tooltip; hover comes
        # first, so the action is rebuilt then.
        if target.property(_PARTS) is None:
            target.hovered.connect(_REFRESH.refresh_action)
    elif isinstance(target, QWidget):
        target.installEventFilter(_REFRESH)
    if hasattr(target, "setProperty"):
        target.setProperty(_PARTS, parts)

    target.setToolTip(html)
    if hasattr(target, "setStatusTip"):
        target.setStatusTip(plain)

    # A screen reader reads the accessible name, never the HTML tooltip.
    if title and hasattr(target, "setAccessibleName") and not (
        target.accessibleName()
    ):
        target.setAccessibleName(title)
    if body and hasattr(target, "setAccessibleDescription") and not (
        target.accessibleDescription()
    ):
        target.setAccessibleDescription(body)
