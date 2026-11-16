"""No fxgui slot runs on a deleted object while a window is torn down.

PySide marks a child's handle deleted as its window's teardown begins, before
Qt deletes the child; a signal the teardown still fires (a scroll range
shrinking, a dock area's current tab) then reached a lambda holding that
handle. pytest-qt fails a test on any exception raised in a slot.
"""

# Third-party
import pytest
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXBreadcrumb, FXMainWindow

_PATH = ["a_project_with_a_long_name", "sq0100", "sh0100_0010", "comp", "v012"]


def _torn_down(window) -> None:
    """Delete `window` now, as a closing app or pytest-qt's teardown does."""
    window.close()
    window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


@pytest.mark.parametrize("where", ["layout", "toolbar"])
def test_a_window_with_a_narrow_breadcrumb_tears_down_quietly(qtbot, where):
    fxstyle.apply_theme("dark")
    crumb = FXBreadcrumb(show_navigation=True, home_icon="")
    window = FXMainWindow(title="Crumbs")
    if where == "toolbar":
        window.addToolBar("Path").addWidget(crumb)
        window.setCentralWidget(QLabel("body"))
    else:
        body = QWidget()
        QVBoxLayout(body).addWidget(crumb)
        window.setCentralWidget(body)
    fxstyle.register_themed_root(window)
    window.resize(220, 120)
    window.show()
    qtbot.waitExposed(window)
    crumb.set_path(_PATH)
    QApplication.processEvents()
    area = crumb._scroll_area
    assert area.widget().sizeHint().width() > area.width(), "a narrow bar"

    _torn_down(window)


def test_a_window_with_tabbed_panes_tears_down_quietly(qtbot):
    fxdocking = pytest.importorskip("fxgui.fxdocking")
    fxstyle.apply_theme("dark")
    window = FXMainWindow(title="Panes")
    docks = fxdocking.FXDockArea()
    window.setCentralWidget(docks)
    docks.set_central(QLabel("centre"))
    docks.add_dock("one", "One", QLabel("one"), "left")
    docks.add_dock("two", "Two", QLabel("two"), "left", tab_with="one")
    fxstyle.register_themed_root(window)
    window.resize(600, 400)
    window.show()
    qtbot.waitExposed(window)

    _torn_down(window)
