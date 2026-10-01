"""A screen-region grab hands back a pixmap or nothing, brings the window
back, and never quits the application."""

# Third-party
from qtpy.QtCore import QCoreApplication, QEvent, QPoint, Qt, QTimer
from qtpy.QtGui import QKeyEvent, QMouseEvent
from qtpy.QtWidgets import QApplication, QWidget

# Internal
from fxgui.fxwidgets import _screen_grab, grab_screen_region


SETTLE = _screen_grab.HIDE_SETTLE_MS


def _send_to_the_overlay(window, event):
    for widget in QApplication.topLevelWidgets():
        if widget is not window and widget.isVisible():
            QApplication.sendEvent(widget, event)
            return
    raise AssertionError("no overlay was showing to receive the event")


def _press_escape(window):
    _send_to_the_overlay(
        window, QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    )


def _shown(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    return window


def test_escape_cancels_the_grab_and_restores_the_window(qtbot):
    window = _shown(qtbot)
    QTimer.singleShot(SETTLE + 50, lambda: _press_escape(window))

    assert grab_screen_region(window) is None
    assert window.isVisible()


def test_a_completed_drag_returns_a_pixmap_and_restores_the_window(qtbot):
    window = _shown(qtbot)

    def drag():
        for kind, at, buttons in (
            (QEvent.MouseButtonPress, QPoint(10, 10), Qt.LeftButton),
            (QEvent.MouseButtonRelease, QPoint(50, 50), Qt.NoButton),
        ):
            _send_to_the_overlay(window, QMouseEvent(
                kind, at, at, Qt.LeftButton, buttons, Qt.NoModifier
            ))

    QTimer.singleShot(SETTLE + 50, drag)

    picked = grab_screen_region(window)

    assert picked is not None and not picked.isNull()
    assert window.isVisible()


def test_the_screen_is_read_only_once_the_hide_has_settled(
    qtbot, monkeypatch
):
    window = _shown(qtbot)
    waits = []
    real = _screen_grab._wait

    def spy(milliseconds):
        waits.append((milliseconds, window.isVisible()))
        real(milliseconds)

    monkeypatch.setattr(_screen_grab, "_wait", spy)
    QTimer.singleShot(SETTLE + 50, lambda: _press_escape(window))

    grab_screen_region(window)

    assert waits == [(SETTLE, False)]


def test_the_grab_never_quits_a_running_app(qtbot):
    app = QApplication.instance()
    assert app.quitOnLastWindowClosed(), "the default this test rests on"
    window = _shown(qtbot)
    state = {"survived": False, "flag_after": None}
    timers = []

    def later(milliseconds, call):
        timer = QTimer(window)
        timer.setSingleShot(True)
        timer.timeout.connect(call)
        timer.start(milliseconds)
        timers.append(timer)

    def survived():
        state["survived"] = True
        app.quit()

    def scenario():
        later(SETTLE + 50, lambda: _press_escape(window))
        grab_screen_region(window)
        state["flag_after"] = QApplication.quitOnLastWindowClosed()
        # Reached only if the grab left the app running.
        later(50, survived)

    later(0, scenario)
    later(10000, app.quit)  # a hang must not strand the suite

    app.exec_()
    for timer in timers:
        timer.stop()
    QCoreApplication.removePostedEvents(app, QEvent.Quit)
    QApplication.setQuitOnLastWindowClosed(False)
    window.close()
    QApplication.processEvents()
    QApplication.setQuitOnLastWindowClosed(True)

    assert state["survived"], "the overlay's close quit the application"
    assert state["flag_after"] is True
