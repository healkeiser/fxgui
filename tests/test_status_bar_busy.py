"""set_busy runs a line along the status bar's top edge, moving nothing."""

# Third-party
from qtpy.QtCore import QAbstractAnimation
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QLabel

# Internal
from fxgui.fxwidgets import FXMainWindow
from fxgui.fxwidgets._status_bar import STATUS_LINE_HEIGHT


def _window(qtbot, framed=True):
    window = FXMainWindow(framed=framed)
    window.setCentralWidget(QLabel("body"))
    qtbot.addWidget(window)
    window.resize(600, 300)
    window.show()
    qtbot.waitExposed(window)
    return window


def _run_to(qtbot, bar, progress):
    """Wait for the busy line to cross `progress` of the bar, where it shows."""
    qtbot.waitUntil(lambda: (bar._busy_line.currentValue() or 0) >= progress)


def _running(bar):
    return bar._busy_line.state() == QAbstractAnimation.Running


def _top_row(bar):
    image = bar.grab().toImage()
    return {
        QColor(image.pixel(x, 1)).name() for x in range(0, bar.width(), 4)
    }


def test_busy_paints_a_line_across_the_top_and_moves_nothing(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()
    resting = _top_row(bar)
    was = (window.centralWidget().geometry(), bar.geometry())

    bar.set_busy(True)
    _run_to(qtbot, bar, 0.4)

    assert bar.is_busy()
    assert (window.centralWidget().geometry(), bar.geometry()) == was
    running = _top_row(bar)
    assert running != resting, "the line shows on a framed bar"
    below = QColor(bar.grab().toImage().pixel(
        bar.width() // 2, STATUS_LINE_HEIGHT + 2)).name()
    assert below == QColor(bar.ground()).name(), "only the top band changes"


def test_the_busy_line_is_one_flat_accent_like_a_progress_chunk(qtbot):
    from fxgui import fxstyle

    window = _window(qtbot)
    bar = window.statusBar()
    bar.set_busy(True)
    _run_to(qtbot, bar, 0.4)

    assert _top_row(bar) <= {
        QColor(bar.ground()).name(),
        QColor(fxstyle.colors().accent_primary).name(),
    }


def test_the_line_moves_while_busy(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()
    bar.set_busy(True)
    _run_to(qtbot, bar, 0.2)

    first = bar.grab().toImage().copy(0, 0, bar.width(), STATUS_LINE_HEIGHT)
    _run_to(qtbot, bar, 0.4)
    later = bar.grab().toImage().copy(0, 0, bar.width(), STATUS_LINE_HEIGHT)

    assert first != later


def test_not_busy_gives_the_bar_its_resting_top_back(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()
    resting = _top_row(bar)

    bar.set_busy(True)
    _run_to(qtbot, bar, 0.2)
    bar.set_busy(False)

    assert not bar.is_busy()
    assert _top_row(bar) == resting
    assert not _running(bar), "a stopped line costs nothing"


def test_a_hidden_busy_bar_stops_its_timer_and_resumes_shown(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()
    bar.set_busy(True)

    bar.hide()
    assert not _running(bar)
    bar.show()
    assert _running(bar)


def test_the_line_keeps_its_pace_through_a_stalled_qt_thread(qtbot):
    import time

    window = _window(qtbot)
    bar = window.statusBar()
    bar.set_busy(True)
    _run_to(qtbot, bar, 0.01)
    before = bar._busy_line.currentValue()

    time.sleep(0.6)  # a loading view holding the Qt thread
    qtbot.wait(50)

    assert bar._busy_line.currentValue() - before > 0.3


def test_busy_shows_over_a_hidden_status_line(qtbot):
    window = _window(qtbot, framed=False)
    bar = window.statusBar()
    bar.hide_status_line()
    resting = _top_row(bar)

    bar.set_busy(True)
    _run_to(qtbot, bar, 0.2)

    assert _top_row(bar) != resting
