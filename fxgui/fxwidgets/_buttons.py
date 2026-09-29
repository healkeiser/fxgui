"""Buttons with a role beyond QPushButton's."""

# Built-in
from typing import Optional, Union

# Third-party
from qtpy.QtWidgets import QPushButton, QWidget

# Internal
from fxgui import fxicons, fxstyle


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
