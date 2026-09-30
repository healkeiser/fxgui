"""FXSystemTray: a themed menu, a Quit that leaves a host alone."""

# Third-party
from qtpy.QtCore import QPoint, QSize
from qtpy.QtWidgets import QApplication, QSystemTrayIcon

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXSystemTray


def test_the_menu_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    tray = FXSystemTray()

    fxstyle.apply_theme("github_light")

    assert tray.tray_menu.styleSheet() == fxstyle.build_stylesheet()


def test_quit_leaves_a_host_application_running(qtbot, monkeypatch):
    quits = []
    monkeypatch.setattr(QApplication, "quit", lambda *args: quits.append(1))
    tray = FXSystemTray()

    tray.quit_action.trigger()

    assert quits == []


def _int_point(x, y):
    # PyQt refuses a float coordinate; PySide truncates it quietly.
    assert isinstance(x, int) and isinstance(y, int), (x, y)
    return QPoint(x, y)


def test_the_menu_opens_at_a_whole_pixel(qtbot, monkeypatch):
    from fxgui.fxwidgets import _system_tray

    monkeypatch.setattr(_system_tray, "QPoint", _int_point)
    tray = FXSystemTray()
    opened = []
    monkeypatch.setattr(tray.tray_menu, "exec_", opened.append)
    # Odd sizes halve to a float.
    monkeypatch.setattr(tray.tray_menu, "sizeHint", lambda: QSize(101, 51))

    tray._on_tray_icon_activated(QSystemTrayIcon.Trigger)

    assert len(opened) == 1 and isinstance(opened[0], QPoint)
