"""A menu item can wear a pill at its right, in the key-hint column."""

# Third-party
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QMenu

# Internal
from fxgui import fxstyle


def _menu(qtbot, app_root, badge=True):
    menu = QMenu(app_root)
    menu.addAction("Open")
    delete = menu.addAction("Delete version...")
    if badge:
        fxstyle.set_menu_badge(delete, "Admin")
    app_root.show()
    qtbot.waitExposed(app_root)
    menu.ensurePolished()
    menu.resize(menu.sizeHint())
    return menu, delete


def _pill_pixels(menu, action):
    shot = menu.grab().toImage()
    item = menu.actionGeometry(action)
    fill = QColor(str(fxstyle.colors().feedback_warning_background)).name()
    y = item.center().y()
    return [x for x in range(item.left(), item.right())
            if shot.pixelColor(x, y).name() == fill]


def test_a_badged_item_wears_its_pill_at_the_right(qtbot, app_root):
    menu, delete = _menu(qtbot, app_root)

    pixels = _pill_pixels(menu, delete)

    item = menu.actionGeometry(delete)
    assert pixels, "the pill is painted"
    assert min(pixels) > item.center().x(), "at the item's right"
    assert delete.text().split("\t")[0] == "Delete version..."


def test_a_plain_menu_paints_no_pill(qtbot, app_root):
    menu, delete = _menu(qtbot, app_root, badge=False)

    assert _pill_pixels(menu, delete) == []
