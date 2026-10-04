"""Timeline/scrubber widget for DCC applications."""

# Built-in
import time
from bisect import bisect_left, bisect_right
from typing import Callable, Dict, Iterable, List, Optional, Tuple

# Third-party
from qtpy.QtCore import QLineF, QPointF, Qt, QTimer, Signal
from qtpy.QtGui import (
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygonF,
)
from qtpy.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._tips import apply_tip


def _coalesce_runs(frames) -> List[Tuple[int, int]]:
    """Return sorted `frames` as contiguous (start, end) runs."""
    if not frames:
        return []
    ordered = sorted(frames)
    runs = []
    start = prev = ordered[0]
    for frame in ordered[1:]:
        if frame == prev + 1:
            prev = frame
            continue
        runs.append((start, prev))
        start = prev = frame
    runs.append((start, prev))
    return runs


def _ink(color: Optional[str]) -> QColor:
    """Return `color`, a theme token or any colour, now; None is the accent."""
    return fxstyle.qcolor(color or "accent_primary")


class _FpsBox(QDoubleSpinBox):
    """A frame rate field that shows 24 as "24" and 23.976 as "23.976"."""

    def textFromValue(self, value: float) -> str:
        """Drop trailing zeros."""
        return f"{value:g}"


class FXTimelineSlider(QWidget):
    """A timeline/scrubber widget for DCC applications.

    - Keyframe markers and a current frame indicator, with optional
      playback controls.
    - Keys while the timeline has focus: Home, Left, Space, Right and End;
      I and O with the in/out controls.
    - Track zoom: the mouse wheel zooms around the cursor, a middle-mouse
      drag pans, `reset_view()` restores the full range.
    - Named marker layers (lines or a top strip) and named regions, mapped
      through the zoomed window. The widget assigns no meaning to a layer.
    - Optional in/out controls (`show_loop_controls`) that request marking
      the current frame; the consumer typically calls `set_loop_region`.
    - Optional keyframe navigation (`show_keyframe_controls`).
    - A hover line with the hovered frame number.
    - Narrow, the "below" layout drops the go-to-start and go-to-end
      buttons, then the frame field, so the transport keeps one row.

    Args:
        parent: Parent widget.
        start_frame: Start frame of the timeline.
        end_frame: End frame of the timeline.
        current_frame: Initial current frame.
        fps: Frames per second for playback; fractional rates such as
            23.976 play at that rate.
        show_controls: Whether to show playback controls.
        show_spinbox: Whether to show the frame spinbox.
        show_loop_controls: Whether to show the mark-in/mark-out buttons.
        show_keyframe_controls: Whether to show the previous/next-keyframe
            navigation buttons.
        controls_position: "left" (one row) or "below" (full-width track on
            top, the transport centred below, fps far left, consumer extras
            from add_control_widget() far right).
        show_range: Whether to show the start and end frame fields, and the
            view fields of the "below" layout; a player's range is fixed.
        show_fps: Whether to show the frame rate field.
        own_clock: Whether playback advances the frame. False for a
            consumer that keeps time itself, such as a movie: play and stop
            only switch the button and emit, the consumer moves the
            playhead with `set_frame(frame, emit=False)`, and
            `frame_changed` then means the person moved it.

    Raises:
        ValueError: `controls_position` is neither "left" nor "below".

    Signals:
        frame_changed: Emitted when the current frame changes.
        playback_started: Emitted when playback starts.
        playback_stopped: Emitted when playback stops.
        view_changed: Emitted with (first, last) when the visible frame
            window changes (zoom, pan, or reset).
        in_point_requested: Mark-in pressed; carries the current frame.
        out_point_requested: Mark-out pressed; carries the current frame.
        loop_toggled: Emitted with the new loop playback state.

    Examples:
        >>> timeline = FXTimelineSlider(start_frame=1, end_frame=100)
        >>> timeline.frame_changed.connect(lambda f: print(f"Frame: {f}"))
        >>> timeline.add_keyframe(10)
        >>> timeline.set_marker_frames(
        ...     "cached", {2, 3, 4}, "feedback_success_foreground", "strip")
        >>> timeline.set_marker_frames("errors", {40, 41}, "#ef4444")
        >>> timeline.set_loop_region(20, 60)
    """

    frame_changed = Signal(int)
    playback_started = Signal()
    playback_stopped = Signal()
    view_changed = Signal(int, int)
    in_point_requested = Signal(int)
    out_point_requested = Signal(int)
    loop_toggled = Signal(bool)

    # Smallest zoomable window, in frames.
    MIN_VIEW_SPAN = 2
    # Region and strip fill alphas over their 1px solid edge.
    REGION_FILL_ALPHA = 50
    STRIP_FILL_ALPHA = 80
    STRIP_HEIGHT = 3
    # The token keyframe diamonds are drawn in; a subclass names its own.
    KEYFRAME_TOKEN = "feedback_warning_foreground"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        start_frame: int = 1,
        end_frame: int = 100,
        current_frame: Optional[int] = None,
        fps: float = 24,
        show_controls: bool = True,
        show_spinbox: bool = True,
        show_loop_controls: bool = False,
        show_keyframe_controls: bool = False,
        controls_position: str = "left",
        show_range: bool = True,
        show_fps: bool = True,
        own_clock: bool = True,
    ):
        super().__init__(parent)
        if controls_position not in ("left", "below"):
            raise ValueError(
                f"Unknown controls_position: {controls_position!r}"
            )
        self._show_loop_controls = show_loop_controls
        self._own_clock = own_clock

        # The range is held here; the start and end spinboxes show it.
        self._start_frame = start_frame
        self._end_frame = end_frame
        self._current_frame = (
            start_frame if current_frame is None else current_frame
        )
        self._keyframes: List[int] = []
        self._is_playing = False
        self._is_dragging = False
        # Visible frame window (None = follow the full range).
        self._view_start: Optional[int] = None
        self._view_end: Optional[int] = None
        # name -> {"frames", "color", "style", "runs", "sorted"}
        self._marker_layers: dict = {}
        # name -> {"start", "end", "color", "brackets"}
        self._regions: dict = {}

        # Playback reads a clock, so the rate holds whatever the timer's
        # whole-millisecond ticks do: the frame is the anchor plus the time
        # since it times the rate.
        self._anchor_frame = self._current_frame
        self._anchor_time = 0.0
        self._ticking = False
        self._playback_timer = QTimer(self)
        self._playback_timer.setTimerType(Qt.PreciseTimer)
        self._playback_timer.timeout.connect(self._on_playback_tick)

        self.setFocusPolicy(Qt.StrongFocus)

        # Every control is built, so none is ever missing; the flags decide
        # which are laid out.
        self._start_spinbox = self._spinbox_for(
            start_frame, "Start Frame", "First frame of the timeline range"
        )
        self._start_spinbox.valueChanged.connect(self._on_start_changed)
        self._end_spinbox = self._spinbox_for(
            end_frame, "End Frame", "Last frame of the timeline range"
        )
        self._end_spinbox.valueChanged.connect(self._on_end_changed)

        self._view_start_spinbox = None
        self._view_end_spinbox = None
        if controls_position == "below":
            # Typing a window zooms to it; only this layout has room.
            self._view_start_spinbox = self._spinbox_for(
                start_frame,
                "View Start",
                "First visible frame; edit to zoom the track",
            )
            self._view_end_spinbox = self._spinbox_for(
                end_frame,
                "View End",
                "Last visible frame; edit to zoom the track",
            )
            for spinbox in (self._view_start_spinbox, self._view_end_spinbox):
                spinbox.valueChanged.connect(self._on_view_spin_changed)
            self.view_changed.connect(self._sync_view_spinboxes)

        self._goto_start_btn = self._button(
            "skip_previous", self.go_to_start,
            "Go to Start", "Jump to the first frame", "Home")
        self._prev_btn = self._button(
            "chevron_left", self.previous_frame,
            "Previous Frame", "Go back one frame", "Left")
        self._play_btn = self._button(
            "play_arrow", self.toggle_playback,
            "Play", "Start playback", "Space", flat=False)
        self._next_btn = self._button(
            "chevron_right", self.next_frame,
            "Next Frame", "Go forward one frame", "Right")
        self._goto_end_btn = self._button(
            "skip_next", self.go_to_end,
            "Go to End", "Jump to the last frame", "End")
        # The loop button's checked state is the one record of loop playback.
        self._loop_btn = self._button(
            "repeat", None,
            "Loop Playback", "Restart from the first frame at the end")
        self._loop_btn.setCheckable(True)
        self._loop_btn.setChecked(True)
        self._loop_btn.toggled.connect(self.loop_toggled)
        self._prev_key_btn = self._button(
            "keyboard_double_arrow_left", self.go_to_previous_keyframe,
            "Previous Keyframe", "Jump to the nearest keyframe before")
        self._next_key_btn = self._button(
            "keyboard_double_arrow_right", self.go_to_next_keyframe,
            "Next Keyframe", "Jump to the nearest keyframe after")
        # login/logout read as entering and leaving the range, and differ
        # from the go-to-start and go-to-end glyphs.
        self._mark_in_btn = self._button(
            "login", self._request_in,
            "Mark In", "Set the loop in point at the current frame", "I")
        self._mark_out_btn = self._button(
            "logout", self._request_out,
            "Mark Out", "Set the loop out point at the current frame", "O")

        self._track_widget = _TimelineTrack(self)
        self._track_widget.setMinimumHeight(24)
        self._track_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )

        self._spinbox = QSpinBox(self)
        self._spinbox.setRange(start_frame, end_frame)
        self._spinbox.setValue(self._current_frame)
        self._spinbox.setFixedWidth(60)
        self._spinbox.valueChanged.connect(self.set_frame)

        # The spinbox's value is the one record of the frame rate.
        self._fps_spinbox = _FpsBox(self)
        self._fps_spinbox.setDecimals(3)
        self._fps_spinbox.setRange(1, 120)
        self._fps_spinbox.setValue(fps)
        self._fps_spinbox.setSuffix(" fps")
        apply_tip(self._fps_spinbox, "FPS", "Frames per second for playback")
        self._fps_spinbox.valueChanged.connect(self._reanchor)

        transport = [self._goto_start_btn, self._prev_btn, self._play_btn,
                     self._next_btn, self._goto_end_btn, self._loop_btn]
        keys = [self._prev_key_btn, self._next_key_btn]
        marks = [self._mark_in_btn, self._mark_out_btn]
        shown = (
            (transport if show_controls else [])
            + (keys if show_controls and show_keyframe_controls else [])
            + (marks if show_controls and show_loop_controls else [])
            + ([self._spinbox] if show_spinbox else [])
        )
        self._extra_controls_layout = QHBoxLayout()
        self._extra_controls_layout.setSpacing(fxstyle.PANE_GAP)

        if controls_position == "below":
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(fxstyle.PANE_GAP)

            track_row = QHBoxLayout()
            track_row.setSpacing(fxstyle.PANE_GAP)
            track_row.addWidget(self._start_spinbox)
            track_row.addWidget(self._view_start_spinbox)
            track_row.addWidget(self._track_widget, 1)
            track_row.addWidget(self._view_end_spinbox)
            track_row.addWidget(self._end_spinbox)
            root.addLayout(track_row)

            # Mirror-symmetric round the frame field: in/out outermost,
            # then start/end, keyframe nav, prev/next. Play sits right of
            # the field, the loop toggle is its left counterpart.
            cluster = QHBoxLayout()
            cluster.setSpacing(2)
            for widget in (
                self._loop_btn, self._mark_in_btn, self._goto_start_btn,
                self._prev_key_btn, self._prev_btn, self._spinbox,
                self._play_btn, self._next_btn, self._next_key_btn,
                self._goto_end_btn, self._mark_out_btn,
            ):
                cluster.addWidget(widget)

            # Equal outer columns keep the cluster centred, whatever sits
            # on either side.
            controls_row = QGridLayout()
            controls_row.setContentsMargins(0, 0, 0, 0)
            controls_row.setColumnStretch(0, 1)
            controls_row.setColumnStretch(2, 1)
            controls_row.addWidget(
                self._fps_spinbox, 0, 0, Qt.AlignLeft | Qt.AlignVCenter
            )
            controls_row.addLayout(cluster, 0, 1)
            controls_row.addLayout(
                self._extra_controls_layout, 0, 2,
                Qt.AlignRight | Qt.AlignVCenter,
            )
            root.addLayout(controls_row)
            self.setMinimumHeight(60)
        else:
            main_layout = QHBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(fxstyle.PANE_GAP)
            main_layout.addWidget(self._start_spinbox)
            controls_layout = QHBoxLayout()
            controls_layout.setSpacing(2)
            for widget in transport + keys + marks:
                controls_layout.addWidget(widget)
            main_layout.addLayout(controls_layout)
            main_layout.addWidget(self._track_widget, 1)
            main_layout.addWidget(self._spinbox)
            main_layout.addWidget(self._end_spinbox)
            main_layout.addWidget(self._fps_spinbox)
            main_layout.addLayout(self._extra_controls_layout)

        # After the layouts parent them: shown unparented, a button would
        # flash up as a window of its own.
        for widget in transport + keys + marks + [self._spinbox]:
            widget.setVisible(widget in shown)
        for widget in (self._start_spinbox, self._end_spinbox,
                       self._view_start_spinbox, self._view_end_spinbox):
            if widget is not None:
                widget.setVisible(show_range)
        self._fps_spinbox.setVisible(show_fps)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Dropped in this order when the row runs out of width.
        self._shed: List[List[QWidget]] = []
        if controls_position == "below":
            self._shed = [
                [w for w in (self._goto_start_btn, self._goto_end_btn)
                 if w in shown],
                [self._spinbox] if self._spinbox in shown else [],
            ]
            # As narrow as the row with everything shed, never narrower.
            self._show_shed(False)
            self.setMinimumWidth(self.layout().minimumSize().width())
            self._show_shed(True)

    def _show_shed(self, shown: bool) -> None:
        for group in self._shed:
            for widget in group:
                widget.setVisible(shown)

    def _fit(self) -> None:
        """Show what the row has room for, dropping in `_shed` order."""
        self._show_shed(True)
        for group in self._shed:
            if self.layout().minimumSize().width() <= self.width():
                return
            for widget in group:
                widget.setVisible(False)

    def resizeEvent(self, event) -> None:
        """Drop or restore the optional controls for the new width."""
        super().resizeEvent(event)
        self._fit()

    def _spinbox_for(self, value: int, title: str, body: str) -> QSpinBox:
        """Return a frame number field holding `value`."""
        spinbox = QSpinBox(self)
        spinbox.setRange(-99999, 99999)
        spinbox.setValue(value)
        # Typed digits apply on Enter or focus out: "250" is not 2, then 25.
        spinbox.setKeyboardTracking(False)
        spinbox.setFixedWidth(55)
        apply_tip(spinbox, title, body)
        return spinbox

    def _button(
        self,
        icon: str,
        slot: Optional[Callable[[], None]],
        title: str,
        body: str,
        keys: str = "",
        flat: bool = True,
    ) -> QPushButton:
        """Return a square transport button a push button's height."""
        button = QPushButton(self)
        fxicons.set_icon(button, icon)
        side = fxstyle.control_height(self)
        button.setFixedSize(side, side)
        button.setFlat(flat)
        if slot is not None:
            button.clicked.connect(slot)
        apply_tip(button, title, body, keys)
        return button

    def add_control_widget(self, widget: QWidget) -> None:
        """Append a consumer widget to the right of the controls."""
        self._extra_controls_layout.addWidget(widget)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Run the transport key the buttons' tips name."""
        actions = {
            Qt.Key_Home: self.go_to_start,
            Qt.Key_Left: self.previous_frame,
            Qt.Key_Space: self.toggle_playback,
            Qt.Key_Right: self.next_frame,
            Qt.Key_End: self.go_to_end,
        }
        if self._show_loop_controls:
            actions[Qt.Key_I] = self._request_in
            actions[Qt.Key_O] = self._request_out
        action = actions.get(event.key())
        if action is None or event.modifiers() not in (
            Qt.NoModifier,
            Qt.KeypadModifier,
        ):
            super().keyPressEvent(event)
            return
        action()
        event.accept()

    def _request_in(self) -> None:
        """Ask the consumer to mark the current frame as the in point."""
        self.in_point_requested.emit(self._current_frame)

    def _request_out(self) -> None:
        """Ask the consumer to mark the current frame as the out point."""
        self.out_point_requested.emit(self._current_frame)

    def current_frame(self) -> int:
        """Return the current frame."""
        return self._current_frame

    def frame_range(self) -> Tuple[int, int]:
        """Return the frame range as (start, end)."""
        return (self._start_frame, self._end_frame)

    def view_range(self) -> Tuple[int, int]:
        """Return the visible window as (first, last); the range unzoomed."""
        if self._view_start is None or self._view_end is None:
            return (self._start_frame, self._end_frame)
        return (self._view_start, self._view_end)

    def is_view_zoomed(self) -> bool:
        """Return whether the track shows a sub-window of the full range."""
        return self.view_range() != (self._start_frame, self._end_frame)

    def set_view_range(self, first: int, last: int) -> None:
        """Zoom the track to the [first, last] frame window.

        The window is clamped inside the full range; a window covering the
        full range (or more) resets the view.
        """
        first, last = int(round(first)), int(round(last))
        span = max(self.MIN_VIEW_SPAN, last - first)
        full_span = self._end_frame - self._start_frame
        if span >= full_span:
            self.reset_view()
            return
        first = max(self._start_frame, min(first, self._end_frame - span))
        last = first + span
        if (first, last) == (self._view_start, self._view_end):
            return
        self._view_start, self._view_end = first, last
        self._track_widget.update()
        self.view_changed.emit(first, last)

    def reset_view(self) -> None:
        """Restore the track to the full frame range."""
        if self._view_start is None and self._view_end is None:
            return
        self._view_start = self._view_end = None
        self._track_widget.update()
        self.view_changed.emit(self._start_frame, self._end_frame)

    def _on_view_spin_changed(self, _value: int) -> None:
        """Zoom the track to the window typed in the view spinboxes."""
        self.set_view_range(
            self._view_start_spinbox.value(), self._view_end_spinbox.value()
        )
        # set_view_range clamps, and skips the signal when nothing changed.
        self._sync_view_spinboxes(*self.view_range())

    def _sync_view_spinboxes(self, first: int, last: int) -> None:
        """Show the visible window in the view spinboxes, without re-emit."""
        if self._view_start_spinbox is None:
            return
        for spinbox, value in (
            (self._view_start_spinbox, first),
            (self._view_end_spinbox, last),
        ):
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def set_marker_frames(
        self,
        name: str,
        frames: Iterable[int],
        color: Optional[str] = None,
        style: str = "line",
    ) -> None:
        """Set (or replace) a named marker layer painted on the track.

        Args:
            name: Layer identifier; setting the same name replaces it.
            frames: Iterable of frame numbers. Empty removes the layer.
            color: A theme token such as "feedback_success_foreground", or
                any QColor value. Read when painted, so a token follows a
                theme switch; None is the accent.
            style: "line" for 1px vertical lines at each frame, or "strip"
                for a translucent band along the top edge with a 1px solid
                top line over contiguous frame runs.

        Raises:
            ValueError: `style` is neither "line" nor "strip".
        """
        if style not in ("line", "strip"):
            raise ValueError(f"Unknown marker style: {style!r}")
        frames = set(frames or ())
        if not frames:
            self.remove_markers(name)
            return
        self._marker_layers[name] = {
            "frames": frames,
            "color": color,
            "style": style,
            # Worked out once: the paint path runs per playback frame.
            "runs": _coalesce_runs(frames) if style == "strip" else None,
            "sorted": sorted(frames) if style == "line" else None,
        }
        self._track_widget.update()

    def remove_markers(self, name: str) -> None:
        """Remove a named marker layer (no-op if absent)."""
        if self._marker_layers.pop(name, None) is not None:
            self._track_widget.update()

    def set_region(
        self,
        name: str,
        start: int,
        end: int,
        color: Optional[str] = None,
        bracket_edges: bool = False,
    ) -> None:
        """Set (or replace) a named frame region painted on the track.

        Args:
            name: Region identifier; setting the same name replaces it.
            start: First frame of the region.
            end: Last frame of the region.
            color: A theme token or any QColor value, read when painted;
                None is the accent.
            bracket_edges: Draw the edges as [ ] brackets, so a zero-width
                region still reads as a marker.
        """
        self._regions[name] = {
            "start": int(min(start, end)),
            "end": int(max(start, end)),
            "color": color,
            "brackets": bool(bracket_edges),
        }
        self._track_widget.update()

    def clear_region(self, name: str) -> None:
        """Remove a named region (no-op if absent)."""
        if self._regions.pop(name, None) is not None:
            self._track_widget.update()

    def set_loop_region(
        self,
        start: Optional[int],
        end: Optional[int],
        color: Optional[str] = None,
    ) -> None:
        """Show the loop in/out range as the bracketed "loop" region.

        `None` for either end clears it.
        """
        if start is None or end is None:
            self.clear_region("loop")
            return
        self.set_region("loop", start, end, color, bracket_edges=True)

    def set_frame(self, frame: int, emit: bool = True) -> None:
        """Set the frame, clamped; `emit` says `frame_changed`."""
        frame = max(self._start_frame, min(frame, self._end_frame))
        if frame == self._current_frame:
            return
        self._current_frame = frame
        self._spinbox.blockSignals(True)
        self._spinbox.setValue(frame)
        self._spinbox.blockSignals(False)
        if not self._ticking:
            self._reanchor()
        self._track_widget.update()
        if emit:
            self.frame_changed.emit(frame)

    def set_range(self, start: int, end: int) -> None:
        """Set the range from `start` to `end`, clamping the frame and view."""
        zoomed = self._view_start is not None and self._view_end is not None
        old_view = self.view_range()
        self._start_frame = start
        self._end_frame = end
        for spinbox, value in (
            (self._start_spinbox, start),
            (self._end_spinbox, end),
        ):
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)
        self._spinbox.setRange(start, end)
        self.set_frame(self._current_frame)
        if zoomed:
            # set_view_range clamps into the new range, or resets.
            self._view_start = self._view_end = None
            self.set_view_range(*old_view)
            if self._view_start is None:
                self.view_changed.emit(start, end)
        self._sync_view_spinboxes(*self.view_range())
        self._track_widget.update()

    def fps(self) -> float:
        """Return the playback frame rate."""
        return self._fps_spinbox.value()

    def set_fps(self, fps: float) -> None:
        """Set the rate, held to 1-120; fractional rates such as 23.976 hold."""
        self._fps_spinbox.setValue(fps)

    def _on_start_changed(self, value: int) -> None:
        """Apply a typed start frame, or put back the last one."""
        start = value if value < self._end_frame else self._start_frame
        self.set_range(start, self._end_frame)

    def _on_end_changed(self, value: int) -> None:
        """Apply a typed end frame, or put back the last one."""
        end = value if value > self._start_frame else self._end_frame
        self.set_range(self._start_frame, end)

    def add_keyframe(self, frame: int) -> None:
        """Mark `frame` as a keyframe."""
        if frame not in self._keyframes:
            self._keyframes.append(frame)
            self._keyframes.sort()
            self._track_widget.update()

    def remove_keyframe(self, frame: int) -> None:
        """Unmark `frame` as a keyframe."""
        if frame in self._keyframes:
            self._keyframes.remove(frame)
            self._track_widget.update()

    def clear_keyframes(self) -> None:
        """Remove all keyframe markers."""
        self._keyframes.clear()
        self._track_widget.update()

    def go_to_previous_keyframe(self) -> None:
        """Jump to the nearest keyframe before the current frame, if any."""
        index = bisect_left(self._keyframes, self._current_frame)
        if index:
            self.set_frame(self._keyframes[index - 1])

    def go_to_next_keyframe(self) -> None:
        """Jump to the nearest keyframe after the current frame, if any."""
        index = bisect_right(self._keyframes, self._current_frame)
        if index < len(self._keyframes):
            self.set_frame(self._keyframes[index])

    def go_to_start(self) -> None:
        """Go to the start frame."""
        self.set_frame(self._start_frame)

    def go_to_end(self) -> None:
        """Go to the end frame."""
        self.set_frame(self._end_frame)

    def next_frame(self) -> None:
        """Advance to the next frame."""
        self.set_frame(self._current_frame + 1)

    def previous_frame(self) -> None:
        """Go to the previous frame."""
        self.set_frame(self._current_frame - 1)

    def loop_playback(self) -> bool:
        """Return whether playback wraps to the start at the end."""
        return self._loop_btn.isChecked()

    def set_loop_playback(self, enabled: bool) -> None:
        """Set whether playback wraps to the start at the end."""
        self._loop_btn.setChecked(bool(enabled))

    def toggle_playback(self) -> None:
        """Toggle playback state."""
        if self._is_playing:
            self.stop()
        else:
            self.play()

    def play(self) -> None:
        """Start playback."""
        self._is_playing = True
        self._reanchor()
        # Ticks at the frame rate; the clock, not the tick count, decides.
        if self._own_clock:
            self._playback_timer.start(max(1, int(1000 / self.fps())))
        fxicons.set_icon(self._play_btn, "pause")
        apply_tip(self._play_btn, "Pause", "Pause playback", "Space")
        self.playback_started.emit()

    def stop(self) -> None:
        """Stop playback."""
        self._is_playing = False
        self._playback_timer.stop()
        fxicons.set_icon(self._play_btn, "play_arrow")
        apply_tip(self._play_btn, "Play", "Start playback", "Space")
        self.playback_stopped.emit()

    def _reanchor(self, *_args) -> None:
        """Count playback from the current frame and the time now."""
        self._anchor_frame = self._current_frame
        self._anchor_time = time.perf_counter()
        if self._is_playing:
            self._playback_timer.setInterval(max(1, int(1000 / self.fps())))

    def _on_playback_tick(self) -> None:
        """Show the frame the clock has reached."""
        elapsed = time.perf_counter() - self._anchor_time
        frame = self._anchor_frame + int(elapsed * self.fps())
        if frame > self._end_frame:
            if not self.loop_playback():
                self.set_frame(self._end_frame)
                self.stop()
                return
            length = self._end_frame - self._start_frame + 1
            frame = self._start_frame + (frame - self._start_frame) % length
        self._ticking = True
        try:
            self.set_frame(frame)
        finally:
            self._ticking = False


class _TimelineTrack(QWidget):
    """Internal widget for drawing the timeline track."""

    # Horizontal inset for the frame<->x mapping: marks at the first/last
    # frame would otherwise be cut in half at the widget edges.
    EDGE_PAD = 6

    def __init__(self, timeline: FXTimelineSlider):
        super().__init__(timeline)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        # Middle-mouse pan state (fractional shift accumulator so slow
        # drags still move the window one frame at a time).
        self._pan_last_x: Optional[float] = None
        self._pan_accum = 0.0
        # Hovered frame (crosshair-style indicator), None when outside.
        self._hover_frame: Optional[int] = None
        self._tick_key: tuple = ()
        self._tick_lines: Dict[bool, List[QLineF]] = {}

    @property
    def _timeline(self) -> FXTimelineSlider:
        """The timeline this track draws, read off the parent.

        Not stored: a reference back to the parent is a cycle, and Python's
        collector then deletes a shown timeline in the middle of an event.
        """
        return self.parentWidget()

    def paintEvent(self, event) -> None:
        """Paint the timeline track."""
        theme = fxstyle.colors()
        text_color = QColor(theme.text)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        track_height = 6
        track_y = (height - track_height) // 2

        # A pill: rounded at half its thickness.
        painter.setBrush(QColor(theme.surface_alt))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            0, track_y, width, track_height, track_height / 2, track_height / 2
        )

        view_first, view_last = self._timeline.view_range()
        frame_range = max(1, view_last - view_first)
        pad = self.EDGE_PAD
        usable = max(1, width - 2 * pad)

        def frame_to_x(frame: int) -> float:
            return pad + (frame - view_first) / frame_range * usable

        minor_color = QColor(text_color)
        minor_color.setAlpha(60)
        major_color = QColor(text_color)
        major_color.setAlpha(170)
        minor_pen = QPen(minor_color, 1)
        major_pen = QPen(major_color, 1)

        for is_major, lines in self._ticks(
            width, track_y, track_height, view_first, view_last
        ).items():
            painter.setPen(major_pen if is_major else minor_pen)
            painter.drawLines(lines)

        # Regions: a translucent fill and edge lines; bracketed edges keep a
        # zero-width region (a lone in/out point) visible.
        for region in self._timeline._regions.values():
            r_start, r_end = region["start"], region["end"]
            if r_end < view_first or r_start > view_last:
                continue
            x0 = int(frame_to_x(max(r_start, view_first)))
            x1 = int(frame_to_x(min(r_end, view_last)))
            region_color = _ink(region["color"])
            fill = QColor(region_color)
            fill.setAlpha(self._timeline.REGION_FILL_ALPHA)
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawRect(x0, 0, max(1, x1 - x0), height)
            painter.setPen(QPen(region_color, 1))
            if region["brackets"]:
                stub = 5
                if r_start >= view_first:
                    painter.drawLine(x0, 1, x0, height - 1)
                    painter.drawLine(x0, 1, x0 + stub, 1)
                    painter.drawLine(x0, height - 1, x0 + stub, height - 1)
                if r_end <= view_last:
                    painter.drawLine(x1, 1, x1, height - 1)
                    painter.drawLine(x1 - stub, 1, x1, 1)
                    painter.drawLine(x1 - stub, height - 1, x1, height - 1)
            else:
                if r_start >= view_first:
                    painter.drawLine(x0, 0, x0, height)
                if r_end <= view_last:
                    painter.drawLine(x1, 0, x1, height)

        # Marker layers: only the visible slice of the precomputed geometry.
        for layer in self._timeline._marker_layers.values():
            layer_color = _ink(layer["color"])
            if layer["style"] == "line":
                painter.setPen(QPen(layer_color, 1, Qt.DashLine))
                ordered = layer["sorted"]
                lo = bisect_left(ordered, view_first)
                hi = bisect_right(ordered, view_last)
                for frame in ordered[lo:hi]:
                    x = int(frame_to_x(frame))
                    painter.drawLine(x, 0, x, height)
            else:  # strip: translucent top band + 1px solid top line
                fill = QColor(layer_color)
                fill.setAlpha(self._timeline.STRIP_FILL_ALPHA)
                strip_h = self._timeline.STRIP_HEIGHT
                line_pen = QPen(layer_color, 1)
                for run_start, run_end in layer["runs"]:
                    if run_end < view_first or run_start > view_last:
                        continue
                    x0 = int(frame_to_x(max(run_start, view_first)))
                    x1 = int(frame_to_x(min(run_end, view_last)))
                    run_w = max(2, x1 - x0)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(fill)
                    painter.drawRect(x0, 0, run_w, strip_h)
                    painter.setPen(line_pen)
                    painter.drawLine(x0, 0, x0 + run_w, 0)

        painter.setBrush(_ink(self._timeline.KEYFRAME_TOKEN))
        painter.setPen(Qt.NoPen)
        for keyframe in self._timeline._keyframes:
            if view_first <= keyframe <= view_last:
                x = frame_to_x(keyframe)
                middle = track_y + track_height / 2
                painter.drawPolygon(QPolygonF([
                    QPointF(x, track_y - 2),
                    QPointF(x + 4, middle),
                    QPointF(x, track_y + track_height + 2),
                    QPointF(x - 4, middle),
                ]))

        # Playhead: a 1px core over a soft glow, under a tag-style handle.
        current = self._timeline.current_frame()
        if view_first <= current <= view_last:
            playhead_x = int(frame_to_x(current))
            playhead_color = QColor(theme.accent_primary)

            glow = QColor(playhead_color)
            glow.setAlpha(70)
            painter.setPen(QPen(glow, 3))
            painter.drawLine(playhead_x, 0, playhead_x, height)
            painter.setPen(QPen(playhead_color, 1))
            painter.drawLine(playhead_x, 0, playhead_x, height)

            painter.setBrush(playhead_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(playhead_x - 3, 0, 7, 4, 2, 2)
            painter.drawPolygon(QPolygonF([
                QPointF(playhead_x - 3, 3),
                QPointF(playhead_x + 4, 3),
                QPointF(playhead_x + 0.5, 9),
            ]))

        # Hover: a muted line at the hovered frame, its number beside it.
        if (
            self._hover_frame is not None
            and view_first <= self._hover_frame <= view_last
        ):
            hover_x = int(frame_to_x(self._hover_frame))
            hover_color = QColor(text_color)
            hover_color.setAlpha(110)
            painter.setPen(QPen(hover_color, 1))
            painter.drawLine(hover_x, 0, hover_x, height)

            text = str(self._hover_frame)
            metrics = painter.fontMetrics()
            text_w = metrics.horizontalAdvance(text)
            # Beside the line, flipped near the right edge.
            label_x = hover_x + 5
            if label_x + text_w + 6 > width:
                label_x = hover_x - text_w - 9
            backdrop = QColor(theme.surface_sunken)
            backdrop.setAlpha(220)
            painter.setPen(Qt.NoPen)
            painter.setBrush(backdrop)
            painter.drawRoundedRect(
                label_x - 2, 1, text_w + 6, metrics.height() + 1,
                fxstyle.BUTTON_RADIUS, fxstyle.BUTTON_RADIUS,
            )
            painter.setPen(text_color)
            painter.drawText(label_x + 1, metrics.ascent() + 2, text)

        painter.end()

    def _ticks(
        self, width: int, track_y: int, track_height: int, first: int, last: int
    ) -> Dict[bool, List[QLineF]]:
        """Return the minor and major tick lines, built once per window."""
        # Scrubbing and playback repaint the same window every frame.
        key = (width, track_y, track_height, first, last)
        if self._tick_key == key:
            return self._tick_lines
        frame_range = max(1, last - first)
        usable = max(1, width - 2 * self.EDGE_PAD)
        pixels_per_frame = width / frame_range
        if pixels_per_frame >= 4:
            interval = 1
        elif pixels_per_frame >= 1:
            interval = 5
        elif pixels_per_frame >= 0.4:
            interval = 10
        else:
            interval = max(1, frame_range // 20)
        frames = list(range(first, last + 1, interval))
        if frames and frames[-1] != last:
            frames.append(last)   # always mark the window edge
        ticks: Dict[bool, List[QLineF]] = {True: [], False: []}
        for frame in frames:
            x = int(self.EDGE_PAD + (frame - first) / frame_range * usable)
            major = (
                (frame - first) % (interval * 5) == 0
                or frame in (first, last)
            )
            extent = 5 if major else 2
            ticks[major].append(QLineF(
                x, track_y - extent, x, track_y + track_height + extent
            ))
        self._tick_key, self._tick_lines = key, ticks
        return ticks

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Left = scrub; middle = start panning the zoomed window."""
        # A click on the track gives the timeline its keys.
        self._timeline.setFocus(Qt.MouseFocusReason)
        if event.button() == Qt.LeftButton:
            self._timeline._is_dragging = True
            self._timeline.set_frame(self._frame_at(event.position().x()))
        elif event.button() == Qt.MiddleButton:
            self._pan_last_x = event.position().x()
            self._pan_accum = 0.0
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for scrubbing, panning, and hover tracking."""
        x = event.position().x()
        if self._pan_last_x is not None:
            self._pan_view(x)
            return
        frame = self._frame_at(x)
        if frame != self._hover_frame:
            self._hover_frame = frame
            self.update()
        if self._timeline._is_dragging:
            self._timeline.set_frame(frame)

    def leaveEvent(self, event) -> None:
        """Clear the hover indicator when the cursor leaves the track."""
        if self._hover_frame is not None:
            self._hover_frame = None
            self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._timeline._is_dragging = False
        elif event.button() == Qt.MiddleButton:
            self._pan_last_x = None
            self.setCursor(Qt.PointingHandCursor)

    def _x_to_ratio(self, x: float) -> float:
        """Map a widget x to the 0..1 track ratio, inset like the paint."""
        usable = max(1, self.width() - 2 * self.EDGE_PAD)
        return max(0.0, min(1.0, (x - self.EDGE_PAD) / usable))

    def _frame_at(self, x: float) -> int:
        """Return the frame under widget x in the visible window."""
        view_first, view_last = self._timeline.view_range()
        return int(round(
            view_first + self._x_to_ratio(x) * (view_last - view_first)
        ))

    def wheelEvent(self, event) -> None:
        """Zoom the visible frame window around the cursor."""
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        first, last = self._timeline.view_range()
        span = last - first
        # At least one frame per notch: 2 * 1.25 rounds back to 2.
        if delta > 0:
            new_span = min(span - 1, round(span * 0.8))
        else:
            new_span = max(span + 1, round(span * 1.25))
        ratio = self._x_to_ratio(event.position().x())
        anchor = first + ratio * span
        new_first = round(anchor - ratio * new_span)
        self._timeline.set_view_range(new_first, new_first + new_span)
        event.accept()

    def _pan_view(self, x: float) -> None:
        """Translate the zoomed window by the cursor delta (in frames)."""
        usable = max(1, self.width() - 2 * self.EDGE_PAD)
        first, last = self._timeline.view_range()
        span = last - first
        self._pan_accum += (self._pan_last_x - x) * span / usable
        self._pan_last_x = x
        shift = int(round(self._pan_accum))
        if shift:
            self._pan_accum -= shift
            self._timeline.set_view_range(first + shift, last + shift)
