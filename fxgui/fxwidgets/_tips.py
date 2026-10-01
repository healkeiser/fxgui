"""Rich tooltips built on Qt's own `setToolTip`, and the keycap widget.

This is the everyday path for tooltips in fxgui. A bare
``setToolTip("Refresh")`` restates the label and teaches nothing; a useful
tooltip answers three things at once, what the control is, what it does to
the user's data, and how to reach it without the mouse. Every string goes
through `tip`, so no call site invents its own layout and the wording stays
consistent: title in the primary text, body dimmed, shortcut on the right as
a keycap.

Reach for `FXTooltip` instead when native tooltips cannot do the job: hosting
live widgets (images, action buttons), staying up while the pointer is over
the tooltip itself, or arrow-anchored placement. Everything else belongs here.

The HTML names palette roles, never a colour. Qt reads them from the
application's palette when the tooltip shows, so a tip set in one theme
shows in the theme of the moment. Rich text draws no rounded background:
the keycap in a tooltip is square; `FXKeycap`, the widget, is round.

Qt ignores `max-width`, and applies a table `width` as a fixed width, so
there is no width cap: the tooltip popup word-wraps itself, up to 440px.
"""

# Built-in
from html import escape
from typing import Optional

# Third-party
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QLabel, QWidget

# Internal
from fxgui import fxstyle


# One step down from the 12px body text set by the global stylesheet.
KEYCAP_FONT_SIZE = 11

# Palette roles the tooltip HTML reads when it shows: the theme's under an
# FXApplication, the host's inside a DCC, where the host draws the box.
_MUTED = "palette(placeholder-text)"
_KEY_FILL = "palette(button)"

fxstyle.register_widget_style(
    f"""
    FXKeycap {{
        background: @state_hover;
        color: @text_muted;
        border: 1px solid @border;
        border-radius: @button_radius;
        padding: 1px 5px;
        font-family: @font_mono;
        font-size: {KEYCAP_FONT_SIZE}px;
    }}
    """
)


def _pretty(keys: str) -> str:
    """Return `keys` in the platform's own words, or as given."""
    return QKeySequence(keys).toString(QKeySequence.NativeText) or keys


def keycap(keys: str) -> str:
    """Render one keyboard shortcut as a key, in rich text.

    Args:
        keys: A Qt key sequence, such as `"Ctrl+S"`, `"F5"` or
            `"Ctrl+Shift+E"`.

    Returns:
        str: HTML for the keycap, or an empty string when `keys` is empty.

    Examples:
        >>> button.setToolTip(f"Save {keycap('Ctrl+S')}")

    Note:
        Rich text in a label reads the palette once, when it is set; a
        keycap on a window is an `FXKeycap`.
    """

    if not keys:
        return ""
    return (
        f'<span style="background:{_KEY_FILL}; color:{_MUTED};'
        f" font-size:{KEYCAP_FONT_SIZE}px;"
        f' font-family:monospace;">&nbsp;{escape(_pretty(keys))}&nbsp;'
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

    head = f"<b>{escape(title)}</b>" if title else ""

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
        rows.append(f'<span style="color:{_MUTED};">{escape(body)}</span>')

    blocks = f"<div>{rows[0]}</div>"
    for row in rows[1:]:
        blocks += f'<div style="margin-top:3px;">{row}</div>'
    return blocks


class FXKeycap(QLabel):
    """One keyboard shortcut drawn as a key, round at the button radius.

    Its look is a registered rule, so it follows every theme switch.

    Examples:
        >>> row.addWidget(FXKeycap("Ctrl+S"))
    """

    def __init__(self, keys: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setText(keys)

    def setText(self, keys: str) -> None:
        """Show `keys` in the platform's own words, as `keycap` does."""
        super().setText(_pretty(keys) if keys else "")


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

    widget.setToolTip(tip(title, body, shortcut))

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
