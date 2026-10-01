"""FXMainWindow's side effects on the application and its parent."""

# Built-in
import inspect

# Third-party
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import FXMainWindow, _main_window


def test_the_window_installs_no_tooltip_manager():
    assert "Tooltip" not in inspect.getsource(_main_window)


def test_close_keeps_parent(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    window = FXMainWindow(parent=parent, title="probe")

    window.close()

    assert window.parent() is parent


def test_main_window_live_updates_on_theme_switch(qtbot):
    """Every window is a themed root and follows apply_theme."""
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
