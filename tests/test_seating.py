"""A tray panel sits in the screen corner nearest its icon, and
rises into place once."""

# Third-party
from qtpy.QtCore import QAbstractAnimation, QPoint, QRect, QSize
from qtpy.QtGui import QGuiApplication
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import FXSeating


SCREEN = QRect(0, 0, 1920, 1040)  # availableGeometry: taskbar excluded
SIZE = QSize(320, 420)
GAP = FXSeating.EDGE_GAP
corner = FXSeating.popup_corner


LOWER_RIGHT = QPoint(
    SCREEN.right() - SIZE.width() + 1 - GAP,
    SCREEN.bottom() - SIZE.height() + 1 - GAP,
)


def test_a_tray_icon_seats_the_panel_one_gap_off_both_near_edges():
    seat = QRect(corner(SIZE, QRect(1600, 1040, 24, 24), None, SCREEN), SIZE)
    assert SCREEN.right() - seat.right() == GAP
    assert SCREEN.bottom() - seat.bottom() == GAP


def test_a_tray_icon_at_the_top_left_takes_that_corner():
    assert corner(SIZE, QRect(100, 0, 24, 24), None, SCREEN) == QPoint(GAP, GAP)


def test_a_click_in_the_overflow_flyout_still_takes_the_corner():
    assert corner(SIZE, QRect(), QPoint(1500, 1000), SCREEN) == LOWER_RIGHT


def test_no_tray_and_no_cursor_takes_the_work_area_s_corner():
    assert corner(SIZE, QRect(), None, SCREEN) == LOWER_RIGHT


def test_the_corner_is_always_clamped_inside_the_screen():
    at = corner(SIZE, QRect(), QPoint(1900, 10), SCREEN)
    assert SCREEN.adjusted(GAP, GAP, -GAP, -GAP).contains(QRect(at, SIZE))


def test_the_anchor_prefers_the_tray_icon_over_the_cursor():
    tray = QRect(1600, 1000, 24, 24)
    assert FXSeating.anchor_point(tray, QPoint(600, 500)) == tray.center()


def test_the_anchor_falls_from_the_cursor_to_nothing():
    assert FXSeating.anchor_point(QRect(), QPoint(6, 5)) == QPoint(6, 5)
    assert FXSeating.anchor_point(QRect(), None) is None


def _panel(qtbot):
    panel = QWidget()
    qtbot.addWidget(panel)
    panel.resize(200, 150)
    return panel, FXSeating(panel)


def _entered(qtbot, seating):
    qtbot.waitUntil(
        lambda: seating.entrance.state() == QAbstractAnimation.Stopped,
        timeout=2000,
    )


def test_every_anchor_names_a_screen_and_a_dead_one_still_does(qtbot):
    panel, seating = _panel(qtbot)
    screen = QGuiApplication.primaryScreen()

    assert seating.screen_for(QRect(0, 0, 24, 24), None) is screen
    assert seating.screen_for(QRect(), QPoint(10, 10)) is screen
    assert seating.screen_for(QRect(), None) is screen
    far = QRect(-100000, -100000, 24, 24)
    assert seating.screen_for(far, None) is panel.screen()


def test_a_show_slides_the_panel_up_into_its_seat_and_fades_it_in(qtbot):
    panel, seating = _panel(qtbot)
    tray = QRect(1600, 1000, 24, 24)
    area = panel.screen().availableGeometry()

    seating.show_at(tray, None)
    started = panel.pos()
    seated = corner(panel.size(), tray, None, area)

    assert started.y() > seated.y() and started.x() == seated.x()
    assert panel.windowOpacity() < 1.0
    _entered(qtbot, seating)
    assert panel.pos() == seated
    assert panel.windowOpacity() == 1.0
    assert panel.isVisible()


def test_a_panel_already_on_screen_is_not_slid_around(qtbot):
    panel, seating = _panel(qtbot)
    tray = QRect(1600, 1000, 24, 24)
    seating.show_at(tray, None)
    _entered(qtbot, seating)
    seated = panel.pos()

    seating.show_at(tray, None)

    assert seating.entrance.state() == QAbstractAnimation.Stopped
    assert panel.pos() == seated


def test_stop_leaves_the_panel_opaque(qtbot):
    panel, seating = _panel(qtbot)
    seating.show_at(QRect(1600, 1000, 24, 24), None)

    seating.stop()

    assert seating.entrance.state() == QAbstractAnimation.Stopped
    assert panel.windowOpacity() == 1.0


def test_a_centred_panel_forgets_its_anchor(qtbot):
    panel, seating = _panel(qtbot)
    seating.show_at(QRect(1600, 1000, 24, 24), None)
    _entered(qtbot, seating)

    seating.center()
    centred = panel.pos()
    seating.seat()

    area = panel.screen().availableGeometry()
    assert panel.pos() == centred
    assert abs(panel.geometry().center().x() - area.center().x()) <= 1


def test_clamp_keeps_a_rect_inside_the_screen_off_its_edges_by_the_gap():
    clamp = FXSeating.clamp
    assert clamp(QPoint(1900, -5), SIZE, SCREEN) == QPoint(1920 - 320, 0)
    assert clamp(QPoint(-5, 900), SIZE, SCREEN, gap=10) == QPoint(10, 1040 - 420 - 10)
    assert clamp(QPoint(100, 100), SIZE, SCREEN) == QPoint(100, 100)
