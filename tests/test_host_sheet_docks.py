"""A host's stylesheet moves nothing an FXDockArea draws.

A DCC sets bare type rules on its window or application (Houdini's
base.qss: `QToolButton { width; height; margin }`; others pad labels and
size buttons). The base sheet leaves those properties open, so a held
window's dock tabs, title bar, title buttons and pane bodies grew under
them; the host rules pin each one.
"""

# Third-party
import pytest

ads = pytest.importorskip("PySide6QtAds")

from qtpy.QtCore import QPoint, QRect, Qt  # noqa: E402
from qtpy.QtGui import QColor  # noqa: E402
from qtpy.QtTest import QTest  # noqa: E402
from qtpy.QtWidgets import (  # noqa: E402
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxdocking, fxstyle  # noqa: E402
from fxgui.fxwidgets import FXMainWindow  # noqa: E402
from _helpers import inks  # noqa: E402

# Houdini 21's base.qss rules the base sheet leaves open, and the kind of
# bare rule other hosts set: sizes, margins and padding on a type.
_HOST_SHEET = (
    "QToolButton { width: 17px; height: 17px; margin: 1px; padding: 0px; }"
    " QPushButton { min-height: 30px; margin: 2px; padding: 5px 12px; }"
    " QLabel { margin: 3px; padding: 2px; color: #ff0000; }"
    " QAbstractItemView { margin: 2px; padding: 1px; }"
    " QTabBar::tab { height: 30px; padding: 4px 20px; }"
    " QMenuBar { border: 1px solid black; padding: 0px 1px; }"
)


def _window(qtbot, parent=None):
    window = FXMainWindow(title="Panes", framed=True)
    docks = fxdocking.FXDockArea()
    window.setCentralWidget(docks)
    docks.set_central(QLabel("centre"))
    tree = QTreeWidget()
    for name in ("sh0010", "sh0020"):
        QTreeWidgetItem(tree, [name])
    fxstyle.mark_flush(tree)
    docks.add_dock("targets", "Targets", tree, "left")
    body = QWidget()
    column = QVBoxLayout(body)
    column.addWidget(QLabel("Checks"))
    column.addWidget(QPushButton("Run"))
    docks.add_dock("checks", "Checks", body, "bottom")
    docks.add_dock("runs", "Runs", QLabel("runs"), "bottom")
    if parent is not None:
        window.setParent(parent, window.windowFlags())
    else:
        qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    window.resize(900, 600)
    window.show()
    qtbot.waitExposed(window)
    for _ in range(3):
        QApplication.processEvents()
    return window, docks


def _places(docks) -> dict:
    """Every shown widget of the dock area, by kind and name, in place."""
    places = {}
    for widget in [docks, *docks.findChildren(QWidget)]:
        if widget.isVisible():
            box = QRect(widget.mapTo(docks, QPoint(0, 0)), widget.size())
            key = (type(widget).__name__, widget.objectName())
            places.setdefault(key, []).append(box.getRect())
    return places


@pytest.mark.parametrize("where", ["host_window", "application"])
def test_a_host_s_sheet_moves_nothing_in_the_dock_area(qtbot, qapp, where):
    fxstyle.apply_theme("dark")
    _free_window, free = _window(qtbot)
    expected = _places(free)

    sheet = qapp.styleSheet()
    host = QMainWindow()
    qtbot.addWidget(host)
    try:
        if where == "application":
            qapp.setStyleSheet(_HOST_SHEET)
        else:
            host.setStyleSheet(_HOST_SHEET)
        host.show()
        qtbot.waitExposed(host)
        _held_window, held = _window(qtbot, host)
        moved = {
            key: (expected.get(key), place)
            for key, place in _places(held).items()
            if expected.get(key) != place
        }
    finally:
        qapp.setStyleSheet(sheet)

    assert not moved


###### The tab strip and the keyboard


def _tabbed(qtbot):
    window = FXMainWindow(title="Tabs", framed=True)
    docks = fxdocking.FXDockArea()
    window.setCentralWidget(docks)
    centre = QLineEdit("centre")
    docks.set_central(centre)
    fields = {}
    for name in ("apps", "runs", "sandbox"):
        fields[name] = QLineEdit(name)
        docks.add_dock(name, name.title(), fields[name], "left",
                       tab_with="" if name == "apps" else "apps")
    qtbot.addWidget(window)
    window.resize(800, 500)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    area = docks.manager().findDockWidget("apps").dockAreaWidget()
    area.setCurrentIndex(0)
    QApplication.processEvents()
    return window, centre, fields, area


def _tabs(area):
    bar = area.titleBar().tabBar()
    return [bar.tab(index) for index in range(bar.count())]


def _key(key, modifier=Qt.NoModifier):
    QTest.keyClick(QApplication.focusWidget(), key, modifier)
    QApplication.processEvents()
    return QApplication.focusWidget()


def test_a_pane_s_tab_strip_is_one_stop_right_before_its_content(qtbot):
    _window, _centre, fields, area = _tabbed(qtbot)
    tab = _tabs(area)[0]
    fields["apps"].setFocus(Qt.TabFocusReason)
    QApplication.processEvents()

    assert _key(Qt.Key_Backtab, Qt.ShiftModifier) is tab
    outside = _key(Qt.Key_Backtab, Qt.ShiftModifier)
    assert outside is not tab and outside not in fields.values()
    assert _key(Qt.Key_Tab) is tab
    assert _key(Qt.Key_Tab) is fields["apps"]


def test_left_and_right_walk_a_pane_s_tabs_with_the_focus(qtbot):
    _window, _centre, _fields, area = _tabbed(qtbot)
    tabs = _tabs(area)
    tabs[0].setFocus(Qt.TabFocusReason)
    QApplication.processEvents()

    QTest.keyClick(tabs[0], Qt.Key_Right)
    QApplication.processEvents()
    assert area.currentIndex() == 1
    assert tabs[1].hasFocus()
    accent = QColor(fxstyle.colors().accent_primary).name()
    assert accent in inks(tabs[1].grab())

    QTest.keyClick(tabs[1], Qt.Key_Left)
    QApplication.processEvents()
    assert area.currentIndex() == 0
    assert tabs[0].hasFocus()
