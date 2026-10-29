"""Timeline zoom, frame 0, and the range spinboxes keep the view consistent."""

# Third-party
from qtpy.QtCore import QEvent, QPoint, QPointF, Qt
from qtpy.QtGui import QMouseEvent, QWheelEvent
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


def _mouse(kind, track, frame, buttons, modifiers):
    """Return a mouse event at `frame`'s x on `track`, no cursor moved."""
    first, last = track._timeline.view_range()
    usable = track.width() - 2 * track.EDGE_PAD
    x = track.EDGE_PAD + (frame - first) / (last - first) * usable
    point = QPointF(x, track.height() / 2)
    button = Qt.NoButton if kind == QEvent.MouseMove else Qt.LeftButton
    return QMouseEvent(
        kind, point, track.mapToGlobal(point), button, buttons, modifiers
    )


def _sweep(track, start, end, modifiers=Qt.ShiftModifier):
    held = Qt.LeftButton
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, start, held, modifiers)
    )
    track.mouseMoveEvent(_mouse(QEvent.MouseMove, track, end, held, modifiers))
    track.mouseReleaseEvent(
        _mouse(QEvent.MouseButtonRelease, track, end, Qt.NoButton, modifiers)
    )


def test_a_shift_drag_on_the_track_requests_the_swept_loop(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, current_frame=50,
        show_loop_controls=True,
    )
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))

    _sweep(timeline._track_widget, 70, 20)

    assert asked == [(20, 70)]
    assert timeline.current_frame() == 50, "a sweep does not scrub"


def test_a_plain_drag_scrubs_and_requests_no_loop(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))

    _sweep(timeline._track_widget, 20, 70, Qt.NoModifier)

    assert asked == []
    assert timeline.current_frame() == 70


def _loop(timeline):
    loop = timeline._regions.get("loop")
    return None if loop is None else (loop["start"], loop["end"])


def test_a_sweep_draws_as_it_grows_then_leaves_the_loop_to_the_consumer(
    qtbot, qapp
):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    track = timeline._track_widget
    held, shift = Qt.LeftButton, Qt.ShiftModifier
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, 20, held, shift)
    )
    track.mouseMoveEvent(_mouse(QEvent.MouseMove, track, 70, held, shift))
    assert _loop(timeline) == (20, 70)

    track.mouseReleaseEvent(
        _mouse(QEvent.MouseButtonRelease, track, 70, Qt.NoButton, shift)
    )

    assert _loop(timeline) is None, "a consumer that ignores it shows none"


def test_a_plain_drag_after_a_sweep_scrubs(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))
    _sweep(timeline._track_widget, 20, 70)

    _sweep(timeline._track_widget, 30, 40, Qt.NoModifier)

    assert asked == [(20, 70)]
    assert timeline.current_frame() == 40


def test_a_lost_release_ends_the_sweep_and_requests_nothing(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, current_frame=50,
        show_loop_controls=True,
    )
    timeline.set_loop_region(10, 30)
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))
    track = timeline._track_widget
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, 60, Qt.LeftButton,
               Qt.ShiftModifier)
    )
    track.mouseMoveEvent(
        _mouse(QEvent.MouseMove, track, 70, Qt.LeftButton, Qt.ShiftModifier)
    )

    # The release went to another window: hover arrives with no button.
    track.mouseMoveEvent(
        _mouse(QEvent.MouseMove, track, 80, Qt.NoButton, Qt.NoModifier)
    )

    assert asked == []
    assert _loop(timeline) == (10, 30)
    assert timeline.current_frame() == 50, "hover does not scrub"


def test_a_press_after_a_lost_release_scrubs(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))
    track = timeline._track_widget
    held, shift = Qt.LeftButton, Qt.ShiftModifier
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, 20, held, shift)
    )
    track.mouseMoveEvent(_mouse(QEvent.MouseMove, track, 70, held, shift))

    # The release was lost and no move came: the next press is a plain one.
    _sweep(track, 40, 45, Qt.NoModifier)

    assert asked == []
    assert _loop(timeline) is None
    assert timeline.current_frame() == 45


def test_a_shift_release_far_from_its_press_requests_the_loop(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))
    track = timeline._track_widget
    shift = Qt.ShiftModifier
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, 20, Qt.LeftButton, shift)
    )

    track.mouseReleaseEvent(
        _mouse(QEvent.MouseButtonRelease, track, 70, Qt.NoButton, shift)
    )

    assert asked == [(20, 70)]


def test_a_shift_press_ends_a_scrub_whose_release_was_lost(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    track = timeline._track_widget
    held = Qt.LeftButton
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, 30, held, Qt.NoModifier)
    )
    _sweep(track, 60, 80)

    # A popup ate the next press: a held move reaches the track alone.
    track.mouseMoveEvent(
        _mouse(QEvent.MouseMove, track, 90, held, Qt.NoModifier)
    )

    assert timeline.current_frame() == 30


def test_a_sweep_puts_back_a_bracketed_loop_with_its_brackets(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    timeline.set_loop_region(10, 30)

    _sweep(timeline._track_widget, 20, 70)

    assert timeline._regions["loop"]["brackets"] is True


def test_a_sweep_keeps_the_loop_s_colour_and_brackets(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    timeline.set_region("loop", 10, 30, "#ff0000")
    track = timeline._track_widget
    held, shift = Qt.LeftButton, Qt.ShiftModifier
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, 20, held, shift)
    )
    track.mouseMoveEvent(_mouse(QEvent.MouseMove, track, 70, held, shift))
    assert timeline._regions["loop"]["color"] == "#ff0000"

    track.mouseReleaseEvent(
        _mouse(QEvent.MouseButtonRelease, track, 70, Qt.NoButton, shift)
    )

    loop = timeline._regions["loop"]
    assert (loop["start"], loop["end"], loop["color"]) == (10, 30, "#ff0000")
    assert loop["brackets"] is False


def test_a_scrub_whose_release_was_lost_stops_on_hover(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=1, end_frame=100)
    track = timeline._track_widget
    track.mousePressEvent(
        _mouse(QEvent.MouseButtonPress, track, 30, Qt.LeftButton,
               Qt.NoModifier)
    )

    track.mouseMoveEvent(
        _mouse(QEvent.MouseMove, track, 80, Qt.NoButton, Qt.NoModifier)
    )

    assert timeline.current_frame() == 30


def test_a_shift_click_that_drifts_a_pixel_requests_nothing(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=1000, show_loop_controls=True
    )
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))
    track = timeline._track_widget
    # A sweep before leaves nothing that counts the drift as a move.
    _sweep(track, 100, 900)
    held, shift = Qt.LeftButton, Qt.ShiftModifier
    press = _mouse(QEvent.MouseButtonPress, track, 500, held, shift)
    drift = QPointF(press.position().x() + 1, press.position().y())
    track.mousePressEvent(press)
    track.mouseMoveEvent(QMouseEvent(
        QEvent.MouseMove, drift, track.mapToGlobal(drift), Qt.NoButton,
        held, shift,
    ))
    track.mouseReleaseEvent(QMouseEvent(
        QEvent.MouseButtonRelease, drift, track.mapToGlobal(drift),
        Qt.LeftButton, Qt.NoButton, shift,
    ))

    assert asked == [(100, 900)]
    assert _loop(timeline) is None


def test_a_shift_click_with_no_loop_leaves_none(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )

    _sweep(timeline._track_widget, 60, 60)

    assert _loop(timeline) is None


def test_a_shift_click_keeps_the_loop_it_found(qtbot, qapp):
    timeline = _timeline(
        qtbot, start_frame=1, end_frame=100, show_loop_controls=True
    )
    timeline.set_loop_region(10, 30)
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))

    _sweep(timeline._track_widget, 60, 60)

    assert asked == []
    loop = timeline._regions["loop"]
    assert (loop["start"], loop["end"]) == (10, 30)


def test_without_loop_controls_a_shift_drag_scrubs(qtbot, qapp):
    timeline = _timeline(qtbot, start_frame=1, end_frame=100)
    asked = []
    timeline.loop_region_requested.connect(lambda a, b: asked.append((a, b)))

    _sweep(timeline._track_widget, 20, 70)

    assert asked == []
    assert timeline.current_frame() == 70


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

    play = timeline._play_btn
    middle = play.mapTo(timeline, play.rect().center()).x()
    assert abs(middle - timeline.width() / 2) <= 40
    assert extra.geometry().right() >= timeline.width() - 2


def test_a_player_hides_the_range_and_the_rate(qtbot, qapp):
    timeline = _timeline(
        qtbot, controls_position="below", show_range=False, show_fps=False)
    hidden = (timeline._start_spinbox, timeline._end_spinbox,
              timeline._view_start_spinbox, timeline._view_end_spinbox,
              timeline._fps_spinbox)
    assert not any(widget.isVisible() for widget in hidden)
    assert timeline._track_widget.isVisible()
    assert timeline._play_btn.isVisible()


def test_a_borrowed_clock_leaves_the_frame_to_its_owner(qtbot, qapp):
    """Play only signals; set_frame moves the playhead without emitting."""
    timeline = _timeline(qtbot, start_frame=1, end_frame=100, own_clock=False)
    moved = []
    timeline.frame_changed.connect(moved.append)
    with qtbot.waitSignal(timeline.playback_started):
        timeline.play()
    qtbot.wait(120)
    assert timeline.current_frame() == 1, "no timer moved the playhead"
    timeline.set_frame(12, emit=False)
    assert timeline.current_frame() == 12 and moved == []
    timeline.next_frame()
    assert moved == [13], "a person's step still says so"


def test_in_and_out_stand_a_group_apart_from_the_steps(qtbot, qapp):
    timeline = _timeline(qtbot, controls_position="below")
    timeline.resize(900, 70)
    qapp.processEvents()
    mark_in, start = timeline._mark_in_btn, timeline._goto_start_btn
    prev, play = timeline._prev_btn, timeline._play_btn
    assert start.x() - mark_in.geometry().right() > prev.x() - (
        start.geometry().right()
    )
    # A bare icon as its neighbours are, not the accent: as Lumen's.
    assert play.isFlat()
    timeline.play()
    timeline.stop()
    assert not play.icon().isNull()


def test_a_narrow_timeline_drops_the_jumps_then_the_frame_field(
    qtbot, qapp
):
    timeline = _timeline(
        qtbot, controls_position="below", show_range=False, show_fps=False)
    wide = timeline.width()
    assert timeline._goto_start_btn.isVisible()
    assert timeline.minimumWidth() < timeline.layout().sizeHint().width()

    timeline.resize(timeline.minimumWidth(), timeline.height())
    assert not timeline._goto_start_btn.isVisible()
    assert not timeline._goto_end_btn.isVisible()
    assert not timeline._spinbox.isVisible()
    assert timeline._play_btn.isVisible() and timeline._loop_btn.isVisible()

    timeline.resize(wide, timeline.height())
    assert timeline._goto_end_btn.isVisible() and timeline._spinbox.isVisible()


def test_a_zoomed_track_paints_as_a_fresh_one(qtbot, qapp):
    """The tick lines are cached per window; a stale cache would show."""
    used = _timeline(qtbot, start_frame=1, end_frame=200)
    used._track_widget.grab()
    used.set_view_range(20, 60)
    fresh = _timeline(qtbot, start_frame=1, end_frame=200)
    fresh.set_view_range(20, 60)
    assert used._track_widget.grab().toImage() == (
        fresh._track_widget.grab().toImage()
    )


def test_the_track_rect_spans_the_frames_the_track_draws(qtbot, qapp):
    timeline = _timeline(
        qtbot, controls_position="below", show_range=False, show_fps=False)
    track = timeline._track_widget
    rect = timeline.track_rect()
    left = track.mapTo(timeline, QPoint(0, 0)).x()
    assert rect.left() == left + track.EDGE_PAD
    assert rect.width() == track.width() - 2 * track.EDGE_PAD
    assert track._frame_at(rect.left() - left) == timeline.view_range()[0]
    assert track._frame_at(rect.right() + 1 - left) == timeline.view_range()[1]


def test_zoom_view_is_the_wheel_s_zoom(qtbot, qapp):
    wheeled = _timeline(qtbot, start_frame=1, end_frame=200)
    called = _timeline(qtbot, start_frame=1, end_frame=200)
    _wheel(wheeled._track_widget, 120)
    called.zoom_view(1, 0.5)
    assert called.view_range() == wheeled.view_range() != (1, 200)
    called.zoom_view(-1, 0.5)
    assert called.view_range() != wheeled.view_range()
