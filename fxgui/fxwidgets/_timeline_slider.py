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


class FXTimelineSlider(fxstyle.FXThemeAware, QWidget):
    """A timeline/scrubber widget perfect for DCC applications.

    This widget provides a timeline slider with:
    - Frame range display
    - Keyframe markers
    - Current frame indicator
    - Optional playback controls

    Args:
        parent: Parent widget.
        start_frame: Start frame of the timeline.
        end_frame: End frame of the timeline.
        current_frame: Initial current frame.
        fps: Frames per second for playback (default 24).
        show_controls: Whether to show playback controls.
        show_spinbox: Whether to show the frame spinbox.

    Signals:
        frame_changed: Emitted when the current frame changes.
        playback_started: Emitted when playback starts.
        playback_stopped: Emitted when playback stops.

    Examples:
        >>> timeline = FXTimelineSlider(start_frame=1, end_frame=100)
        >>> timeline.frame_changed.connect(lambda f: print(f"Frame: {f}"))
        >>> timeline.add_keyframe(10)
        >>> timeline.add_keyframe(50)
    """

    frame_changed = Signal(int)
    playback_started = Signal()
    playback_stopped = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        start_frame: int = 1,
        end_frame: int = 100,
        current_frame: Optional[int] = None,
        fps: int = 24,
        show_controls: bool = True,
        show_spinbox: bool = True,
    ):
        super().__init__(parent)

        self._start_frame = start_frame
        self._end_frame = end_frame
        self._current_frame = current_frame if current_frame else start_frame
        self._keyframes: List[int] = []
        self._is_playing = False
        self._is_dragging = False
        self._fps = fps

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

        # Calculate frame-to-pixel conversion
        frame_range = self._timeline._end_frame - self._timeline._start_frame
        if frame_range <= 0:
            frame_range = 1

        def frame_to_x(frame: int) -> float:
            ratio = (frame - self._timeline._start_frame) / frame_range
            return ratio * width

        # Draw frame tick marks
        tick_color = QColor(self._timeline._text_color)
        tick_color.setAlpha(80)
        tick_pen = QPen(tick_color)
        tick_pen.setWidth(1)
        painter.setPen(tick_pen)

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

        for frame in range(
            self._timeline._start_frame, self._timeline._end_frame + 1
        ):
            if (frame - self._timeline._start_frame) % tick_interval == 0:
                x = frame_to_x(frame)
                # Major tick every 10 frames, minor otherwise
                is_major = (
                    (frame - self._timeline._start_frame) % (tick_interval * 5)
                    == 0
                    or frame == self._timeline._start_frame
                    or frame == self._timeline._end_frame
                )
                tick_height = 6 if is_major else 3
                painter.drawLine(int(x), track_y - tick_height, int(x), track_y)

        # Draw keyframe markers
        for keyframe in self._timeline._keyframes:
            if (
                self._timeline._start_frame
                <= keyframe
                <= self._timeline._end_frame
            ):
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

        # Draw playhead
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

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for scrubbing."""
        if event.button() == Qt.LeftButton:
            self._timeline._is_dragging = True
            self._update_frame_from_mouse(event.x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for scrubbing."""
        if self._timeline._is_dragging:
            self._update_frame_from_mouse(event.x())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._timeline._is_dragging = False

    def _update_frame_from_mouse(self, x: int) -> None:
        """Update frame based on mouse position."""
        width = self.width()
        if width <= 0:
            return

        ratio = max(0.0, min(1.0, x / width))
        frame_range = self._timeline._end_frame - self._timeline._start_frame
        frame = int(self._timeline._start_frame + ratio * frame_range)
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

    timeline = FXTimelineSlider(start_frame=1, end_frame=120, current_frame=1)
    timeline.add_keyframe(1)
    timeline.add_keyframe(30)
    timeline.add_keyframe(60)
    timeline.add_keyframe(90)
    timeline.add_keyframe(120)

    frame_label = QLabel("Frame: 1")

    def on_frame_changed(frame):
        frame_label.setText(f"Frame: {frame}")

    timeline.frame_changed.connect(on_frame_changed)

    # Playback controls
    controls_layout = QHBoxLayout()
    prev_btn = QPushButton("Prev Key")
    fxicons.set_icon(prev_btn, "skip_previous")
    next_btn = QPushButton("Next Key")
    fxicons.set_icon(next_btn, "skip_next")
    # prev_btn.clicked.connect(timeline.go_to_previous_keyframe)
    # next_btn.clicked.connect(timeline.go_to_next_keyframe)
    controls_layout.addWidget(prev_btn)
    controls_layout.addWidget(next_btn)

    layout.addWidget(timeline)
    layout.addWidget(frame_label)
    layout.addLayout(controls_layout)
    layout.addStretch()

    window.resize(600, 150)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
