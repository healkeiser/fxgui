"""Tests for `fxgui.fxicons` icon-mode behavior.

The QApplication, headless platform, and cleanup are handled by pytest-qt's
`qapp`/`qtbot` fixtures (see conftest.py). Run with: ``pytest``.

Icons carry per-state pixmaps:
- Disabled  -> grayed (everywhere)
- Selected  -> accent color (selected item rows)
- Active    -> accent color (hovered rows, highlighted menu items)

Qt also renders a *focused button*'s icon in Active mode, but buttons have no
accent background, so `set_icon` strips Active for button widgets only.
"""

from qtpy.QtGui import QIcon
from qtpy.QtCore import QSize
from qtpy.QtWidgets import QPushButton, QToolButton, QAction

from fxgui import fxicons

_SIZE = QSize(48, 48)


def _img(icon: QIcon, mode):
    return icon.pixmap(_SIZE, mode).toImage()


def _active_matches_normal(icon: QIcon) -> bool:
    return _img(icon, QIcon.Active) == _img(icon, QIcon.Normal)


def test_get_icon_has_per_state_colors(qapp):
    """A bare get_icon() carries distinct Disabled / Selected / Active pixmaps
    so menus and item views recolor their icons on a highlight background."""
    icon = fxicons.get_icon("check", width=48, height=48)
    normal = _img(icon, QIcon.Normal)
    assert _img(icon, QIcon.Disabled) != normal
    assert _img(icon, QIcon.Selected) != normal
    assert _img(icon, QIcon.Active) != normal


def test_include_active_false_drops_active(qapp):
    """include_active=False yields a button-safe icon (Active == Normal)."""
    icon = fxicons.get_icon("check", width=48, height=48, include_active=False)
    assert _active_matches_normal(icon)


def test_button_icon_drops_active_recolor(qtbot):
    """Regression: a focused QPushButton renders its icon in Active mode, so
    set_icon must strip Active for buttons or the icon recolors on focus."""
    button = QPushButton("Save")
    qtbot.addWidget(button)
    fxicons.set_icon(button, "check", width=48, height=48)

    button.show()
    qtbot.waitExposed(button)
    button.setFocus()

    icon = button.icon()
    assert not icon.isNull()
    assert _active_matches_normal(icon)


def test_toolbutton_icon_drops_active_recolor(qtbot):
    """QToolButton hover also triggers Active mode; it must be stripped too."""
    button = QToolButton()
    qtbot.addWidget(button)
    fxicons.set_icon(button, "check", width=48, height=48)
    assert _active_matches_normal(button.icon())


def test_menu_action_keeps_active_recolor(qapp):
    """A QAction (menu item) is not a button: its highlighted icon must keep
    the accent recolor so it stays readable on the accent background."""
    action = QAction("Open")
    fxicons.set_icon(action, "check", width=48, height=48)
    assert not _active_matches_normal(action.icon())
