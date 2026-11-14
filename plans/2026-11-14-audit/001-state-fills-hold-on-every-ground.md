# Plan 001: Hover, pressed and selection fills stand off every ground they sit on

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxstyle.py fxgui/style.yaml docs/how-to/theming.md tests/test_fxstyle.py tests/test_theme_keys.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S-M
- **Risk**: MED
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

fxgui derives each theme's hover fill (`state_hover`), pressed and checked
fill (`state_pressed`) and selected-row fill (`selection`) from the theme's
other colours. The derivation checks each fill against only some of the
backgrounds ("grounds") it is drawn on. So in several bundled themes a state
is invisible:

- `catppuccin_latte`: the pressed fill `#dde0e6` is *lighter* than the hover
  fill `#c9cbd0`, and sits at 1.001:1 on `surface_sunken` `#dce0e8`. A
  pressed button in a list or on the window frame shows nothing.
- Hover on the window frame (toolbar and status bar bands, where
  `FXMainWindow` makes icon buttons flat): `light` 1.177:1,
  `solarized_light` 1.188:1. Hover on an alternate row (`surface_alt`):
  `nord` 1.018:1, `github_dark` 1.124:1.
- `selection` is a plain 15% mix that is never checked: on latte's
  `surface_sunken` it reads at 1.025:1, so a selected row in a list is
  invisible.

After this plan, every derived fill clears the theme's state floor (1.2:1,
`fxstyle.STATE_MIN_CONTRAST`) on `surface`, `surface_sunken`, `surface_alt`,
`well` and `frame`; a derived pressed fill always sits *past* hover (further
from the surface); and a derived `selection` visibly differs from `surface`,
`surface_sunken` and `well`.

**Public behaviour that changes**: the resolved colours (`fxstyle.colors()`,
the `@tokens` in the sheet) change in five bundled themes (listed in Step 5).
This is a defect fix. A theme that *states* its own fills keeps them as today:
a stated `state_hover`/`state_pressed` is only held to the theme's own floor
(`state_contrast`), and a stated `selection` is never touched. Pascal's
`lotchi_dark`/`lotchi_light` themes (which state their fills and set
`state_contrast: 1.0`) come out byte-identical.

## Current state

Files:

- `fxgui/fxstyle.py` — the theme engine. `_readable_states` (lines
  1237-1298) derives hover, pressed and the text inks; `_token_map` (lines
  1332-1461) builds every `@token`, including `selection` (lines 1393-1407).
- `fxgui/style.yaml` — the bundled themes and the comment block that documents
  each key (lines 96-97 `selection`, 124-128 the state keys).
- `docs/how-to/theming.md` — the user doc of the same keys (line 41
  `selection`, lines 92-94 the state keys).
- `tests/test_fxstyle.py` — theme engine tests; the parametrized contrast
  tests at lines 209-237 are the pattern for the new tests.
- `tests/test_theme_keys.py` — calls `_readable_states` directly with a
  brand theme that states its fills at `state_contrast: 1.0`; must keep
  passing unchanged.

The derivation today:

```python
# fxgui/fxstyle.py:1254-1273
    surface = theme_data["surface"]
    pole = _pole_from(surface)
    rows_on = [theme_data.get(key, surface)
               for key in ("surface", "surface_sunken", "well")]
    # A theme may hold its states closer, as a brand's own fills do.
    floor = float(theme_data.get("state_contrast", STATE_MIN_CONTRAST))
    hover = step_toward(
        theme_data.get("state_hover")
        or mix_oklab(surface, theme_data["text"], HOVER_TINT), pole,
        lambda color: all(
            _reads(ground, floor)(color) for ground in rows_on))
    pressed = step_toward(
        theme_data.get("state_pressed")
        or mix_oklab(surface, theme_data["text"], PRESSED_TINT),
        pole, _reads(hover, floor))
    grounds = [
        theme_data.get(key, surface)
        for key in ("surface", "surface_sunken", "surface_alt", "well",
                    "frame", "tooltip")
    ] + [hover]
```

```python
# fxgui/fxstyle.py:1393-1397
    # A selected item's fill is the accent unless the theme names a softer
    # one, whose inks are the theme's own text and icon made to read on it.
    selection = theme_data.get("selection") or mix_oklab(
        theme_data["surface"], accent_primary, SELECTION_TINT)
    tokens["@selection"] = selection
```

Helpers you will use (all in `fxgui/fxstyle.py`, do not change them):

- `step_toward(start, toward, done)` (line 1058): walks from `start` to
  `toward` in 40 sRGB steps and returns the first colour `done(color)`
  accepts (step 0 is `start` itself).
- `_reads(against, minimum)` (line 1082): returns a test "contrast with
  `against` >= `minimum`".
- `_pole_from(ground)` (line 930): black or white, whichever stands further
  from `ground`. Fills step toward it.
- `get_contrast_ratio(a, b)` (line 896): WCAG contrast, 1.0 to 21.0.
- `_visibly_differ(one, two)` (line 938): True when two fills read as two
  states: contrast >= 1.1 or a channel differs by 48 or more (hue counts).

Why the latte pressed fill is lighter than hover: the derived starts are
weak tints (hover 5%, pressed 10% of `text` over `surface`). Hover is pushed
far (to `#c9cbd0`) to clear `surface_sunken`. Pressed starts at `#dde0e6`,
which is already 1.2:1 from hover — on the *wrong side* — so the walk stops
at step 0.

Order of computation: `_token_map` runs
`theme_data.update(_depth_colors(theme_data))` (line 1347, which computes
`frame` and `well` when a theme omits them) *before*
`theme_data.update(_readable_states(theme_data))` (line 1348). So `frame`
and `well` are present when `_readable_states` runs from `_token_map`.
`tests/test_theme_keys.py` calls `_readable_states` with a dict that has
no `frame`/`well`; the existing `theme_data.get(key, surface)` fallback
covers that. Keep it.

Conventions: Google-style docstrings; comments explain *why*, briefly; tests
are plain functions named as sentences, parametrized over
`fxstyle.get_available_themes()`.

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| One test file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_fxstyle.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it `3201 passed, 6 skipped` (23 new tests) |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |
| Token dump | see Step 1 | writes a JSON file |

Never run tests on the real Qt platform: conftest forces `offscreen`; do not
override it. Any ad-hoc Python must call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, or it overwrites the owner's real settings file. Run
ad-hoc scripts with `PYTHONPATH=.` from the worktree root: a script's own
folder comes first on `sys.path`, and the venv's editable install points at
another checkout, so without it you would dump the wrong code.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxstyle.py` — `_readable_states` and the `selection` lines of
  `_token_map` only.
- `fxgui/style.yaml` — the comment lines documenting `selection` (96-97)
  and `state_hover`/`state_pressed` (124-127). No colour value changes.
- `docs/how-to/theming.md` — line 41 (`selection`) and lines 92-93
  (`state_hover`, `state_pressed`).
- `tests/test_fxstyle.py` — new tests.

**Out of scope** (do NOT touch):

- Any theme's colour values in `style.yaml`: the fix is in the derivation,
  so third-party themes get it too.
- `fxgui/qss/style.qss` and which token each rule uses — that is plan 002.
- `tooltip` as a ground for hover/pressed: no opaque pair of fills can clear
  every theme's tooltip (dracula's `tooltip` equals its `scrollbar_thumb`);
  plan 002 adds see-through overlay fills for that.
- `_depth_colors`, `_primary_button_fills`, the text-ink logic in
  `_readable_states` (the `reading(...)` calls) — unchanged.
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout (e.g.
  `git worktree add ..\fxgui-001 -b fix/state-fills-hold-on-every-ground`
  from the commit the operator names). The repo has no `.gitmodules` at the
  planned-at commit; if one exists by now, run
  `git submodule update --init --depth 1`.
- Branch: `fix/state-fills-hold-on-every-ground`.
- Commits in the repo style (`git log --oneline -10`), e.g.
  `[FIX] state fills stand off every ground they sit on`,
  `[DOC] theming: what the state fills are held against`.
- Do not push, tag or release: the operator does. Never edit `CHANGELOG.md`.

## Steps

### Step 1: Dump today's tokens

Create a scratch script **outside the repo** (for example
`%TEMP%\fxgui_dump_tokens.py`):

```python
"""Dump every bundled theme's resolved colour tokens to a JSON file."""
import json, os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from qtpy.QtCore import QSettings
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                  tempfile.mkdtemp())
from qtpy.QtWidgets import QApplication
app = QApplication([])
from fxgui import fxstyle
print("fxgui from", fxstyle.__file__, file=sys.stderr)
tokens = {t: fxstyle._colour_tokens(t) for t in fxstyle.get_available_themes()}
with open(sys.argv[1], "w", encoding="utf-8") as out:
    json.dump(tokens, out, indent=1, sort_keys=True)
```

Run it from the worktree root (Git Bash):

```bash
PYTHONPATH=. "C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python.exe" "$TEMP/fxgui_dump_tokens.py" "$TEMP/tokens_before.json"
```

**Verify**: stderr prints `fxgui from <worktree root>\fxgui\fxstyle.py`
(the worktree, not `Documents\GitHub\fxgui`), and
`$TEMP/tokens_before.json` exists with 11 theme keys.

### Step 2: Hold hover and pressed on every ground, pressed past hover

In `fxgui/fxstyle.py`, `_readable_states`, replace lines 1256-1268 (from
`rows_on = ...` through the `pressed = step_toward(...)` call) with:

```python
    # Every ground a state fill is drawn on: a pane, a view, a list set in a
    # pane, an alternate row, and the frame's bands, where icon buttons are
    # flat.
    state_grounds = [
        theme_data.get(key, surface)
        for key in ("surface", "surface_sunken", "surface_alt", "well",
                    "frame")
    ]
    # A theme may hold its states closer, as a brand's own fills do.
    floor = float(theme_data.get("state_contrast", STATE_MIN_CONTRAST))

    def stands_off(*others: str) -> Callable[[str], bool]:
        return lambda color: all(
            _reads(ground, floor)(color)
            for ground in (*state_grounds, *others))

    hover = step_toward(
        theme_data.get("state_hover")
        or mix_oklab(surface, theme_data["text"], HOVER_TINT), pole,
        stands_off())
    stated = theme_data.get("state_pressed")
    off_hover = stands_off(hover)

    def past_hover(color: str) -> bool:
        # The derived start can sit on the surface's side of a hover pushed
        # far, as catppuccin_latte's did: a pressed fill lighter than hover.
        return get_contrast_ratio(color, pole) < get_contrast_ratio(
            hover, pole)

    pressed = step_toward(
        stated or mix_oklab(surface, theme_data["text"], PRESSED_TINT),
        pole,
        lambda color: off_hover(color) and (bool(stated) or past_hover(color)))
```

Leave the `grounds = [...]` list for the text inks (lines 1269-1273) and
everything after it unchanged. `Callable` is already imported in
`fxstyle.py` (used by `step_toward`'s signature); confirm with
`grep -n "^from typing" fxgui/fxstyle.py`.

Update the docstring bullets for `state_hover` and `state_pressed` (lines
1240-1244) to say: hover is stepped away from `surface` until it differs by
the floor from `surface`, `surface_sunken`, `surface_alt`, `well` and
`frame`; pressed is stepped on until it differs by the floor from hover and
from those grounds, and, when derived (not stated), until it sits past hover
toward black or white.

**Verify**: `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_fxstyle.py tests/test_theme_keys.py tests/test_row_hover.py`
→ all pass.

### Step 3: Hold a derived selection off the views it fills

In `_token_map`, replace lines 1393-1397 with:

```python
    # A selected item's fill is the accent unless the theme names a softer
    # one, whose inks are the theme's own text and icon made to read on it.
    # A derived one steps toward the accent until a selected row shows on
    # every view it fills: catppuccin_latte's 15% vanished on its lists.
    selection = theme_data.get("selection")
    if not selection:
        views = [
            theme_data.get(key, theme_data["surface"])
            for key in ("surface", "surface_sunken", "well")
        ]
        selection = step_toward(
            mix_oklab(theme_data["surface"], accent_primary, SELECTION_TINT),
            accent_primary,
            lambda color: all(_visibly_differ(color, view) for view in views))
    tokens["@selection"] = selection
```

The lines after (`@selection_border`, the `selection == accent_primary`
branch) stay as they are.

**Verify**: same command as Step 2 → all pass.

### Step 4: Add the tests

In `tests/test_fxstyle.py`, after `test_a_pressed_fill_stands_off_the_hover_fill`
(around line 230), add:

```python
_STATE_GROUNDS = ("surface", "surface_sunken", "surface_alt", "well", "frame")


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_every_state_fill_stands_off_every_ground_it_sits_on(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    ratio = fxstyle.get_contrast_ratio
    floor = fxstyle.state_contrast(theme)
    for fill in ("state_hover", "state_pressed"):
        for ground in _STATE_GROUNDS:
            assert ratio(colors[fill], colors[ground]) >= floor, (fill, ground)
    for ground in ("surface", "surface_sunken", "well"):
        assert fxstyle._visibly_differ(colors["selection"], colors[ground]), (
            ground)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_pressed_fill_sits_past_the_hover_fill(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    pole = fxstyle._pole_from(colors["surface"])
    ratio = fxstyle.get_contrast_ratio
    assert ratio(colors["state_pressed"], pole) < ratio(
        colors["state_hover"], pole)


def test_a_stated_selection_is_kept_even_where_it_hides(qapp, monkeypatch):
    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    # Latte's own surface_sunken: a theme's stated fill is its choice.
    themes["_stated"] = {**themes["catppuccin_latte"], "selection": "#dce0e8"}
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})
    assert fxstyle._token_map("_stated")["@selection"] == "#dce0e8"
```

(`monkeypatch.setattr(fxstyle, "_colors", ...)` is the pattern already used
by `test_a_partial_or_unknown_theme_fills_from_dark` at line 166;
conftest resets `_colors` after each test.)

**Verify**: `... -m pytest -q tests/test_fxstyle.py` → all pass, 23 more
tests than before (11 + 11 + 1). To prove the tests catch the bug:
`git stash push -m plan001-proof -- fxgui/fxstyle.py`, rerun → the first
new test fails for `light`, `github_dark`, `catppuccin_latte`, `nord` and
`solarized_light`, the second for `catppuccin_latte` only; then restore with `git stash list`, find the
`plan001-proof` entry, `git stash apply <its sha>` and `git stash drop`
that entry (never a bare `git stash pop`: the stash is shared across
worktrees).

### Step 5: Dump the tokens again and compare

```bash
PYTHONPATH=. "C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python.exe" "$TEMP/fxgui_dump_tokens.py" "$TEMP/tokens_after.json"
"C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python.exe" -c "import json,os;b=json.load(open(os.path.expandvars('$TEMP/tokens_before.json')));a=json.load(open(os.path.expandvars('$TEMP/tokens_after.json')));[print(t,{k:(b[t].get(k),a[t].get(k)) for k in sorted(set(b[t])|set(a[t])) if b[t].get(k)!=a[t].get(k)}) for t in sorted(b) if b[t]!=a[t]]"
```

**Verify**: only these themes print, with about these changes (a prototype
of exactly the code above produced them; derived tokens that read these
colours, such as `nav_ink`, `text_on_selection` or `icon_on_selection`, may
also move):

| Theme | Changes |
|---|---|
| `light` | `state_hover` `#d3d3d3`→`#cdcdcd`, `state_pressed` `#bebebe`→`#b8b8b8`, `text_muted` `#5a5a5a`→`#575757` |
| `github_dark` | `state_hover` `#21252b`→`#272b31`, `state_pressed` `#2f3439`→`#34393e` |
| `catppuccin_latte` | `state_pressed` `#dde0e6`→`#b6b9be`, `selection` `#d0def8`→`#c3d5f8`, `text` `#35374a`→`#36394b` |
| `nord` | `state_hover` `#3b414d`→`#4a505a`, `state_pressed` `#484d59`→`#5b606a` |
| `solarized_light` | `state_hover` `#dcd8c8`→`#d6d2c2`, `text` `#3a464a`→`#364246`, `text_muted` `#556062`→`#525c5e` |

`dark`, `dracula`, `one_dark_pro`, `github_light`, `catppuccin_mocha` and
`material_dark` must not print. Put this table (with your actual values) in
the commit message body of the `[FIX]` commit.

### Step 6: Update the docs of the keys

- `fxgui/style.yaml` comment block: line 96-97 `selection` — add "stepped
  toward accent_primary until it visibly differs from surface,
  surface_sunken and well"; lines 124-127 — `state_hover` "held to 1.2:1 on
  surface, surface_sunken, surface_alt, well and frame"; `state_pressed`
  "pushed to 1.2:1 from state_hover and those grounds; when omitted, past
  state_hover".
- `docs/how-to/theming.md` line 41 (`selection`), 92 (`state_hover`), 93
  (`state_pressed`): the same facts in the doc's own wording. Keep the
  table format (one row per key).

**Verify**: `grep -n "surface_alt" fxgui/style.yaml docs/how-to/theming.md`
shows the new wording on the state lines; `git diff --stat` lists only the
in-scope files.

### Step 7: Whole suite and lint

**Verify**:
- `... -m pytest -q -n 8` → `3201 passed, 6 skipped`.
- `...\ruff.exe check --select F,B,BLE .` → `All checks passed!`

## Test plan

- New, in `tests/test_fxstyle.py` (pattern: the parametrized contrast tests
  at lines 209-237 of the same file):
  - `test_every_state_fill_stands_off_every_ground_it_sits_on` — every
    bundled theme: hover and pressed >= the theme's floor on `surface`,
    `surface_sunken`, `surface_alt`, `well`, `frame`; `selection` visibly
    differs from `surface`, `surface_sunken`, `well`. Regression for latte's
    pressed/sunken 1.001, light's hover/frame 1.177, nord's
    hover/surface_alt 1.018, latte's selection/sunken 1.025.
  - `test_a_pressed_fill_sits_past_the_hover_fill` — regression for latte's
    pressed lighter than hover.
  - `test_a_stated_selection_is_kept_even_where_it_hides` — a theme's own
    `selection` is never stepped.
- Existing, must pass unchanged: `tests/test_theme_keys.py` (a stated brand
  pair at `state_contrast: 1.0` is kept), the text-ink tests at
  `tests/test_fxstyle.py:213-237`, `tests/test_row_hover.py`,
  `tests/test_frame_controls.py` (it compares pixels with the token, so it
  follows the new values by itself).

## Done criteria

- [ ] Whole suite: `3201 passed, 6 skipped`
- [ ] Ruff: `All checks passed!`
- [ ] `grep -n "rows_on" fxgui/fxstyle.py` returns nothing
- [ ] Step 5's comparison prints only `light`, `github_dark`,
      `catppuccin_latte`, `nord`, `solarized_light`
- [ ] `git status` shows changes only in the four in-scope files
- [ ] `plans/2026-11-14-audit/README.md` status row for 001 updated

## STOP conditions

Stop and report (do not improvise) if:

- The code at `fxgui/fxstyle.py:1254-1273` or `1393-1397` does not match the
  excerpts above.
- Step 1's stderr shows `fxgui` loaded from anywhere but the worktree.
- Step 5 shows a change in `dark`, `dracula`, `one_dark_pro`,
  `github_light`, `catppuccin_mocha` or `material_dark`, or a theme's
  `text`/`text_muted` moving by more than a few levels per channel: the
  derivation did something this plan did not intend.
- `tests/test_theme_keys.py` fails: stated fills are no longer kept, which
  breaks Pascal's brand themes.
- A text-ink test (`test_every_text_ink_reads_on_every_surface_it_sits_on`,
  `test_muted_text_stays_a_visible_step_from_text`) fails: a pushed fill
  left no room for text to reach 4.5:1. Report the theme and values.
- Making a test pass seems to need a change to a theme's colour values in
  `style.yaml`.

## Maintenance notes

- The five grounds in `state_grounds` are where the sheet draws state fills
  today. A new place that puts hover/pressed on another opaque ground (a new
  card colour) must join that list, or use plan 002's overlay tokens.
- `tooltip` is deliberately not a ground here; plan 002 handles fills on
  raised cards with see-through overlays.
- Reviewer: check that a *stated* `state_pressed` skips `past_hover`
  (brand themes keep their exact fills), and that `selection` is only
  stepped when the theme omits it.
- Pascal: nothing to delete. Its `lotchi_dark`/`lotchi_light` state every
  fill and `state_contrast: 1.0`, so their resolved colours do not change
  (measured with Pascal's `lotchi_colors.yaml` overlaid).
