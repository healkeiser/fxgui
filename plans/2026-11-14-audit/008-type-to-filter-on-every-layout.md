# Plan 008: Type-to-filter takes AltGr characters on every keyboard layout

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_keyboard.py tests/test_keyboard_widgets.py docs/how-to/widgets.md`
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

`FXKeyboardTree` (and `FXFilteredTree`, which wraps it) sends what you type
on the tree into a filter field. It refuses any key held with Ctrl or Alt,
so that shortcuts like Ctrl+A stay shortcuts. But Qt on Windows reports
the **AltGr** key (the right Alt, used on many European layouts to type
symbols) as Ctrl+Alt. So on a French AZERTY keyboard the characters
`@ # { [ | \ ] } €`, and on German QWERTZ `@ { [ ] } \ | €`, never reach
the filter: the key is silently dropped. Artists with those keyboards
cannot filter a tree by a name containing `@` or `#`. After this plan, a
printable character typed with exactly Ctrl+Alt (AltGr) counts as typing;
plain Ctrl, plain Alt and Meta chords stay commands.

## Current state

Files:

- `fxgui/fxwidgets/_keyboard.py` — `FXKeyboardTree` (lines 40–109);
  the modifier set at line 27; the typing test at lines 101–109.
- `tests/test_keyboard_widgets.py` — the pattern; helpers `_shown`,
  `_press`, `_tree_and_field` (lines 23–55); the existing
  `test_a_command_chord_is_not_typing` (lines 80–84) must keep passing.
- `docs/how-to/widgets.md` — the widget list mentions `FXKeyboardTree`
  (line 101) and `FXFilteredTree` (line 94); there is no section about
  them yet. Sections: `## Breadcrumbs` (157), `## Your Own Item-Data Roles`
  (199), `## Tooltips` (222).

`fxgui/fxwidgets/_keyboard.py:26-27`:

```python
# Shift is absent: shifted characters are still typing.
_COMMAND_MODIFIERS = Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier
```

`fxgui/fxwidgets/_keyboard.py:101-109`:

```python
    def _typed_into_the_field(self, event: QKeyEvent) -> bool:
        field, text = self._filter_field, event.text()
        if field is None or not text or not text.isprintable():
            return False
        if text in self._qt_keys or event.modifiers() & _COMMAND_MODIFIERS:
            return False
        field.setFocus(Qt.ShortcutFocusReason)
        field.insert(text)
        return True
```

`_COMMAND_MODIFIERS` is also used by `_is_return` (lines 34–37); leave that
use alone.

Facts measured during planning (offscreen probe, this commit):

- `QTest.keyClick(tree, Qt.Key_At, Qt.ControlModifier | Qt.AltModifier)`
  delivers a key event with text `"@"` and modifiers Ctrl+Alt; the filter
  stays empty today.
- With a window `QShortcut(QKeySequence("/"))` next to a tree that has
  `type_into(field)`, `QTest.keyClick(tree, Qt.Key_Slash)` fires the
  shortcut and the field stays empty: Qt's shortcut map runs before the
  tree sees the key. `Qt.Key_Exclam` (no shortcut) types `!` into the field.

The owner's report, and the verdict (record it; do not act on it): on
AZERTY the key at the US `/` position types `!`. Qt matches shortcuts by
the **character** produced, so `!` correctly goes to the filter, and
Shift+`:` (which types `/` on AZERTY) fires a `/` shortcut. That is
correct behaviour. Matching shortcuts by physical key (`nativeScanCode`)
is rejected: `QShortcut` cannot do it, macOS gives no scan codes, and the
keycap shown in a tooltip would name the wrong character.

Conventions: Google-style docstrings, type annotations, Qt only through
`qtpy`, comments explain why in one line.

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| Keyboard tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_keyboard_widgets.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer and takes keyboard focus). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_keyboard.py` — `_typed_into_the_field` and a new
  module-level constant/helper next to `_COMMAND_MODIFIERS`.
- `tests/test_keyboard_widgets.py` — new tests appended.
- `docs/how-to/widgets.md` — one new short section.

**Out of scope** (do NOT touch):

- Which handler wins between a window's single-character shortcut and
  typing on the tree. Today the shortcut wins (Qt's shortcut map runs
  first). Changing that is an owner decision; the new test only records it.
- Matching shortcuts by physical key (scan code): rejected, see above.
- `_is_return` and `FXSplitButton.keyPressEvent`.
- macOS Option-key characters (see Maintenance notes).
- `CHANGELOG.md`, any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch:
  `fix/type-to-filter-altgr`. (No `.gitmodules`: no submodule step.)
- Commit style, e.g. `[FIX] FXKeyboardTree: AltGr characters reach the filter`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: Write the failing test first

Append to `tests/test_keyboard_widgets.py` test 1 from the "Test plan"
(`test_an_altgr_character_is_typing`).

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_keyboard_widgets.py -k altgr`
→ 1 failed (the field text is `''`, not `'@'`).

### Step 2: Count AltGr as typing

In `fxgui/fxwidgets/_keyboard.py`, under `_COMMAND_MODIFIERS`, add:

```python
# Windows reports AltGr as Ctrl+Alt, so exactly those two (Shift allowed)
# with a printable character is typing: @ # { [ on AZERTY and QWERTZ.
_ALTGR = Qt.ControlModifier | Qt.AltModifier


def _is_typing(event: QKeyEvent) -> bool:
    """Return whether `event`'s modifiers leave it plain typing."""
    held = event.modifiers() & _COMMAND_MODIFIERS
    return held == Qt.NoModifier or held == _ALTGR
```

and in `_typed_into_the_field` replace
`if text in self._qt_keys or event.modifiers() & _COMMAND_MODIFIERS:` with
`if text in self._qt_keys or not _is_typing(event):`.

Notes for the executor:

- `held` masks out Shift and Keypad, so Shift+AltGr still types; Meta with
  Ctrl+Alt is not equal to `_ALTGR`, so it stays a command.
- If `held == Qt.NoModifier` raises a type error in this binding, compare
  with `not held` instead; both mean "no command modifier".
- A Ctrl+Alt shortcut registered on the window (e.g. Ctrl+Alt+E) still
  wins: Qt's shortcut map runs before `keyPressEvent`.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_keyboard_widgets.py`
→ all pass, including `test_an_altgr_character_is_typing` and the existing
`test_a_command_chord_is_not_typing`.

### Step 3: Add the remaining tests

Append tests 2–4 from the "Test plan".

**Verify**: same command → all pass: 4 new test functions, 6 new test
items (test 2 has 3 parameters).

### Step 4: Docs

In `docs/how-to/widgets.md`, add a section `## Keyboard Trees` right before
`## Tooltips` (not after `## Breadcrumbs`, which another plan edits). Keep
it short, plain words:

- `FXKeyboardTree.type_into(field)` sends what is typed on the tree to a
  filter field; `FXFilteredTree` does it for you. So a tree needs no
  "focus the filter" shortcut: start typing.
- Ctrl, Alt and Meta chords stay commands; a character typed with AltGr
  (reported by Windows as Ctrl+Alt) is typing.
- A shortcut made of one symbol (`/`, `?`) depends on the keyboard layout:
  Qt matches the character typed, not the key's position, so on AZERTY
  `/` is Shift+`:`. A window shortcut of one character wins over typing on
  the tree, so keep single-character shortcuts off windows that hold a
  filtered tree, or use a chord (`Ctrl+F`).

One small code block:

```python
from fxgui.fxwidgets import FXFilteredTree

tree = FXFilteredTree(placeholder="Filter shots...")
# Typing on tree.tree goes to tree.filter_bar.
```

**Verify**: `grep -n "## Keyboard Trees" docs/how-to/widgets.md` → one
match, on a line before `## Tooltips`. You add no links, so the strict docs
build cannot break; zensical is not installed in the venv, do not install
it, and say in your report that the docs build was not run.

### Step 5: Whole suite and lint

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8`
→ `3184 passed, 6 skipped` (3178 + 6 new items), 0 failed.
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .`
→ `All checks passed!`

## Test plan

Append to `tests/test_keyboard_widgets.py`, using its `_tree_and_field`
and `_press` helpers (`_press` sends `QTest.keyClick` to the focus widget,
which goes through Qt's shortcut override first, like a real key).

1. `test_an_altgr_character_is_typing` — `tree.type_into(field)`;
   `_press(Qt.Key_At, Qt.ControlModifier | Qt.AltModifier)` → `field.text() == "@"`
   and `field.hasFocus()`; then `tree.setFocus()`,
   `QApplication.processEvents()`, and
   `_press(Qt.Key_BraceLeft, Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier)`
   → `field.text() == "@{"` (Shift with AltGr still types).
2. `test_alt_and_meta_chords_are_not_typing` — parametrize over
   `(Qt.Key_F, Qt.AltModifier)`, `(Qt.Key_At, Qt.MetaModifier)`,
   `(Qt.Key_At, Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)` →
   `field.text() == ""` and `tree.hasFocus()`.
3. `test_a_window_shortcut_of_one_character_wins_over_typing` — build with
   `_tree_and_field`, `tree.type_into(field)`, add
   `QShortcut(QKeySequence("/"), window)` (import `QShortcut`,
   `QKeySequence` from `qtpy.QtGui`), count `activated`;
   `_press(Qt.Key_Slash)` → shortcut fired once, `field.text() == ""`.
   Docstring: it records today's priority, not a wish.
4. `test_a_character_with_no_shortcut_is_typing` — `_press(Qt.Key_Exclam)`
   → `field.text() == "!"` (the AZERTY key at the US `/` place).

Do not add a test for Ctrl+Alt+letter: `QTest` gives such an event the
letter as text, while a real US keyboard gives none, so the test would
assert something no user sees.

## Done criteria

- [ ] `pytest -q tests/test_keyboard_widgets.py` passes with 6 new test
      items (4 functions; test 2 has 3 parameters).
- [ ] Whole suite: `3184 passed, 6 skipped` (3178 + 6), 0 failed.
- [ ] Ruff passes.
- [ ] `git status` shows only the three in-scope files.
- [ ] `plans/2026-11-14-audit/README.md` status row updated.

## STOP conditions

- `_typed_into_the_field` or `_COMMAND_MODIFIERS` no longer match the
  excerpts (drift).
- `test_a_command_chord_is_not_typing` (Ctrl+A) fails after Step 2.
- Test 3 shows the shortcut does not fire, or the field gets `/`: Qt's
  shortcut order differs from what was measured; report it, do not change
  the tree to "fix" the priority.
- Any `FXFilteredTree` test fails after Step 2.

## Maintenance notes

- Public behaviour change (a defect fix): on Windows, a printable
  character typed with AltGr (Ctrl+Alt) on an `FXKeyboardTree` with
  `type_into` now goes to the filter. Signatures unchanged.
- Known limit: an unregistered Ctrl+Alt+letter chord whose event carries a
  printable letter would also type it. On Windows US layouts such events
  carry no text, so this is theoretical.
- Deferred: macOS reports Option as Alt, and Option types characters there
  (Option+5 is `{` on French Mac). Alt alone is still refused, so on a Mac
  those characters do not reach the filter. Not fixed here because it
  could not be tested on this Windows box; the fix would be
  "on `sys.platform == 'darwin'`, Alt alone with printable text is typing".
- Owner decision, out of scope: whether typing on a focused tree should win
  over a window's single-character shortcut. Test 3 pins today's answer
  (the shortcut wins); change the test with the decision.
- Pascal: nothing to delete. If Pascal has a single-symbol window shortcut
  to focus a tree's filter, it can drop it, since typing on the tree
  already filters.
