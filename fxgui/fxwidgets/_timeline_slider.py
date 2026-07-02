"""Timeline/scrubber widget for DCC applications."""

# Built-in
from typing import List, Optional, Tuple

# Third-party
from qtpy.QtCore import Qt, Signal, QTimer
from qtpy.QtGui import QColor, QMouseEvent, QPainter, QPen
from qtpy.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._tooltip import FXTooltip


def _coalesce_runs(frames) -> List[Tuple[int, int]]:
    """Coalesce a set of frame numbers into contiguous (start, end) runs so
    strip-style markers paint a few rects instead of one per frame."""
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


class FXTimelineSlider(fxstyle.FXThemeAware, QWidget):
    """A timeline/scrubber widget perfect for DCC applications.

    This widget provides a timeline slider with:
    - Frame range display
    - Keyframe markers
    - Current frame indicator
    - Optional playback controls
    - Track zoom: mouse wheel over the track zooms the visible frame window
      around the cursor, middle-mouse drag pans it, `reset_view()` restores
      the full range (view_changed reports the visible window).
    - Named marker layers: per-frame markers rendered as vertical lines or
      a top strip (e.g. cached frames), and named regions (e.g. a loop
      range), all mapped through the zoomed window. The widget assigns no
      meaning to a layer: the consumer picks names, colors and styles.
    - Optional in/out controls (`show_loop_controls`): bracket buttons that
      request marking the current frame as loop in/out point; the consumer
      decides what marking does and typically calls `set_loop_region`.
    - Optional keyframe navigation (`show_keyframe_controls`): buttons
      jumping to the nearest keyframe before/after the current frame
      (`go_to_previous_keyframe` / `go_to_next_keyframe`).
    - Hover indicator: a crosshair-style line with the hovered frame
      number, cleared when the cursor leaves the track.

    Args:
        parent: Parent widget.
        start_frame: Start frame of the timeline.
        end_frame: End frame of the timeline.
        current_frame: Initial current frame.
        fps: Frames per second for playback (default 24).
        show_controls: Whether to show playback controls.
        show_spinbox: Whether to show the frame spinbox.
        show_loop_controls: Whether to show the mark-in/mark-out buttons.
        show_keyframe_controls: Whether to show the previous/next-keyframe
            navigation buttons.

    Signals:
        frame_changed: Emitted when the current frame changes.
        playback_started: Emitted when playback starts.
        playback_stopped: Emitted when playback stops.
        view_changed: Emitted with (first, last) when the visible frame
            window changes (zoom, pan, or reset).
        in_point_requested: Mark-in button pressed; carries the current
            frame. The widget draws nothing by itself.
        out_point_requested: Mark-out button pressed; carries the current
            frame.

    Examples:
        >>> timeline = FXTimelineSlider(start_frame=1, end_frame=100)
        >>> timeline.frame_changed.connect(lambda f: print(f"Frame: {f}"))
        >>> timeline.add_keyframe(10)
        >>> timeline.add_keyframe(50)
        >>> timeline.set_marker_frames("cached", {2, 3, 4}, "#22c55e", "strip")
        >>> timeline.set_marker_frames("errors", {40, 41}, "#ef4444")
        >>> timeline.set_loop_region(20, 60)
    """

    frame_changed = Signal(int)
    playback_started = Signal()
    playback_stopped = Signal()
    view_changed = Signal(int, int)
    in_point_requested = Signal(int)
    out_point_requested = Signal(int)

    # Smallest zoomable window, in frames.
    MIN_VIEW_SPAN = 2
    # Marker rendering: fill alphas match a 1px solid line + translucent
    # fill look (region fill / strip fill).
    REGION_FILL_ALPHA = 50
    STRIP_FILL_ALPHA = 80
    STRIP_HEIGHT = 4

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        start_frame: int = 1,
        end_frame: int = 100,
        current_frame: Optional[int] = None,
        fps: int = 24,
        show_controls: bool = True,
        show_spinbox: bool = True,
        show_loop_controls: bool = False,
        show_keyframe_controls: bool = False,
    ):
        super().__init__(parent)

        self._start_frame = start_frame
        self._end_frame = end_frame
        self._current_frame = current_frame if current_frame else start_frame
        self._keyframes: List[int] = []
        self._is_playing = False
        self._is_dragging = False
        self._fps = fps
        # Visible frame window (None = follow the full range).
        self._view_start: Optional[int] = None
        self._view_end: Optional[int] = None
        # Named marker layers / regions painted on the track.
        # name -> {"frames": set, "color": QColor, "style": "line"|"strip"}
        self._marker_layers: dict = {}
        # name -> {"start": int, "end": int, "color": QColor}
        self._regions: dict = {}

        # Playback timer
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_tick)

        # Theme colors (will be set in _apply_theme_styles)
        self._track_color = None
        self._playhead_color = None
        self._keyframe_color = QColor("#ff9800")
        self._text_color = None

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Start frame spinbox (editable)
        self._start_spinbox = QSpinBox()
        self._start_spinbox.setRange(-99999, 99999)
        self._start_spinbox.setValue(self._start_frame)
        self._start_spinbox.setFixedWidth(55)
        self._start_spinbox_tooltip = FXTooltip(
            parent=self._start_spinbox,
            title="Start Frame",
            description="First frame of the timeline range",
        )
        self._start_spinbox.valueChanged.connect(self._on_start_changed)
        main_layout.addWidget(self._start_spinbox)

        # Playback controls
        if show_controls:
            controls_layout = QHBoxLayout()
            controls_layout.setSpacing(2)

            # Go to start
            self._goto_start_btn = QPushButton()
            fxicons.set_icon(self._goto_start_btn, "skip_previous")
            self._goto_start_btn.setFixedSize(24, 24)
            self._goto_start_btn.setFlat(True)
            self._goto_start_btn.clicked.connect(self.go_to_start)
            self._goto_start_btn_tooltip = FXTooltip(
                parent=self._goto_start_btn,
                title="Go to Start",
                description="Jump to the first frame",
                shortcut="Home",
            )
            controls_layout.addWidget(self._goto_start_btn)

            # Previous frame
            self._prev_btn = QPushButton()
            fxicons.set_icon(self._prev_btn, "chevron_left")
            self._prev_btn.setFixedSize(24, 24)
            self._prev_btn.setFlat(True)
            self._prev_btn.clicked.connect(self.previous_frame)
            self._prev_btn_tooltip = FXTooltip(
                parent=self._prev_btn,
                title="Previous Frame",
                description="Go back one frame",
                shortcut="Left",
            )
            controls_layout.addWidget(self._prev_btn)

            # Play/Pause
            self._play_btn = QPushButton()
            fxicons.set_icon(self._play_btn, "play_arrow")
            self._play_btn.setFixedSize(28, 28)
            self._play_btn.clicked.connect(self.toggle_playback)
            self._play_btn_tooltip = FXTooltip(
                parent=self._play_btn,
                title="Play",
                description="Start playback",
                shortcut="Space",
            )
            controls_layout.addWidget(self._play_btn)

            # Next frame
            self._next_btn = QPushButton()
            fxicons.set_icon(self._next_btn, "chevron_right")
            self._next_btn.setFixedSize(24, 24)
            self._next_btn.setFlat(True)
            self._next_btn.clicked.connect(self.next_frame)
            self._next_btn_tooltip = FXTooltip(
                parent=self._next_btn,
                title="Next Frame",
                description="Go forward one frame",
                shortcut="Right",
            )
            controls_layout.addWidget(self._next_btn)

            # Go to end
            self._goto_end_btn = QPushButton()
            fxicons.set_icon(self._goto_end_btn, "skip_next")
            self._goto_end_btn.setFixedSize(24, 24)
            self._goto_end_btn.setFlat(True)
            self._goto_end_btn.clicked.connect(self.go_to_end)
            self._goto_end_btn_tooltip = FXTooltip(
                parent=self._goto_end_btn,
                title="Go to End",
                description="Jump to the last frame",
                shortcut="End",
            )
            controls_layout.addWidget(self._goto_end_btn)

            # Keyframe navigation (opt-in): jump to the nearest keyframe
            # before/after the current frame.
            if show_keyframe_controls:
                self._prev_key_btn = QPushButton()
                fxicons.set_icon(self._prev_key_btn, "keyboard_double_arrow_left")
                self._prev_key_btn.setFixedSize(24, 24)
                self._prev_key_btn.setFlat(True)
                self._prev_key_btn.clicked.connect(self.go_to_previous_keyframe)
                self._prev_key_btn_tooltip = FXTooltip(
                    parent=self._prev_key_btn,
                    title="Previous Keyframe",
                    description="Jump to the nearest keyframe before",
                )
                controls_layout.addWidget(self._prev_key_btn)

                self._next_key_btn = QPushButton()
                fxicons.set_icon(self._next_key_btn, "keyboard_double_arrow_right")
                self._next_key_btn.setFixedSize(24, 24)
                self._next_key_btn.setFlat(True)
                self._next_key_btn.clicked.connect(self.go_to_next_keyframe)
                self._next_key_btn_tooltip = FXTooltip(
                    parent=self._next_key_btn,
                    title="Next Keyframe",
                    description="Jump to the nearest keyframe after",
                )
                controls_layout.addWidget(self._next_key_btn)

            # Mark in / mark out (opt-in). The widget only requests: the
            # consumer decides what marking means (typically it ends up
            # calling set_loop_region).
            if show_loop_controls:
                self._mark_in_btn = QPushButton()
                fxicons.set_icon(self._mark_in_btn, "first_page")
                self._mark_in_btn.setFixedSize(24, 24)
                self._mark_in_btn.setFlat(True)
                self._mark_in_btn.clicked.connect(
                    lambda: self.in_point_requested.emit(self._current_frame)
                )
                self._mark_in_btn_tooltip = FXTooltip(
                    parent=self._mark_in_btn,
                    title="Mark In",
                    description="Set the loop in point at the current frame",
                    shortcut="I",
                )
                controls_layout.addWidget(self._mark_in_btn)

                self._mark_out_btn = QPushButton()
                fxicons.set_icon(self._mark_out_btn, "last_page")
                self._mark_out_btn.setFixedSize(24, 24)
                self._mark_out_btn.setFlat(True)
                self._mark_out_btn.clicked.connect(
                    lambda: self.out_point_requested.emit(self._current_frame)
                )
                self._mark_out_btn_tooltip = FXTooltip(
                    parent=self._mark_out_btn,
                    title="Mark Out",
                    description="Set the loop out point at the current frame",
                    shortcut="O",
                )
                controls_layout.addWidget(self._mark_out_btn)

            main_layout.addLayout(controls_layout)

        # Timeline track (custom painted)
        self._track_widget = _TimelineTrack(self)
        self._track_widget.setMinimumHeight(24)
        self._track_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        main_layout.addWidget(self._track_widget, 1)

        # Frame spinbox
        if show_spinbox:
            self._spinbox = QSpinBox()
            self._spinbox.setRange(start_frame, end_frame)
            self._spinbox.setValue(self._current_frame)
            self._spinbox.setFixedWidth(60)
            self._spinbox.valueChanged.connect(self._on_spinbox_changed)
            main_layout.addWidget(self._spinbox)

        # End frame spinbox (editable)
        self._end_spinbox = QSpinBox()
        self._end_spinbox.setRange(-99999, 99999)
        self._end_spinbox.setValue(self._end_frame)
        self._end_spinbox.setFixedWidth(55)
        self._end_spinbox_tooltip = FXTooltip(
            parent=self._end_spinbox,
            title="End Frame",
            description="Last frame of the timeline range",
        )
        self._end_spinbox.valueChanged.connect(self._on_end_changed)
        main_layout.addWidget(self._end_spinbox)

        # FPS spinbox (editable)
        self._fps_spinbox = QSpinBox()
        self._fps_spinbox.setRange(1, 120)
        self._fps_spinbox.setValue(self._fps)
        self._fps_spinbox.setSuffix(" fps")
        self._fps_spinbox.setFixedWidth(65)
        self._fps_spinbox_tooltip = FXTooltip(
            parent=self._fps_spinbox,
            title="FPS",
            description="Frames per second for playback",
        )
        self._fps_spinbox.valueChanged.connect(self._on_fps_changed)
        main_layout.addWidget(self._fps_spinbox)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(30)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        self._track_color = QColor(self.theme.surface_alt)
        self._playhead_color = QColor(self.theme.accent_primary)
        self._text_color = QColor(self.theme.text)

        # Trigger repaint of track widget
        if hasattr(self, "_track_widget"):
            self._track_widget.update()

    @property
    def current_frame(self) -> int:
        """Return the current frame."""
        return self._current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Set the current frame."""
        self.set_frame(value)

    @property
    def frame_range(self) -> Tuple[int, int]:
        """Return the frame range as (start, end)."""
        return (self._start_frame, self._end_frame)

    @property
    def view_range(self) -> Tuple[int, int]:
        """Return the visible frame window as (first, last).

        Equals `frame_range` unless the track has been zoomed.
        """
        if self._view_start is None or self._view_end is None:
            return (self._start_frame, self._end_frame)
        return (self._view_start, self._view_end)

    @property
    def is_view_zoomed(self) -> bool:
        """Whether the track shows a sub-window of the full range."""
        return self.view_range != (self._start_frame, self._end_frame)

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

    def set_marker_frames(
        self,
        name: str,
        frames,
        color: str = "#ef4444",
        style: str = "line",
    ) -> None:
        """Set (or replace) a named marker layer painted on the track.

        The widget assigns no meaning to a layer: the consumer picks the
        name, color and style (a render-farm app may mark cached frames, a
        review app approved ones).

        Args:
            name: Layer identifier; setting the same name replaces it.
            frames: Iterable of frame numbers. Empty removes the layer.
            color: Marker color (any QColor-compatible value).
            style: "line" for 1px vertical lines at each frame, or "strip"
                for a translucent band along the top edge with a 1px solid
                top line over contiguous frame runs.
        """
        if style not in ("line", "strip"):
            raise ValueError(f"Unknown marker style: {style!r}")
        frames = set(frames or ())
        if not frames:
            self.remove_markers(name)
            return
        self._marker_layers[name] = {
            "frames": frames,
            "color": QColor(color),
            "style": style,
        }
        self._track_widget.update()

    def remove_markers(self, name: str) -> None:
        """Remove a named marker layer (no-op if absent)."""
        if self._marker_layers.pop(name, None) is not None:
            self._track_widget.update()

    def set_region(
        self, name: str, start: int, end: int, color: str = "#5278e0"
    ) -> None:
        """Set (or replace) a named frame region painted on the track.

        Rendered as a translucent fill across the track with 1px solid
        edge lines, like a graph's linear region.

        Args:
            name: Region identifier; setting the same name replaces it.
            start: First frame of the region.
            end: Last frame of the region.
            color: Region color (edges solid, fill translucent).
        """
        self._regions[name] = {
            "start": int(min(start, end)),
            "end": int(max(start, end)),
            "color": QColor(color),
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
        color: str = "#5278e0",
    ) -> None:
        """Show the loop in/out range on the track (None, None clears).

        Sugar over `set_region("loop", ...)` for the common loop-range
        pairing with the in/out controls.
        """
        if start is None or end is None:
            self.clear_region("loop")
            return
        self.set_region("loop", start, end, color)

    def set_frame(self, frame: int, emit: bool = True) -> None:
        """Set the current frame.

        Args:
            frame: The frame number.
            emit: Whether to emit the frame_changed signal.
        """
        frame = max(self._start_frame, min(frame, self._end_frame))
        if frame != self._current_frame:
            self._current_frame = frame
            if hasattr(self, "_spinbox"):
                self._spinbox.blockSignals(True)
                self._spinbox.setValue(frame)
                self._spinbox.blockSignals(False)
            self._track_widget.update()
            if emit:
                self.frame_changed.emit(frame)

    def set_range(self, start: int, end: int) -> None:
        """Set the frame range.

        Args:
            start: Start frame.
            end: End frame.
        """
        self._start_frame = start
        self._end_frame = end
        self._start_spinbox.blockSignals(True)
        self._end_spinbox.blockSignals(True)
        self._start_spinbox.setValue(start)
        self._end_spinbox.setValue(end)
        self._start_spinbox.blockSignals(False)
        self._end_spinbox.blockSignals(False)
        if hasattr(self, "_spinbox"):
            self._spinbox.setRange(start, end)
        self._current_frame = max(start, min(self._current_frame, end))
        # A new range invalidates any zoomed window.
        if self._view_start is not None or self._view_end is not None:
            self._view_start = self._view_end = None
            self.view_changed.emit(start, end)
        self._track_widget.update()

    def set_fps(self, fps: int) -> None:
        """Set the frames per second.

        Args:
            fps: Frames per second for playback.
        """
        self._fps = max(1, min(120, fps))
        self._fps_spinbox.blockSignals(True)
        self._fps_spinbox.setValue(self._fps)
        self._fps_spinbox.blockSignals(False)
        if self._is_playing:
            self._playback_timer.setInterval(1000 // self._fps)

    @property
    def fps(self) -> int:
        """Return the current FPS."""
        return self._fps

    def _on_fps_changed(self, value: int) -> None:
        """Handle FPS spinbox change."""
        self._fps = value
        if self._is_playing:
            self._playback_timer.setInterval(1000 // self._fps)

    def _on_start_changed(self, value: int) -> None:
        """Handle start frame spinbox change."""
        if value < self._end_frame:
            self._start_frame = value
            if hasattr(self, "_spinbox"):
                self._spinbox.setRange(value, self._end_frame)
            if self._current_frame < value:
                self.set_frame(value)
            self._track_widget.update()

    def _on_end_changed(self, value: int) -> None:
        """Handle end frame spinbox change."""
        if value > self._start_frame:
            self._end_frame = value
            if hasattr(self, "_spinbox"):
                self._spinbox.setRange(self._start_frame, value)
            if self._current_frame > value:
                self.set_frame(value)
            self._track_widget.update()

    def add_keyframe(self, frame: int) -> None:
        """Add a keyframe marker.

        Args:
            frame: The frame number to mark.
        """
        if frame not in self._keyframes:
            self._keyframes.append(frame)
            self._keyframes.sort()
            self._track_widget.update()

    def remove_keyframe(self, frame: int) -> None:
        """Remove a keyframe marker.

        Args:
            frame: The frame number to remove.
        """
        if frame in self._keyframes:
            self._keyframes.remove(frame)
            self._track_widget.update()

    def clear_keyframes(self) -> None:
        """Remove all keyframe markers."""
        self._keyframes.clear()
        self._track_widget.update()

    def go_to_previous_keyframe(self) -> None:
        """Jump to the nearest keyframe before the current frame (no-op if
        there is none)."""
        previous = [k for k in self._keyframes if k < self._current_frame]
        if previous:
            self.set_frame(max(previous))

    def go_to_next_keyframe(self) -> None:
        """Jump to the nearest keyframe after the current frame (no-op if
        there is none)."""
        following = [k for k in self._keyframes if k > self._current_frame]
        if following:
            self.set_frame(min(following))

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

    def toggle_playback(self) -> None:
        """Toggle playback state."""
        if self._is_playing:
            self.stop()
        else:
            self.play()

    def play(self) -> None:
        """Start playback."""
        self._is_playing = True
        self._playback_timer.start(1000 // self._fps)
        if hasattr(self, "_play_btn"):
            fxicons.set_icon(self._play_btn, "pause")
            self._play_btn.setToolTip("Pause")
        self.playback_started.emit()

    def stop(self) -> None:
        """Stop playback."""
        self._is_playing = False
        self._playback_timer.stop()
        if hasattr(self, "_play_btn"):
            fxicons.set_icon(self._play_btn, "play_arrow")
            self._play_btn.setToolTip("Play")
        self.playback_stopped.emit()

    def _on_playback_tick(self) -> None:
        """Handle playback timer tick."""
        next_frame = self._current_frame + 1
        if next_frame > self._end_frame:
            next_frame = self._start_frame  # Loop back to start
        self.set_frame(next_frame)

    def _on_spinbox_changed(self, value: int) -> None:
        """Handle spinbox value change."""
        self.set_frame(value)


class _TimelineTrack(QWidget):
    """Internal widget for drawing the timeline track."""

    def __init__(self, timeline: FXTimelineSlider):
        super().__init__(timeline)
        self._timeline = timeline
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        # Middle-mouse pan state (fractional shift accumulator so slow
        # drags still move the window one frame at a time).
        self._pan_last_x: Optional[int] = None
        self._pan_accum = 0.0
        # Hovered frame (crosshair-style indicator), None when outside.
        self._hover_frame: Optional[int] = None

    def paintEvent(self, event) -> None:
        """Paint the timeline track."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        track_height = 6
        track_y = (height - track_height) // 2

        # Draw track background
        painter.setBrush(self._timeline._track_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, track_y, width, track_height, 3, 3)

        # Calculate frame-to-pixel conversion over the visible window
        # (equals the full range unless the track is zoomed).
        view_first, view_last = self._timeline.view_range
        frame_range = view_last - view_first
        if frame_range <= 0:
            frame_range = 1

        def frame_to_x(frame: int) -> float:
            ratio = (frame - view_first) / frame_range
            return ratio * width

        # Draw frame tick marks crossing the track (both sides). Major
        # ticks are longer and more visible than minor ones.
        minor_color = QColor(self._timeline._text_color)
        minor_color.setAlpha(60)
        major_color = QColor(self._timeline._text_color)
        major_color.setAlpha(170)
        minor_pen = QPen(minor_color, 1)
        major_pen = QPen(major_color, 1)

        # Determine tick spacing based on frame range and width
        pixels_per_frame = width / max(1, frame_range)
        if pixels_per_frame >= 4:  # Show all frames if there's enough space
            tick_interval = 1
        elif pixels_per_frame >= 1:
            tick_interval = 5
        elif pixels_per_frame >= 0.4:
            tick_interval = 10
        else:
            tick_interval = max(1, frame_range // 20)

        for frame in range(view_first, view_last + 1):
            if (frame - view_first) % tick_interval == 0:
                x = int(frame_to_x(frame))
                # Major tick every 10 frames, minor otherwise
                is_major = (
                    (frame - view_first) % (tick_interval * 5) == 0
                    or frame == view_first
                    or frame == view_last
                )
                tick_extent = 5 if is_major else 2
                painter.setPen(major_pen if is_major else minor_pen)
                painter.drawLine(
                    x, track_y - tick_extent,
                    x, track_y + track_height + tick_extent,
                )

        # Named regions: translucent fill + 1px solid edge lines (graph
        # linear-region look). Under markers and playhead.
        for region in self._timeline._regions.values():
            r_start, r_end = region["start"], region["end"]
            if r_end < view_first or r_start > view_last:
                continue
            x0 = frame_to_x(max(r_start, view_first))
            x1 = frame_to_x(min(r_end, view_last))
            fill = QColor(region["color"])
            fill.setAlpha(self._timeline.REGION_FILL_ALPHA)
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawRect(int(x0), 0, max(1, int(x1 - x0)), height)
            painter.setPen(QPen(region["color"], 1))
            if r_start >= view_first:
                painter.drawLine(int(x0), 0, int(x0), height)
            if r_end <= view_last:
                painter.drawLine(int(x1), 0, int(x1), height)

        # Named marker layers.
        for layer in self._timeline._marker_layers.values():
            if layer["style"] == "line":
                painter.setPen(QPen(layer["color"], 1, Qt.DashLine))
                for frame in layer["frames"]:
                    if view_first <= frame <= view_last:
                        x = int(frame_to_x(frame))
                        painter.drawLine(x, 0, x, height)
            else:  # strip: translucent top band + 1px solid top line
                fill = QColor(layer["color"])
                fill.setAlpha(self._timeline.STRIP_FILL_ALPHA)
                strip_h = self._timeline.STRIP_HEIGHT
                for run_start, run_end in _coalesce_runs(layer["frames"]):
                    if run_end < view_first or run_start > view_last:
                        continue
                    x0 = int(frame_to_x(max(run_start, view_first)))
                    x1 = int(frame_to_x(min(run_end, view_last)))
                    run_w = max(2, x1 - x0)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(fill)
                    painter.drawRect(x0, 0, run_w, strip_h)
                    painter.setPen(QPen(layer["color"], 1))
                    painter.drawLine(x0, 0, x0 + run_w, 0)

        # Draw keyframe markers (visible window only)
        for keyframe in self._timeline._keyframes:
            if view_first <= keyframe <= view_last:
                x = frame_to_x(keyframe)
                painter.setBrush(self._timeline._keyframe_color)
                painter.setPen(Qt.NoPen)
                # Diamond shape for keyframe
                points = [
                    (x, track_y - 2),
                    (x + 4, track_y + track_height // 2),
                    (x, track_y + track_height + 2),
                    (x - 4, track_y + track_height // 2),
                ]
                from qtpy.QtGui import QPolygonF
                from qtpy.QtCore import QPointF

                polygon = QPolygonF([QPointF(p[0], p[1]) for p in points])
                painter.drawPolygon(polygon)

        # Draw playhead (skip when scrolled out of the visible window)
        if view_first <= self._timeline._current_frame <= view_last:
            playhead_x = frame_to_x(self._timeline._current_frame)

            # Playhead line
            pen = QPen(self._timeline._playhead_color)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(int(playhead_x), 0, int(playhead_x), height)

            # Playhead handle (triangle at top)
            painter.setBrush(self._timeline._playhead_color)
            painter.setPen(Qt.NoPen)
            handle_size = 8
            from qtpy.QtGui import QPolygonF
            from qtpy.QtCore import QPointF

            handle = QPolygonF(
                [
                    QPointF(playhead_x - handle_size // 2, 0),
                    QPointF(playhead_x + handle_size // 2, 0),
                    QPointF(playhead_x, handle_size),
                ]
            )
            painter.drawPolygon(handle)

        # Hover indicator: a muted vertical line at the hovered frame with
        # its number in a small label, like a graph crosshair.
        if (
            self._hover_frame is not None
            and view_first <= self._hover_frame <= view_last
        ):
            hover_x = int(frame_to_x(self._hover_frame))
            hover_color = QColor(self._timeline._text_color)
            hover_color.setAlpha(110)
            painter.setPen(QPen(hover_color, 1))
            painter.drawLine(hover_x, 0, hover_x, height)

            font = painter.font()
            font.setPixelSize(9)
            painter.setFont(font)
            text = str(self._hover_frame)
            metrics = painter.fontMetrics()
            text_w = metrics.horizontalAdvance(text)
            # Beside the line, flipped near the right edge, dark backdrop.
            label_x = hover_x + 5
            if label_x + text_w + 6 > width:
                label_x = hover_x - text_w - 9
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 160))
            painter.drawRoundedRect(
                label_x - 2, 1, text_w + 6, metrics.height() + 1, 3, 3
            )
            painter.setPen(QColor(self._timeline._text_color))
            painter.drawText(label_x + 1, metrics.ascent() + 2, text)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Left = scrub; middle = start panning the zoomed window."""
        if event.button() == Qt.LeftButton:
            self._timeline._is_dragging = True
            self._update_frame_from_mouse(event.x())
        elif event.button() == Qt.MiddleButton:
            self._pan_last_x = event.x()
            self._pan_accum = 0.0
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for scrubbing, panning, and hover tracking."""
        if self._pan_last_x is not None:
            self._pan_view(event.x())
            return
        self._set_hover_from_x(event.x())
        if self._timeline._is_dragging:
            self._update_frame_from_mouse(event.x())

    def leaveEvent(self, event) -> None:
        """Clear the hover indicator when the cursor leaves the track."""
        if self._hover_frame is not None:
            self._hover_frame = None
            self.update()
        super().leaveEvent(event)

    def _set_hover_from_x(self, x: int) -> None:
        """Track the hovered frame for the crosshair-style indicator."""
        width = self.width()
        if width <= 0:
            return
        ratio = max(0.0, min(1.0, x / width))
        view_first, view_last = self._timeline.view_range
        frame = int(round(view_first + ratio * (view_last - view_first)))
        if frame != self._hover_frame:
            self._hover_frame = frame
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._timeline._is_dragging = False
        elif event.button() == Qt.MiddleButton:
            self._pan_last_x = None
            self.setCursor(Qt.PointingHandCursor)

    def wheelEvent(self, event) -> None:
        """Zoom the visible frame window around the cursor."""
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        width = max(1, self.width())
        # QWheelEvent position: Qt6 position(), Qt5 pos().
        x = (
            event.position().x()
            if hasattr(event, "position")
            else event.pos().x()
        )
        first, last = self._timeline.view_range
        span = last - first
        factor = 0.8 if delta > 0 else 1.25
        new_span = span * factor
        ratio = max(0.0, min(1.0, x / width))
        anchor = first + ratio * span
        new_first = anchor - ratio * new_span
        self._timeline.set_view_range(
            round(new_first), round(new_first + new_span)
        )
        event.accept()

    def _pan_view(self, x: int) -> None:
        """Translate the zoomed window by the cursor delta (in frames)."""
        width = max(1, self.width())
        first, last = self._timeline.view_range
        span = last - first
        self._pan_accum += (self._pan_last_x - x) * span / width
        self._pan_last_x = x
        shift = int(round(self._pan_accum))
        if shift:
            self._pan_accum -= shift
            self._timeline.set_view_range(first + shift, last + shift)

    def _update_frame_from_mouse(self, x: int) -> None:
        """Update frame based on mouse position (view-window mapping)."""
        width = self.width()
        if width <= 0:
            return

        ratio = max(0.0, min(1.0, x / width))
        view_first, view_last = self._timeline.view_range
        frame = int(round(view_first + ratio * (view_last - view_first)))
        self._timeline.set_frame(frame)


def example() -> None:
    import sys
    from qtpy.QtWidgets import (
        QVBoxLayout,
        QWidget,
        QLabel,
        QPushButton,
        QHBoxLayout,
    )
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXTimelineSlider Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)

    # ── Basic timeline: keyframes only ──────────────────────────────────
    layout.addWidget(QLabel("Basic (keyframes):"))
    timeline = FXTimelineSlider(start_frame=1, end_frame=120, current_frame=1)
    for key in (1, 30, 60, 90, 120):
        timeline.add_keyframe(key)
    layout.addWidget(timeline)

    frame_label = QLabel("Frame: 1")
    timeline.frame_changed.connect(
        lambda frame: frame_label.setText(f"Frame: {frame}")
    )
    layout.addWidget(frame_label)

    # ── Full-featured timeline ──────────────────────────────────────────
    # Marker layers + regions + in/out controls + track zoom. Hover the
    # track and use the mouse wheel to zoom around the cursor, drag with
    # the middle mouse button to pan, everything stays aligned.
    layout.addWidget(
        QLabel(
            "Full (markers, regions, in/out, zoom -- wheel zooms the "
            "track, MMB pans):"
        )
    )
    full = FXTimelineSlider(
        start_frame=1001,
        end_frame=1240,
        current_frame=1050,
        show_loop_controls=True,
    )
    # A "cached frames" strip (translucent band + solid top line).
    full.set_marker_frames(
        "cached",
        set(range(1020, 1081)) | set(range(1150, 1201)),
        color="#22c55e",
        style="strip",
    )
    # An "error frames" layer (dashed vertical lines).
    full.set_marker_frames(
        "errors", {1035, 1036, 1132, 1197}, color="#ef4444", style="line"
    )
    # The in/out buttons only request; the demo commits the loop region.
    loop = {"in": None, "out": None}

    def _mark(which, frame):
        loop[which] = frame
        if loop["in"] is not None and loop["out"] is not None:
            full.set_loop_region(loop["in"], loop["out"])

    full.in_point_requested.connect(lambda f: _mark("in", f))
    full.out_point_requested.connect(lambda f: _mark("out", f))
    full.set_loop_region(1040, 1120)   # preset so the region is visible
    layout.addWidget(full)

    view_label = QLabel("View: 1001-1240")
    full.view_changed.connect(
        lambda first, last: view_label.setText(f"View: {first}-{last}")
    )
    layout.addWidget(view_label)

    reset_btn = QPushButton("Reset view")
    fxicons.set_icon(reset_btn, "fit_screen")
    reset_btn.clicked.connect(full.reset_view)
    clear_btn = QPushButton("Clear loop")
    fxicons.set_icon(clear_btn, "close")
    clear_btn.clicked.connect(lambda: full.set_loop_region(None, None))
    controls_layout = QHBoxLayout()
    controls_layout.addWidget(reset_btn)
    controls_layout.addWidget(clear_btn)
    controls_layout.addStretch()
    layout.addLayout(controls_layout)
    layout.addStretch()

    window.resize(760, 300)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
