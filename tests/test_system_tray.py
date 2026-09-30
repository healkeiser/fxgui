"""FXSystemTray: a themed menu, a Quit that leaves a host alone."""

# Third-party
from qtpy.QtCore import QPoint
from qtpy.QtWidgets import QApplication, QSystemTrayIcon

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXSystemTray


def test_the_menu_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    tray = FXSystemTray()

    fxstyle.apply_theme("github_light")

    assert tray.tray_menu.styleSheet() == fxstyle.load_stylesheet()


def test_quit_leaves_a_host_application_running(qtbot, monkeypatch):
    quits = []
    monkeypatch.setattr(QApplication, "quit", lambda *args: quits.append(1))
    tray = FXSystemTray()

    tray.quit_action.trigger()

    assert quits == []


def test_a_left_click_opens_the_menu_at_the_cursor(qtbot, monkeypatch):
    from fxgui.fxwidgets import _system_tray

    class _Cursor:
        @staticmethod
        def pos():
            return QPoint(321, 123)

    monkeypatch.setattr(_system_tray, "QCursor", _Cursor)
    tray = FXSystemTray()
    opened = []
    monkeypatch.setattr(tray.tray_menu, "exec_", opened.append)

    tray._on_tray_icon_activated(QSystemTrayIcon.Context)
    assert opened == []
    tray._on_tray_icon_activated(QSystemTrayIcon.Trigger)
    assert opened == [QPoint(321, 123)]
