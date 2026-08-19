"""Tests for `fxgui.fxwidgets.FXMainWindow` global side effects.

Regressions:
- Constructing any FXMainWindow used to install FXTooltipManager globally,
  hijacking the host application's tooltips when embedded in a DCC.
- closeEvent used to call setParent(None), breaking parent-managed lifetime.
"""

# Third-party
from qtpy.QtWidgets import QApplication, QWidget

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


def test_no_tooltip_hijack_under_fxapplication():
    """The manager used to auto-install whenever fxgui owned the application,
    which made native tooltips unreachable in the commonest fxgui app.

    Only one QApplication may exist per process and pytest-qt owns it, so the
    FXApplication branch cannot be entered from a test. Assert instead that
    the branch is gone: nothing in the constructor may decide to install the
    manager by inspecting the application class.
    """
    import inspect

    from fxgui.fxwidgets import _main_window

    source = inspect.getsource(_main_window.FXMainWindow.__init__)

    assert "FXTooltipManager.install()" in source
    # The old branch imported FXApplication to sniff the running app.
    assert "import FXApplication" not in source
    assert "rich_tooltips is None" not in source


def test_rich_tooltips_false_is_still_off(qtbot):
    window = FXMainWindow(title="probe", rich_tooltips=False)
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
