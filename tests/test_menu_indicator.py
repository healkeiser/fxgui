"""A menu's check box sits in the icon column, centred on the icons."""

import pytest
from qtpy.QtGui import QColor, QIcon, QPixmap
from qtpy.QtWidgets import QMenu

from fxgui import fxstyle


def _far(a: QColor, b: QColor, step: int = 40) -> bool:
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()),
               abs(a.blue() - b.blue())) > step


def _ink(image, rect) -> list:
    """Return the columns of the first ink run from the left of `rect`."""
    y = rect.center().y()
    paper = image.pixelColor(rect.right() - 2, y)
    rows = range(rect.top() + 2, rect.bottom() - 1)
    run = []
    for x in range(rect.left(), rect.left() + 60):
        if any(_far(image.pixelColor(x, r), paper) for r in rows):
            run.append(x)
        elif run:
            break
    return run


def _centre(run) -> float:
    return (run[0] + run[-1]) / 2


def _menu(qtbot, theme):
    fxstyle.apply_theme(theme)
    menu = QMenu()
    qtbot.addWidget(menu)
    fxstyle.register_themed_root(menu)
    square = QPixmap(16, 16)
    square.fill(QColor("#ff0000"))
    icon = menu.addAction(QIcon(square), "Minimize")
    check = menu.addAction("Browser")
    check.setCheckable(True)
    both = menu.addAction(QIcon(square), "Pinned")
    both.setCheckable(True)
    menu.popup(menu.pos())
    qtbot.waitExposed(menu)
    return menu, icon, check, both


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
@pytest.mark.parametrize("checked", [False, True])
def test_the_check_box_is_centred_on_the_icon_column(qtbot, theme, checked):
    menu, icon, check, _both = _menu(qtbot, theme)
    check.setChecked(checked)
    menu.update()
    qtbot.wait(10)
    image = menu.grab().toImage()
    at_icon = _ink(image, menu.actionGeometry(icon))
    at_check = _ink(image, menu.actionGeometry(check))
    assert at_icon and at_check
    assert abs(_centre(at_icon) - _centre(at_check)) <= 1, (at_icon, at_check)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_checked_icon_action_marks_its_icon_in_place(qtbot, theme):
    """Qt draws the icon instead of the check box, so the icon shows it."""
    menu, icon, _check, both = _menu(qtbot, theme)
    rect = menu.actionGeometry(both)
    off = menu.grab(rect).toImage()
    both.setChecked(True)
    menu.update()
    qtbot.wait(10)
    on = menu.grab(rect).toImage()
    assert on != off
    # Nothing is drawn beside the icon: the mark stays in its column.
    image = menu.grab().toImage()
    at_icon = _ink(image, menu.actionGeometry(icon))
    at_both = _ink(image, rect)
    assert abs(_centre(at_icon) - _centre(at_both)) <= 1, (at_icon, at_both)
