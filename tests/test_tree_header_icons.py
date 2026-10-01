"""A tree header's icon follows a theme switch with no hook of its own."""

# Third-party
from qtpy.QtCore import QSize
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget

# Internal
from fxgui import fxicons, fxstyle


def _ink(icon) -> str:
    image = icon.pixmap(QSize(32, 32)).toImage()
    for x in range(image.width()):
        for y in range(image.height()):
            colour = image.pixelColor(x, y)
            if colour.alpha() == 255:
                return colour.name().lower()
    return ""


def test_a_header_icon_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setHeaderLabels(["Name"])
    tree.headerItem().setIcon(0, fxicons.get_icon("check"))
    dark = _ink(tree.headerItem().icon(0))

    fxstyle.apply_theme("light")

    light = _ink(tree.headerItem().icon(0))
    assert light == QColor(fxstyle.colors().icon).name().lower()
    assert light != dark
