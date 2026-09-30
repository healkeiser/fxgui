"""Buttons with a role beyond Qt's own, and a pill that joins them."""

# Built-in
from typing import List, Optional, Union

# Third-party
from qtpy.QtCore import QEvent, QObject, QSize, QTimer
from qtpy.QtGui import QIcon
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
from fxgui import _compat, fxicons, fxstyle, fxutils
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
        self._icon_name = icon
        self.setProperty("fxRole", "primary")
        self.pressed.connect(self._on_theme_changed)
        self.released.connect(self._on_theme_changed)
        self._on_theme_changed()
        # The icon is a pixmap baked in the on-accent ink.
        fxstyle.theme_changed.connect(self._on_theme_changed)

    def enterEvent(self, event) -> None:
        """Draw the icon in the hover fill's ink."""
        super().enterEvent(event)
        self._on_theme_changed()

    def leaveEvent(self, event) -> None:
        """Draw the icon in the resting fill's ink."""
        super().leaveEvent(event)
        self._on_theme_changed()

    def _on_theme_changed(self, _theme_name: Optional[str] = None) -> None:
        """Draw the icon in the ink of the current fill."""
        # Not fxicons.set_icon: its refresh recolours to the plain icon
        # colour, which vanishes on the accent in most themes. Qt has no
        # icon mode for a hovered push button, so the ink follows the state.
        if not self._icon_name:
            return
        hovered = self.underMouse() and not self.isDown()
        ink = (
            fxstyle.get_icon_on_accent_secondary()
            if hovered
            else fxstyle.get_icon_on_accent_primary()
        )
        self.setIcon(
            fxicons.get_icon(self._icon_name, color=ink, include_active=False)
        )


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
FXIconButton:focus {
    border: 1px solid @accent_primary;
}
FXIconButton:checked:focus {
    border: 1px solid @text;
}
""")


class FXIconButton(QToolButton):
    """A round, flat icon button, filled with the accent when checked.

    Args:
        icon: A material icon name.
        parent: Parent widget.
        tip: The tooltip, set through `apply_tip`.
        checkable: Whether a click toggles the button.
        checked_icon: The icon shown while checked. Defaults to `icon`.
        size: The circle's diameter, in logical pixels.

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
        size: int = 28,
    ):
        super().__init__(parent)
        self._icon_name = icon
        self._checked_icon_name = checked_icon or icon
        self.setAutoRaise(True)
        self.setCheckable(checkable)
        self.setFixedSize(size, size)
        glyph = round(size * 0.57)
        self.setIconSize(QSize(glyph, glyph))
        # Per instance, since the radius follows the size. Under half the
        # side: Qt draws square corners for a radius of exactly half.
        self.setStyleSheet(
            f"FXIconButton {{ border-radius: {size // 2 - 1}px; }}")
        if tip:
            apply_tip(self, tip)
        self._on_theme_changed()
        # The icon pixmaps are baked in theme inks.
        fxstyle.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, _theme_name: Optional[str] = None) -> None:
        """Render the icon pixmaps in the current theme's inks."""
        # Not fxicons.set_icon: its Active pixmap is drawn for the accent,
        # and unchecked this button hovers on state_hover. Active is how Qt
        # draws a hovered tool button's icon. Rendered at this widget's own
        # ratio, which a second screen may raise.
        side = self.iconSize().width()
        ratio = self.devicePixelRatioF()
        disabled = fxicons._get_disabled_icon_color()
        plain = fxstyle.get_icon_color()
        icon = QIcon()
        for name, state, rest, hover in (
            (self._icon_name, QIcon.Off, plain, plain),
            (self._checked_icon_name, QIcon.On,
             fxstyle.get_icon_on_accent_primary(),
             fxstyle.get_icon_on_accent_secondary()),
        ):
            for mode, ink in (
                (QIcon.Normal, rest),
                (QIcon.Active, hover),
                (QIcon.Disabled, disabled),
            ):
                icon.addPixmap(
                    fxicons.get_pixmap(name, side, side, color=ink, dpr=ratio),
                    mode,
                    state,
                )
        self.setIcon(icon)

    def event(self, event: QEvent) -> bool:
        """Re-render the icon when the widget moves to a denser screen."""
        if event.type() == getattr(QEvent, "DevicePixelRatioChange", None):
            self._on_theme_changed()
        return super().event(event)


_JOINED_HEIGHT = 30
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
    f"""
FXJoinedGroup {{
    border: 1px solid @border_light;
    border-radius: @button_radius;
    background-color: transparent;
    padding: 0px;
}}
FXJoinedGroup[fxFocus="true"] {{
    border-color: @accent_primary;
}}
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
        self.setFixedHeight(_JOINED_HEIGHT)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setProperty("fxFocus", "false")
        layout = QHBoxLayout(self)
        # The frame's own 1px width already insets the children.
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._widgets: List[QWidget] = []
        QApplication.instance().focusChanged.connect(self._on_focus_changed)

    def add_widget(self, widget: QWidget) -> None:
        """Append `widget` at the right end of the group."""
        widget.setParent(self)
        widget.setFixedHeight(_JOINED_HEIGHT - 2)
        self.layout().addWidget(widget)
        self._widgets.append(widget)
        widget.installEventFilter(self)
        self._place_children()

    def _place_children(self) -> None:
        # Only shown children count: a hidden one must not keep the round
        # end or leave a divider on the first one showing.
        if not _compat.is_valid(self):
            return
        self._widgets = [
            w for w in self._widgets
            if _compat.is_valid(w) and w.parent() is self
        ]
        shown = [w for w in self._widgets if not w.isHidden()]
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
        """Forget a child that is deleted or moved to another parent."""
        # Deferred: a deleted child is still half alive while it is removed.
        if event.type() == QEvent.ChildRemoved:
            QTimer.singleShot(0, self._place_children)
        return super().event(event)

    def _on_focus_changed(self, _old, new) -> None:
        inside = new is not None and self.isAncestorOf(new)
        if (self.property("fxFocus") == "true") != inside:
            self.setProperty("fxFocus", "true" if inside else "false")
            fxutils.repolish(self)


def example() -> None:
    import sys
    from qtpy.QtWidgets import QHBoxLayout
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXPrimaryButton Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QHBoxLayout(widget)
    layout.addStretch()
    layout.addWidget(QPushButton("Cancel", widget))
    layout.addWidget(FXPrimaryButton("Post", widget, icon="send"))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
