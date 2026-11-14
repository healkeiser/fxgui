# Plan 015: Seven small widget defects fixed, each with its test

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_toggle_switch.py fxgui/fxwidgets/_checkable_combo.py fxgui/fxwidgets/_accordion.py fxgui/fxwidgets/_inputs.py fxgui/fxwidgets/_status_dot.py fxgui/fxwidgets/_tag_input.py fxgui/fxwidgets/_tree_items.py fxgui/fxwidgets/_flow_layout.py tests/test_toggle_switch.py tests/test_checkable_combo.py tests/test_accordion.py tests/test_inputs.py tests/test_status_dot.py tests/test_tag_input.py tests/test_sorted_tree_item.py tests/test_flow_layout.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. Each step is independent: a
> mismatch in one step's file blocks only that step — do the others and
> report the blocked one.

## Status

- **Priority**: P2
- **Effort**: S (each step is a few lines)
- **Risk**: LOW
- **Depends on**: none (plan 011 also edits `_tag_input.py`, the chip's
  label line; this plan edits the remove button lines — no overlap)
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Seven independent defects, each confirmed by a probe at `b283eb13`:

1. A toggle switch checked with its signals blocked draws as off.
2. A checkable combo ticks a disabled row; and nothing but the painted text
   says which rows are ticked (screen readers read Qt's `currentText()`, a
   different value).
3. An empty accordion is falsy (`if accordion:` is False), because it defines `__len__`.
4. A read-only validated line edit shakes and flashes red on every key.
5. The status dot is clickable but unreachable by keyboard and nameless to a
   screen reader (Pascal wires its click to open the Timesheet); a tag
   chip's remove button has no tooltip or accessible name.
6. Natural sort crashes on a superscript digit: `'²'.isdigit()` is True and `int('²')` raises.
7. `FXFlowLayout` ignores its contents margins.

## Current state (probe results at `b283eb13`)

```
1 toggle checked True pos 0.0
2 disabled ticked: ['b'] currentText 'a' display 'b'
3 empty accordion bool False
4 readonly flash group State.Running
5 dot focus 0 (NoFocus) acc name ''; chip remove tip '' ''
6 _natural_key("1²") raises ValueError
7 margins (10,20,30,40): label at (0,0); heightForWidth(300) 12; minimumSize 60x12
```

Conventions: Google docstrings; type annotations; comments say why,
briefly; Qt only through `qtpy`; colours read from `fxstyle.colors()` at
paint time; tests are plain functions named as sentences, one test file per
widget (paths below). `apply_tip` lives in `fxgui/fxwidgets/_tips.py`
(import: `from fxgui.fxwidgets._tips import apply_tip`); it sets a rich
tooltip, a status tip and, unless the caller set one, the accessible name.

### 1. `fxgui/fxwidgets/_toggle_switch.py`

Line 73: `self.toggled.connect(self._on_toggled)`. Lines 102–111:

```python
    def _on_toggled(self, checked: bool) -> None:
        """Slide to the new state, or jump there while nobody sees it."""
        self._animation.stop()
        end = 1.0 if checked else 0.0
        if not self.isVisible():
            self.position = end
            return
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(end)
        self._animation.start()
```

`toggled` is not emitted while signals are blocked, so the thumb stays.
Qt calls the virtual `checkStateSet()` from `setChecked` even with signals
blocked — but NOT during a mouse click (probed: a click calls
`nextCheckState` and emits `toggled`, no `checkStateSet`). So both hooks are
needed. Calling `_on_toggled` twice for one change is harmless (the second
call restarts the same slide from the same position).
Tests: `tests/test_toggle_switch.py` (pattern: `test_a_switch_checked_before_it_shows_is_drawn_on`, line 15).

### 2. `fxgui/fxwidgets/_checkable_combo.py`

Lines 119–126:

```python
    def _toggle(self, row: int) -> None:
        item = self.model().item(row) if row >= 0 else None
        if item is not None:
            item.setCheckState(
                Qt.Unchecked
                if item.checkState() == Qt.Checked
                else Qt.Checked
            )
```

It is called from `eventFilter` on a mouse release and on Space (lines
85–103), bypassing Qt's own disabled-item handling. `paintEvent` (lines
105–113) paints `display_text()` (line 81: the ticked rows joined by
", "). `_on_item_changed` (lines 128–135) runs on every tick change:

```python
    def _on_item_changed(self, *_) -> None:
        if self._setting:
            return
        self.update()
        checked = self.checked_items()
        if checked != self._said:
            self._said = checked
            self.checked_changed.emit(checked)
```

Class docstring lines 19–35. Tests: `tests/test_checkable_combo.py`
(helpers `_opened`, `_click_row`, lines 14–28).

### 3. `fxgui/fxwidgets/_accordion.py`, lines 173–179

```python
    def __len__(self) -> int:
        """Return the number of sections."""
        return len(self._sections)

    def __iter__(self):
        """Iterate over sections."""
        return iter(self._sections)
```

Tests: `tests/test_accordion.py` (pattern: line 11, `FXAccordion(animation_duration=0)`).

### 4. `fxgui/fxwidgets/_inputs.py`, `FXValidatedLineEdit.keyPressEvent`, lines 172–186

```python
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Shake when a typed character changed nothing: it was rejected."""
        # The selection too: a selected character retyped as itself leaves
        # the text and cursor as they were, but was taken.
        before = (self.text(), self.cursorPosition(), self.selectedText())
        super().keyPressEvent(event)
        typed = event.text()
        if (
            self.validator() is not None
            and typed
            and typed.isprintable()
            and (self.text(), self.cursorPosition(), self.selectedText())
            == before
        ):
            self._show_rejection_feedback()
```

Tests: `tests/test_inputs.py` — helpers `_validated(qtbot)` (lines 19–25)
and `_animating(edit)` (lines 28–30).

### 5. `fxgui/fxwidgets/_status_dot.py` (whole widget, 75 lines) and the chip

```python
    def __init__(self, parent: Optional[QWidget] = None, diameter: int = 8):
        super().__init__(parent)
        self._feedback: Optional[str] = None
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.PointingHandCursor)

    def set_feedback(self, key: Optional[str], tooltip: str = "") -> None:
        ...
        known = key if hasattr(
            fxstyle.colors(), f"feedback_{key}_foreground") else None
        self.setToolTip(tooltip)
        if known != self._feedback:
            self._feedback = known
            self.update()
    ...
    def paintEvent(self, event) -> None:
        """Fill one antialiased circle, inset half a pixel so no edge is cut."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color())
        painter.drawEllipse(
            QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        )

    def mouseReleaseEvent(self, event) -> None:
        """Emit `clicked` on a left-button release."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)
```

`tests/test_status_dot.py` line 39 asserts `dot.toolTip() == "Recording"` —
keep `setToolTip(tooltip)` as is. Imports at lines 7–8:
`from qtpy.QtCore import QRectF, Qt, Signal` and
`from qtpy.QtGui import QColor, QPainter, QPalette`.

Chip remove button, `fxgui/fxwidgets/_tag_input.py` lines 57–66:

```python
        self.remove_button = None
        if removable:
            self.remove_button = QPushButton()
            self.remove_button.setFixedSize(16, 16)
            self.remove_button.setFlat(True)
            self.remove_button.setCursor(Qt.PointingHandCursor)
            self.remove_button.clicked.connect(self._on_remove)
            layout.addWidget(self.remove_button)
            fxicons.set_icon(
                self.remove_button, "x", color="icon_on_accent_primary")
```

Tests: `tests/test_status_dot.py`, `tests/test_tag_input.py`.

### 6. `fxgui/fxwidgets/_tree_items.py`, lines 49–54

```python
    @staticmethod
    def _natural_key(text: str) -> list:
        return [
            int(part) if part.isdigit() else part.lower()
            for part in _NATURAL_SORT_PATTERN.split(text)
        ]
```

Line 13: `_NATURAL_SORT_PATTERN = re.compile(r"([0-9]+)")` (ASCII digits
only), so `"1²"` splits to `['', '1', '²']`, and `'²'.isdigit()` is True.
`str.isdecimal()` is False for `'²'`. Tests: `tests/test_sorted_tree_item.py`
(helper `_sorted(qtbot, rows)`, lines 11–23).

### 7. `fxgui/fxwidgets/_flow_layout.py`, lines 67–85

```python
    def heightForWidth(self, width: int) -> int:
        """Return the height wrapping into `width` takes."""
        return self._place(QRect(0, 0, width, 0), move=False)

    def setGeometry(self, rect: QRect) -> None:
        """Place every item inside `rect`, wrapping."""
        super().setGeometry(rect)
        self._place(rect, move=True)

    def sizeHint(self) -> QSize:
        """Return the minimum size: asking for more would widen the parent."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Return the widest single item: nothing narrower can hold it."""
        size = QSize()
        for item in self._shown():
            size = size.expandedTo(item.minimumSize())
        return size
```

`__init__` sets margins to 0, so every existing user (and Pascal, which never
sets margins on one) is unaffected. Tests: `tests/test_flow_layout.py`
(helper `_row(qtbot, count, spacing)`, lines 11–18).

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| This plan's tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_toggle_switch.py tests/test_checkable_combo.py tests/test_accordion.py tests/test_inputs.py tests/test_status_dot.py tests/test_tag_input.py tests/test_sorted_tree_item.py tests/test_flow_layout.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call, or it overwrites the owner's real settings.

## Scope

**In scope** (the only files you should modify): the eight source files and
eight test files named in the drift check, at the symbols named per step.

**Out of scope** (do NOT touch):

- The chip's label text format (plan 011).
- `FXStatusDot`'s tooltip text handling (it stays `setToolTip(tooltip)`, a test pins it).
- `FXCheckableComboBox.currentText()` — it is Qt's, and overriding it would
  change what Qt's own code reads; document it instead.
- `fxgui/examples.py` — no new public widget.
- `CHANGELOG.md`; any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch: `fix/small-widget-defects`.
  (There is no `.gitmodules`, so no submodule step.)
- One commit per step, e.g. `[FIX] toggle switch: a blocked setChecked still moves the thumb`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

Each step: make the change, add its test (Test plan, same number), run the
step's test file.

### Step 1: Toggle switch thumb follows any check change

Keep the `toggled` connection (a mouse click does not call `checkStateSet`).
Add, after `_on_toggled`:

```python
    def checkStateSet(self) -> None:
        """Follow a `setChecked` too, which says nothing with signals blocked."""
        super().checkStateSet()
        self._on_toggled(self.isChecked())
```

**Verify**: `...python.exe -m pytest -q tests/test_toggle_switch.py` → all pass.

### Step 2: Checkable combo skips disabled rows and says what is ticked

1. In `_toggle`, change the guard to
   `if item is not None and item.isEnabled():`.
2. In `_on_item_changed`, after `self.update()`, add
   `self.setAccessibleDescription(self.display_text())` with the comment
   `# A screen reader reads Qt's current row; the ticks are the value.`
   (Description, not name: the name is the caller's label for the combo.)
3. Add to the class docstring, after the paragraph:
   `` `currentText()` is Qt's current row, not the ticks: read `checked_items()` or `display_text()`. ``

**Verify**: `...python.exe -m pytest -q tests/test_checkable_combo.py` → all pass.

### Step 3: An accordion is always truthy

Add after `__len__`:

```python
    def __bool__(self) -> bool:
        """Return True: an empty accordion is still a widget."""
        return True
```

**Verify**: `...python.exe -m pytest -q tests/test_accordion.py` → all pass.

### Step 4: A read-only validated edit never shakes

In `keyPressEvent`, add `not self.isReadOnly()` as the first condition of the `if`.

**Verify**: `...python.exe -m pytest -q tests/test_inputs.py` → all pass.

### Step 5: The status dot is reachable and named; the chip's remove button is named

Status dot (`_status_dot.py`):

1. In `__init__`, add `self.setFocusPolicy(Qt.TabFocus)` — Tab reaches it;
   a mouse click does not pull focus away from where the person was typing.
2. In `set_feedback`, after `self.setToolTip(tooltip)`, add
   `self.setAccessibleName(tooltip)`.
3. Add a key handler:

```python
    def keyPressEvent(self, event) -> None:
        """Emit `clicked` on Space or Enter, as a button does."""
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)
```

4. Show focus: in `paintEvent`, replace `painter.setPen(Qt.NoPen)` with

```python
        # A focused dot wears a ring, so the keyboard shows where it is.
        painter.setPen(
            QPen(QColor(fxstyle.colors().accent_primary), 1.0)
            if self.hasFocus() else Qt.NoPen
        )
```

   and import `QPen` from `qtpy.QtGui`. Also update the class docstring's
   `Signals:` line to `clicked: A left-button release, or Space or Enter while focused.`

Chip (`_tag_input.py`): import `apply_tip` from `fxgui.fxwidgets._tips` and,
after `layout.addWidget(self.remove_button)`, add
`apply_tip(self.remove_button, "Remove", text)`.

**Verify**: `...python.exe -m pytest -q tests/test_status_dot.py tests/test_tag_input.py` → all pass.

### Step 6: Natural sort ignores superscripts

In `_natural_key`, replace `part.isdigit()` with `part.isdecimal()`.

**Verify**: `...python.exe -m pytest -q tests/test_sorted_tree_item.py tests/test_item_views.py` → all pass.

### Step 7: The flow layout honours its contents margins

```python
    def heightForWidth(self, width: int) -> int:
        """Return the height wrapping into `width` takes, margins included."""
        margins = self.contentsMargins()
        inner = width - margins.left() - margins.right()
        return (
            self._place(QRect(0, 0, inner, 0), move=False)
            + margins.top() + margins.bottom()
        )

    def setGeometry(self, rect: QRect) -> None:
        """Place every item inside `rect` less the margins, wrapping."""
        super().setGeometry(rect)
        self._place(rect.marginsRemoved(self.contentsMargins()), move=True)
```

and in `minimumSize`, before `return size`:

```python
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )
```

**Verify**: `...python.exe -m pytest -q tests/test_flow_layout.py tests/test_tag_input.py` → all pass.

### Step 8: Whole suite and lint

**Verify**: whole suite → `3186 passed, 6 skipped` (3178 + 8), 0 failed; lint → `All checks passed!`.

## Test plan

One new test per step (two for step 5), each appended to that widget's test file.

1. `tests/test_toggle_switch.py` — `test_a_switch_checked_with_signals_blocked_is_drawn_on`:
   unshown switch; `blockSignals(True)`; `setChecked(True)`; `blockSignals(False)`;
   assert `switch.position == 1.0`. (Before: 0.0.) The existing
   `test_a_shown_switch_still_slides` covers the click/`toggled` path.
2. `tests/test_checkable_combo.py` — `test_a_disabled_row_is_never_ticked`:
   `combo = _opened(qtbot)`; `combo.model().item(1).setEnabled(False)`;
   `_click_row(combo, 1)`; assert `combo.checked_items() == []` (before the
   fix: `["cache"]`). Then `_click_row(combo, 0)` and assert
   `combo.accessibleDescription() == "render"`. (Do not test Space on the
   disabled row: Qt refuses a disabled row as the view's current index, so
   `setCurrentIndex` leaves row 0 current and Space would tick "render" —
   probed.)
3. `tests/test_accordion.py` — `test_an_empty_accordion_is_truthy`:
   `accordion = FXAccordion(animation_duration=0)`; assert `bool(accordion)` and `len(accordion) == 0`.
4. `tests/test_inputs.py` — `test_a_read_only_field_never_shakes`:
   `edit = _validated(qtbot)`; `edit.setReadOnly(True)`; `QTest.keyClicks(edit, "1")`;
   assert `not _animating(edit)`.
5. `tests/test_status_dot.py` — `test_the_dot_is_reached_by_tab_and_answers_space_and_enter`:
   dot with `set_feedback("success", "Timesheet complete")`; assert
   `dot.focusPolicy() == Qt.TabFocus` and `dot.accessibleName() == "Timesheet complete"`;
   collect `clicked` in a list; `QTest.keyClick(dot, Qt.Key_Space)`,
   `QTest.keyClick(dot, Qt.Key_Return)` → two clicks. (Import `QTest` from `qtpy.QtTest`.)
   `tests/test_tag_input.py` — `test_the_remove_button_says_what_it_removes`:
   `chip = FXTagChip("comp")`; assert `chip.remove_button.accessibleName() == "Remove"`
   and `"comp" in chip.remove_button.toolTip()`.
6. `tests/test_sorted_tree_item.py` — `test_a_superscript_digit_sorts_as_text`:
   `_sorted(qtbot, [(["v2", ""], None), (["v1²", ""], None), (["v1", ""], None)])`
   returns without raising and starts with `"v1"` (assert the full order the
   run gives you is stable: `["v1", "v1²", "v2"]` — if Qt orders it
   differently, STOP and report the order).
7. `tests/test_flow_layout.py` — `test_the_margins_frame_the_items`: a host
   with `layout = FXFlowLayout(host, spacing=4)`, `layout.setContentsMargins(10, 20, 30, 40)`,
   one `QPushButton` with `setFixedSize(60, 20)`; host resized to 300×200,
   shown, `qtbot.waitExposed(host)`; assert `button.pos() == QPoint(10, 20)`,
   `layout.heightForWidth(300) == 20 + 20 + 40` and
   `layout.minimumSize() == QSize(60 + 40, 20 + 60)`.

## Done criteria

- [ ] 8 new tests exist and pass.
- [ ] Whole suite: `3186 passed, 6 skipped`, 0 failed.
- [ ] Lint: `All checks passed!`.
- [ ] `grep -n "isdigit" fxgui/fxwidgets/_tree_items.py` → no match.
- [ ] `git status` shows only in-scope files modified.
- [ ] `plans/2026-11-14-audit/README.md` row 015 updated (list any step blocked by drift).

## STOP conditions

Stop and report (do not improvise) if:

- A step's excerpt does not match the live code (block only that step; do the others).
- Step 1: `test_a_shown_switch_still_slides` or any toggle test fails —
  the double hook must not change the click slide.
- Step 5: any existing test asserts the status dot has `NoFocus`, or the
  focus ring breaks `test_a_state_paints_in_its_feedback_colour` (it grabs
  an unfocused dot, so it should not).
- Step 7: any existing flow-layout or tag-input geometry test changes result
  (all existing layouts have zero margins).
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- Public behaviour changes (all fixes): blocked `setChecked` moves the
  thumb; disabled combo rows cannot be ticked; the combo's accessible
  description is its ticks; `bool(FXAccordion())` is True; read-only fields
  stay still; the status dot is in the Tab order, answers Space/Enter, has
  an accessible name and a focus ring; the chip's remove button has a tip
  and a name; superscripts no longer crash sorting; flow-layout margins
  apply. Nobody calling these APIs as documented loses anything.
- Reviewer: step 5's focus ring is 1 px inside an 8 px dot; check it reads
  in light and dark themes in the gallery (`python -m fxgui.examples`).
- Deferred: `FXStatusDot`'s tooltip goes through `setToolTip` raw (rich-text
  guess on caller text). Callers pass fixed strings today; switching to
  `apply_tip` would change `toolTip()` and a pinned test.
- Pascal, once this ships: nothing to delete. The launcher's timesheet dot
  (`src/ls_pascal/apps/launcher/views/popup.py` ~293) becomes keyboard-reachable
  with no change; its tooltip text becomes its spoken name.
