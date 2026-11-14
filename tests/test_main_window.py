"""FXMainWindow's side effects on the application and its parent."""

# Built-in

# Third-party

# Internal


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


def _host_with_embedded(qtbot):
    from qtpy.QtWidgets import QLineEdit, QVBoxLayout, QWidget

    from fxgui.fxwidgets import FXMainWindow

    host = QWidget()
    qtbot.addWidget(host)
    elsewhere = QLineEdit(host)
    # A layout strips the window flag a main window is made with.
    embedded = FXMainWindow()
    embedded.setCentralWidget(QLineEdit())
    layout = QVBoxLayout(host)
    layout.addWidget(elsewhere)
    layout.addWidget(embedded)
    host.show()
    qtbot.waitExposed(host)
    with qtbot.waitActive(host):
        host.activateWindow()
    elsewhere.setFocus()
    assert elsewhere.hasFocus()
    return host, elsewhere, embedded


def test_an_embedded_window_s_shortcuts_stay_out_of_the_host(qtbot):
    from qtpy.QtCore import Qt
    from qtpy.QtTest import QTest

    _host, elsewhere, embedded = _host_with_embedded(qtbot)
    closed = []
    embedded.close_action.triggered.connect(lambda: closed.append(True))

    QTest.keyClick(elsewhere, Qt.Key_Q, Qt.ControlModifier | Qt.AltModifier)
    assert closed == []

    inside = embedded.centralWidget()
    inside.setFocus()
    QTest.keyClick(inside, Qt.Key_Q, Qt.ControlModifier | Qt.AltModifier)
    assert closed == [True]


def test_a_window_moved_into_a_host_scopes_its_shortcuts(qtbot):
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QWidget

    from fxgui.fxwidgets import FXMainWindow

    window = FXMainWindow()
    qtbot.addWidget(window)
    assert window.close_action.shortcutContext() == Qt.WindowShortcut
    host = QWidget()
    qtbot.addWidget(host)

    window.setParent(host)

    assert window.close_action.shortcutContext() == Qt.WidgetWithChildrenShortcut


def test_a_scoped_action_stays_out_of_the_host(qtbot):
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QAction
    from qtpy.QtTest import QTest

    _host, elsewhere, embedded = _host_with_embedded(qtbot)
    action = QAction("Run", embedded)
    action.setShortcut("Ctrl+Alt+K")
    ran = []
    action.triggered.connect(lambda: ran.append(True))
    embedded.scope_shortcut(action)

    QTest.keyClick(elsewhere, Qt.Key_K, Qt.ControlModifier | Qt.AltModifier)
    assert ran == []

    inside = embedded.centralWidget()
    inside.setFocus()
    QTest.keyClick(inside, Qt.Key_K, Qt.ControlModifier | Qt.AltModifier)
    assert ran == [True]


def test_a_scoped_shortcut_follows_the_window_into_a_host(qtbot):
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QAction, QKeySequence, QShortcut
    from qtpy.QtWidgets import QWidget

    from fxgui.fxwidgets import FXMainWindow

    window = FXMainWindow()
    qtbot.addWidget(window)
    action = QAction("Run", window)
    shortcut = QShortcut(QKeySequence("Ctrl+J"), window)
    window.scope_shortcut(action)
    window.scope_shortcut(shortcut)
    assert action.shortcutContext() == Qt.WindowShortcut
    host = QWidget()
    qtbot.addWidget(host)

    window.setParent(host)

    assert action.shortcutContext() == Qt.WidgetWithChildrenShortcut
    assert shortcut.context() == Qt.WidgetWithChildrenShortcut


def test_a_deleted_scoped_action_is_skipped(qtbot):
    from qtpy.QtCore import QEvent, Qt
    from qtpy.QtGui import QAction
    from qtpy.QtWidgets import QApplication, QWidget

    from fxgui.fxwidgets import FXMainWindow

    window = FXMainWindow()
    qtbot.addWidget(window)
    action = QAction("Run", window)
    window.scope_shortcut(action)
    action.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    host = QWidget()
    qtbot.addWidget(host)

    window.setParent(host)

    # The reparent went through the scoped list, dead action and all.
    assert window.close_action.shortcutContext() == Qt.WidgetWithChildrenShortcut
