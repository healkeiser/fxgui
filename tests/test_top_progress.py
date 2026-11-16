"""FXTopProgress: a 2 px accent line along its parent's top edge."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QAccessible
from qtpy.QtWidgets import QApplication, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXTopProgress


@pytest.fixture
def pane(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.resize(300, 100)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_it_hides_until_started_and_lets_the_mouse_through(pane):
    progress = FXTopProgress(pane)
    assert not progress.isVisible()
    assert progress.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert progress.focusPolicy() == Qt.NoFocus


def test_it_runs_along_the_top_edge_and_follows_resizes(pane):
    progress = FXTopProgress(pane)
    progress.set_value(0.5)
    assert progress.isVisible()
    assert (progress.x(), progress.y(), progress.height()) == (0, 0, 2)
    assert progress.width() == 300
    pane.resize(420, 100)
    QApplication.processEvents()
    assert progress.width() == 420


def test_a_value_draws_that_share_of_the_width_in_the_accent(pane):
    progress = FXTopProgress(pane)
    progress.set_value(0.4)
    image = progress.grab().toImage()
    accent = fxstyle.colors().accent_primary.lower()
    assert image.pixelColor(10, 1).name() == accent
    assert image.pixelColor(110, 1).name() == accent
    assert image.pixelColor(130, 1).name() != accent


def test_set_value_clamps_and_reports_a_percent(pane):
    progress = FXTopProgress(pane)
    progress.set_value(1.5)
    assert progress.fraction() == 1.0
    assert (progress.minimum(), progress.maximum(), progress.value()) == (
        0, 100, 100)
    progress.set_value(0.42)
    assert progress.value() == 42
    assert not progress.is_indeterminate()


def test_screen_readers_see_a_progress_bar_with_its_value(pane):
    progress = FXTopProgress(pane)
    progress.set_value(0.4)
    interface = QAccessible.queryAccessibleInterface(progress)
    assert interface.role() == QAccessible.ProgressBar
    assert interface.valueInterface().currentValue() == 40


def test_reduced_motion_shows_a_still_full_line_and_hides_at_once(pane):
    progress = FXTopProgress(pane)
    progress.start()
    assert progress.isVisible()
    assert progress.is_indeterminate()
    assert progress.fraction() == 1.0
    progress.finish()
    assert not progress.isVisible()


def test_with_motion_it_waits_creeps_and_runs_out(qtbot, pane, motion):
    progress = FXTopProgress(pane)
    progress.start()
    # Only a wait long enough to notice shows.
    assert not progress.isVisible()
    qtbot.waitUntil(lambda: progress.fraction() > 0.05, timeout=2000)
    assert progress.isVisible()
    assert progress.fraction() < 0.9
    progress.finish()
    assert progress.isVisible()
    qtbot.waitUntil(lambda: not progress.isVisible(), timeout=2000)
    assert progress.fraction() == 1.0


def test_a_short_wait_never_shows(qtbot, pane, motion):
    progress = FXTopProgress(pane)
    progress.start()
    progress.finish()
    assert not progress.isVisible()
    qtbot.wait(250)
    assert not progress.isVisible()
