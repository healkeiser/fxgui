# Plan 002: Every button follows one state convention, and flat buttons show on any ground

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxstyle.py fxgui/qss/style.qss fxgui/style.yaml docs/how-to/theming.md tests/test_frame_controls.py tests/test_floating_dialog.py tests/test_fxstyle.py`
> Plan 001 changes `fxgui/fxstyle.py`, `fxgui/style.yaml`,
> `docs/how-to/theming.md` and `tests/test_fxstyle.py`; that drift is
> expected. Any *other* change in these paths: compare the "Current state"
> excerpts against the live code; on a mismatch, treat it as a STOP
> condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/2026-11-14-audit/001-state-fills-hold-on-every-ground.md
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Buttons in fxgui's sheet disagree about which fill means what, so a state
often shows nothing:

- A plain or `setFlat(True)` push button uses the *pressed* fill for hover,
  pressed and checked alike: hovering a checked button changes nothing, and
  in 8 of 11 themes a checked button at rest looks exactly like a hovered
  one (its edge `@grid` equals the rest edge `@border_light`).
- A flat icon button (`fxRole="flat"`, what `FXMainWindow` gives icon
  buttons on its toolbar and status bar) has no checked rule at all, so a
  checked one looks unchecked.
- A checked tool button shows nothing more when hovered.
- On a raised card (a panel painted `@tooltip`, as Pascal's media player
  is), opaque fills can equal the card: in Pascal's `lotchi_dark`,
  `state_pressed` *is* `tooltip` (`#191A1D`), so hovering its player
  buttons shows nothing. No pair of existing tokens differs from `@tooltip`
  in every theme (dracula's `scrollbar_thumb` equals its `tooltip`).

After this plan: one convention — hover `@state_hover`, pressed and checked
`@state_pressed`, a checked button under the pointer a new
`@state_checked_hover` (so the click that unchecks it shows). Buttons with
no ground of their own (flat push buttons, plain tool buttons) use new
see-through tokens — `@state_hover_overlay`, `@state_pressed_overlay`,
`@state_checked_hover_overlay`, the theme's `text` at a small alpha — which
show on any ground: a pane, a band, a card, a tooltip.

**Public behaviour that changes** (a defect fix): a hovered non-flat push
button fills `@state_hover` instead of `@state_pressed`; flat and tool
buttons fill with see-through text instead of opaque greys; a checked
hovered button gets a fill of its own; dock title buttons and the ghost
search field hover with `@state_hover`; tab-bar scroll buttons press with
`@state_pressed`. `fxstyle.colors()` gains four attributes. No signature
changes.

## Current state

Plan 001 must already be merged: it makes `state_pressed` sit past
`state_hover` in every theme, which the overlays below rely on (before it,
catppuccin_latte's pressed overlay came out *fainter* than its hover
overlay). Check: `grep -n "def test_a_pressed_fill_sits_past_the_hover_fill" tests/test_fxstyle.py`
prints one line. If not, STOP.

Files:

- `fxgui/qss/style.qss` — the base sheet; `@name` placeholders are replaced
  by token values. All the button rules below live here.
- `fxgui/fxstyle.py` — `_readable_states` (derives `state_hover`,
  `state_pressed`, text inks; after plan 001 it has `state_grounds`,
  `stands_off(...)`, `pressed`) and `_token_map` (builds every `@token`;
  `tokens` is a dict of `"@name" -> value`, and every key of `theme_data`
  becomes a token automatically at lines ~1350-1354).
- `docs/how-to/theming.md` — the token table (lines ~88-94) and the
  "Fills and edges by state" table (lines ~419-431).
- `fxgui/style.yaml` — no change (the new tokens are derived only).
- `tests/test_frame_controls.py` — lines 292-308 assert a flat icon
  button's hover/pressed pixels *equal* `state_hover`/`state_pressed`; they
  must change to the overlay blend.
- `tests/test_floating_dialog.py` — lines 144-153 assert a hovered dialog
  button equals `state_pressed`; must change to `state_hover`.

How tokens reach the sheet and `colors()`: `_substitute` replaces the
longest `@name` first (`tests/test_fxstyle.py:48`), so `@state_hover_overlay`
is never cut into `@state_hover` + `_overlay`. `fxstyle.colors()` is built
from every `@` token (`_colour_tokens`, `fxstyle.py:473-479`), so the new
tokens appear there with no extra code. **Form of the overlays**:
`#AARRGGBB` (alpha first), the form `QColor` reads and that QSS accepts —
the theme file already uses it for `shadow` and `scrim`. A probe confirmed
a QSS `background-color: #40ffffff` renders the exact sRGB blend over the
parent's fill.

The rules today (copy-checked at `b283eb13`):

```css
/* fxgui/qss/style.qss:604-623 */
QPushButton:flat,
QPushButton:flat:disabled,
QPushButton:flat:focus
{
    background-color: transparent;
    border-color: transparent;
}

QPushButton:flat:hover
{
    background-color: @state_pressed;
}

QPushButton:flat:pressed,
QPushButton:flat:checked
{
    background-color: @state_pressed;
}
```

```css
/* fxgui/qss/style.qss:644-654 */
QPushButton:checked{
    background-color: @state_pressed;
    border-color: @grid;
}

/* A button hovers by its fill alone, so it never looks focused. */
QPushButton:hover
{
    background-color: @state_pressed;
    color: @text;
}
```

```css
/* fxgui/qss/style.qss:734-737 */
QPushButton:pressed
{
    background-color: @state_pressed;
}
```

```css
/* fxgui/qss/style.qss:1286-1308 */
QToolButton:hover,
QToolButton[popupMode="1"]:hover {
    background-color: @state_hover;
}

/* The button's own fill shows through, and its border stays whole. */
QToolButton::menu-button:hover {
    background-color: transparent;
}

QToolButton:pressed,
QToolButton::menu-button:pressed {
    background-color: @state_pressed;
}

/* A toggle that is on fills, with no edge: a sheet's 1px round edge
   comes out jagged. */
QToolButton:checked {
    background-color: @state_pressed;
    border-color: transparent;
}
```

```css
/* fxgui/qss/style.qss:1606-1624 */
QPushButton[fxRole="flat"],
QPushButton[fxRole="flat"]:disabled
{
    background-color: transparent;
    border: 1px solid transparent;
    padding: 4px;
}

QPushButton[fxRole="flat"]:hover
{
    background-color: @state_hover;
}

QPushButton[fxRole="flat"]:pressed
{
    background-color: @state_pressed;
}
```

Siblings: `style.qss:377-381` (ghost field `:hover, :focus` →
`@state_pressed`), `style.qss:925-928` (`QTabBar QToolButton:hover,
:pressed` → `@state_hover`), `style.qss:1013-1015`
(`QDockWidget::close-button:hover, ::float-button:hover` →
`@state_pressed`).

**Why the checked flat button shows nothing**: Qt QSS specificity counts
attribute selectors (`[fxRole="flat"]`) and pseudo-states (`:checked`) the
same. `QPushButton[fxRole="flat"]` and `QPushButton:checked` tie, and the
flat rule comes later in the file, so its `transparent` wins. Every rule
below is written with that in mind: a more specific state rule
(`:checked:hover`, two pseudo-states) beats a single one regardless of
order; ties go to the later rule. The new blocks were prototyped (patched
copy of `style.qss` + patched tokens) and every state rendered as intended
in all 11 themes.

Conventions: Google docstrings; comments say *why*, briefly; tests are
plain functions named as sentences; pixel tests follow
`tests/test_frame_controls.py` (`_flat`, `_at`, `hover` from
`tests/_helpers.py`).

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| One test file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_button_states.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | before this plan (after 001): `3201 passed, 6 skipped`; after: `3267 passed, 6 skipped` (66 new) |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

Never run tests or the gallery on the real Qt platform (it moves the
owner's pointer); conftest forces `offscreen`. Any ad-hoc Python must call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, and run with `PYTHONPATH=.` so the worktree's
`fxgui` wins over the venv's editable install (another checkout).

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxstyle.py` — `_readable_states` (one new fill), a new private
  helper `_overlay`, and `_token_map` (three overlay tokens).
- `fxgui/qss/style.qss` — the rules quoted above, nothing else.
- `docs/how-to/theming.md` — the two tables named above.
- `tests/test_button_states.py` (create).
- `tests/test_frame_controls.py` — lines 292-308 only.
- `tests/test_floating_dialog.py` — the `state_pressed` assertion at line
  ~152 only.
- Any other existing test whose *only* failure is that it asserts a button
  hover/pressed/checked pixel equals the old token (see Step 6).

**Out of scope** (do NOT touch):

- Rows, tabs, menu items, menu bar items, header sections: they keep their
  fills (`QWidget:item:hover`, `QTabBar::tab`, `QMenu::item`, ...).
- `fxgui/fxwidgets/_buttons.py` (`FXIconButton`, `FXJoinedGroup`): they
  register their own rules; changing them is a follow-up (Maintenance
  notes).
- Primary buttons (`fxRole="primary"`): they keep `@primary_button*`.
- Making the overlays settable in `style.yaml`: they are derived only.
- `CHANGELOG.md`.

## Git workflow

- Work in a git worktree on top of plan 001's merged result, never the
  shared checkout. No `.gitmodules` at the planned-at commit; if one exists,
  run `git submodule update --init --depth 1`.
- Branch: `fix/one-state-convention-for-buttons`.
- Commits in repo style, e.g. `[FIX] buttons: one state convention, see-through fills for flat buttons`,
  `[DOC] theming: button states and the overlay tokens`.
- Do not push, tag or release. Never edit `CHANGELOG.md`.

## Steps

### Step 1: Derive `state_checked_hover`

In `fxgui/fxstyle.py`, `_readable_states`, right after the `pressed = ...`
assignment (added by plan 001), add:

```python
    # A checked button under the pointer: a step past pressed, so the click
    # that unchecks it shows. One step at least, for a brand's floor of 1.
    checked_hover = step_toward(
        pressed, pole,
        lambda color: color != pressed and stands_off(pressed)(color))
```

Then hold `text` on it too: change

```python
    text = reading(theme_data["text"], grounds + [pressed])
```

to

```python
    text = reading(theme_data["text"], grounds + [pressed, checked_hover])
```

and add `"state_checked_hover": checked_hover,` to the returned dict, after
`"state_pressed"`. Add a docstring bullet: ``state_checked_hover``: stepped
on from ``state_pressed`` until it differs from it (and every state ground)
by the floor; ``text`` reads at 4.5:1 on it.

**Verify**: `... -m pytest -q tests/test_fxstyle.py tests/test_theme_keys.py`
→ all pass. Expected side effect (from the prototype): `dark`'s resolved
`text` moves about one level lighter (it read 4.45:1 on the new fill); no
other theme's `text` moves.

### Step 2: Add the overlay helper and tokens

In `fxgui/fxstyle.py`, after `_visibly_differ` (line ~948), add:

```python
def _overlay(ink: str, ground: str, fill: str) -> str:
    """Return `ink`, see-through, standing off `ground` as `fill` does.

    The least alpha, in hundredths up to a half, whose blend over `ground`
    reaches the contrast `fill` has with it. For a control with no ground
    of its own: it shows on a band, a card or a tooltip alike, where an
    opaque fill may equal the ground.

    Returns:
        The colour as ``#AARRGGBB``, which QSS and QColor both read.
    """
    target = get_contrast_ratio(fill, ground)
    color = QColor(ink)
    for step in range(1, 51):
        color.setAlpha(round(255 * step / 100))
        if get_contrast_ratio(
                mix(ground, ink, color.alphaF()), ground) >= target:
            break
    return color.name(QColor.NameFormat.HexArgb)
```

(The blend is tested with the alpha Qt will actually paint, the 8-bit one,
so rounding never leaves it short. `mix` is fxstyle's sRGB interpolation,
which is exactly how Qt blends a see-through fill.)

In `_token_map`, right after the `selection` block (after the
`@icon_on_selection` lines, ~1407), add:

```python
    # A flat button has no ground of its own (a band, a card, a tooltip),
    # where an opaque fill can equal the ground: its fills are the text,
    # see-through, standing off `surface` as the opaque ones do.
    for state in ("state_hover", "state_pressed", "state_checked_hover"):
        tokens[f"@{state}_overlay"] = _overlay(
            theme_data["text"], theme_data["surface"], theme_data[state])
```

**Verify**:

```bash
PYTHONPATH=. "C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python.exe" -c "import os,tempfile;os.environ['QT_QPA_PLATFORM']='offscreen';from qtpy.QtCore import QSettings;QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,tempfile.mkdtemp());from qtpy.QtWidgets import QApplication;a=QApplication([]);from fxgui import fxstyle as f;[print(t,{k:v for k,v in f._colour_tokens(t).items() if k.startswith('state_')}) for t in f.get_available_themes()]"
```

→ every theme prints `state_checked_hover` and three `*_overlay` values of
the form `#AARRGGBB`; the alpha byte is between `03` and `80` (hex); the
last six digits equal that theme's `text`. Expected hover/pressed alphas
(prototype, may differ by a hundredth): dark 0.10/0.20 (`1a`/`33`),
dracula 0.07/0.14; in every theme hover < pressed < checked_hover.

### Step 3: Push buttons — one convention

In `fxgui/qss/style.qss`:

(a) Replace lines 644-654 (`QPushButton:checked{` through the
`QPushButton:hover` rule) with:

```css
/* One convention for every button: hover @state_hover, pressed and checked
   @state_pressed, and a checked button under the pointer
   @state_checked_hover, so the click that unchecks it shows. A button
   hovers by its fill alone, so it never looks focused. Kept before the
   primary rules, which win the ties. */
QPushButton:hover
{
    background-color: @state_hover;
    color: @text;
}

QPushButton:pressed
{
    background-color: @state_pressed;
}

QPushButton:checked
{
    background-color: @state_pressed;
    border-color: @grid;
}

QPushButton:checked:hover
{
    background-color: @state_checked_hover;
}

QPushButton:checked:pressed
{
    background-color: @state_pressed;
}
```

(b) Delete the now-duplicate rule at lines 734-737
(`QPushButton:pressed { background-color: @state_pressed; }`, just above
`/* FXPrimaryButton, or any QPushButton with fxRole="primary"...`).

(c) Replace lines 604-623 (the `:flat` rules) with:

```css
/* A flat push button (setFlat) is a bare icon: no edge, no fill at rest.
   Its fills are see-through, so they show on whatever it sits on: a band,
   a card, a tooltip. */
QPushButton:flat,
QPushButton:flat:disabled,
QPushButton:flat:focus
{
    background-color: transparent;
    border-color: transparent;
}

QPushButton:flat:hover
{
    background-color: @state_hover_overlay;
}

QPushButton:flat:pressed,
QPushButton:flat:checked
{
    background-color: @state_pressed_overlay;
}

QPushButton:flat:checked:hover
{
    background-color: @state_checked_hover_overlay;
}

QPushButton:flat:checked:pressed
{
    background-color: @state_pressed_overlay;
}
```

(d) Replace lines 1606-1624 (the `fxRole="flat"` rules) with:

```css
/* A flat icon button: no box at rest and none when disabled. It sits on the
   frame's bands, so its fills are see-through, as a setFlat button's.
   Its focus ring is in KEYBOARD FOCUS below. */
QPushButton[fxRole="flat"],
QPushButton[fxRole="flat"]:disabled
{
    background-color: transparent;
    border: 1px solid transparent;
    padding: 4px;
}

QPushButton[fxRole="flat"]:hover
{
    background-color: @state_hover_overlay;
}

QPushButton[fxRole="flat"]:pressed,
QPushButton[fxRole="flat"]:checked
{
    background-color: @state_pressed_overlay;
}

QPushButton[fxRole="flat"]:checked:hover
{
    background-color: @state_checked_hover_overlay;
}

QPushButton[fxRole="flat"]:checked:pressed
{
    background-color: @state_pressed_overlay;
}
```

**Verify**: `grep -c "QPushButton:pressed" fxgui/qss/style.qss` → `1`;
`grep -n "QPushButton\[fxRole=\"flat\"\]:checked" fxgui/qss/style.qss` → 3
lines; `... -m pytest -q tests/test_fxstyle.py` → all pass
(`test_every_token_family_resolves` proves no `@` is left unresolved).

### Step 4: Tool buttons, tab scroll buttons, dock buttons, ghost field

(a) Replace lines 1286-1308 (from the comment `/* Hover is the neutral
fill and keeps the edge...` through the `QToolButton:checked` rule) with:

```css
/* The one button convention. A plain tool button has no ground of its own
   (a toolbar, a band, a card), so its fills are see-through; a split button
   reads as a QPushButton, opaque, its arrow part included. */
QToolButton:hover {
    background-color: @state_hover_overlay;
}

QToolButton[popupMode="1"]:hover {
    background-color: @state_hover;
}

/* The button's own fill shows through, and its border stays whole. */
QToolButton::menu-button:hover {
    background-color: transparent;
}

QToolButton:pressed {
    background-color: @state_pressed_overlay;
}

QToolButton[popupMode="1"]:pressed,
QToolButton::menu-button:pressed {
    background-color: @state_pressed;
}

/* A toggle that is on fills, with no edge: a sheet's 1px round edge
   comes out jagged. */
QToolButton:checked {
    background-color: @state_pressed_overlay;
    border-color: transparent;
}

QToolButton:checked:hover {
    background-color: @state_checked_hover_overlay;
}

QToolButton:checked:pressed {
    background-color: @state_pressed_overlay;
}

QToolButton[popupMode="1"]:checked {
    background-color: @state_pressed;
}

QToolButton[popupMode="1"]:checked:hover {
    background-color: @state_checked_hover;
}

QToolButton[popupMode="1"]:checked:pressed {
    background-color: @state_pressed;
}
```

(b) Tab-bar scroll buttons, lines 925-928 — split into:

```css
QTabBar QToolButton:hover {
    background-color: @state_hover;
}

QTabBar QToolButton:pressed {
    background-color: @state_pressed;
}
```

(They are opaque on purpose: Qt draws them over the last tab. Their
selectors outrank `QToolButton:hover`, so they stay opaque.)

(c) Dock title buttons, lines 1013-1015: `background: @state_pressed;` →
`background: @state_hover;` (the `:pressed` rule at 1017-1020 stays).

(d) Ghost search field, lines 377-381 — split into:

```css
QLineEdit[fxGhost="true"]:hover
{
    background-color: @state_hover;
}

/* Typed in, it holds the pressed fill, hovered or not. */
QLineEdit[fxGhost="true"]:focus
{
    background-color: @state_pressed;
}
```

**Verify**: list every rule whose selector has `:hover` and whose fill is
the opaque `@state_pressed` (Git Bash, from the worktree root):

```bash
"C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python.exe" - fxgui/qss/style.qss <<'EOF'
import re, sys
s = re.sub(r"/\*.*?\*/", "", open(sys.argv[1], encoding="utf-8").read(), flags=re.S)
for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", s):
    sel, body = " ".join(m.group(1).split()), m.group(2)
    if re.search(r"@state_pressed\b(?!_)", body) and ":hover" in sel:
        print(sel)
EOF
```

→ prints nothing. (At `b283eb13` it prints four rules: the ghost field,
`QPushButton:flat:hover`, `QPushButton:hover`, the dock title buttons.)
Then `... -m pytest -q tests/test_fxstyle.py tests/test_split_button_height.py`
→ all pass.

### Step 5: Add the pixel and token tests

Create `tests/test_button_states.py`, modelled on
`tests/test_frame_controls.py` (its `_flat` builder and `_at` pixel
reader). Content to cover — write it in that file's style:

```python
"""Every button state shows, on any ground: one convention for all."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication, QFrame, QPushButton, QToolButton, QVBoxLayout, QWidget,
)

# Internal
from fxgui import fxicons, fxstyle

from _helpers import hover, unhover

THEMES = fxstyle.get_available_themes()

# A raised card, as a media player's controls sit on: a ground an opaque
# fill can match.
fxstyle.register_widget_style(
    "QFrame#fxTestTooltipCard { background-color: @tooltip; border: none; }")


def _button(kind):
    if kind == "tool":
        button = QToolButton()
    else:
        button = QPushButton("Apply" if kind == "push" else "")
        if kind == "setFlat":
            button.setFlat(True)
        elif kind == "fxRole":
            button.setProperty("fxRole", "flat")
    button.setCheckable(True)
    if kind != "push":
        fxicons.set_icon(button, "arrow-left")
    return button


def _shown(qtbot, theme, button, card):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    holder = QFrame(window)
    if card:
        holder.setObjectName("fxTestTooltipCard")
    QVBoxLayout(window).addWidget(holder)
    QVBoxLayout(holder).addWidget(button)
    qtbot.addWidget(window)
    window.resize(200, 120)
    window.show()
    qtbot.waitExposed(window)
    window.setFocus()
    QApplication.processEvents()
    return window


def _fill(window, button):
    # A tool button has a 2 px margin: read inside it, clear of the icon.
    point = (QPoint(3, button.height() // 2)
             if isinstance(button, QToolButton)
             else QPoint(fxstyle.BUTTON_RADIUS, 2))
    return window.grab().toImage().pixelColor(
        button.mapTo(window, point)).name()


def _states(qtbot, qapp, window, button):
    """Return the fill at rest, hovered, pressed, checked, checked+hovered."""
    rest = _fill(window, button)
    hover(qtbot, button)
    hovered = _fill(window, button)
    button.setDown(True)
    qapp.processEvents()
    pressed = _fill(window, button)
    button.setDown(False)
    button.setChecked(True)
    qapp.processEvents()
    checked_hovered = _fill(window, button)
    unhover(qtbot, button)
    checked = _fill(window, button)
    return rest, hovered, pressed, checked, checked_hovered
```

Tests (66 in all):

1. `test_every_state_of_a_flat_button_shows_on_a_tooltip_card` —
   parametrized over `THEMES` × `kind in ("setFlat", "fxRole", "tool")`
   (33). On the card: `rest == QColor(colors.tooltip).name()`; each of
   hovered, pressed, checked, checked_hovered satisfies
   `fxstyle._visibly_differ(fill, ground)`; `_visibly_differ(pressed,
   hovered)`; `_visibly_differ(checked_hovered, checked)`;
   `checked == pressed`.
2. `test_a_push_button_wears_one_fill_per_state` — over `THEMES` (11),
   kind `"push"`, no card: hovered == `state_hover`, pressed and checked ==
   `state_pressed`, checked_hovered == `state_checked_hover` (compare
   `QColor(token).name()`).
3. `test_each_overlay_is_the_text_see_through_as_far_as_its_fill` — over
   `THEMES` (11), no widgets: for each of the three states,
   `QColor(colors[f"{state}_overlay"])` is valid, its `.name()` equals
   `QColor(colors["text"]).name()`, `0 < alpha() <= 128`, and unless
   `alpha() == 128` the blend
   `fxstyle.mix(colors["surface"], colors["text"], overlay.alphaF())`
   has contrast with `surface` >= that of `colors[state]` with `surface`.
   Use `fxstyle._colour_tokens(theme)` for `colors`.
4. `test_a_checked_hover_fill_stands_past_the_pressed_fill` — over `THEMES`
   (11): contrast(`state_checked_hover`, `state_pressed`) >=
   `fxstyle.state_contrast(theme)`, and contrast(`text`,
   `state_checked_hover`) >= 4.5.

The prototype measured all 44 widget cases passing in every bundled theme
with the exact rules of Steps 3-4 and the sample points above.

**Verify**: `... -m pytest -q tests/test_button_states.py` → `66 passed`.
Prove the widget tests catch the bug:
`git stash push -m plan002-proof -- fxgui/qss/style.qss`, rerun → test 1
(checked fxRole buttons, checked+hover) and test 2 fail; then find the
`plan002-proof` entry in `git stash list`, `git stash apply <its sha>`, and
drop that entry (never a bare `git stash pop`: the stash is shared across
worktrees).

### Step 6: Update the tests that assert the old fills

- `tests/test_frame_controls.py:292-308` (`test_a_hovered_flat_button_fills`,
  `test_a_pressed_flat_button_fills`): the pixel is now the overlay over
  the frame. Replace each equality with a comparison to the blend, within 2
  per channel, using `near` from `_helpers` (add it to the
  `from _helpers import ...` line):

  ```python
  overlay = QColor(fxstyle.colors().state_hover_overlay)
  expected = fxstyle.mix(_color("frame"), overlay.name(), overlay.alphaF())
  assert near(_at(window, button, fxstyle.BUTTON_RADIUS, 2), expected, 2)
  ```

  (and `state_pressed_overlay` in the pressed test).
- `tests/test_floating_dialog.py:152`: `colors.state_pressed` →
  `colors.state_hover` (a dialog button is a plain push button; it now
  hovers with the hover fill).
- Run the whole suite. For every other failure, read the test: if it only
  asserts that a push or tool button's hover/pressed/checked pixel equals
  the *old* token, update it to the new convention (opaque token for plain
  push and split buttons, overlay blend via `near(..., 2)` for flat push and
  plain tool buttons). Anything else is a STOP condition.

**Verify**: `... -m pytest -q -n 8` → `3267 passed, 6 skipped`.

### Step 7: Document the convention and the tokens

`docs/how-to/theming.md`:

- After the "Interactive State Colors" table (line ~94), add a short
  paragraph: four colours are derived, never set in a theme —
  `state_checked_hover` (a checked button under the pointer: a step past
  `state_pressed` by the same floor; `text` reads at 4.5:1 on it) and
  `state_hover_overlay`, `state_pressed_overlay`,
  `state_checked_hover_overlay` (`text` as `#AARRGGBB` at the least alpha
  whose blend over `surface` stands off it as the opaque fill does; flat
  push buttons and plain tool buttons wear them, so their states show on a
  band, a card or a tooltip). `fxstyle.colors()` has them;
  `QColor(fxstyle.colors().state_hover_overlay)` reads the alpha.
- In "Fills and edges by state" (line ~427): Push button column — Hover
  `fill @state_hover`, Pressed `fill @state_pressed`, Checked `fill
  @state_pressed, edge @grid`; Tool button (flat) column — hover/pressed/
  checked the three overlays, checked "no edge" (the sheet sets the edge
  transparent; the table's "edge @accent_primary" is wrong); add a row
  "Checked and hovered": push `fill @state_checked_hover`, tool
  `fill @state_checked_hover_overlay`, other columns empty.

**Verify**: `grep -n "state_checked_hover" docs/how-to/theming.md` → at
least 2 lines. If zensical is installed in the venv,
`... -m zensical build` → exit 0 (strict: no broken link); otherwise say
so in the report.

### Step 8: Lint and final suite

**Verify**: ruff → `All checks passed!`; whole suite → `3267 passed, 6 skipped`.

## Test plan

- New file `tests/test_button_states.py` (pattern:
  `tests/test_frame_controls.py`), 66 tests:
  - flat push (`setFlat`), flat icon (`fxRole="flat"`) and plain tool
    buttons on a `@tooltip` card, every theme: hover, pressed, checked and
    checked+hover each visibly differ from the card; pressed differs from
    hover; checked+hover differs from checked (regressions: checked
    `fxRole` flat showed nothing; hover on checked showed nothing; hover on
    a tooltip card invisible).
  - plain push button, every theme: exact token per state (regression:
    hover was `@state_pressed`).
  - overlay tokens: right ink, alpha range, contrast reached.
  - `state_checked_hover`: past pressed by the floor; text reads on it.
- Updated: `tests/test_frame_controls.py:292-308`,
  `tests/test_floating_dialog.py:152`, and any test Step 6 finds.

## Done criteria

- [ ] `3267 passed, 6 skipped` on the whole suite
- [ ] ruff `All checks passed!`
- [ ] `grep -n "QPushButton:flat:hover" -A 2 fxgui/qss/style.qss` shows `@state_hover_overlay`
- [ ] `grep -n "QPushButton\[fxRole=\"flat\"\]:checked" fxgui/qss/style.qss` → 3 lines
- [ ] `git status` lists only in-scope files
- [ ] `plans/2026-11-14-audit/README.md` status row for 002 updated

## STOP conditions

Stop and report (do not improvise) if:

- Plan 001 is not merged (the grep in "Current state" prints nothing).
- The QSS at the quoted line ranges does not match the excerpts.
- A state renders the wrong fill and reordering *within the block you
  wrote* does not fix it. Do not add `!important` (Qt QSS has none), extra
  type selectors, or widget-level `setStyleSheet` calls.
- A test fails that concerns rows, tabs, menus, headers, primary buttons,
  `FXIconButton` or `FXJoinedGroup`: this plan should not change them.
- `test_every_text_ink_reads_on_every_surface_it_sits_on` or
  `tests/test_theme_keys.py` fails after Step 1.
- In any bundled theme an overlay comes out at the cap (alpha `80`): the
  text is too close to the surface for a see-through fill to reach the
  opaque one's contrast; report the theme.

## Maintenance notes

- Specificity rule of thumb for future button rules in this sheet: a state
  that combines two pseudo-states (`:checked:hover`) must be written out,
  for the plain selector *and* for each attribute variant
  (`[fxRole="flat"]`, `[popupMode="1"]`), or a tie goes to whatever rule
  comes later in the file.
- Overlays are tuned against `surface`. On a much darker or lighter card,
  the same alpha gives a little more or less contrast (the prototype
  measured every state over `tooltip` visibly different, about 1.2:1 or
  more, in every bundled theme); re-run test 1 if a theme's `tooltip`
  moves far from its `surface`.
- With a brand floor of 1.0 (Pascal's Lotchi themes), overlays come out
  faint by design (hover alpha ~0.03): the brand chose faint fills. Measured
  on `lotchi_dark`'s tooltip card: rest `#191a1d`, hover `#1f2023`, pressed
  `#232427`, checked+hover `#28292c` — all distinct, where before hover
  showed nothing.
- Deferred: `FXIconButton` and `FXJoinedGroup` (`fxgui/fxwidgets/_buttons.py`
  lines ~85-100 and ~243-250) still use opaque `@state_hover`/
  `@state_pressed`; `FXIconButton` is transparent at rest and could take
  the overlays the same way. Non-flat push buttons are also transparent at
  rest; they keep opaque fills here to limit the visual change.
- Pascal: once this ships, Pascal can delete its own flat-button state rule
  for the media player card in `src/ls_pascal/apps/widgets/player.py`
  (the owner saw one; `origin/main` at `32e6a577` has only the card rule
  `QWidget#picture_card, QWidget#media_player { background-color: @tooltip; ... }`
  at ~lines 577-580 and `control_button`'s `setFlat(True)` at ~565-571, so
  it may live on an unpushed branch). The lotchi_light pressed-ink problem
  the owner saw (pressed fill `#9f9fa9` under icon ink `#54555B`, about
  2.8:1) comes from that Pascal rule and goes away with it.
