# Plan 004: The timeline keeps playing after a wrap, Space always plays, and the track can be hidden

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_timeline_slider.py tests/test_timeline_slider.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`FXTimelineSlider` is the playback bar of Pascal's media player. Three defects:

1. **Loop off stops playback at once after a wrap.** Playback computes the
   frame from a clock: `anchor_frame + elapsed * fps`. When looping wraps
   past the end, only the shown frame is wrapped; the anchor is not moved.
   The clock frame stays past the end, so turning loop off makes the very
   next tick stop playback. Measured: range 1–10, start at 9, wrap to 3,
   loop off, one frame later → frame 10, playing False. Expected: frame 4,
   still playing.
2. **Space on a focused transport button presses that button** instead of
   play/pause. The transport buttons take focus on click (Qt's default
   `StrongFocus`), so after clicking "Next frame", Space clicks "Next frame"
   again. Pascal works around this by setting `NoFocus` on every button.
3. **No public way to hide the track.** Pascal hides the private
   `_track_widget` and calls `setMinimumHeight(0)` to beat a hard 60 px
   floor.

After this plan: the clock is re-anchored on a wrap, transport buttons never
take focus (the timeline keeps it, so its keys always work), and a
`show_track` constructor keyword hides the track and drops the floor.

## Current state

File: `fxgui/fxwidgets/_timeline_slider.py` (1207 lines). Class
`FXTimelineSlider(QWidget)`.

Constructor signature, lines 153–168 — every visibility option is a
`show_*` keyword:

```python
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
```

The docstring's Args section documents each keyword (lines 84–106; e.g.
line 101 `show_fps: Whether to show the frame rate field.`).

The timeline itself takes focus, line 204:

```python
        self.setFocusPolicy(Qt.StrongFocus)
```

Its `keyPressEvent` (lines 457–477) maps Home, Left, Space, Right, End (and
I/O with loop controls) to the transport actions.

Every transport button is made by `_button`, lines 434–451:

```python
    def _button(
        self,
        icon: str,
        slot: Optional[Callable[[], None]],
        title: str,
        body: str,
        keys: str = "",
    ) -> QPushButton:
        """Return a flat square transport button a push button's height."""
        button = QPushButton(self)
        fxicons.set_icon(button, icon)
        side = fxstyle.control_height(self)
        button.setFixedSize(side, side)
        button.setFlat(True)
        if slot is not None:
            button.clicked.connect(slot)
        apply_tip(button, title, body, keys)
        return button
```

The track, lines 274–278:

```python
        self._track_widget = _TimelineTrack(self)
        self._track_widget.setMinimumHeight(24)
        self._track_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
```

The "below" layout's hard floor, line 362 (inside `if controls_position == "below":`):

```python
            self.setMinimumHeight(60)
```

Visibility is applied after the layouts parent the widgets, lines 379–388:

```python
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
```

The clock, lines 816–838:

```python
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
```

`set_frame` (line 679) re-anchors only when not ticking (`if not self._ticking: self._reanchor()`),
so a tick never moves the anchor.

Measured at `b283eb13` (offscreen): "below" layout minimum height is 60;
the layout's own minimum is 54 with the track, 26 with the track hidden and
`show_range=False` (just the transport row).

Tests: `tests/test_timeline_slider.py`. It fakes the clock by monkeypatching
the module's `time.perf_counter` — see lines 435–453, the pattern to copy:

```python
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
```

It steps a whole second (24 frames) after loop off, so it cannot see the bug;
it must still pass after the fix (3 + 24 = 27 > 10, so it still stops at 10).
The `_timeline(qtbot, **kwargs)` helper (lines 13–19) builds, resizes to
600×60, shows and waits.

Conventions: Google docstrings with Args; type annotations; comments say why,
briefly; tests are plain functions named as sentences.

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| Timeline tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_timeline_slider.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's 3 new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call, or it overwrites the owner's real settings.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_timeline_slider.py` — `__init__`, its docstring,
  `_button`, `_on_playback_tick`.
- `tests/test_timeline_slider.py` — new tests appended.

**Out of scope** (do NOT touch):

- `_TimelineTrack` and its painting — unrelated.
- The "left" layout's sizing — it has no 60 px floor.
- `fxgui/examples.py` — `show_track` is a small keyword; no gallery section needed.
- `CHANGELOG.md` — a release action writes it.
- Any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch: `fix/timeline-playback`.
  (There is no `.gitmodules`, so no submodule step.)
- One commit per step is fine. Style: `[FIX] ...` / `[FEAT] ...`, e.g.
  `[FIX] timeline: a wrap re-anchors the clock, so loop off keeps playing`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: Re-anchor the clock on a wrap

In `_on_playback_tick`, after computing the wrapped `frame`, move the anchor
back by the whole loops played, so `anchor + elapsed * fps` lands on the
wrapped frame. Keep `_anchor_time`: the fractional frame phase stays exact,
so timing is continuous. Target shape:

```python
            length = self._end_frame - self._start_frame + 1
            loops = (frame - self._start_frame) // length
            # The clock counts from the wrapped frame, so loop off later
            # plays on to the end instead of stopping at once.
            self._anchor_frame -= loops * length
            frame -= loops * length
```

(This replaces the `frame = self._start_frame + (frame - self._start_frame) % length`
line; the result is the same frame.)

Add the test `test_turning_loop_off_after_a_wrap_plays_on_to_the_end`
(see Test plan, test 1) and run it.

**Verify**: `...python.exe -m pytest -q tests/test_timeline_slider.py -k "loop"` → all pass, including the new test and `test_looping_wraps_by_the_clock_and_stopping_holds_the_end`.

### Step 2: Transport buttons never take focus

In `_button`, after `button.setFlat(True)`, add:

```python
        # The timeline keeps the focus, so Space plays rather than pressing
        # whichever button was clicked last.
        button.setFocusPolicy(Qt.NoFocus)
```

`Qt` is already imported. The timeline keeps `StrongFocus` (line 204).
Add test 2 (Test plan).

**Verify**: `...python.exe -m pytest -q tests/test_timeline_slider.py` → all pass.

### Step 3: Add the `show_track` keyword

1. Add `show_track: bool = True,` to the signature right after
   `show_fps: bool = True,` (before `own_clock`). Keyword position after the
   existing ones keeps every positional call working.
2. Document it in Args after `show_fps`:
   `show_track: Whether to show the track. Hidden, the "below" layout is only as tall as its rows.`
3. In the visibility block (lines 379–388), add
   `self._track_widget.setVisible(show_track)` (after the layouts have parented it, like the others).
4. Make the 60 px floor apply only with the track: change line 362 to

```python
            if show_track:
                self.setMinimumHeight(60)
```

Default behaviour is unchanged (`show_track=True` keeps the floor and the track).
Add test 3 (Test plan).

**Verify**: `...python.exe -m pytest -q tests/test_timeline_slider.py` → all pass.

### Step 4: Whole suite and lint

**Verify**: whole-suite command → `3181 passed, 6 skipped` (3178 + 3), 0 failed; lint → `All checks passed!`.

## Test plan

Append to `tests/test_timeline_slider.py`, following the fake-clock pattern of
`test_looping_wraps_by_the_clock_and_stopping_holds_the_end` (lines 435–453)
and the `_timeline` helper.

1. `test_turning_loop_off_after_a_wrap_plays_on_to_the_end` — range 1–10,
   `current_frame=9`, fake clock at 0.0, `play()`, stop the real timer
   (`timeline._playback_timer.stop()`). `now[0] += 4 / 24`, tick → frame 3.
   `set_loop_playback(False)`. `now[0] += 1 / 24 + 1e-6`, tick →
   `current_frame() == 4` and `timeline._is_playing` is True. Then
   `now[0] += 10 / 24`, tick → frame 10 and not playing. Call `timeline.stop()`
   only if still playing. (Before Step 1 this fails: frame 10, not playing.)
2. `test_space_plays_after_a_transport_button_was_clicked` —
   `timeline = _timeline(qtbot, start_frame=1, end_frame=100)`;
   `timeline.setFocus()`; `QTest.mouseClick(timeline._next_btn, Qt.LeftButton)`
   (a synthetic event; it does not move the real pointer);
   assert `timeline.focusWidget() is timeline`;
   `QTest.keyClick(timeline.focusWidget(), Qt.Key_Space)`; assert
   `timeline._is_playing`; `timeline.stop()`. Also assert every transport
   button has `focusPolicy() == Qt.NoFocus` (`_goto_start_btn`, `_prev_btn`,
   `_play_btn`, `_next_btn`, `_goto_end_btn`, `_loop_btn`, `_prev_key_btn`,
   `_next_key_btn`, `_mark_in_btn`, `_mark_out_btn`). (Before Step 2 the
   clicked button holds focus and Space presses it.)
3. `test_a_hidden_track_lets_a_player_shrink_to_its_controls` —
   `_timeline(qtbot, controls_position="below", show_range=False, show_track=False)`;
   assert `not timeline._track_widget.isVisible()`, `timeline.minimumHeight() < 60`
   and `timeline.sizeHint().height() < 60`. A default `_timeline(qtbot, controls_position="below")`
   still has `minimumHeight() == 60` and a visible track.

`Qt` and `QTest` are already imported at the top of the test file.

## Done criteria

- [ ] `tests/test_timeline_slider.py` passes, with the 3 new tests.
- [ ] Whole suite: `3181 passed, 6 skipped`, 0 failed.
- [ ] Lint: `All checks passed!`.
- [ ] `grep -n "show_track" fxgui/fxwidgets/_timeline_slider.py` shows the keyword, its docstring line, and its two uses.
- [ ] `git status` shows only the two in-scope files modified.
- [ ] `plans/2026-11-14-audit/README.md` row 004 updated.

## STOP conditions

Stop and report (do not improvise) if:

- The excerpts above do not match the live code (drift).
- `test_looping_wraps_by_the_clock_and_stopping_holds_the_end` fails after
  Step 1 — the re-anchor changed wrap timing, which it must not.
- After Step 2, any existing test that clicks a transport button and then
  expects that button to have focus fails (none is known; report which).
- Hiding the track breaks `track_rect()` users in the suite
  (`test_the_track_rect_spans_the_frames_the_track_draws` or any other).
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- Public behaviour changes: transport buttons are no longer in the Tab
  order and never take focus on click (keyboard users drive playback with
  the timeline's own keys, which the button tips name). New opt-in keyword
  `show_track`. A loop turned off after a wrap now plays to the end — a fix.
- The loop button has no key of its own; with `NoFocus` it is mouse-only.
  If keyboard access to loop is wanted, add a key in `keyPressEvent` (e.g. L)
  and to the loop button's tip, rather than giving the button focus back.
- Reviewer: check the anchor arithmetic keeps `elapsed` continuous (no
  `_anchor_time` reset on a wrap), so a wrap never drops or repeats a frame.
- Plan 019 ("public names for what Pascal reaches into") may also list the
  track; `show_track` covers Pascal's only use.
- Pascal, once this ships: in `src/ls_pascal/apps/widgets/player.py`
  `_timeline` (lines ~1063–1071 on origin/main), delete the `NoFocus` loop
  over `findChildren(QAbstractButton)`, the `timeline._track_widget.setVisible(track)`
  line and `timeline.setMinimumHeight(0)`, and pass `show_track=track` to the constructor.
