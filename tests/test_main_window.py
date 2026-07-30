"""Tests for `fxgui.fxwidgets.FXMainWindow` global side effects.

Regressions:
- Constructing any FXMainWindow used to install FXTooltipManager globally,
  hijacking the host application's tooltips when embedded in a DCC.
- closeEvent used to call setParent(None), breaking parent-managed lifetime.
"""

# Third-party
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import FXMainWindow
from fxgui.fxwidgets._tooltip import FXTooltipManager


def test_no_tooltip_hijack_under_plain_qapplication(qtbot):
    """pytest-qt's QApplication is not an FXApplication, i.e. the embedded
    (DCC host) situation: the tooltip manager must NOT auto-install."""
    assert not FXTooltipManager.is_installed()
    window = FXMainWindow(title="probe")
    qtbot.addWidget(window)
    assert not FXTooltipManager.is_installed()


def test_rich_tooltips_opt_in(qtbot):
    window = FXMainWindow(title="probe", rich_tooltips=True)
    qtbot.addWidget(window)
    try:
        assert FXTooltipManager.is_installed()
    finally:
        FXTooltipManager.uninstall()
    assert not FXTooltipManager.is_installed()


def test_close_keeps_parent(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    window = FXMainWindow(parent=parent, title="probe")

    window.close()

    assert window.parent() is parent


def test_main_window_live_updates_on_theme_switch(qtbot):
    """set_stylesheet=True windows are themed roots: every window
    follows apply_theme, not just the one that triggered it."""
    from fxgui import fxstyle
    from fxgui.fxwidgets import FXMainWindow

    window_a = FXMainWindow()
    window_b = FXMainWindow()
    qtbot.addWidget(window_a)
    qtbot.addWidget(window_b)

    fxstyle.apply_theme("light")
    sheet_a, sheet_b = window_a.styleSheet(), window_b.styleSheet()
    fxstyle.apply_theme("dark")

    assert window_a.styleSheet() != sheet_a
    assert window_b.styleSheet() != sheet_b
