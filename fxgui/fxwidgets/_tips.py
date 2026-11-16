"""Rich tooltips built on Qt's own `setToolTip`, and the keycap widget.

`apply_tip` is fxgui's one tooltip. A useful tooltip answers three things
at once: what the control is, what it does to the user's data, and how to
reach it without the mouse. Every string goes through `tip`, so the layout
is the same everywhere: title in the primary text, body dimmed, shortcut
after the title and a middle dot as keycaps, one per key. A tip about a
thing rather than a control adds labelled facts, a code line (a path, a
key, a command) and a closing hint.

`tip` writes the current theme's colours into the HTML, so `apply_tip`
rebuilds it each time Qt is about to show it: a tip set in one theme shows
in the theme in force. Rich text draws no rounded background: a keycap in a
tooltip is square; `FXKeycap`, the widget, is round.
"""

# Built-in
from html import escape
from typing import Iterable, List, Optional, Tuple

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
    QApplication,
    QTreeWidgetItem,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui._compat import is_valid


# Where apply_tip keeps a tip's parts, `tip`'s arguments by name: a property
# on a widget or action, an item role on a view's item.
_PARTS = "fxTipParts"
_PARTS_ROLE = Qt.ItemDataRole.UserRole + 0x7F1
# The accessible (name, description) apply_tip last set, so a later tip
# replaces its own words but never a name the caller chose.
_SPOKEN = "fxTipSpoken"

# Gaps between keycaps: keys of one chord sit close, chords further apart.
_KEY_GAP = 2
_CHORD_GAP = 8
_KEY_GAP_HTML = "&nbsp;"
_CHORD_GAP_HTML = "&nbsp;&nbsp;&nbsp;"

# Pixels above the body, which belongs to the title, and above each later
# block: the facts, the code, the hint.
_LINE_GAP = 3
_BLOCK_GAP = 8
# Between a fact's label and its value.
_FACT_GAP = 14
# Around the code, inside its fill.
_CODE_PADDING = 4
# Characters a row of code holds: about 320 px, a tooltip's widest in the
# reference look, in a mono face at the code's size.
_CODE_COLUMNS = 48

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
        background: transparent;
        color: @text;
        border: 1px solid @border_light;
        border-radius: @small_radius;
        padding: 0px 4px;
        min-width: 10px;
        min-height: 18px;
        qproperty-alignment: AlignCenter;
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
    # A tooltip is a `surface` card; `tooltip` fills what sits on it.
    return _CHORD_GAP_HTML.join(
        _KEY_GAP_HTML.join(
            f'<span style="background:{colors.tooltip};'
            f' color:{colors.text_muted};">&nbsp;{escape(name)}&nbsp;</span>'
            for name in chord
        )
        for chord in _chords(keys)
    )


def _kept(facts: Iterable[Tuple[str, Optional[str]]]) -> List[List[str]]:
    """Return the facts that have a value, as pairs of strings."""
    return [
        [str(label), str(value)]
        for label, value in facts or ()
        if value is not None and str(value) != ""
    ]


def _lines(text: str) -> str:
    """Return caller text as HTML: escaped, a newline breaking the line."""
    return escape(text).replace("\n", "<br>")


def _facts(facts: List[List[str]]) -> str:
    """Return the facts as a table: the label dimmed, the value beside it."""
    muted = fxstyle.colors().text_muted
    rows = "".join(
        f'<tr><td style="color:{muted}; padding-right:{_FACT_GAP}px;">'
        f"{escape(label)}</td><td>{_lines(value)}</td></tr>"
        for label, value in facts
    )
    return f'<table cellspacing="0" cellpadding="1">{rows}</table>'


def _code(text: str) -> str:
    """Return `text` as code: the theme's mono face in a block of its own.

    Qt breaks a line at a space only, so a path would make the tooltip as
    wide as itself: the rows are cut here, and Qt wraps nothing.
    """
    colors = fxstyle.colors()
    families = fxstyle.font(role="mono").families()
    face = f"font-family:'{escape(families[0])}'; " if families else ""
    rows = "\n".join(
        row for line in text.split("\n") for row in _code_rows(line)
    )
    # A cell is filled edge to edge, a span only behind each row's glyphs;
    # `pre` keeps the rows as cut, their spaces included.
    return (
        f'<table cellspacing="0" cellpadding="{_CODE_PADDING}"'
        f' bgcolor="{colors.tooltip}"><tr>'
        '<td style="white-space:pre;">'
        f'<span style="{face}font-size:{fxstyle.FONT_SIZE - 2}px;'
        f' color:{colors.text};">{escape(rows)}</span></td></tr></table>'
    )


def _code_rows(line: str) -> List[str]:
    """Cut a line of code into rows of `_CODE_COLUMNS` characters at most.

    After a folder separator while the row holds one, else after an
    underscore or a space, else at the last column.
    """
    rows = []
    while len(line) > _CODE_COLUMNS:
        head = line[:_CODE_COLUMNS]
        cut = max(head.rfind("\\"), head.rfind("/")) + 1
        if not cut:
            cut = max(head.rfind("_"), head.rfind(" ")) + 1 or _CODE_COLUMNS
        rows.append(line[:cut])
        line = line[cut:]
    rows.append(line)
    return rows


def tip(
    title: str,
    body: str = "",
    shortcut: str = "",
    *,
    facts: Iterable[Tuple[str, Optional[str]]] = (),
    code: str = "",
    hint: str = "",
) -> str:
    """Build the HTML for a rich tooltip.

    Args:
        title: What the control is, in a couple of words. Sentence case, no
            trailing period, it is a label and not a sentence.
        body: What the control does, or why it is unavailable; a newline
            breaks the line. Defaults to `""`.
        shortcut: A Qt key sequence, such as `"Ctrl+S"`. Defaults to `""`.
        facts: What is known about the thing, as (label, value) pairs,
            drawn as a table in the order given. A pair whose value is
            empty or None is left out. Defaults to `()`.
        code: A path, a key or a command, drawn in the theme's mono face
            on a faint fill. A long line is cut into rows after a folder
            separator, so a path never widens the tooltip; a newline
            starts a row too. Defaults to `""`.
        hint: A closing line, dimmed: what a double-click does. Defaults
            to `""`.

    Returns:
        str: HTML to hand to `setToolTip`. An empty string when every
            argument is empty, so a caller can pass a missing value
            through without producing an empty floating box.

    Examples:
        >>> tip("", "", "")
        ''
        >>> button.setToolTip(
        ...     tip("Save", "Write the scene to disk", "Ctrl+S")
        ... )
        >>> item.setToolTip(
        ...     tip(
        ...         "livetest v001",
        ...         facts=[("Product", "render/livetest"), ("Files", "8")],
        ...         code=path,
        ...         hint="Double-click to play the preview",
        ...     )
        ... )

    Note:
        The HTML holds the current theme's colours: call it when the tip
        shows, as a model's `data(ToolTipRole)` does, or use `apply_tip`.
        Every caller string is HTML-escaped, so a path or a name holding
        `&` or `<` reaches the user as text instead of corrupting the markup.
        Qt ignores `max-width` and applies a table `width` as a fixed width,
        so there is no width cap: the tooltip wraps itself, up to 440 px.
    """

    kept = _kept(facts)
    if not (title or body or shortcut or kept or code or hint):
        return ""

    # A plain tip is one line at the body's weight, as the web look's; a
    # tip with facts, code or a hint keeps its title emphasised over them.
    rich = bool(kept or code or hint)
    head = escape(title)
    if title and rich:
        weight = fxstyle.drawn_weight(fxstyle.EMPHASIS_WEIGHT)
        head = f'<span style="font-weight:{weight};">{head}</span>'
    muted = fxstyle.colors().text_muted

    # Each block with the gap above it; the first block's is not drawn.
    rows = []
    if shortcut:
        # The keys follow the words after a middle dot, on the same line.
        dot = f'<span style="color:{muted};">&nbsp;·&nbsp;</span>' if head else ""
        rows.append((0, f"{head}{dot}{keycap(shortcut)}"))
    elif head:
        rows.append((0, head))
    if body:
        rows.append(
            (_LINE_GAP, f'<span style="color:{muted};">{_lines(body)}</span>')
        )
    if kept:
        rows.append((_BLOCK_GAP, _facts(kept)))
    if code:
        rows.append((_BLOCK_GAP, _code(code)))
    if hint:
        rows.append(
            (_BLOCK_GAP, f'<span style="color:{muted};">{_lines(hint)}</span>')
        )

    blocks = f"<div>{rows[0][1]}</div>"
    for gap, row in rows[1:]:
        blocks += f'<div style="margin-top:{gap}px;">{row}</div>'
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
                # Now, not on the queued show: until then the size hint
                # leaves it out, and a holder placing the caps by it does.
                cap.show()


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
                event.globalPos(),
                tip(**parts),
                watched,
                view.visualRect(index),
            )
            return True
        parts = watched.property(_PARTS)
        if parts:
            watched.setToolTip(tip(**parts))
        return False

    @Slot()
    def refresh_action(self) -> None:
        """Rebuild the hovered action's tooltip."""
        action = self.sender()
        action.setToolTip(tip(**action.property(_PARTS)))


_refresher: Optional[_TipRefresh] = None


def _refresh() -> _TipRefresh:
    """Return the one refresher, made on first use in the GUI thread.

    Not at import: a module imported on a worker thread would leave the
    filter living there, and Qt calls a filter only in its own thread.
    """
    global _refresher
    if _refresher is None or not is_valid(_refresher):
        _refresher = _TipRefresh()
        application = QApplication.instance()
        if application is not None:
            _refresher.moveToThread(application.thread())
            _refresher.setParent(application)
    return _refresher


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
    *,
    facts: Iterable[Tuple[str, Optional[str]]] = (),
    code: str = "",
    hint: str = "",
) -> None:
    """Set a rich tooltip on `target`, plus a markup-free status tip.

    The tooltip is rebuilt each time it shows, in the theme in force.

    Args:
        target: A widget, an action, or an item already in its list, tree
            or table widget; a tree item gets the tip on every column.
        title: What the control is, in a couple of words.
        body: What the control does. Defaults to `""`.
        shortcut: A Qt key sequence, such as `"Ctrl+S"`. Defaults to `""`.
        facts: (label, value) pairs, drawn as a table; a pair with no
            value is left out. Defaults to `()`.
        code: A path, a key or a command, in the mono face. Defaults to
            `""`.
        hint: A closing line, dimmed. Defaults to `""`.

    Raises:
        ValueError: `target` is an item not yet added to a view.

    Examples:
        >>> apply_tip(
        ...     button,
        ...     "Save",
        ...     "Write the scene to disk",
        ...     "Ctrl+S",
        ... )
        >>> apply_tip(
        ...     item,
        ...     "livetest v001",
        ...     facts=[("Product", "render/livetest"), ("Files", "8")],
        ...     code=path,
        ...     hint="Double-click to play the preview",
        ... )

    Note:
        The status tip carries the title and body without markup. Qt shows
        it in the window's status bar on hover, which is where a person
        looks for "what is this" before a tooltip has had time to appear.
        The title becomes the accessible name, and the body, facts, code
        and hint the accessible description, one per line in plain words; a
        later call replaces them, but never a name set by hand.
    """

    # Lists and strings only: the parts cross a QVariant and come back.
    parts = {
        "title": title,
        "body": body,
        "shortcut": shortcut,
        "facts": _kept(facts),
        "code": code,
        "hint": hint,
    }
    html = tip(**parts)
    plain = " - ".join(part for part in (title, body) if part)
    described = "\n".join(
        line
        for line in (
            body,
            *(
                f"{label}: {value}" if label else value
                for label, value in parts["facts"]
            ),
            code,
            hint,
        )
        if line
    )

    if isinstance(target, (QTreeWidgetItem, QListWidgetItem, QTableWidgetItem)):
        _view_of(target).viewport().installEventFilter(_refresh())
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
            target.hovered.connect(_refresh().refresh_action)
    elif isinstance(target, QWidget):
        target.installEventFilter(_refresh())
    if hasattr(target, "setProperty"):
        target.setProperty(_PARTS, parts)

    target.setToolTip(html)
    if hasattr(target, "setStatusTip"):
        target.setStatusTip(plain)

    # A screen reader reads the accessible name, never the HTML tooltip.
    if not hasattr(target, "setAccessibleName"):
        return
    spoken: list[str] = list(target.property(_SPOKEN) or ("", ""))
    if target.accessibleName() in ("", spoken[0]):
        target.setAccessibleName(title)
        spoken[0] = title
    if target.accessibleDescription() in ("", spoken[1]):
        target.setAccessibleDescription(described)
        spoken[1] = described
    target.setProperty(_SPOKEN, spoken)
