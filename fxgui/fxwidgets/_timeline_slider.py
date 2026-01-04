"""FXTimelineSlider - Timeline/scrubber widget for DCC applications."""

from typing import List, Optional, Tuple

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QMouseEvent, QPainter, QPen
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

from fxgui import fxicons, fxstyle


class FXTimelineSlider(QWidget):
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

        # Get theme colors
        theme_colors = fxstyle.get_theme_colors()
        accent_colors = fxstyle.get_accent_colors()

        self._track_color = QColor(theme_colors["surface_alt"])
        self._playhead_color = QColor(accent_colors["primary"])
        self._keyframe_color = QColor("#ff9800")
        self._text_color = QColor(theme_colors["text"])

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Start frame label
        self._start_label = QLabel(str(self._start_frame))
        self._start_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        self._start_label.setFixedWidth(40)
        self._start_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addWidget(self._start_label)

        # Playback controls
        if show_controls:
            controls_layout = QHBoxLayout()
            controls_layout.setSpacing(2)

            # Go to start
            self._goto_start_btn = QPushButton()
            self._goto_start_btn.setIcon(fxicons.get_icon("skip_previous"))
            self._goto_start_btn.setFixedSize(24, 24)
            self._goto_start_btn.setFlat(True)
            self._goto_start_btn.setToolTip("Go to start")
            self._goto_start_btn.clicked.connect(self.go_to_start)
            controls_layout.addWidget(self._goto_start_btn)

            # Previous frame
            self._prev_btn = QPushButton()
            self._prev_btn.setIcon(fxicons.get_icon("chevron_left"))
            self._prev_btn.setFixedSize(24, 24)
            self._prev_btn.setFlat(True)
            self._prev_btn.setToolTip("Previous frame")
            self._prev_btn.clicked.connect(self.previous_frame)
            controls_layout.addWidget(self._prev_btn)

            # Play/Pause
            self._play_btn = QPushButton()
            self._play_btn.setIcon(fxicons.get_icon("play_arrow"))
            self._play_btn.setFixedSize(28, 28)
            self._play_btn.setToolTip("Play")
            self._play_btn.clicked.connect(self.toggle_playback)
            controls_layout.addWidget(self._play_btn)

            # Next frame
            self._next_btn = QPushButton()
            self._next_btn.setIcon(fxicons.get_icon("chevron_right"))
            self._next_btn.setFixedSize(24, 24)
            self._next_btn.setFlat(True)
            self._next_btn.setToolTip("Next frame")
            self._next_btn.clicked.connect(self.next_frame)
            controls_layout.addWidget(self._next_btn)

            # Go to end
            self._goto_end_btn = QPushButton()
            self._goto_end_btn.setIcon(fxicons.get_icon("skip_next"))
            self._goto_end_btn.setFixedSize(24, 24)
            self._goto_end_btn.setFlat(True)
            self._goto_end_btn.setToolTip("Go to end")
            self._goto_end_btn.clicked.connect(self.go_to_end)
            controls_layout.addWidget(self._goto_end_btn)

            main_layout.addLayout(controls_layout)

        # Timeline track (custom painted)
        self._track_widget = _TimelineTrack(self)
        self._track_widget.setMinimumHeight(24)
        self._track_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(self._track_widget, 1)

        # Frame spinbox
        if show_spinbox:
            self._spinbox = QSpinBox()
            self._spinbox.setRange(start_frame, end_frame)
            self._spinbox.setValue(self._current_frame)
            self._spinbox.setFixedWidth(60)
            self._spinbox.valueChanged.connect(self._on_spinbox_changed)
            main_layout.addWidget(self._spinbox)

        # End frame label
        self._end_label = QLabel(str(self._end_frame))
        self._end_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        self._end_label.setFixedWidth(40)
        main_layout.addWidget(self._end_label)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(30)

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
            if hasattr(self, '_spinbox'):
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
        self._start_label.setText(str(start))
        self._end_label.setText(str(end))
        if hasattr(self, '_spinbox'):
            self._spinbox.setRange(start, end)
        self._current_frame = max(start, min(self._current_frame, end))
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
        if hasattr(self, '_play_btn'):
            self._play_btn.setIcon(fxicons.get_icon("pause"))
            self._play_btn.setToolTip("Pause")
        self.playback_started.emit()

    def stop(self) -> None:
        """Stop playback."""
        self._is_playing = False
        if hasattr(self, '_play_btn'):
            self._play_btn.setIcon(fxicons.get_icon("play_arrow"))
            self._play_btn.setToolTip("Play")
        self.playback_stopped.emit()

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

        # Draw keyframe markers
        for keyframe in self._timeline._keyframes:
            if self._timeline._start_frame <= keyframe <= self._timeline._end_frame:
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
        handle = QPolygonF([
            QPointF(playhead_x - handle_size // 2, 0),
            QPointF(playhead_x + handle_size // 2, 0),
            QPointF(playhead_x, handle_size),
        ])
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


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    import os
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel, QPushButton, QHBoxLayout
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
    prev_btn = QPushButton("◀ Prev Key")
    next_btn = QPushButton("Next Key ▶")
    prev_btn.clicked.connect(timeline.go_to_previous_keyframe)
    next_btn.clicked.connect(timeline.go_to_next_keyframe)
    controls_layout.addWidget(prev_btn)
    controls_layout.addWidget(next_btn)

    layout.addWidget(timeline)
    layout.addWidget(frame_label)
    layout.addLayout(controls_layout)
    layout.addStretch()

    window.resize(600, 150)
    window.show()
    sys.exit(app.exec())
