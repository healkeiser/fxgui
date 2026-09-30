"""Timeline zoom, frame 0, and the range spinboxes keep the view consistent."""

# Third-party
from qtpy.QtCore import QPoint, QPointF, Qt
from qtpy.QtGui import QWheelEvent

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXTimelineSlider


def _timeline(qtbot, **kwargs):
    timeline = FXTimelineSlider(**kwargs)
    qtbot.addWidget(timeline)
    timeline.resize(600, 60)
    timeline.show()
    qtbot.waitExposed(timeline)
    return timeline


def _wheel(track, delta):
    centre = QPointF(track.width() / 2, track.height() / 2)
    event = QWheelEvent(
        centre, track.mapToGlobal(centre), QPoint(0, 0), QPoint(0, delta),
        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False,
    )
    track.wheelEvent(event)


def test_zooming_out_of_the_smallest_window_grows_it(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=1, end_frame=100)
    timeline.set_view_range(10, 12)
    for _ in range(3):
        before = timeline.view_range
        _wheel(timeline._track_widget, -120)
        after = timeline.view_range
        assert after[1] - after[0] > before[1] - before[0]


def test_frame_zero_is_a_valid_start_frame(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=-10, end_frame=10, current_frame=0)
    assert timeline.current_frame == 0


def test_start_spinbox_goes_through_set_range_and_clamps_the_view(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, controls_position="below"
    )
    timeline.set_view_range(40, 60)
    timeline.set_frame(45)

    timeline._start_spinbox.setValue(50)

    assert timeline.frame_range == (50, 100)
    first, last = timeline.view_range
    assert 50 <= first and last <= 100
    assert timeline.current_frame == 50
    assert timeline._view_start_spinbox.value() == first


def test_start_spinbox_past_the_end_is_refused(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=1, end_frame=100)
    timeline._start_spinbox.setValue(150)
    assert timeline.frame_range == (1, 100)
    assert timeline._start_spinbox.value() == 1


def test_track_reads_theme_colours_at_paint_time(qtbot, qapp):
    timeline = _timeline(qtbot)
    assert not isinstance(timeline, fxstyle.FXThemeAware)
    fxstyle.apply_theme("light")
    assert timeline._track_color.name() == fxstyle.colors().surface_alt.lower()
