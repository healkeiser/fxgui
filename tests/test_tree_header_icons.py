"""A tree header's icon follows a theme switch with no hook of its own."""

# Third-party
from qtpy.QtCore import QSize
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget

# Internal
from fxgui import fxicons, fxstyle

from _helpers import first_ink


def test_a_header_icon_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setHeaderLabels(["Name"])
    tree.headerItem().setIcon(0, fxicons.get_icon("check"))
    dark = first_ink(tree.headerItem().icon(0).pixmap(QSize(32, 32)))

    fxstyle.apply_theme("light")

    light = first_ink(tree.headerItem().icon(0).pixmap(QSize(32, 32)))
    assert light == QColor(fxstyle.colors().icon).name().lower()
    assert light != dark
