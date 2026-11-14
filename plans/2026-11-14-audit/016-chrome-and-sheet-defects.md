# Plan 016: A banner waits for show(), a hover tip never erases a message, the base sheet parses, and the proxy's sort is documented

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_notification_banner.py fxgui/fxwidgets/_status_bar.py fxgui/qss/style.qss fxgui/fxcore.py tests/test_notification_banner_dismiss.py tests/test_status_bar.py tests/test_base_sheet.py tests/test_fxcore.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. Steps are independent: drift in
> one step's file blocks only that step. (Plan 011 also edits
> `_notification_banner.py` — other lines; if it landed first, only line
> numbers move.)

## Status

- **Priority**: P2
- **Effort**: S (each step)
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Four independent defects in window chrome and the theme sheet:

1. **A banner made on a hidden parent pops up by itself.** A child widget
   that was never hidden explicitly is shown with its parent. A banner built
   before its window shows appears at the top right with no slide and no
   dismiss timer (probed: visible at (464, 0), timer inactive), before the
   code ever calls `show()`.
2. **A hover tip erases a status bar error in a plain `QMainWindow`.** Only
   `FXMainWindow` routes Qt's status tips to `FXStatusBar.show_tip`. In any
   other window, Qt writes the tip into `QStatusBar`'s own message, which
   kills the bar's timeout and, when the tip clears, emits an empty
   `messageChanged` — which the bar takes as "the message timed out" and
   clears a 60 s error. Probed: after hovering, the error label is empty and
   the tint gone. While the tip shows, Qt also paints the tip text under fxgui's label.
3. **Malformed declarations in the base sheet** (`fxgui/qss/style.qss`): two
   colours in one `border`, a `background` given a width and a style, and a
   selector that paints any 3 px tall or wide `QFrame` (a `QLabel` is a
   `QFrame`) through Qt's read-only `height`/`width` properties. Qt drops or
   half-reads them silently; a later edit "fixing" one by guess changes
   layouts everywhere (probed: `border: 1px solid transparent` on the
   `QFrame[frameShape="0"]` rule grows every label by 2 px).
4. **`FXSortFilterProxyModel` never sorts by value.** With no filter,
   `lessThan` returns source row order, so a header click does nothing.
   Investigation (below) shows this is the intended design; the fix is to
   document it.

## Current state

### 1. Banner — `fxgui/fxwidgets/_notification_banner.py`

End of `__init__`, lines 278–285:

```python
        self._update_icons()

        for label, callback in (actions or {}).items():
            self.add_action(label, callback)

        self.adjustSize()
        if parent:
            parent.installEventFilter(self)
```

`show()` (line 334) positions, animates and starts the timer; `_staying`
(lines 103–112) counts only banners with `not banner.isHidden()`.
The same pattern exists and works in `FXLoadingOverlay`,
`fxgui/fxwidgets/_loading_spinner.py` line 178: `self.hide()` as the last
line of `__init__`. Tests: `tests/test_notification_banner_dismiss.py`
(helper `_host(qtbot)` lines 27–33; `test_banners_shown_on_a_hidden_parent_stack`
line 110 must keep passing).

### 2. Status bar — `fxgui/fxwidgets/_status_bar.py`

`FXStatusBar(QStatusBar)` line 240. Connection at line 315:
`self.messageChanged.connect(self._on_status_message_changed)`.
`showMessage` (lines 376–431) writes fxgui's own labels and calls
`super().showMessage(" ", timeout=int(duration * 1000))` (line 412) only so
Qt's timer ends the message. The handler, lines 466–470:

```python
    @Slot(str)
    def _on_status_message_changed(self, message: str) -> None:
        """Clear the labels and tint when Qt's timeout empties the message."""
        if not message:
            self._clear()
```

`show_tip(tip)` (lines 357–374) writes a tip where messages go and gives a
still-standing message back on an empty tip. `showEvent`, lines 514–518:

```python
    def showEvent(self, event) -> None:
        """Run the busy line again, if it ran when the bar hid."""
        super().showEvent(event)
        self._hold_message_room()
        self._run_busy_line()
```

`QEvent` is already imported (from `qtpy.QtCore`). The class has no
`eventFilter` today. `FXMainWindow.event`
(`fxgui/fxwidgets/_main_window.py` lines 604–608) routes
`QStatusTipEvent` to `bar.show_tip(event.tip())` — leave it; it becomes a
fallback.

Root cause: `QMainWindow::event` handles `QEvent.StatusTip` by calling the
C++ `QStatusBar::showMessage(tip)` (the Python override is never called),
which replaces the `" "` message and its timer. A status-tip event travels
up the parent chain to the window, so an event filter on the bar's
`window()` sees it first. Probed with such a filter: during the tip the
label shows the tip and `currentMessage()` stays `" "`; after the tip the
error and its tint are back.

Tests: `tests/test_status_bar.py` (helper `_bar(qtbot)` lines 16–30, a plain
`QWidget` host); `tests/test_status_items.py` lines 169–196 cover the
`FXMainWindow` path and must keep passing.

### 3. Sheet — `fxgui/qss/style.qss` (1705 lines)

Lines 509–513:

```css
QFrame[frameShape="0"]
{
    border-radius: @button_radius;
    border: 1px transparent @border_strong;
}
```

Lines 548–558:

```css
QTextEdit#fxOutputLogArea {
    font-family: @font_mono;
    font-size: 9pt;
}

QToolBar {
    border: 1px transparent @border_strong;
    background: 1px solid @surface;
    font-weight: bold;
    border-bottom: 1px solid @border;
}
```

Lines 1469–1472:

```css
QStatusBar::item {
    background: transparent;
    border: 1px transparent @border;
}
```

Lines 1481–1483:

```css
QFrame[height="3"], QFrame[width="3"] {
    background-color: @border_strong;
}
```

Probe results at `b283eb13` (offscreen, Fusion, dark and light, a window with
a label, a `NoFrame` frame, a `QTextEdit#fxOutputLogArea`, a toolbar, a
status bar with an item): replacing the five declarations as in Step 3 gives
**identical geometry and identical pixels** in both themes. Details:

- `QFrame[frameShape="0"]`: Qt reads today's value as no border.
  `border: none;` is identical. `border: 1px solid transparent;` is NOT (every label +2 px).
- `QToolBar`: today's `background` is read as `@surface` and the border as none.
  `border: none; background: @surface;` is identical. Deleting both lines is NOT.
- `QStatusBar::item`: `border: none;` is identical.
- `font-size: 9pt` is valid QSS, not malformed; it is the only point size in
  a sheet whose sizes are pixel tokens. `@font_size_small` (= `FONT_SIZE - 1`
  px = 12 px, `fxgui/fxstyle.py` line 1441) renders identically at 96 DPI
  and follows the theme's size from now on.
- The 3 px selector: no fxgui code makes a 3 px `QFrame` (searched
  `fxgui/` for fixed 3 px sizes), and the gallery shows none (walked every
  tab of `examples.build()`). It only paints whatever widget happens to be
  3 px when polished. Delete it.

Lines 535 (`QStackedWidget { border: 1px transparent; }`) and 1438
(`QToolBox { ... border: 1px transparent; }`) are valid (width + colour; no
style means none) — leave them.

Tests: `tests/test_base_sheet.py` (pattern: `test_the_base_sheet_sets_no_background_or_font`,
line 58, which reads `fxstyle._build_stylesheet("dark")`; fixture `app_root`
from `tests/conftest.py` lines 122–142).

### 4. Proxy — `fxgui/fxcore.py`

`FXSortFilterProxyModel(QSortFilterProxyModel)`, line 57. Its `__init__`
ends with `self.sort(0, Qt.AscendingOrder)` (line 98): the proxy always
sorts, so that filtering can rank. `lessThan`, lines 189–196:

```python
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Rank the higher score in the sorted column first; ties keep order."""
        if self._active():
            left_score = self._cell_score(left)
            right_score = self._cell_score(right)
            if left_score != right_score:
                return left_score > right_score
        return left.row() < right.row()
```

Intent evidence:

- `tests/test_item_views.py` line 556, `test_a_substring_hit_ranks_with_a_perfect_score`:
  `# A tie keeps the source order.` then asserts `["heron", "character_hero_main"]`
  (alphabetical would swap them).
- Because of the `sort(0)` in `__init__`, returning `super().lessThan(...)`
  with no filter would alphabetise every model behind this proxy by
  default — a silent default change for every consumer.
- No fxgui widget and no Pascal code uses this proxy (searched), and no doc
  promises header sorting.

Conclusion: source order is the design; document that a header click does
not sort by value. Class docstring lines 58–74. Tests: `tests/test_fxcore.py`
(helpers `_proxy_with(words, ratio=...)` and `_visible(proxy)` at the top of the file).

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| This plan's tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_notification_banner_dismiss.py tests/test_notification_banner_defaults.py tests/test_notification_banner_actions.py tests/test_status_bar.py tests/test_status_items.py tests/test_base_sheet.py tests/test_fxcore.py tests/test_item_views.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |
| Render check | see Step 3 | before and after outputs identical |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call, or it overwrites the owner's real settings.
The venv's editable install points at another checkout: a script must put
the repo root first on `sys.path` (the script below does) and be run from the repo root.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_notification_banner.py` — the end of `__init__` only.
- `fxgui/fxwidgets/_status_bar.py` — `showEvent`, a new `eventFilter`, the
  handler's docstring.
- `fxgui/qss/style.qss` — the five declarations/rules quoted above.
- `fxgui/fxcore.py` — the `FXSortFilterProxyModel` docstring only.
- `tests/test_notification_banner_dismiss.py`, `tests/test_status_bar.py`,
  `tests/test_base_sheet.py`, `tests/test_fxcore.py` — new tests.

**Out of scope** (do NOT touch):

- `FXMainWindow.event`'s status-tip branch — harmless once the bar filters; removing it is a separate cleanup.
- `lessThan`'s logic — see the investigation; changing it changes every consumer's default order.
- Other `border: 1px transparent;` rules (lines 535, 1438) — valid.
- `CHANGELOG.md`; any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch: `fix/chrome-and-sheet-defects`.
  (There is no `.gitmodules`, so no submodule step.)
- One commit per step, e.g. `[FIX] banner: a card made on a hidden window waits for show()`,
  `[DOC] FXSortFilterProxyModel: rows keep the source order`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: A banner is hidden until `show()`

Add as the last line of `FXNotificationBanner.__init__` (after the
`installEventFilter` block):

```python
        # Hidden until show(): a child never hidden would appear with its
        # parent, unplaced and with no timer.
        self.hide()
```

Add test 1.

**Verify**: `...python.exe -m pytest -q tests/test_notification_banner_dismiss.py tests/test_notification_banner_defaults.py tests/test_notification_banner_actions.py` → all pass.

### Step 2: The status bar takes its window's status tips

In `FXStatusBar`:

1. In `showEvent`, after `super().showEvent(event)`, add
   `self.window().installEventFilter(self)` with the comment
   `# Status tips reach the window first; Qt would write them into the bar's own message, ending ours.`
   (Installing the same filter twice is a no-op in Qt.)
2. Add:

```python
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Show the window's status tips with `show_tip`, as messages are."""
        if event.type() == QEvent.StatusTip and watched is self.window():
            self.show_tip(event.tip())
            return True
        return super().eventFilter(watched, event)
```

   Import `QObject` from `qtpy.QtCore` if it is not already imported.
3. Change the handler's docstring to
   `"""Clear the labels and tint when the bar's own timeout ends its message."""`
   (its body stays: tips no longer reach Qt's message, so an empty
   `messageChanged` now only comes from the timeout or `clearMessage`).

Add test 2.

**Verify**: `...python.exe -m pytest -q tests/test_status_bar.py tests/test_status_items.py` → all pass.

### Step 3: The base sheet's declarations parse, rendered exactly as before

1. **Before editing**, save the script below as `qss_render_check.py` in a
   temporary folder outside the repo (e.g. `%TEMP%\fxgui-016\`), then run it
   from the repo root and keep its output:
   `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe %TEMP%\fxgui-016\qss_render_check.py > %TEMP%\fxgui-016\before.txt`
   (Git Bash: use `"$TEMP/fxgui-016/..."`.)

```python
"""Print the geometry and a pixel hash of widgets the edited QSS rules style."""
import hashlib, os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())
from qtpy.QtCore import QSettings
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())
from qtpy.QtWidgets import (QApplication, QFrame, QLabel, QMainWindow, QStatusBar,
                            QTextEdit, QToolBar, QVBoxLayout, QWidget)
app = QApplication([])
from fxgui import fxstyle
fxstyle.set_style(app, "Fusion")
fxstyle.register_themed_root(app)
for theme in ("dark", "light"):
    fxstyle.apply_theme(theme)
    root = QMainWindow()
    body = QWidget()
    column = QVBoxLayout(body)
    label = QLabel("label text")
    blank = QFrame()
    blank.setFrameShape(QFrame.NoFrame)
    blank.setFixedSize(40, 20)
    log = QTextEdit()
    log.setObjectName("fxOutputLogArea")
    log.setPlainText("log line")
    for widget in (label, blank, log):
        column.addWidget(widget)
    toolbar = QToolBar()
    toolbar.addAction("Act")
    root.addToolBar(toolbar)
    bar = QStatusBar()
    bar.addWidget(QLabel("item"))
    root.setStatusBar(bar)
    root.setCentralWidget(body)
    root.resize(400, 300)
    root.show()
    app.processEvents()
    for name, widget in (("label", label), ("blank", blank), ("log", log),
                         ("toolbar", toolbar), ("statusbar", bar)):
        print(theme, name, widget.geometry().getRect(), widget.contentsRect().getRect())
    image = root.grab().toImage()
    data = bytes(image.constBits())[: image.sizeInBytes()]
    print(theme, "pixels", hashlib.md5(data).hexdigest())
    root.close()
```

   Expected: 12 lines (6 per theme). Running it twice gives the same output (it is deterministic).

2. Edit `fxgui/qss/style.qss`:
   - line 512 `border: 1px transparent @border_strong;` → `border: none;`
   - line 550 `font-size: 9pt;` → `font-size: @font_size_small;`
   - lines 554–555 → `border: none;` and `background: @surface;`
   - line 1471 `border: 1px transparent @border;` → `border: none;`
   - delete lines 1481–1483 (the `QFrame[height="3"], QFrame[width="3"]` rule) and one of the blank lines around it.
3. Run the script again into `after.txt` and compare:
   `git diff --no-index %TEMP%\fxgui-016\before.txt %TEMP%\fxgui-016\after.txt` → no output (identical).
4. Add tests 3 and 4.

**Verify**: render check identical; `...python.exe -m pytest -q tests/test_base_sheet.py` → all pass.

### Step 4: Document the proxy's order (investigation outcome)

Add a paragraph to the `FXSortFilterProxyModel` class docstring, after the
first paragraph:

```
    Rows keep the source model's order until a filter ranks them, and rows
    with the same score keep it too. The proxy sorts itself to rank, so a
    view's header click does not sort by value: sort the source model.
```

Add test 5, which pins it.

**Verify**: `...python.exe -m pytest -q tests/test_fxcore.py tests/test_item_views.py` → all pass.

### Step 5: Whole suite and lint

**Verify**: whole suite → `3183 passed, 6 skipped` (3178 + 5), 0 failed; lint → `All checks passed!`.

## Test plan

1. `tests/test_notification_banner_dismiss.py` —
   `test_a_banner_made_on_a_hidden_parent_waits_for_show`: `parent = QWidget()`,
   `parent.resize(800, 600)`, `qtbot.addWidget(parent)`; banner with
   `severity_type=INFO` (timeout default 5000) built before `parent.show()`;
   `parent.show()`, `qtbot.waitExposed(parent)`; assert
   `not banner.isVisible()`; then `banner.show()`; assert `banner.isVisible()`
   and `banner._dismiss_timer.isActive()`. (Before Step 1: visible, no timer.)
2. `tests/test_status_bar.py` — `test_a_hover_tip_in_a_plain_window_gives_the_message_back`:
   `window = QMainWindow()`, `qtbot.addWidget(window)`, `bar = FXStatusBar()`,
   `window.setStatusBar(bar)`, a `QPushButton` as central widget, show and
   `qtbot.waitExposed(window)`; `bar.showMessage("boom", ERROR, duration=60)`;
   `said = bar.message_label.text()`;
   `QApplication.sendEvent(button, QStatusTipEvent("Where this leads"))` →
   assert `bar.message_label.text() == "Where this leads"` and
   `bar.currentMessage() != "Where this leads"` (Qt paints no tip of its own);
   `QApplication.sendEvent(button, QStatusTipEvent(""))` → assert
   `bar.message_label.text() == said`, `bar.message_label.isVisible()` and
   `bar.tint() is not None`. Imports: `QMainWindow`, `QPushButton`,
   `QApplication` from `qtpy.QtWidgets`; `QStatusTipEvent` from `qtpy.QtGui`.
   Close/cleanup through `qtbot`. (Before Step 2: label empty, tint None.)
3. `tests/test_base_sheet.py` — `test_the_base_sheet_has_no_half_read_declarations`:
   read `fxstyle.STYLE_FILE.read_text(encoding="utf-8")`; assert no match for
   `re.search(r"border:\s*\d+px\s+transparent\s+@", text)`, for
   `re.search(r"background:\s*\d+px", text)`, and that
   `'QFrame[height="3"]' not in text`. Add `import re` at the top of the file.
4. Same file — `test_a_three_pixel_frame_wears_no_fill_of_its_own(qtbot, app_root)`:
   a `QFrame` with `setFixedHeight(3)` added to `app_root.layout()`; `_show(qtbot, app_root)`;
   the frame's pixel `frame.grab().toImage().pixelColor(5, 1).name()` is not
   `QColor(fxstyle.colors().border_strong).name()`. (Before Step 3: it is `#444444` = border_strong in dark.)
5. `tests/test_fxcore.py` — `test_without_a_filter_rows_keep_the_source_order`:
   `proxy = _proxy_with(["banana", "apple", "cherry"])`; `proxy.sort(0)`;
   assert `_visible(proxy) == ["banana", "apple", "cherry"]`.

## Done criteria

- [ ] 5 new tests exist and pass.
- [ ] Render check: before and after outputs identical.
- [ ] Whole suite: `3183 passed, 6 skipped`, 0 failed.
- [ ] Lint: `All checks passed!`.
- [ ] `grep -n "1px transparent @\|background: 1px\|height=\"3\"" fxgui/qss/style.qss` → no match.
- [ ] `git status` shows only in-scope files modified (the render-check files live outside the repo).
- [ ] `plans/2026-11-14-audit/README.md` row 016 updated.

## STOP conditions

Stop and report (do not improvise) if:

- A step's excerpt does not match the live code (block that step only).
- Step 3's before/after outputs differ in any line: report the diff; do not
  pick another replacement by trial.
- Step 2 changes the result of any test in `tests/test_status_items.py` or
  `tests/test_status_bar.py`.
- Step 1 changes any existing banner test result.
- Your dispatch instructions say header sorting by value is wanted for
  `FXSortFilterProxyModel`: stop before Step 4 — that needs a design (the
  proxy's self-sort and the tie rule would both change), not this plan.
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- Public behaviour changes: a banner no longer appears unless `show()` is
  called (fix; every documented use calls `show()`). `FXStatusBar` in any
  window now takes that window's status tips (as it already did under
  `FXMainWindow`), and a tip never ends a message. The 3 px `QFrame` rule is
  gone: a consumer relying on it to colour a 3 px divider loses the fill (no
  fxgui or Pascal code does; such a divider should use a `frameShape`
  `HLine`/`VLine`, which the sheet styles). The log pane's font size now
  follows the theme's pixel size (identical today).
- Reviewer: check the status bar's filter returns `True` only for
  `QEvent.StatusTip` on its own window; a bar moved to another window keeps
  a filter on the old one, which then never matches (`watched is self.window()`).
- Deferred: removing `FXMainWindow.event`'s now-redundant status-tip branch.
- Pascal, once this ships: nothing to delete. Pascal's windows are
  `FXMainWindow`s with `StatusBar(FXStatusBar)`
  (`src/ls_pascal/apps/widgets/status_items.py`), so steps 1–3 only harden
  what it already gets; its banners always call `show()`.
