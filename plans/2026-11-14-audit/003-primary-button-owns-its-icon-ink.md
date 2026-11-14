# Plan 003: An icon set on a primary button keeps the on-accent ink

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxicons.py fxgui/fxwidgets/_buttons.py tests/test_primary_button.py docs/how-to/icons.md`
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

`fxicons.set_icon(button, "save")` is the documented way to put an icon on
any button. On an `FXPrimaryButton` (a button filled with the theme's accent
colour) it goes wrong in two ways:

1. The button was built with `icon=`: the icon you set is thrown away the
   next time the pointer enters or leaves the button, because the button
   re-sets its own stored icons on hover.
2. The button was built without `icon=`: the icon stays, but in the ordinary
   `icon` ink (grey `#b4b4b4` in the dark theme) on the accent fill, where
   the theme wants `icon_on_accent_primary` (`#ffffff`). It reads badly.

The same happens on any plain `QPushButton` whose `fxRole` property is
`"primary"` (fxgui sets that on a dialog's main button automatically), and
on a checkable `FXIconButton`, whose own icons overwrite yours at the next
toggle. Pascal, the main consumer, hits case 2 on three buttons today. After
this plan, `set_icon` on any primary button draws the on-accent ink, and an
icon set from outside is never silently reverted.

## Current state

Files:

- `fxgui/fxicons.py` — icon loading. `set_icon` (lines 852–873) is a thin
  wrapper over `get_icon`.
- `fxgui/fxwidgets/_buttons.py` — `FXPrimaryButton` (lines 23–82) and
  `FXIconButton` (lines 131–191).
- `fxgui/fxstyle.py` — `_rank_dialog_buttons` (lines 2661–2683) gives a
  dialog's main `QPushButton` the property `fxRole="primary"` when the
  `QDialogButtonBox` is first shown (called from line 2778, on `QEvent.Show`).
  Read only; do not edit.
- `tests/test_primary_button.py` — existing tests for `FXPrimaryButton`;
  the pattern for the new tests.
- `docs/how-to/icons.md` — line 125–126 documents `set_icon` as a plain
  `setIcon`.

`fxgui/fxicons.py:852-873`:

```python
def set_icon(widget: Any, icon_name: str, **kwargs: Any) -> QIcon:
    """Set an icon on a widget; it takes its theme inks when drawn.

    Args:
        widget: Anything with `setIcon` (QAction, QPushButton, etc.).
        icon_name: The name of the icon.
        **kwargs: Passed to `get_icon` (width, height, color, inks,
            library, style, extension).
    ...
    """
    icon = get_icon(icon_name, **kwargs)
    widget.setIcon(icon)
    return icon
```

`get_icon` (line 676) takes `icon_name, width, height, color, library,
style, extension, inks, fallback`. With no `color`, the ink is the theme
token `icon`.

`fxgui/fxwidgets/_buttons.py:47-82` (`FXPrimaryButton`):

```python
        super().__init__(text or "", parent)
        self._icons = {}
        self.pressed.connect(self._show_icon)
        self.released.connect(self._show_icon)
        if icon:
            self.set_icon_name(icon)
        self.setProperty("fxRole", "primary")

    def set_icon_name(self, icon: str) -> None:
        """Draw the icon `icon` in the on-accent icon colour."""
        # Qt draws a hovered push button's icon in Normal mode, so the
        # hover fill's ink is a second icon swapped in; each resolves its
        # token when drawn.
        self._icons = {
            hovered: fxicons.get_icon(icon, color=ink)
            for hovered, ink in (
                (False, "icon_on_accent_primary"),
                (True, "icon_on_accent_secondary"),
            )
        }
        self._show_icon()

    def enterEvent(self, event) -> None:
        ...
        self._show_icon()

    def leaveEvent(self, event) -> None:
        ...
        self._show_icon()

    def _show_icon(self) -> None:
        if self._icons:
            self.setIcon(self._icons[self.underMouse() and not self.isDown()])
```

`fxgui/fxwidgets/_buttons.py:164-191` (`FXIconButton`):

```python
        # Active is a hovered tool button: checked, on primary_button_hover,
        # it takes the secondary ink.
        self._icons = {
            False: fxicons.get_icon(icon),
            True: fxicons.get_icon(
                checked_icon or icon, color="icon_on_accent_primary",
                inks={"active": "icon_on_accent_secondary"}),
        }
        self.toggled.connect(self._show_icon)
        self._show_icon(self.isChecked())
    ...
    def _show_icon(self, checked: bool) -> None:
        self.setIcon(self._icons[checked])
```

`FXEmojiButton` (`fxgui/fxwidgets/_emoji_picker.py:239`) subclasses
`FXIconButton` and never calls `setIcon` itself; it must keep working.

Facts checked during planning:

- All 11 bundled themes in `fxgui/style.yaml` set
  `icon_on_accent_secondary` equal to `icon_on_accent_primary`, so a plain
  `QPushButton` given only the primary ink looks right in every bundled
  theme. A custom theme may differ; `FXPrimaryButton` keeps its hover swap.
- Pascal calls `fxicons.set_icon` on an `FXPrimaryButton` built without
  `icon=` at `src/ls_pascal/apps/hub/views/comments.py:384` and `:1040` and
  `src/ls_pascal/apps/hub/views/composer.py:402`. Nobody calls `set_icon` on
  an `FXIconButton`.

Conventions: Google-style docstrings (Args/Returns), type annotations, Qt
only through `qtpy`, comments say why in one line. Do not import
`fxgui.fxwidgets` from `fxgui/fxicons.py` (fxwidgets imports fxicons; use
duck typing).

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| One test file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_primary_button.py` | all pass |
| Icon button tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_icon_button_and_group.py tests/test_fxicons.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call, or it overwrites the owner's real settings.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxicons.py` — `set_icon` only.
- `fxgui/fxwidgets/_buttons.py` — `FXPrimaryButton` and `FXIconButton` only.
- `tests/test_primary_button.py` — new tests appended.
- `docs/how-to/icons.md` — the `set_icon` paragraph (lines 125–126).

**Out of scope** (do NOT touch):

- `fxgui/fxstyle.py` `_rank_dialog_buttons` — re-inking an icon set
  *before* the dialog is shown would need the icon's name, which the button
  does not keep. Document the order instead (Step 4).
- `CHANGELOG.md` — a release action writes it.
- Any Pascal file.
- `fxgui/examples.py` — the gallery already shows `FXPrimaryButton(icon=)`.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch: `fix/primary-button-icon-ink`.
  (There is no `.gitmodules`, so no submodule step.)
- Commit style: `[FIX] ...`, e.g.
  `[FIX] set_icon on a primary button keeps the on-accent ink`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: Let an icon set from outside win on both buttons

In `fxgui/fxwidgets/_buttons.py`:

`FXPrimaryButton`:

- Add a `setIcon(self, icon: QIcon) -> None` override that empties
  `self._icons` and then calls `super().setIcon(icon)`. Docstring: an icon
  set from outside is kept in every state; `set_icon_name` gives the
  on-accent swap back.
- In `_show_icon`, call `super().setIcon(...)` instead of `self.setIcon(...)`
  so the button's own swap does not clear `_icons`.
- Import `QIcon` from `qtpy.QtGui` for the annotation.

`FXIconButton`:

- Move the `self._icons = {...}` block of `__init__` into a new public
  method `set_icon_name(self, icon: str, checked_icon: Optional[str] = None) -> None`
  that builds the same two icons and then calls
  `self._show_icon(self.isChecked())`. Keep the "Active is a hovered tool
  button" comment with it. `__init__` calls
  `self.set_icon_name(icon, checked_icon)` where the block was, and keeps
  `self.toggled.connect(self._show_icon)`.
- Add the same `setIcon` override (empty `_icons`, then `super().setIcon`).
- `_show_icon(self, checked)` becomes: `if self._icons: super().setIcon(self._icons[checked])`.

Target shape (FXPrimaryButton part):

```python
    def setIcon(self, icon: QIcon) -> None:
        """Set `icon` and keep it in every state, hovered or not."""
        self._icons = {}
        super().setIcon(icon)

    def _show_icon(self) -> None:
        if self._icons:
            super().setIcon(
                self._icons[self.underMouse() and not self.isDown()])
```

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_primary_button.py tests/test_icon_button_and_group.py tests/test_emoji_picker.py`
→ all pass. Also run `tests/test_buttons_theme.py` (it builds both buttons
with icons) → all pass.

### Step 2: Make `set_icon` pick the on-accent ink for a primary button

In `fxgui/fxicons.py`, `set_icon` becomes, in this order:

1. If `kwargs` is empty and `widget` has a callable `set_icon_name`
   attribute (`FXPrimaryButton`, `FXIconButton`), call
   `widget.set_icon_name(icon_name)` and return `widget.icon()`. The widget
   then owns its state inks (hover on the primary button, checked on the
   icon button).
2. Else, if neither `color` nor `inks` is in `kwargs` and
   `widget.property("fxRole") == "primary"` (guard: only call `property`
   when the widget has it, e.g. `getattr(widget, "property", None)`; a
   `QAction` has `property` too and returns `None`, which is fine), set
   `kwargs["color"] = "icon_on_accent_primary"`.
3. Then the existing two lines: `icon = get_icon(icon_name, **kwargs)`,
   `widget.setIcon(icon)`, `return icon`.

Why only empty kwargs for step 1: `set_icon_name` takes no size or library
arguments, so any other kwarg would be dropped silently. With kwargs, an
`FXPrimaryButton` still goes through step 2 (it has `fxRole="primary"`) and
the `setIcon` override from Step 1 keeps the icon.

Update the docstring: one sentence that on a primary button (an
`FXPrimaryButton`, or any button with `fxRole="primary"`) with no `color`
or `inks`, the icon takes the on-accent ink, and an `FXPrimaryButton` /
`FXIconButton` keeps its own state inks. Add one example line:
`>>> fxicons.set_icon(post_button, "send")  # on-accent ink`.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_fxicons.py tests/test_primary_button.py`
→ all pass.

### Step 3: Add the tests

Append to `tests/test_primary_button.py` (reuse its `_window_with_button`,
`_icon_inks`, `hover`, `unhover` helpers; see "Test plan" for the list).

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_primary_button.py`
→ all pass, including the 6 new tests. Then prove they guard the fix:
`git diff fxgui/fxicons.py > ../plan003.patch && git checkout fxgui/fxicons.py`,
rerun the file: at least tests 1, 4 and 5 below fail. Restore with
`git apply ../plan003.patch` and rerun: all pass. (Do not use `git stash`:
the stash is shared with other worktrees.)

### Step 4: Update the docs

In `docs/how-to/icons.md`, replace the sentence at lines 125–126
("`set_icon(widget, name)` works on anything with `setIcon()`: buttons,
actions, `FXIconLabel`. It is `widget.setIcon(get_icon(name))`.") with:
it works on anything with `setIcon()`; it is
`widget.setIcon(get_icon(name))`, except on a primary button, where with no
`color` it draws the on-accent ink (`icon_on_accent_primary`), and an
`FXPrimaryButton` or `FXIconButton` keeps its hover/checked inks. Add one
sentence: a dialog's main button becomes primary when the dialog is first
shown, so set its icon after `show()`, or pass
`color="icon_on_accent_primary"`.

**Verify**: `grep -n "icon_on_accent_primary" docs/how-to/icons.md` → shows
the new line near line 126 (plus the existing ones at ~155–165).
The docs build is strict about links; you added none, so no build is needed.

### Step 5: Whole suite and lint

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8`
→ `3184 passed, 6 skipped` (3178 + 6 new), 0 failed.
the Lint command from the table → `All checks passed!`

## Test plan

New tests in `tests/test_primary_button.py`, named as sentences, all in the
`"dark"` theme unless stated (dark `icon` ink is `#b4b4b4`,
`icon_on_accent_primary` is `#ffffff`; read them from
`fxstyle._token_map("dark")` rather than hard-coding):

1. `test_an_icon_set_after_construction_takes_the_on_accent_ink` — build
   `_window_with_button(qtbot, "dark")` (no `icon=`), call
   `fxicons.set_icon(button, "send")`, assert `_icon_inks(button) ==
   {tokens["@icon_on_accent_primary"]}`; `hover(qtbot, button)`, assert the
   same; `unhover`, assert the same.
2. `test_set_icon_replaces_the_construction_icon_for_good` — build with
   `icon="send"`, `fxicons.set_icon(button, "save")`, `hover`, then assert
   `button.icon().pixmap(16, 16).toImage() ==
   fxicons.get_icon("save", color="icon_on_accent_secondary").pixmap(16, 16).toImage()`;
   `unhover`, assert it equals the `icon_on_accent_primary` "save" image.
3. `test_a_raw_qicon_survives_hover` — build with `icon="send"`, make
   `icon = fxicons.get_icon("save", color="#ff0000")`, `button.setIcon(icon)`,
   `hover`, `unhover`, assert `button.icon().cacheKey() == icon.cacheKey()`.
4. `test_a_plain_push_button_with_the_primary_role_takes_the_on_accent_ink`
   — a `QPushButton` in a themed window with
   `setProperty("fxRole", "primary")`; `set_icon(b, "send")` → on-accent
   ink. Also `set_icon(b, "send", color="#ff0000")` → `{"#ff0000"}` (an
   explicit colour is kept).
5. `test_a_dialog_ranked_button_takes_the_on_accent_ink` — a
   `QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)` in a
   themed window, shown and exposed; assert
   `box.button(QDialogButtonBox.Ok).property("fxRole") == "primary"`; then
   `set_icon(ok, "check")` → on-accent ink. The Cancel button,
   `set_icon(cancel, "x")`, keeps `tokens["@icon"]`.
6. `test_set_icon_on_a_checkable_icon_button_survives_a_toggle` — an
   `FXIconButton("eye-off", window, checkable=True)` shown in a themed
   window; `fxicons.set_icon(b, "eye")`; `b.setChecked(True)`; assert its
   16×16 image equals that of
   `fxicons.get_icon("eye", color="icon_on_accent_primary")`;
   `b.setChecked(False)`; assert it equals `fxicons.get_icon("eye")`'s.

Pattern: the existing `test_the_icon_takes_the_ink_of_each_state_fill` and
`_window_with_button` in the same file. Import `fxicons` from `fxgui`, and
`QDialogButtonBox` / `FXIconButton` as needed.

## Done criteria

- [ ] `pytest -q tests/test_primary_button.py` passes, 6 new tests included.
- [ ] Whole suite: `3184 passed, 6 skipped`, 0 failed.
- [ ] The Lint command from the table passes.
- [ ] `grep -n "fxwidgets" fxgui/fxicons.py` shows no new import.
- [ ] `git status` shows only the four in-scope files changed.
- [ ] `plans/2026-11-14-audit/README.md` status row updated.

## STOP conditions

- `FXPrimaryButton` or `FXIconButton` no longer stores its icons in
  `self._icons` or no longer re-sets them in `_show_icon` (drift).
- A test that existed before this plan fails after Step 1, especially in
  `tests/test_icon_button_and_group.py` or the emoji picker tests (the
  `setIcon` override broke a caller that sets icons internally).
- Adding the duck-typed branch in `set_icon` makes any test in
  `tests/test_fxicons*.py` fail (some widget in the suite has a
  `set_icon_name` with a different meaning: report it, do not rename it).
- The dialog test shows `fxRole` is not `"primary"` after show (the
  ranking trigger moved; do not edit `fxstyle.py`).

## Maintenance notes

- Public behaviour changes: `set_icon` with no colour on a primary button
  now draws `icon_on_accent_primary` instead of `icon`; an icon set from
  outside on `FXPrimaryButton` / `FXIconButton` is no longer reverted on
  hover/toggle. New public method `FXIconButton.set_icon_name(icon,
  checked_icon=None)`. All signatures are unchanged.
- Known limit: `set_icon` reads `fxRole` when called. A dialog button
  ranked primary later (on first show) keeps the ink it got. Documented in
  `docs/how-to/icons.md`.
- Known limit: `set_icon(icon_button, name, library=...)` (any kwarg) skips
  `set_icon_name`, so a checked `FXIconButton` shows the plain ink on the
  accent. Rare; extend `set_icon_name` with kwargs if a caller needs it.
- Reviewer: check the duck-typed `set_icon_name` branch only fires with
  empty kwargs, and that `_show_icon` uses `super().setIcon`.
- Pascal: nothing to delete; its three `fxicons.set_icon` calls on
  `FXPrimaryButton` (`apps/hub/views/comments.py:384`, `:1040`,
  `apps/hub/views/composer.py:402`) start drawing the right ink with no
  change (they could also move to `FXPrimaryButton(..., icon=...)`).
