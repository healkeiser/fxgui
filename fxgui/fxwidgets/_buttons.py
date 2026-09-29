"""Buttons with a role beyond Qt's own, and a pill that joins them."""

# Built-in
from typing import List, Optional, Union

# Third-party
from qtpy.QtCore import QSize
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
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._tips import apply_tip


class FXPrimaryButton(fxstyle.FXThemeAware, QPushButton):
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
        self._on_theme_changed()

    def _on_theme_changed(self) -> None:
        # Not fxicons.set_icon: its refresh recolours to the plain icon
        # colour, which vanishes on the accent in most themes.
        if self._icon_name:
            self.setIcon(
                fxicons.get_icon(
                    self._icon_name,
                    color=fxstyle.get_icon_on_accent_primary(),
                    include_active=False,
                )
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


class FXIconButton(fxstyle.FXThemeAware, QToolButton):
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

    def _on_theme_changed(self) -> None:
        # Not fxicons.set_icon: a tool button's Active pixmap is drawn for
        # the accent, and this one hovers on state_hover.
        side = self.iconSize().width()
        icon = QIcon(
            fxicons.get_icon(
                self._icon_name, side, side, include_active=False)
        )
        icon.addPixmap(
            fxicons.get_pixmap(
                self._checked_icon_name,
                side,
                side,
                color=fxstyle.get_icon_on_accent_primary(),
            ),
            QIcon.Normal,
            QIcon.On,
        )
        self.setIcon(icon)


_JOINED_HEIGHT = 30
_STATES = ("", ":hover", ":focus", ":pressed", ":on", ":disabled")


def _each_state(selectors: str, body: str) -> str:
    """Return one QSS rule for `selectors` in every state a child can be in."""
    names = [s.strip() for s in selectors.split(",")]
    joined = ",\n".join(name + state for name in names for state in _STATES)
    return f"{joined} {{ {body} }}\n"


# Children lose their own border in every state, or the theme's :hover and
# :focus rules would draw one inside the pill.
# Radii under half the height: Qt draws square corners at exactly half.
_R = _JOINED_HEIGHT // 2 - 2
fxstyle.register_widget_style(
    f"""
FXJoinedGroup {{
    border: 1px solid @border_light;
    border-radius: {_JOINED_HEIGHT // 2 - 1}px;
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
    """Widgets side by side in one pill outline, with a divider between.

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
        last = len(self._widgets) - 1
        for index, child in enumerate(self._widgets):
            if last == 0:
                place = "only"
            elif index == 0:
                place = "first"
            elif index == last:
                place = "last"
            else:
                place = "middle"
            child.setProperty("fxJoined", place)
            fxutils.repolish(child)

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
