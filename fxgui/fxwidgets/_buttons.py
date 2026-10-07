"""Buttons with a role beyond Qt's own, and a pill that joins them."""

# Built-in
from typing import Optional, Union

# Third-party
from qtpy.QtCore import QEvent, QObject, QSize
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._tips import apply_tip


class FXPrimaryButton(QPushButton):
    """The main action of a form, drawn on the theme's accent.

    The look lives in the theme stylesheet under
    ``QPushButton[fxRole="primary"]``, so any QPushButton given that
    property matches it too.

    Args:
        text: The button's label, or its parent as with QPushButton.
        parent: Parent widget.
        icon: A material icon name, drawn in the on-accent icon colour.

    Examples:
        >>> post = FXPrimaryButton("Post", form, icon="send")
    """

    def __init__(
        self,
        text: Union[str, QWidget, None] = "",
        parent: Optional[QWidget] = None,
        *,
        icon: Optional[str] = None,
    ):
        if isinstance(text, QWidget):
            text, parent = "", text
        super().__init__(text or "", parent)
        self._icons = {}
        self.pressed.connect(self._show_icon)
        self.released.connect(self._show_icon)
        if icon:
            self.set_icon_name(icon)
        self.setProperty("fxRole", "primary")

    def set_icon_name(self, icon: str) -> None:
        """Draw the material icon `icon` in the on-accent icon colour."""
        # Qt draws a hovered push button's icon in Normal mode, so the
        # hover fill's ink is a second icon swapped in; each resolves its
        # token when drawn.
        self._icons = {
            hovered: fxicons.get_icon(icon, color=ink)
            for hovered, ink in (
                (False, "icon_on_accent_primary"),
                (True, "icon_on_accent_secondary"),
            )
        }
        self._show_icon()

    def enterEvent(self, event) -> None:
        """Draw the icon in the hover fill's ink."""
        super().enterEvent(event)
        self._show_icon()

    def leaveEvent(self, event) -> None:
        """Draw the icon in the resting fill's ink."""
        super().leaveEvent(event)
        self._show_icon()

    def _show_icon(self) -> None:
        if self._icons:
            self.setIcon(self._icons[self.underMouse() and not self.isDown()])


fxstyle.register_widget_style("""
FXIconButton {
    background-color: transparent;
    border: 1px solid transparent;
    margin: 0px;
    padding: 0px;
}
FXIconButton:hover {
    background-color: @state_hover;
    border: 1px solid transparent;
}
FXIconButton:pressed {
    background-color: @state_pressed;
    border: 1px solid transparent;
}
FXIconButton:checked {
    background-color: @primary_button;
    border: 1px solid @primary_button;
}
FXIconButton:checked:hover {
    background-color: @primary_button_hover;
    border: 1px solid @primary_button_hover;
}
FXIconButton:checked:pressed {
    background-color: @primary_button_pressed;
    border: 1px solid @primary_button_pressed;
}
FXIconButton[fxFocusVisible="true"]:focus {
    border: 1px solid @accent_primary;
}
FXIconButton[fxFocusVisible="true"]:checked:focus {
    border: 1px solid @text;
}
""")

# The radius follows the side, so every size gets its rule at import: one
# registered later would re-sheet every root. Under half the side, since Qt
# draws square corners for exactly half.
# ponytail: a side outside this range takes the nearest end's radius.
_SIZES = range(8, 97)
fxstyle.register_widget_style("".join(
    f'FXIconButton[fxSize="{side}"] {{ border-radius: {side // 2 - 1}px; }}\n'
    for side in _SIZES
))


class FXIconButton(QToolButton):
    """A round, flat icon button, filled with the accent when checked.

    Args:
        icon: A material icon name.
        parent: Parent widget.
        tip: The tooltip, set through `apply_tip`.
        checkable: Whether a click toggles the button.
        checked_icon: The icon shown while checked. Defaults to `icon`.
        size: The circle's diameter, in logical pixels. Defaults to a
            push button's height.

    Examples:
        >>> eye = FXIconButton("visibility_off", bar, tip="Show to client",
        ...                    checkable=True, checked_icon="visibility")
    """

    def __init__(
        self,
        icon: str,
        parent: Optional[QWidget] = None,
        *,
        tip: str = "",
        checkable: bool = False,
        checked_icon: Optional[str] = None,
        size: Optional[int] = None,
    ):
        super().__init__(parent)
        size = size or fxstyle.control_height(self)
        self.setAutoRaise(True)
        self.setCheckable(checkable)
        self.setFixedSize(size, size)
        glyph = round(size * 0.57)
        self.setIconSize(QSize(glyph, glyph))
        self.setProperty("fxSize", min(max(size, _SIZES[0]), _SIZES[-1]))
        if tip:
            apply_tip(self, tip)
        # Active is a hovered tool button: checked, on primary_button_hover,
        # it takes the secondary ink.
        self._icons = {
            False: fxicons.get_icon(icon),
            True: fxicons.get_icon(
                checked_icon or icon, color="icon_on_accent_primary",
                inks={"active": "icon_on_accent_secondary"}),
        }
        self.toggled.connect(self._show_icon)
        self._show_icon(self.isChecked())

    def _show_icon(self, checked: bool) -> None:
        self.setIcon(self._icons[checked])


_STATES = ("", ":hover", ":focus", ":pressed", ":on", ":disabled")


def _each_state(selectors: str, body: str) -> str:
    """Return one QSS rule for `selectors` in every state a child can be in."""
    names = [s.strip() for s in selectors.split(",")]
    joined = ",\n".join(name + state for name in names for state in _STATES)
    return f"{joined} {{ {body} }}\n"


# Children lose their own border in every state, or the theme's :hover and
# :focus rules would draw one inside the outline.
# The end children sit 1 px inside the frame, so their radius is 1 px less.
_R = fxstyle.BUTTON_RADIUS - 1
fxstyle.register_widget_style(
    """
FXJoinedGroup {
    border: 1px solid @border_light;
    border-radius: @button_radius;
    background-color: transparent;
    padding: 0px;
}
FXJoinedGroup[fxFocus="true"] {
    border-color: @accent_primary;
}
"""
    + _each_state(
        "FXJoinedGroup > *[fxJoined]", "border: none; border-radius: 0px;")
    + _each_state(
        'FXJoinedGroup > *[fxJoined="middle"], '
        'FXJoinedGroup > *[fxJoined="last"]',
        "border-left: 1px solid @border;",
    )
    + _each_state(
        'FXJoinedGroup > *[fxJoined="first"], '
        'FXJoinedGroup > *[fxJoined="only"]',
        f"border-top-left-radius: {_R}px; border-bottom-left-radius: {_R}px;"
        " padding-left: 12px;",
    )
    + _each_state(
        'FXJoinedGroup > *[fxJoined="last"], '
        'FXJoinedGroup > *[fxJoined="only"]',
        f"border-top-right-radius: {_R}px;"
        f" border-bottom-right-radius: {_R}px; padding-right: 12px;",
    )
    + """
FXJoinedGroup > QComboBox[fxJoined],
FXJoinedGroup > QPushButton[fxJoined],
FXJoinedGroup > QToolButton[fxJoined] {
    background-color: transparent;
}
FXJoinedGroup > *[fxJoined]:hover {
    background-color: @state_hover;
}
FXJoinedGroup > QPushButton[fxJoined]:pressed {
    background-color: @state_pressed;
}
FXJoinedGroup > QPushButton[fxRole="primary"] {
    background-color: @primary_button;
}
FXJoinedGroup > QPushButton[fxRole="primary"]:hover {
    background-color: @primary_button_hover;
}
FXJoinedGroup > QPushButton[fxRole="primary"]:pressed {
    background-color: @primary_button_pressed;
}
FXJoinedGroup > QPushButton[fxRole="primary"]:disabled {
    background-color: @surface_alt;
}
"""
)


class FXJoinedGroup(QFrame):
    """Widgets side by side in one button outline, with a divider between.

    A child with keyboard focus lights the whole outline in the accent.

    Args:
        parent: Parent widget.

    Examples:
        >>> group = FXJoinedGroup(composer)
        >>> group.add_widget(status_combo)
        >>> group.add_widget(FXPrimaryButton("Post", group))
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # A shaped frame: the theme hides the border of a NoFrame QFrame.
        self.setFrameShape(QFrame.StyledPanel)
        # The outline is a push button's height; the children sit inside it.
        self.setFixedHeight(fxstyle.control_height(self))
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setProperty("fxFocus", "false")
        layout = QHBoxLayout(self)
        # The frame's own 1px width already insets the children.
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        QApplication.instance().focusChanged.connect(self._on_focus_changed)
        # Asked once now, so the focus watch runs before a child's focus.
        fxstyle.focus_visible(self)

    def add_widget(self, widget: QWidget) -> None:
        """Append `widget` at the right end of the group."""
        widget.setParent(self)
        widget.setFixedHeight(self.height() - 2)
        self.layout().addWidget(widget)
        widget.installEventFilter(self)
        self._place_children()

    def _place_children(self) -> None:
        # Only shown children count: a hidden one must not keep the round
        # end or leave a divider on the first one showing.
        layout = self.layout()
        children = (layout.itemAt(i).widget() for i in range(layout.count()))
        shown = [w for w in children if w is not None and not w.isHidden()]
        last = len(shown) - 1
        for index, child in enumerate(shown):
            if last == 0:
                place = "only"
            elif index == 0:
                place = "first"
            elif index == last:
                place = "last"
            else:
                place = "middle"
            if child.property("fxJoined") != place:
                child.setProperty("fxJoined", place)
                fxutils.repolish(child)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Re-place the children when one is shown or hidden."""
        if event.type() in (QEvent.ShowToParent, QEvent.HideToParent):
            self._place_children()
        return super().eventFilter(watched, event)

    def event(self, event: QEvent) -> bool:
        """Re-place the children when one is deleted or moved elsewhere."""
        # The layout has already dropped the child: Qt tells it first.
        if event.type() == QEvent.ChildRemoved:
            self._place_children()
        return super().event(event)

    def _on_focus_changed(self, _old, new) -> None:
        inside = (
            new is not None
            and self.isAncestorOf(new)
            and fxstyle.focus_visible(new)
        )
        if (self.property("fxFocus") == "true") != inside:
            self.setProperty("fxFocus", "true" if inside else "false")
            fxutils.repolish(self)
