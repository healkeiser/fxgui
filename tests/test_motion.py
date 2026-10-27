"""A row's hover fades out after the pointer; windows and popups fade in."""

# Third-party
from qtpy.QtCore import QPropertyAnimation
from qtpy.QtWidgets import (
    QMenu,
    QStyle,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

# Third-party
import pytest

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate

from _helpers import themed_window


@pytest.fixture(autouse=True)
def _motion(monkeypatch):
    """Play the fades the rest of the suite turns off."""
    monkeypatch.delenv(fxstyle.REDUCED_MOTION_VAR, raising=False)


def test_reduced_motion_turns_every_fade_off(qtbot, monkeypatch):
    monkeypatch.setenv(fxstyle.REDUCED_MOTION_VAR, "1")
    assert not fxstyle.motion()
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    window.show()
    qtbot.waitExposed(window)
    assert not _fades(window)


def _rows(qtbot):
    view = QTreeWidget()
    view.setHeaderHidden(True)
    delegate = FXThumbnailDelegate(view)
    view.setItemDelegate(delegate)
    for index in range(3):
        QTreeWidgetItem(view, [f"Row{index}"])
    window = themed_window(qtbot, "dark", view)
    indexes = [view.model().index(row, 0) for row in range(3)]
    # The window holds the view: the test keeps it.
    return window, view, delegate, indexes


def _option(view, hovered: bool) -> QStyleOptionViewItem:
    option = QStyleOptionViewItem()
    option.widget = view
    if hovered:
        option.state |= QStyle.State_MouseOver
    return option


def test_a_row_lights_at_once_and_fades_after_the_pointer(qtbot):
    _window, view, delegate, (first, second, _third) = _rows(qtbot)
    assert delegate._hover_amount(_option(view, True), first) == 1.0
    # The pointer moves on: the first row still shows some of its hover.
    assert delegate._hover_amount(_option(view, True), second) == 1.0
    # Still lit, now fading: the clock may not have ticked yet.
    assert 0.0 < delegate._hover_amount(_option(view, False), first) <= 1.0
    assert delegate._fading and delegate._fade_timer.isActive()
    # Done within the fade, and the timer stops with nothing left.
    qtbot.waitUntil(
        lambda: delegate._hover_amount(_option(view, False), first) == 0.0,
        timeout=1000,
    )
    qtbot.waitUntil(lambda: not delegate._fade_timer.isActive(), timeout=1000)


def test_a_row_the_pointer_leaves_the_view_from_fades_too(qtbot):
    _window, view, delegate, (first, _second, _third) = _rows(qtbot)
    delegate._hover_amount(_option(view, True), first)
    assert 0.0 < delegate._hover_amount(_option(view, False), first) <= 1.0
    assert delegate._hovered is None and delegate._fading


def test_a_row_never_hovered_wears_none(qtbot):
    _window, view, delegate, (_first, _second, third) = _rows(qtbot)
    assert delegate._hover_amount(_option(view, False), third) == 0.0


def _fades(widget: QWidget) -> list:
    return [
        child for child in widget.findChildren(QPropertyAnimation)
        if bytes(child.propertyName()) == b"windowOpacity"
    ]


def test_a_themed_window_fades_in_when_shown(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    window.show()
    qtbot.waitExposed(window)
    fades = _fades(window)
    assert fades, "the window shows with no fade"
    assert fades[0].duration() == fxstyle.WINDOW_FADE_MS


def test_a_panel_brought_forward_fades_in(qtbot):
    from qtpy.QtWidgets import QLabel, QStackedWidget

    stack = QStackedWidget()
    first, second = QLabel("one"), QLabel("two")
    stack.addWidget(first)
    stack.addWidget(second)
    window = themed_window(qtbot, "dark", stack)
    # While the window still fades in, its pages ride that fade.
    if window.windowOpacity() < 1.0:
        stack.setCurrentWidget(second)
        assert not [
            child for child in second.children()
            if type(child).__name__ == "_Reveal"
        ]
        stack.setCurrentWidget(first)
    qtbot.waitUntil(lambda: window.windowOpacity() == 1.0, timeout=2000)
    stack.setCurrentWidget(second)
    covers = [
        child for child in second.children()
        if type(child).__name__ == "_Reveal"
    ]
    assert covers, "the page came forward with no fade"
    qtbot.waitUntil(
        lambda: not any(
            type(child).__name__ == "_Reveal" for child in second.children()
        ),
        timeout=2000,
    )


def test_a_see_through_page_hides_under_its_cover_while_it_rises(qtbot):
    from qtpy.QtGui import QColor, QPainter
    from qtpy.QtWidgets import QStackedWidget

    class Lined(QWidget):
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(0, 40, self.width(), 1, QColor("#ffffff"))
            painter.end()

    stack = QStackedWidget()
    lined = Lined()
    stack.addWidget(QWidget())
    stack.addWidget(lined)
    window = themed_window(qtbot, "dark", stack)
    qtbot.waitUntil(lambda: window.windowOpacity() == 1.0, timeout=2000)
    stack.setCurrentWidget(lined)
    qtbot.waitUntil(
        lambda: any(type(c).__name__ == "_Reveal" and 0.2 < c._shown < 0.8
                    for c in lined.children()),
        timeout=2000,
    )
    shot = lined.grab().toImage()

    # The page itself stays under the cover: only its fading copy shows.
    assert max(
        QColor(shot.pixel(5, y)).lightness() for y in range(shot.height())
    ) < 250, "a see-through page showed through its cover"
    # The cover is the colour the page shows, not transparent black.
    cover, surface = shot.pixelColor(5, 0), QColor(fxstyle.colors().surface)
    assert max(
        abs(cover.red() - surface.red()),
        abs(cover.green() - surface.green()),
        abs(cover.blue() - surface.blue()),
    ) <= 2, cover.name()


def test_a_page_on_another_ground_is_covered_in_that_ground(qtbot):
    """A page on a card or a well hides under the card's colour."""
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QColor
    from qtpy.QtWidgets import QStackedWidget, QVBoxLayout

    card = QWidget()
    card.setObjectName("card")
    card.setAttribute(Qt.WA_StyledBackground)
    card.setStyleSheet("QWidget#card { background-color: #204060; }")
    stack = QStackedWidget()
    page = QWidget()
    stack.addWidget(QWidget())
    stack.addWidget(page)
    QVBoxLayout(card).addWidget(stack)
    window = themed_window(qtbot, "dark", card)
    qtbot.waitUntil(lambda: window.windowOpacity() == 1.0, timeout=2000)
    stack.setCurrentWidget(page)
    qtbot.waitUntil(
        lambda: any(type(c).__name__ == "_Reveal" and 0.2 < c._shown < 0.8
                    for c in page.children()),
        timeout=2000,
    )
    cover = page.grab().toImage().pixelColor(5, 5)
    want = QColor("#204060")
    assert max(
        abs(cover.red() - want.red()),
        abs(cover.green() - want.green()),
        abs(cover.blue() - want.blue()),
    ) <= 2, cover.name()


def test_a_pane_opened_grows_open_to_its_width(qtbot):
    from qtpy.QtWidgets import QLabel, QMainWindow

    from fxgui.fxdocking import FXDockArea

    window = QMainWindow()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    docks = FXDockArea(window)
    window.setCentralWidget(docks)
    docks.add_dock("main", "Main", QLabel("main"), "left")
    docks.add_dock("side", "Side", QLabel("side"), "right")
    window.resize(800, 400)
    window.show()
    qtbot.waitExposed(window)
    side = docks.manager().findDockWidget("side")
    qtbot.wait(300)
    full = side.dockAreaWidget().width()
    toggle = side.toggleViewAction()
    toggle.trigger()
    qtbot.wait(100)
    toggle.trigger()
    qtbot.wait(60)
    assert side.dockAreaWidget().width() < full, "the pane popped open"
    qtbot.waitUntil(
        lambda: side.dockAreaWidget().width() == full, timeout=2000)


def test_a_pane_show_dock_opens_grows_open_too(qtbot):
    from qtpy.QtWidgets import QLabel, QMainWindow

    from fxgui.fxdocking import FXDockArea

    window = QMainWindow()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    docks = FXDockArea(window)
    window.setCentralWidget(docks)
    docks.add_dock("main", "Main", QLabel("main"), "left")
    docks.add_dock("side", "Side", QLabel("side"), "right")
    window.resize(800, 400)
    window.show()
    qtbot.waitExposed(window)
    side = docks.manager().findDockWidget("side")
    # Past the window's settling, when its panes came up with it.
    qtbot.wait(700)
    full = side.dockAreaWidget().width()
    side.toggleView(False)
    qtbot.wait(100)
    docks.show_dock("side")
    qtbot.wait(60)
    assert side.dockAreaWidget().width() < full, "the pane popped open"
    qtbot.waitUntil(
        lambda: side.dockAreaWidget().width() == full, timeout=2000)


def _settled_sides(qtbot):
    """A window with a main and a side pane, past its own settling."""
    from qtpy.QtWidgets import QLabel, QMainWindow

    from fxgui.fxdocking import FXDockArea

    window = QMainWindow()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    docks = FXDockArea(window)
    window.setCentralWidget(docks)
    docks.add_dock("main", "Main", QLabel("main"), "left")
    docks.add_dock("side", "Side", QLabel("side"), "right")
    window.resize(800, 400)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(700)
    window.docks_ = docks
    return window, docks, docks.manager().findDockWidget("side")


def test_a_grown_pane_gets_its_floor_back(qtbot):
    """The grow lets the area shrink to nothing; it must not stay so."""
    _window, docks, side = _settled_sides(qtbot)
    floor = side.dockAreaWidget().minimumSize()
    full = side.dockAreaWidget().width()
    side.toggleView(False)
    qtbot.wait(100)

    docks.show_dock("side")
    qtbot.waitUntil(
        lambda: side.dockAreaWidget().width() == full, timeout=2000)
    qtbot.wait(100)

    assert not side.dockAreaWidget().minimumSize().isNull()
    assert side.dockAreaWidget().minimumSize() == floor


def test_a_pane_opened_while_its_window_fades_takes_its_width_at_once(
        qtbot):
    """The window's own fade is the motion: a pane does not grow under it."""
    window, docks, side = _settled_sides(qtbot)
    full = side.dockAreaWidget().width()
    side.toggleView(False)
    qtbot.wait(100)
    window.setWindowOpacity(0.5)

    docks.show_dock("side")
    qtbot.wait(60)

    assert side.dockAreaWidget().width() == full
    window.setWindowOpacity(1.0)


def test_a_layout_restored_after_settling_moves_no_pane(qtbot):
    """A restore shows every pane; none of them is a person picking one."""
    _window, docks, side = _settled_sides(qtbot)
    full = side.dockAreaWidget().width()
    state = docks.save_state()
    side.toggleView(False)
    qtbot.wait(100)

    docks.restore_state(state)

    assert not side.widget().findChildren(fxstyle._Reveal), "no fade either"
    qtbot.wait(60)
    assert side.dockAreaWidget().width() == full


def test_a_pane_the_layout_opens_takes_its_width_at_once(qtbot):
    """A window building or restoring its panes grows none of them."""
    from qtpy.QtWidgets import QLabel, QMainWindow

    from fxgui.fxdocking import FXDockArea

    window = QMainWindow()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    docks = FXDockArea(window)
    window.setCentralWidget(docks)
    docks.add_dock("main", "Main", QLabel("main"), "left")
    docks.add_dock("side", "Side", QLabel("side"), "right")
    window.resize(800, 400)
    window.show()
    qtbot.waitExposed(window)
    side = docks.manager().findDockWidget("side")
    qtbot.wait(300)
    full = side.dockAreaWidget().width()
    side.toggleView(False)
    qtbot.wait(100)
    side.toggleView(True)
    qtbot.wait(60)
    assert side.dockAreaWidget().width() == full


def test_a_themed_menu_fades_in_when_shown(qtbot):
    window = themed_window(qtbot, "dark")
    menu = QMenu(window)
    menu.addAction("One")
    menu.popup(window.mapToGlobal(window.rect().center()))
    qtbot.waitUntil(menu.isVisible)
    fades = _fades(menu)
    assert fades and fades[0].duration() == fxstyle.POPUP_FADE_MS
    menu.close()


def test_the_page_shown_with_its_window_rides_the_window_fade(qtbot):
    """Qt shows a window's pages before the window: only one fade runs."""
    from qtpy.QtWidgets import QApplication, QLabel, QStackedWidget

    stack = QStackedWidget()
    first = QLabel("one")
    stack.addWidget(first)
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    from qtpy.QtWidgets import QVBoxLayout

    QVBoxLayout(window).addWidget(stack)
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    assert _fades(window), "the window shows with no fade"
    assert not [
        child for child in first.children()
        if type(child).__name__ == "_Reveal"
    ], "the first page fades on top of the window's fade"


def test_a_row_hovered_in_another_cell_stays_hovered(qtbot):
    """A table marks one cell: the row's other cells must not fade out."""
    from qtpy.QtTest import QTest
    from qtpy.QtWidgets import QTableWidget, QTableWidgetItem

    table = QTableWidget(2, 2)
    for row in range(2):
        for column in range(2):
            table.setItem(row, column, QTableWidgetItem("cell"))
    delegate = FXThumbnailDelegate(table)
    table.setItemDelegate(delegate)
    window = themed_window(qtbot, "dark", table)
    target = table.visualRect(table.model().index(0, 1)).center()
    QTest.mouseMove(table.viewport(), target)
    qtbot.waitUntil(table.viewport().underMouse, timeout=2000)
    option = QStyleOptionViewItem()
    option.widget = table
    option.state = QStyle.State_Enabled
    first = table.model().index(0, 0)
    assert delegate._hover_amount(option, first) == 1.0
    assert not delegate._fade_timer.isActive()
    assert window.isVisible()
