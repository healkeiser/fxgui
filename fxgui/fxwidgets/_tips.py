"""Rich tooltips built on Qt's own `setToolTip`.

This is the everyday path for tooltips in fxgui. A bare
``setToolTip("Refresh")`` restates the label and teaches nothing; a useful
tooltip answers three things at once, what the control is, what it does to
the user's data, and how to reach it without the mouse. Every string goes
through `tip`, so no call site invents its own layout and the wording stays
consistent: title in the theme's primary text, body dimmed, shortcut on the
right as a keycap.

Reach for `FXTooltip` instead when native tooltips cannot do the job: hosting
live widgets (images, action buttons), staying up while the pointer is over
the tooltip itself, or arrow-anchored placement. Everything else belongs here.

Qt renders a tooltip through `QTextDocument`, which supports a small subset
of HTML: `b`, `span style` (color, background, font), `br` and tables. It has
no flexbox, no `gap`, and it ignores `border-radius` on inline spans, which is
why the keycap is a background-tinted span inside a table cell rather than a
rounded pill. The keycap sits in a right-aligned cell of a full-width table
because that is the only way Qt's rich text will push part of a line to the
right edge.

There is deliberately no width cap here. Qt ignores `max-width`, and the one
width it does honour, a table `width` attribute, it applies as a fixed width
rather than a maximum, which puts a short tooltip in an oversized box. It is
not needed either: the tooltip popup word-wraps itself, measured at 192px for
a short body, 224px for a full sentence, and saturating at 440px however long
the body gets, so a tooltip never stretches across a monitor on its own.

Rich text takes only literal colours, so `tip` and `keycap` write those of
the theme in force when called. `apply_tip` builds the tooltip again each
time it shows, so a widget's tooltip follows a switch. The surface they land
on is styled by the `QToolTip` rule in `qss/style.qss`, from the same tokens.
"""

# Built-in
from html import escape

# Third-party
from qtpy.QtCore import QEvent, QObject
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QToolTip, QWidget

# Internal
from fxgui import fxstyle


# One step down from the 12px body text set by the global stylesheet.
KEYCAP_FONT_SIZE = 11


def keycap(keys: str) -> str:
    """Render one keyboard shortcut as a key.

    Args:
        keys: A Qt key sequence, such as `"Ctrl+S"`, `"F5"` or
            `"Ctrl+Shift+E"`.

    Returns:
        str: HTML for the keycap, or an empty string when `keys` is empty.

    Examples:
        >>> button.setToolTip(f"Save {keycap('Ctrl+S')}")

    Note:
        The sequence is run through `QKeySequence` so a Mac shows the
        platform glyphs rather than the literal "Ctrl". Sequences Qt cannot
        parse fall back to the raw string.
    """

    if not keys:
        return ""

    colors = fxstyle.get_theme_colors()
    pretty = QKeySequence(keys).toString(QKeySequence.NativeText)
    return (
        f'<span style="background:{colors["state_hover"]};'
        f' color:{colors["text_muted"]};'
        f" font-size:{KEYCAP_FONT_SIZE}px;"
        f' font-family:monospace;">&nbsp;{escape(pretty or keys)}&nbsp;'
        "</span>"
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
        Every caller string is HTML-escaped, so a path or a name holding
        `&` or `<` reaches the user as text instead of corrupting the markup.
    """

    if not (title or body or shortcut):
        return ""

    colors = fxstyle.get_theme_colors()
    head = ""
    if title:
        head = (
            f'<span style="color:{colors["text"]};">'
            f"<b>{escape(title)}</b></span>"
        )

    rows = []
    if shortcut:
        # A spacer cell pushes the keycap to the right edge; Qt rich text
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
        rows.append(
            f'<span style="color:{colors["text_muted"]};">'
            f"{escape(body)}</span>"
        )

    blocks = f"<div>{rows[0]}</div>"
    for row in rows[1:]:
        blocks += f'<div style="margin-top:3px;">{row}</div>'
    return blocks


class _ShownTip(QObject):
    """Show its widget's `apply_tip` tooltip built in the theme of the moment."""

    NAME = "fxShownTip"

    def __init__(self, widget: QWidget):
        super().__init__(widget)
        self.setObjectName(self.NAME)
        self.parts = ("", "", "")
        self.html = ""
        widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Show the tip as `tip` builds it now, unless it was replaced."""
        if (
            event.type() == QEvent.ToolTip
            and self.html
            and watched.toolTip() == self.html
        ):
            QToolTip.showText(event.globalPos(), tip(*self.parts), watched)
            return True
        return False


def apply_tip(
    widget: QWidget,
    title: str,
    body: str = "",
    shortcut: str = "",
) -> None:
    """Set a rich tooltip on `widget`, plus a markup-free status tip.

    Args:
        widget: The widget to annotate.
        title: What the control is, in a couple of words.
        body: What the control does. Defaults to `""`.
        shortcut: A Qt key sequence, such as `"Ctrl+S"`. Defaults to `""`.

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
        "what is this" before a tooltip has had time to appear. Widgets
        without `setStatusTip` only get the tooltip.
    """

    html = tip(title, body, shortcut)
    widget.setToolTip(html)
    if isinstance(widget, QWidget):
        shown = widget.findChild(_ShownTip, _ShownTip.NAME)
        if shown is None:
            shown = _ShownTip(widget)
        shown.parts = (title, body, shortcut)
        shown.html = html

    plain = f"{title} - {body}" if body else title
    if hasattr(widget, "setStatusTip"):
        widget.setStatusTip(plain)

    # A screen reader reads the accessible name, never the HTML tooltip.
    if title and hasattr(widget, "setAccessibleName") and not (
        widget.accessibleName()
    ):
        widget.setAccessibleName(title)
    if body and hasattr(widget, "setAccessibleDescription") and not (
        widget.accessibleDescription()
    ):
        widget.setAccessibleDescription(body)
