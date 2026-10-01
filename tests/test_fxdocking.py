"""Dock panes in Qt Advanced Docking System: `fxgui.fxdocking`."""

# Built-in
import os
import subprocess
import sys
from pathlib import Path

# Third-party
import pytest

ads = pytest.importorskip("PySide6QtAds")

from qtpy.QtCore import QRect, Qt  # noqa: E402
from qtpy.QtGui import QAction, QColor, QKeySequence  # noqa: E402
from qtpy.QtTest import QTest  # noqa: E402
from qtpy.QtWidgets import (  # noqa: E402
    QAbstractButton,
    QApplication,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxdocking, fxicons, fxstyle  # noqa: E402
from fxgui.fxwidgets import FXMainWindow  # noqa: E402

GAP = 6
THEMES = fxstyle.get_available_themes()


def _window(qtbot, panes=("side",), size=(900, 600), show=True):
    """Return a framed window docking `panes` around a label centre."""
    window = FXMainWindow(title="Docked", framed=True)
    docks = fxdocking.FXDockArea(gap=GAP)
    window.setCentralWidget(docks)
    window.docks = docks
    docks.set_central(QLabel("body"))
    window.toggles = {}
    window.panes = {}
    for name in panes:
        widget = QLabel(name)
        window.panes[name] = widget
        if name == "low":
            window.toggles[name] = docks.add_dock(
                name, name.title(), widget, "bottom", beside="side")
        elif name == "right":
            window.toggles[name] = docks.add_dock(
                name, name.title(), widget, "right")
        else:
            window.toggles[name] = docks.add_dock(
                name, name.title(), widget, "left")
    qtbot.addWidget(window)
    window.resize(*size)
    if show:
        window.show()
        qtbot.waitExposed(window)
        qtbot.wait(50)
    return window


def _three(qtbot, **kwargs):
    return _window(qtbot, ("side", "low", "right"), **kwargs)


def _pixel(window, widget, x, y):
    point = widget.mapTo(window, widget.rect().topLeft())
    image = window.grab().toImage()
    return QColor(image.pixel(point.x() + x, point.y() + y)).name()


def _frame():
    return QColor(fxstyle.get_theme_colors()["frame"]).name()


def _areas(window):
    return [
        area for area in window.docks.manager().findChildren(
            ads.CDockAreaWidget)
        if area.isVisible() and area.window() is window]


def _gaps(window):
    """Return the gaps across, down, and from the panes to the edges."""
    docks = window.docks.manager()
    rects = [area.rect().translated(area.mapTo(docks, area.rect().topLeft()))
             for area in _areas(window)]
    across, down = set(), set()
    for one in rects:
        for two in rects:
            beside = min(one.bottom(), two.bottom()) > max(one.top(), two.top())
            above = min(one.right(), two.right()) > max(one.left(), two.left())
            if beside and two.left() > one.right():
                across.add(two.left() - one.right() - 1)
            if above and two.top() > one.bottom():
                down.add(two.top() - one.bottom() - 1)
    box = docks.rect()
    edges = {
        min(r.left() for r in rects) - box.left(),
        min(r.top() for r in rects) - box.top(),
        box.right() - max(r.right() for r in rects),
        box.bottom() - max(r.bottom() for r in rects),
    }
    # Only neighbours: a pane two columns over is not a gap.
    return ({g for g in across if g < 40}, {g for g in down if g < 40},
            edges)


def _one_gap(window):
    across, down, edges = _gaps(window)
    assert across <= {GAP} and down <= {GAP}, (across, down)
    assert across or down, "there are neighbours to measure"
    assert edges == {GAP}, edges


def _corners_are_frame(window):
    image = window.grab().toImage()
    for area in _areas(window):
        box = area.rect()
        for corner in (box.topLeft(), box.topRight(), box.bottomLeft(),
                       box.bottomRight()):
            seen = QColor(image.pixel(area.mapTo(window, corner))).name()
            assert seen == _frame(), (area.objectName(), corner, seen)


def _handles(window):
    handles = []
    for splitter in window.docks.manager().findChildren(ads.CDockSplitter):
        for index in range(1, splitter.count()):
            handle = splitter.handle(index)
            if handle.isVisible():
                handles.append(handle)
    return handles


# -- Pure checks --------------------------------------------------------


def test_restorable_takes_a_layout_naming_the_same_panes(qtbot):
    window = _window(qtbot, ("side", "low"))
    built = window.docks.save_state()

    assert fxdocking.restorable(built, built)


def test_restorable_refuses_a_layout_naming_other_panes(qtbot):
    first = _window(qtbot, ("side",))
    other = _window(qtbot, ("side", "low"))

    assert not fxdocking.restorable(
        first.docks.save_state(), other.docks.save_state())


def test_restorable_refuses_a_layout_with_a_pane_in_a_side_bar():
    tucked = b'<QtAdvancedDockingSystem><SideBar Area="1"/>' \
        b'<Widget Name="side"/></QtAdvancedDockingSystem>'
    built = b'<QtAdvancedDockingSystem><Widget Name="side"/>' \
        b'</QtAdvancedDockingSystem>'

    assert fxdocking.restorable(built, built)
    assert not fxdocking.restorable(tucked, built)


def test_restorable_refuses_a_broken_layout():
    built = b'<QtAdvancedDockingSystem><Widget Name="side"/>' \
        b'</QtAdvancedDockingSystem>'

    assert not fxdocking.restorable(b"not a layout", built)


def test_the_icons_qtads_draws_leave_fxgui_s_cached_icons_alive(qtbot):
    from shiboken6 import Shiboken

    _window(qtbot)

    # QtAds deletes the icon it is given; fxgui's own must stay Python's.
    for name in ("close", "open_in_new", "expand_more"):
        cached = fxicons.get_icon(name)
        assert Shiboken.isValid(cached), name
        assert Shiboken.ownedByPython(cached), name


def test_a_second_window_opens_after_the_first_is_gone(qtbot):
    first = _window(qtbot)
    first.close()
    first.deleteLater()
    for _ in range(3):
        QApplication.processEvents()

    second = _window(qtbot)

    assert second.docks.manager().findDockWidget("side").isVisible()


# -- Panes --------------------------------------------------------------


def test_the_centre_holds_the_body(qtbot):
    window = _window(qtbot)

    held = window.docks.manager().centralWidget()
    assert held.widget().text() == "body"


def test_a_pane_folds_from_its_toggle(qtbot):
    window = _window(qtbot)

    window.toggles["side"].trigger()
    assert not window.panes["side"].isVisible()
    window.toggles["side"].trigger()
    assert window.panes["side"].isVisible()


def test_a_pane_offers_no_auto_hide(qtbot):
    window = _window(qtbot)
    area = window.docks.manager().findDockWidget("side").dockAreaWidget()

    pin = area.titleBar().button(ads.TitleBarButtonAutoHide)
    assert pin is None or not pin.isVisible()
    assert not ads.CDockManager.testAutoHideConfigFlag(
        ads.CDockManager.eAutoHideFlag.AutoHideFeatureEnabled)


def test_a_pane_tabbed_with_another_shares_its_tab_bar(qtbot):
    window = _window(qtbot, show=False)
    docks = window.docks
    docks.add_dock("low", "Low", QLabel("low"), "bottom", beside="side")
    docks.add_dock("peer", "Peer", QLabel("peer"), "bottom", tab_with="side")
    window.show()
    qtbot.waitExposed(window)

    manager = docks.manager()
    area = manager.findDockWidget("side").dockAreaWidget()
    assert manager.findDockWidget("peer").dockAreaWidget() is area
    assert manager.findDockWidget("low").dockAreaWidget() is not area
    assert area.currentDockWidget() is manager.findDockWidget("side"), (
        "a new tab does not take the front from the pane it joins")


def test_a_second_pane_on_one_side_tabs_with_the_first(qtbot):
    window = _window(qtbot, ("side", "more"))

    manager = window.docks.manager()
    assert manager.findDockWidget("more").dockAreaWidget() is (
        manager.findDockWidget("side").dockAreaWidget())


def test_tabbing_with_a_pane_that_is_not_there_says_which(qtbot):
    window = _window(qtbot, show=False)

    with pytest.raises(ValueError, match="nowhere"):
        window.docks.add_dock(
            "peer", "Peer", QLabel("peer"), "right", tab_with="nowhere")
    with pytest.raises(ValueError, match="nowhere"):
        window.docks.add_dock(
            "peer", "Peer", QLabel("peer"), "right", beside="nowhere")
    with pytest.raises(ValueError, match="middle"):
        window.docks.add_dock("peer", "Peer", QLabel("peer"), "middle")


def test_a_panes_title_and_tip_land_on_its_tab(qtbot):
    window = _window(qtbot)

    window.docks.set_dock_title("side", "Renamed")
    window.docks.set_dock_tip("side", "the side pane")

    held = window.docks.manager().findDockWidget("side")
    assert held.tabWidget().text() == "Renamed"
    assert held.tabWidget().toolTip() == "the side pane"


def test_show_dock_opens_a_closed_pane_in_front(qtbot):
    window = _window(qtbot, ("side", "more"))
    window.toggles["side"].trigger()

    window.docks.show_dock("side")

    held = window.docks.manager().findDockWidget("side")
    assert window.panes["side"].isVisible()
    assert held.dockAreaWidget().currentDockWidget() is held


def test_showing_a_floating_pane_raises_its_window(qtbot, monkeypatch):
    window = _window(qtbot)
    held = window.docks.manager().findDockWidget("side")
    held.setFloating()
    QApplication.processEvents()
    floating = held.floatingDockContainer()
    asked = []
    # Whether the window then turns active is the platform's call: under
    # offscreen Linux a floating pane is a QDockWidget that stays inactive.
    monkeypatch.setattr(floating, "raise_", lambda: asked.append("raise"))
    monkeypatch.setattr(
        floating, "activateWindow", lambda: asked.append("activate")
    )

    window.docks.show_dock("side")

    assert asked == ["raise", "activate"]


def test_a_floating_panes_tabs_keep_their_docked_height(qtbot):
    window = _window(qtbot, show=False)
    window.docks.add_dock("peer", "Peer", QLabel("peer"), "left",
                          tab_with="side")
    window.show()
    qtbot.waitExposed(window)
    manager = window.docks.manager()
    area = manager.findDockWidget("side").dockAreaWidget()
    docked = area.titleBar().height()

    area.setFloating()
    qtbot.wait(300)

    floated = manager.findDockWidget("side").dockAreaWidget().titleBar()
    assert floated.height() == docked


def test_a_pane_floats_above_the_window_it_belongs_to(qtbot):
    window = _window(qtbot)
    held = window.docks.manager().findDockWidget("side")

    held.setFloating()
    qtbot.wait(100)

    floating = held.floatingDockContainer()
    assert floating.isWindow()
    # Unbound: the QtAds binding's own `windowHandle` makes a new window.
    owner = QWidget.windowHandle(floating).transientParent()
    assert owner is window.windowHandle()


# -- Saved layouts ------------------------------------------------------


def test_a_closed_pane_stays_closed_in_the_next_window(qtbot):
    first = _window(qtbot)
    first.toggles["side"].trigger()
    state = first.docks.save_state()
    first.close()

    second = _window(qtbot, show=False)
    second.docks.restore_state(state)
    second.show()
    qtbot.waitExposed(second)

    assert not second.panes["side"].isVisible()


def test_a_layout_restored_after_the_first_show_applies_at_once(qtbot):
    first = _window(qtbot)
    first.toggles["side"].trigger()
    state = first.docks.save_state()

    second = _window(qtbot)
    assert second.docks.restore_state(state)

    assert not second.panes["side"].isVisible()


def test_reset_layout_brings_a_closed_pane_back(qtbot):
    first = _window(qtbot)
    first.toggles["side"].trigger()
    second = _window(qtbot, show=False)
    second.docks.restore_state(first.docks.save_state())
    second.show()
    qtbot.waitExposed(second)
    assert not second.panes["side"].isVisible()

    second.docks.reset_layout()

    assert second.panes["side"].isVisible()


def test_a_window_closed_unshown_keeps_the_layout_it_was_given(qtbot):
    first = _window(qtbot)
    first.toggles["side"].trigger()
    state = first.docks.save_state()

    unshown = _window(qtbot, show=False)
    unshown.docks.restore_state(state)

    assert unshown.docks.save_state() == state


def test_a_pane_the_saved_layout_never_named_opens_anyway(qtbot):
    first = _window(qtbot)
    state = first.docks.save_state()

    second = _window(qtbot, ("side2",), show=False)
    assert not second.docks.restore_state(state)
    second.show()
    qtbot.waitExposed(second)

    assert second.panes["side2"].isVisible()


def test_a_layout_saved_with_a_tucked_pane_opens_it_docked(qtbot):
    flag = ads.CDockManager.eAutoHideFlag.AutoHideFeatureEnabled
    _window(qtbot, show=False)
    ads.CDockManager.setAutoHideConfigFlag(flag, True)
    try:
        first = _window(qtbot)
        tucked = first.docks.manager().findDockWidget("side")
        tucked.setAutoHide(True)
        assert tucked.isAutoHide()
        state = first.docks.save_state()
    finally:
        ads.CDockManager.setAutoHideConfigFlag(flag, False)

    second = _window(qtbot, show=False)
    second.docks.restore_state(state)
    second.show()
    qtbot.waitExposed(second)

    held = second.docks.manager().findDockWidget("side")
    assert not held.isAutoHide()
    assert second.panes["side"].isVisible()


def test_kept_open_panes_cannot_close(qtbot):
    window = _window(qtbot, ("side", "low"))
    window.docks.keep_panes_open()

    closable = ads.CDockWidget.DockWidgetFeature.DockWidgetClosable
    for name in ("side", "low"):
        pane = window.docks.manager().findDockWidget(name)
        assert not pane.features() & closable, name
        pane.toggleViewAction().trigger()
        close = pane.dockAreaWidget().titleBar().button(
            ads.TitleBarButtonClose)
        assert close is None or not close.isVisible(), name
        assert pane.isVisible(), name


def test_a_stored_layout_with_a_kept_pane_closed_opens_it(qtbot):
    first = _window(qtbot)
    first.toggles["side"].trigger()
    state = first.docks.save_state()

    second = _window(qtbot, show=False)
    second.docks.keep_panes_open()
    second.docks.restore_state(state)
    second.show()
    qtbot.waitExposed(second)

    assert second.panes["side"].isVisible()


def test_a_kept_pane_closed_in_a_layout_restored_after_the_show_opens(qtbot):
    first = _window(qtbot)
    first.toggles["side"].trigger()
    state = first.docks.save_state()
    second = _window(qtbot)
    second.docks.keep_panes_open()

    assert second.docks.restore_state(state)

    assert second.panes["side"].isVisible()


# -- The look: cards on the frame, one gap apart ------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_every_pane_is_a_rounded_card_on_the_frame(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = _three(qtbot)

    _corners_are_frame(window)
    area = _areas(window)[0]
    edge = QColor(fxstyle.get_theme_colors()["pane_border"]).name()
    radius = fxstyle.BUTTON_RADIUS
    assert _pixel(window, area, area.width() // 2, 0) == edge
    assert _pixel(window, area, 0, area.height() // 2) == edge
    # Round, not square: a square card's top row is its edge to the corner.
    assert _pixel(window, area, 0, 0) != edge
    assert _pixel(window, area, radius, 0) == edge


@pytest.mark.parametrize("theme", THEMES)
def test_one_gap_across_down_and_at_the_edges(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = _three(qtbot)

    _one_gap(window)
    across, down, _edges = _gaps(window)
    assert across and down


def test_the_tab_bar_is_inset_off_the_round_corners(qtbot):
    window = _three(qtbot)

    for area in _areas(window):
        margins = area.titleBar().layout().contentsMargins()
        assert margins.left() == fxstyle.BUTTON_RADIUS
        assert margins.right() == fxstyle.BUTTON_RADIUS
        tab = area.currentDockWidget().tabWidget()
        assert tab.mapTo(area, tab.rect().topLeft()).x() >= (
            fxstyle.BUTTON_RADIUS), "no tab starts under the corner"


def test_the_current_tab_pill_follows_a_theme_change(qtbot):
    window = _window(qtbot)
    tab = window.docks.manager().findDockWidget("side").tabWidget()

    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        qtbot.wait(20)
        fill = QColor(fxstyle.get_theme_colors()["state_hover"]).name()
        # Inside the pill's edge, left of its text.
        assert _pixel(window, tab, 5, tab.height() // 2) == fill, theme


def test_a_moved_pane_keeps_the_gap(qtbot):
    window = _three(qtbot)
    manager = window.docks.manager()
    low = manager.findDockWidget("low")
    right = manager.findDockWidget("right").dockAreaWidget()

    manager.addDockWidget(ads.BottomDockWidgetArea, low, right)
    qtbot.wait(50)

    assert low.dockAreaWidget() is not None
    _one_gap(window)
    _corners_are_frame(window)


def test_a_floated_and_redocked_pane_keeps_the_gap(qtbot):
    window = _three(qtbot)
    manager = window.docks.manager()
    low = manager.findDockWidget("low")

    low.setFloating()
    qtbot.wait(100)
    floating = low.floatingDockContainer()
    margins = floating.dockContainer().layout().contentsMargins()
    assert (margins.left(), margins.top(), margins.right(),
            margins.bottom()) == (GAP,) * 4
    assert _pixel(floating, low.dockAreaWidget(), 0, 0) == _frame()
    manager.addDockWidget(ads.BottomDockWidgetArea, low,
                          manager.findDockWidget("side").dockAreaWidget())
    qtbot.wait(50)

    _one_gap(window)
    _corners_are_frame(window)


def test_a_pane_reopened_from_its_toggle_keeps_the_gap(qtbot):
    window = _three(qtbot)
    toggle = window.toggles["low"]

    toggle.trigger()
    qtbot.wait(50)
    toggle.trigger()
    qtbot.wait(50)

    _one_gap(window)


def test_a_restored_layout_keeps_the_gap_the_mark_and_the_inset(qtbot):
    window = _three(qtbot)
    manager = window.docks.manager()
    state = window.docks.save_state()
    manager.findDockWidget("low").toggleView(False)
    qtbot.wait(50)

    assert window.docks.restore_state(state)
    qtbot.wait(50)

    _one_gap(window)
    for splitter in manager.findChildren(ads.CDockSplitter):
        assert splitter.property(fxstyle.FRAME_PROPERTY) is True
        assert splitter.handleWidth() == GAP
    for area in _areas(window):
        margins = area.titleBar().layout().contentsMargins()
        assert margins.left() == fxstyle.BUTTON_RADIUS


def test_the_mark_and_the_frame_follow_a_theme_switch(qtbot):
    window = _three(qtbot)
    fxstyle.apply_theme("light")
    qtbot.wait(50)

    _corners_are_frame(window)
    handle = _handles(window)[0]
    assert _pixel(window, handle, 0, 0) == _frame()


def test_sizes_weigh_the_split(qtbot):
    window = FXMainWindow(title="Weighed", framed=True)
    docks = fxdocking.FXDockArea(gap=GAP)
    window.setCentralWidget(docks)
    docks.set_central(QLabel("body"))
    docks.add_dock("wide", "Wide", QLabel("wide"), "left", size=(3, 1))
    docks.add_dock("narrow", "Narrow", QLabel("narrow"), "right",
                   size=(1, 1))
    qtbot.addWidget(window)
    window.resize(1200, 600)
    window.show()
    qtbot.waitExposed(window)
    manager = docks.manager()

    wide = manager.findDockWidget("wide").dockAreaWidget().width()
    narrow = manager.findDockWidget("narrow").dockAreaWidget().width()
    assert wide > 2 * narrow, (wide, narrow)


class _Growing(QWidget):
    """A pane whose floor rises once it fills."""

    def __init__(self):
        super().__init__()
        self.column = QVBoxLayout(self)

    def fill(self, rows):
        for index in range(rows):
            label = QLabel(f"row {index}")
            label.setMinimumHeight(30)
            self.column.addWidget(label)


def test_a_pane_in_front_grows_as_its_content_does(qtbot):
    window = _window(qtbot, show=False)
    grown = _Growing()
    window.docks.add_dock("grown", "Grown", grown, "right")
    window.show()
    qtbot.waitExposed(window)

    grown.fill(12)
    qtbot.waitUntil(
        lambda: grown.height() >= grown.minimumSizeHint().height(),
        timeout=2000)


def test_a_tabbed_pane_floors_to_the_tab_in_front(qtbot):
    window = _window(qtbot, show=False)
    tall = _Growing()
    tall.fill(12)
    window.docks.add_dock("tall", "Tall", tall, "right")
    window.docks.add_dock("short", "Short", QLabel("short"), "right",
                          tab_with="tall")
    window.show()
    qtbot.waitExposed(window)
    manager = window.docks.manager()
    area = manager.findDockWidget("tall").dockAreaWidget()
    qtbot.wait(50)
    assert tall.height() >= tall.minimumSizeHint().height()
    floor = area.minimumHeight()

    window.docks.show_dock("short")
    qtbot.wait(50)

    assert area.minimumHeight() < floor, "the floor follows the tab in front"


def test_a_theme_change_after_a_layout_restore_raises_nothing(qtbot):
    window = _three(qtbot)
    window.docks.restore_state(window.docks.save_state())
    qtbot.wait(50)

    for theme in ("light", "dark", "light"):
        fxstyle.apply_theme(theme)
        qtbot.wait(20)

    assert window.docks.manager().findDockWidget("side").isVisible()


def test_a_theme_change_after_the_window_closed_raises_nothing(qtbot):
    window = _window(qtbot)
    window.close()
    window.deleteLater()
    QApplication.processEvents()

    fxstyle.apply_theme("light")
    qtbot.wait(20)
    fxstyle.apply_theme("dark")


def test_the_drop_targets_wear_the_theme_in_force(qtbot):
    window = _window(qtbot)
    crosses = window.docks.manager().findChildren(ads.CDockOverlayCross)
    assert crosses
    part = ads.CDockOverlayCross.eIconColor.FrameColor

    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        accent = QColor(fxstyle.get_theme_colors()["accent_primary"]).name()
        for cross in crosses:
            assert cross.iconColor(part).name() == accent, theme


_AT_SCALE = """
import sys
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QLabel
app = QApplication(sys.argv)
from fxgui import fxdocking, fxstyle
from fxgui.fxwidgets import FXMainWindow
fxstyle.apply_theme("dark")
window = FXMainWindow(title="Scaled", framed=True)
docks = fxdocking.FXDockArea()
window.setCentralWidget(docks)
docks.set_central(QLabel("body"))
docks.add_dock("side", "Side", QLabel("side"), "left")
docks.add_dock("low", "Low", QLabel("low"), "bottom", beside="side")
docks.add_dock("right", "Right", QLabel("right"), "right")
window.resize(900, 600)
window.show()
for _ in range(20):
    app.processEvents()
import PySide6QtAds as ads
image = window.grab().toImage()
ratio = image.devicePixelRatio()
frame = QColor(fxstyle.get_theme_colors()["frame"]).name()
ink = QColor(fxstyle.get_theme_colors()["splitter_mark"]).name()
areas = [a for a in docks.manager().findChildren(ads.CDockAreaWidget)
         if a.isVisible()]
for area in areas:
    corner = area.mapTo(window, area.rect().topLeft())
    seen = QColor(image.pixel(int(corner.x() * ratio), int(corner.y() * ratio)))
    assert seen.name() == frame, seen.name()
handles = [s.handle(i) for s in docks.manager().findChildren(ads.CDockSplitter)
           for i in range(1, s.count()) if s.handle(i).isVisible()]
assert handles
for handle in handles:
    holder = handle.parentWidget()
    box = handle.geometry().translated(
        holder.mapTo(window, holder.rect().topLeft()))
    inked = [
        (x, y)
        for x in range(int(box.left() * ratio) + 1,
                       int((box.right() + 1) * ratio) - 1)
        for y in range(int(box.top() * ratio) + 1,
                       int((box.bottom() + 1) * ratio) - 1)
        if QColor(image.pixel(x, y)).name() != frame]
    assert inked, "a mark at this scale"
    assert all(QColor(image.pixel(x, y)).name() == ink for x, y in inked)
print("ratio", ratio)
"""


def test_corners_and_the_mark_hold_at_150_percent(tmp_path):
    env = dict(os.environ, QT_SCALE_FACTOR="1.5", QT_QPA_PLATFORM="offscreen",
               PYTHONPATH=os.pathsep.join(sys.path), APPDATA=str(tmp_path))
    done = subprocess.run(
        [sys.executable, "-c", _AT_SCALE], env=env, capture_output=True,
        text=True, timeout=120, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "ratio 1.5" in done.stdout


# -- Keys and focus -----------------------------------------------------


def _activated(qtbot, window):
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitUntil(lambda: QApplication.activeWindow() is window,
                    timeout=2000)


def _floated(qtbot):
    """Return a window whose `side` pane, a line edit, floats focused."""
    window = _window(qtbot, ("side",), show=False)
    field = QLineEdit()
    window.field = field
    window.docks.add_dock("field", "Field", field, "right")
    window.ran = []
    act = QAction("Run", window)
    act.setShortcut(QKeySequence("Ctrl+Shift+Y"))
    act.triggered.connect(lambda _c=False: window.ran.append("window"))
    window.addAction(act)
    _activated(qtbot, window)
    held = window.docks.manager().findDockWidget("field")
    held.setFloating()
    floating = held.floatingDockContainer()
    qtbot.waitExposed(floating)
    floating.activateWindow()
    field.setFocus()
    qtbot.waitUntil(field.hasFocus, timeout=2000)
    return window, floating


def test_a_window_key_answers_in_its_floating_pane(qtbot):
    window, _floating = _floated(qtbot)

    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Y,
                   Qt.ControlModifier | Qt.ShiftModifier)

    qtbot.waitUntil(lambda: window.ran == ["window"], timeout=2000)


def test_a_widget_s_own_key_stays_out_of_a_floating_pane(qtbot):
    window = _window(qtbot, ("side",), show=False)
    undone = []
    canvas = QLineEdit()
    undo = QAction("Undo", canvas)
    undo.setShortcut(QKeySequence("Ctrl+G"))
    undo.setShortcutContext(Qt.WidgetWithChildrenShortcut)
    undo.triggered.connect(lambda _c=False: undone.append(True))
    canvas.addAction(undo)
    window.docks.set_central(canvas)
    field = QLineEdit()
    window.docks.add_dock("field", "Field", field, "right")
    _activated(qtbot, window)
    held = window.docks.manager().findDockWidget("field")
    held.setFloating()
    floating = held.floatingDockContainer()
    qtbot.waitExposed(floating)
    floating.activateWindow()
    field.setFocus()
    qtbot.waitUntil(field.hasFocus, timeout=2000)

    QTest.keyClick(field, Qt.Key_G, Qt.ControlModifier)
    qtbot.wait(50)

    assert undone == []
    assert undo not in floating.actions()


def test_tab_follows_the_declared_order_across_panes(qtbot):
    window = _window(qtbot, ("side",), show=False)
    fields = {}
    for name, area in (("one", "left"), ("two", "right"), ("three", "left")):
        fields[name] = QLineEdit(name)
        window.docks.add_dock(name, name.title(), fields[name], area)
    window.docks.show_dock("three")
    QWidget.setTabOrder(fields["two"], fields["three"])
    QWidget.setTabOrder(fields["three"], fields["one"])
    _activated(qtbot, window)
    for name in ("one", "two", "three"):
        window.docks.show_dock(name)
    # One and three tab together; bring each to the front before it walks.
    fields["two"].setFocus()
    qtbot.waitUntil(fields["two"].hasFocus, timeout=2000)

    QTest.keyClick(fields["two"], Qt.Key_Tab)

    assert QApplication.focusWidget() is fields["three"]


def test_tab_passes_a_widget_whose_focus_goes_elsewhere(qtbot):
    # A search bar hands its focus to a field the tab order put elsewhere;
    # Qt's own walk stops at the bar and jumps to that field.
    window = _window(qtbot, ("side",), show=False)
    first, last, field = QLineEdit(), QLineEdit(), QLineEdit()
    bar = QWidget()
    bar.setFocusProxy(field)
    holder = QWidget()
    column = QVBoxLayout(holder)
    for widget in (first, bar, last):
        column.addWidget(widget)
    window.docks.add_dock("fields", "Fields", holder, "right")
    window.docks.add_dock("far", "Far", field, "left")
    _activated(qtbot, window)
    first.setFocus()
    qtbot.waitUntil(first.hasFocus, timeout=2000)

    QTest.keyClick(first, Qt.Key_Tab)

    assert QApplication.focusWidget() is last


def test_tab_skips_a_hidden_widget_in_the_chain(qtbot):
    window = _window(qtbot, ("side",), show=False)
    first, hidden, last = QLineEdit(), QLineEdit(), QLineEdit()
    holder = QWidget()
    column = QVBoxLayout(holder)
    for field in (first, hidden, last):
        column.addWidget(field)
    window.docks.add_dock("fields", "Fields", holder, "right")
    _activated(qtbot, window)
    hidden.hide()
    first.setFocus()
    qtbot.waitUntil(first.hasFocus, timeout=2000)

    QTest.keyClick(first, Qt.Key_Tab)

    assert QApplication.focusWidget() is last


_CHILD = "FXGUI_PANE_FOCUS_CHILD"


@pytest.mark.skipif(os.environ.get(_CHILD) != "1", reason="child only")
@pytest.mark.parametrize("how", ["toggle", "button"])
def test_child_close_a_pane_on_the_focus(qtbot, how):
    window = _window(qtbot, ("side",), show=False)
    # Somewhere for the keyboard to go.
    window.docks.set_central(QLineEdit())
    field = QLineEdit()
    window.docks.add_dock("field", "Field", field, "right")
    _activated(qtbot, window)
    field.setFocus()
    qtbot.waitUntil(field.hasFocus, timeout=2000)
    pane = window.docks.manager().findDockWidget("field")

    if how == "toggle":
        pane.toggleViewAction().trigger()
    else:
        button = pane.dockAreaWidget().findChild(
            QAbstractButton, "dockAreaCloseButton")
        assert button is not None and button.isVisible()
        QTest.mouseClick(button, Qt.LeftButton)

    qtbot.waitUntil(lambda: not field.isVisible(), timeout=2000)
    assert not field.hasFocus()


@pytest.mark.parametrize("how", ["toggle", "button"])
def test_a_pane_closed_on_the_focus_does_not_crash(how, tmp_path):
    # A child pytest: a native crash in Qt's focus move fails this case only.
    env = {**os.environ, _CHILD: "1", "APPDATA": str(tmp_path)}
    ran = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
         f"{Path(__file__)}::test_child_close_a_pane_on_the_focus[{how}]"],
        cwd=Path(__file__).parents[1], env=env, capture_output=True,
        text=True, timeout=300, check=False)

    said = ran.stdout[-3000:] + ran.stderr[-3000:]
    assert ran.returncode == 0, said
    assert "1 passed" in ran.stdout, said


# -- Banners ------------------------------------------------------------


def test_a_floating_pane_s_banner_host_is_its_app_window_s_area(qtbot):
    window, _floating = _floated(qtbot)

    host = fxdocking.banner_host(window.field)

    assert host is window.docks
    assert host.window() is window


def test_a_plain_widget_s_banner_host_is_its_window(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    inner = QLabel(window)

    assert fxdocking.banner_host(inner) is window


@pytest.mark.parametrize("width", [700, 1100])
def test_a_clear_top_leaves_every_pane_title_bar_clear(qtbot, width):
    window = _window(qtbot, ("side", "right"), size=(width, 600))
    docks = window.docks
    card = (320, 60)

    top = docks.clear_top(*card)

    placed = QRect(docks.width() - card[0] - GAP, top, *card)
    assert top >= GAP
    bars = [bar for bar in docks.manager().findChildren(
        ads.CDockAreaTitleBar) if bar.isVisible()]
    assert bars
    for bar in bars:
        box = QRect(bar.mapTo(docks, bar.rect().topLeft()), bar.size())
        assert not placed.intersects(box), bar


def test_a_burst_of_tree_signals_sweeps_once(qtbot, monkeypatch):
    window = _three(qtbot)
    docks = window.docks
    swept = []
    monkeypatch.setattr(docks, "_sweep", lambda: swept.append(1))

    for _ in range(5):
        docks._resweep()
    qtbot.wait(20)

    assert swept == [1]


def test_the_shim_paths_are_gone():
    from fxgui import _compat

    for name in ("later", "rehome", "focus_step"):
        assert not hasattr(_compat, name), name
