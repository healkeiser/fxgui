"""FXLoadingSpinner idles while hidden; FXLoadingOverlay follows its parent."""

# Third-party
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import FXLoadingOverlay, FXLoadingSpinner


def test_a_hidden_spinner_stops_its_timer_and_resumes_when_shown(qtbot):
    spinner = FXLoadingSpinner()
    qtbot.addWidget(spinner)
    spinner.start()
    qtbot.waitExposed(spinner)

    spinner.hide()
    assert not spinner._timer.isActive()
    assert spinner.is_spinning()

    spinner.show()
    assert spinner._timer.isActive()


def test_a_stopped_spinner_stays_stopped_when_shown(qtbot):
    spinner = FXLoadingSpinner()
    qtbot.addWidget(spinner)
    spinner.start()
    spinner.stop()

    spinner.hide()
    spinner.show()

    assert not spinner._timer.isActive()


def test_the_spinner_has_no_angle_property():
    assert not hasattr(FXLoadingSpinner, "angle")


def test_the_overlay_follows_its_parent_resizing(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    parent.resize(200, 100)
    overlay = FXLoadingOverlay(parent, "Loading")
    parent.show()
    overlay.show()

    parent.resize(400, 300)

    assert overlay.geometry() == parent.rect()


def test_the_overlay_carries_no_dead_sheet(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)

    overlay = FXLoadingOverlay(parent, "Loading")

    assert overlay.styleSheet() == ""
    assert overlay._message_label.styleSheet() == ""
