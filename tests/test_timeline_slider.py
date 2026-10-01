"""Timeline zoom, frame 0, and the range spinboxes keep the view consistent."""

# Third-party
from qtpy.QtCore import QPoint, QPointF, Qt
from qtpy.QtGui import QWheelEvent
from qtpy.QtTest import QTest

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
        before = timeline.view_range()
        _wheel(timeline._track_widget, -120)
        after = timeline.view_range()
        assert after[1] - after[0] > before[1] - before[0]


def test_frame_zero_is_a_valid_start_frame(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=-10, end_frame=10, current_frame=0)
    assert timeline.current_frame() == 0


def test_start_spinbox_goes_through_set_range_and_clamps_the_view(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, controls_position="below"
    )
    timeline.set_view_range(40, 60)
    timeline.set_frame(45)

    timeline._start_spinbox.setValue(50)

    assert timeline.frame_range() == (50, 100)
    first, last = timeline.view_range()
    assert 50 <= first and last <= 100
    assert timeline.current_frame() == 50
    assert timeline._view_start_spinbox.value() == first


def test_a_typed_range_applies_on_enter_not_per_key(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=1, end_frame=100, current_frame=50)
    field = timeline._end_spinbox
    field.setFocus()
    field.selectAll()

    QTest.keyClicks(field, "250")
    assert timeline.frame_range() == (1, 100)
    assert timeline.current_frame() == 50, "no stop at frame 2 on the way"
    QTest.keyClick(field, Qt.Key_Return)

    assert timeline.frame_range() == (1, 250)
    assert timeline.current_frame() == 50


def test_start_spinbox_past_the_end_is_refused(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=1, end_frame=100)
    timeline._start_spinbox.setValue(150)
    assert timeline.frame_range() == (1, 100)
    assert timeline._start_spinbox.value() == 1


def _pixel(widget, x, y):
    return widget.grab().toImage().pixelColor(x, y).name()


def test_track_reads_theme_colours_at_paint_time(qtbot, qapp):
    timeline = _timeline(qtbot, current_frame=100)
    fxstyle.apply_theme("light")
    track = timeline._track_widget
    assert _pixel(track, track.width() // 3, track.height() // 2) == (
        fxstyle.colors().surface_alt.lower()
    )


def test_the_tipped_keys_drive_the_timeline(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, current_frame=50,
        show_loop_controls=True,
    )
    marks = []
    timeline.in_point_requested.connect(marks.append)
    timeline.out_point_requested.connect(marks.append)

    for key, frame in (
        (Qt.Key_Right, 51), (Qt.Key_Left, 50),
        (Qt.Key_End, 100), (Qt.Key_Home, 1),
    ):
        QTest.keyClick(timeline, key)
        assert timeline.current_frame() == frame
    QTest.keyClick(timeline, Qt.Key_I)
    QTest.keyClick(timeline, Qt.Key_O)
    QTest.keyClick(timeline, Qt.Key_Space)

    assert marks == [1, 1]
    assert timeline._is_playing
    timeline.stop()


def test_a_click_on_the_track_gives_the_timeline_its_keys(qtbot, qapp):
    timeline = _timeline(qtbot)
    track = timeline._track_widget

    QTest.mouseClick(track, Qt.LeftButton, Qt.NoModifier, track.rect().center())

    assert timeline.focusWidget() is timeline


def test_playback_follows_the_clock_at_a_fractional_rate(
    qtbot, qapp, monkeypatch
):
    from fxgui.fxwidgets import _timeline_slider

    timeline = _timeline(qtbot, start_frame=1, end_frame=1000, fps=23.976)
    now = [100.0]
    monkeypatch.setattr(_timeline_slider.time, "perf_counter", lambda: now[0])
    timeline.play()
    timeline._playback_timer.stop()

    now[0] += 10.0
    timeline._on_playback_tick()

    assert timeline.fps() == 23.976
    assert timeline.current_frame() == 1 + int(10.0 * 23.976)
    timeline.stop()


def test_looping_wraps_by_the_clock_and_stopping_holds_the_end(
    qtbot, qapp, monkeypatch
):
    from fxgui.fxwidgets import _timeline_slider

    timeline = _timeline(qtbot, start_frame=1, end_frame=10, current_frame=9)
    now = [0.0]
    monkeypatch.setattr(_timeline_slider.time, "perf_counter", lambda: now[0])
    timeline.play()
    timeline._playback_timer.stop()
    now[0] += 4 / 24
    timeline._on_playback_tick()
    assert timeline.current_frame() == 3

    timeline.set_loop_playback(False)
    now[0] += 1.0
    timeline._on_playback_tick()
    assert timeline.current_frame() == 10
    assert not timeline._is_playing


def test_one_record_of_rate_and_loop(qtbot, qapp):
    timeline = _timeline(qtbot, show_controls=False)
    toggled = []
    timeline.loop_toggled.connect(toggled.append)

    timeline.set_fps(30)
    timeline.set_loop_playback(False)

    assert timeline._fps_spinbox.value() == timeline.fps() == 30
    assert timeline.loop_playback() is False
    assert toggled == [False]
    assert timeline._loop_btn.isHidden()


def test_markers_take_a_token_and_follow_the_theme(qtbot, qapp):
    token = _timeline(qtbot, start_frame=0, end_frame=10, current_frame=5)
    token.set_region("shot", 0, 10, color="feedback_error_foreground")
    hexed = _timeline(qtbot, start_frame=0, end_frame=10, current_frame=5)
    edge = (token._track_widget.EDGE_PAD, 1)
    seen = set()

    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        hexed.set_region(
            "shot", 0, 10, color=fxstyle.colors().feedback_error_foreground
        )
        drawn = _pixel(token._track_widget, *edge)
        assert drawn == _pixel(hexed._track_widget, *edge)
        seen.add(drawn)

    assert len(seen) == 2, "the token followed the switch"


def test_keyframes_wear_the_keyframe_token(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=0, end_frame=10, current_frame=0)
    timeline.add_keyframe(5)
    track = timeline._track_widget
    x = track.EDGE_PAD + (track.width() - 2 * track.EDGE_PAD) // 2

    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        ink = getattr(fxstyle.colors(), FXTimelineSlider.KEYFRAME_TOKEN)
        assert _pixel(track, x, track.height() // 2) == ink.lower()


def test_the_transport_stays_centred_beside_wide_extras(qtbot, qapp):
    from qtpy.QtWidgets import QPushButton

    timeline = FXTimelineSlider(controls_position="below")
    qtbot.addWidget(timeline)
    extra = QPushButton("A rather wide consumer button")
    timeline.add_control_widget(extra)
    timeline.resize(900, 70)
    timeline.show()
    qtbot.waitExposed(timeline)
    qapp.processEvents()

    field = timeline._spinbox
    middle = field.mapTo(timeline, field.rect().center()).x()
    assert abs(middle - timeline.width() / 2) <= 40
    assert extra.geometry().right() >= timeline.width() - 2
