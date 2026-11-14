# Plan 010: Three theme-loading fixes: computed on-accent inks, a real mono font, app-mode window fades

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxstyle.py fxgui/fxwidgets/_tips.py tests/test_fxstyle.py tests/test_fxstyle_fonts.py tests/test_tips.py tests/test_motion.py`
> Plans 001 and 002 also edit `fxgui/fxstyle.py` and `tests/test_fxstyle.py`
> (`_readable_states`, `_token_map`, new tests); that drift is fine. If the
> functions this plan touches (`_builtin_theme`, `_theme_data`, `font`,
> `register_themed_root`, `_FocusVisibility.eventFilter`, `_tips._code`)
> changed, compare them with the excerpts below; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Three small defects in how a theme is loaded and applied. Each is
independent; do them as three commits.

1. **On-accent inks.** `style.yaml` documents `text_on_accent_*` and
   `icon_on_accent_*` as "auto-computed if omitted". But a theme added by
   `fxstyle.overlay_color_file` that omits them inherits the bundled
   `dark` theme's white. With a light accent the button text is unreadable:
   accent `#ffeb3b` got `text_on_accent_primary` `#ffffff`, 1.22:1. Pascal
   works around it by restating every on-accent key in its own theme file.
2. **Mono font.** `fxstyle.font(role="mono")` returns a font with *no*
   family when the mono role resolves to the CSS generic `monospace` (any
   machine without Consolas or Courier New, e.g. Linux). Qt then draws the
   proportional default face. `fxwidgets/_tips.py` works around it.
3. **Window fade.** A themed window fades in when shown, but only in "host
   mode" (fxgui themes single windows inside another application). In "app
   mode" (`FXApplication`, which registers the `QApplication` itself as the
   themed root) no window ever fades, because the marker property the fade
   checks is never set there.

**Public behaviour that changes**: (1) a theme that omits on-accent keys,
other than `dark` itself, now gets inks computed from its own accents (the
documented behaviour); all 11 bundled themes state all four keys, so none
changes. (2) `font(role="mono")` names the platform's fixed-pitch family
instead of none when the role falls to `monospace`. (3) In app mode, a
window that calls `register_themed_root` (`FXMainWindow`, `FXDialog`,
`FXFloatingDialog`, `FXConfirmDelete`, `FXSplashScreen`, a caller's own)
fades in over `WINDOW_FADE_MS` (250 ms) as it already does in host mode;
`FXGUI_REDUCED_MOTION=1` still turns it off.

## Current state

Files:

- `fxgui/fxstyle.py` — theme engine: `_builtin_theme` (497-507),
  `_theme_data` (520-527), `register_themed_root` (2218-2240),
  `_FocusVisibility.eventFilter` (2739-2783), `_fade_in` (2854-2863),
  `font` (3016-3045).
- `fxgui/fxwidgets/_tips.py` — tooltip HTML; `_code` (178-201) has the
  mono workaround.
- `tests/test_fxstyle.py` — theme engine tests (on-accent test at 192-206;
  `_yaml(tmp_path, text)` helper at 30-33 writes a colour file).
- `tests/test_fxstyle_fonts.py` — font tests; `test_font_takes_a_role` at
  286-290 asserts the bug (`families() == []`).
- `tests/test_tips.py` — `test_code_names_the_family_of_the_mono_role` at
  284-300 tests the workaround.
- `tests/test_motion.py` — fade tests (`_fades(widget)` helper at 92-96;
  host-mode window test at 99-107); fixtures `app_root`/`host_root` are in
  `tests/conftest.py:122-157`.

### (1) On-accent inks

```python
# fxgui/fxstyle.py:496-507
@lru_cache(maxsize=1)
def _builtin_theme() -> dict:
    """Return the default file's dark theme, the baseline for every key.

    Keys computed from others are left out, so a file whose accent differs
    gets them computed from its own accent.
    """
    theme = _read_yaml(DEFAULT_COLOR_FILE)["themes"][_DEFAULT_THEME]
    return {
        key: value for key, value in theme.items()
        if not key.startswith(("text_on_accent", "icon_on_accent"))
    }
```

```python
# fxgui/fxstyle.py:520-527
def _theme_data(theme_name: str) -> dict:
    """Return a theme's raw values over the file's dark and the built-in dark."""
    themes = get_colors().get("themes", {})
    return {
        **_builtin_theme(),
        **themes.get(_DEFAULT_THEME, {}),
        **themes.get(theme_name, {}),
    }
```

The baseline strips the keys, but the middle layer (`themes["dark"]` of the
*loaded* file) puts them back: with the default file, or any file overlaid
on it, that `dark` states `text_on_accent_primary: "#ffffff"` etc.
(`fxgui/style.yaml:178-179, 198-199`). `_token_map` (lines 1377-1391) only
computes an ink (`_pole_from(accent)`, black or white, whichever reads
better) when the key is missing. The existing test at
`tests/test_fxstyle.py:192-196` even says so in its comment: "Only when
dark itself omits the on-accent keys does the computed fallback run".

An unknown theme name must keep resolving to exactly `dark`
(`test_a_partial_or_unknown_theme_fills_from_dark`,
`tests/test_fxstyle.py:166-167`, asserts `_token_map("no_such_theme") ==
_token_map("dark")`), so only strip for a theme that exists in the file.
Bundled themes inherit dark through YAML anchors (`<<: *dark`), which copy
dark's keys into their own mapping at parse time; a probe confirmed all 11
bundled themes state all four on-accent keys themselves, so none changes.

### (2) Mono font

```python
# fxgui/fxstyle.py:3034-3045
    theme = theme or get_theme()
    roles = _font_config(theme)
    family = _font_family(roles.get(role, roles["body"]))
    result = QFont()
    result.setFamilies([] if family in _GENERIC_FONT_FAMILIES else [family])
    result.setPixelSize(FONT_SIZE)
    weight, hinting = _shape(theme, role)
    if weight is not None:
        result.setWeight(_WEIGHTS[weight])
    if hinting is not None:
        result.setHintingPreference(_HINTING[hinting])
    return result
```

`_font_family` (731-760) returns the first installed family of the role, or
a CSS generic (`_GENERIC_FONT_FAMILIES`, line 379: cursive, fantasy,
monospace, sans-serif, serif) lowercased, or the platform default. The
default mono role is `["Consolas", "Courier New", "monospace"]`
(`fxstyle.py:389`, `style.yaml:82`).

```python
# fxgui/fxwidgets/_tips.py:178-191
def _code(text: str) -> str:
    """Return `text` as code: the theme's mono face in a block of its own.
    ...
    """
    colors = fxstyle.colors()
    # Qt's rich text ignores the generic `monospace`: name a family, the
    # system's fixed one when the theme's mono role found none.
    families = fxstyle.font(role="mono").families()
    if not families and QGuiApplication.instance() is not None:
        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        families = [fixed.family()]
    face = f"font-family:'{escape(families[0])}'; " if families else ""
```

`QFontDatabase` and `QGuiApplication` are used nowhere else in `_tips.py`
(only the import at line 23 and lines 188-189).

Measured fact: under `QT_QPA_PLATFORM=offscreen` (the test platform),
`QFontDatabase.systemFont(FixedFont).family()` is the string `"monospace"`
itself; on real Windows it is a real family (Courier New). So tests must
compare with whatever `systemFont` returns, never a hard-coded name, and
the new code must not drop that name just because it equals a generic.

### (3) Window fade

```python
# fxgui/fxstyle.py:2234-2240
    if isinstance(root, QWidget) and not _in_host(root):
        return
    _themed_roots.add(root)
    if isinstance(root, QWidget):
        root.setProperty(ROOT_PROPERTY, True)
    _watch_focus()
    _apply_to_root(root, _build_stylesheet(), palette(), font())
```

```python
# fxgui/fxstyle.py:2760-2769 (inside _FocusVisibility.eventFilter)
        elif kind == QEvent.Show and isinstance(watched, QWidget):
            if watched.windowType() in (Qt.Popup, Qt.ToolTip):
                self._dress_popup(watched)
            elif (
                watched.isWindow()
                and watched.property(ROOT_PROPERTY)
                # Shown by the application, not restored by the system.
                and not event.spontaneous()
            ):
                _fade_in(watched, WINDOW_FADE_MS)
```

`_in_host(root)` is True for a widget when the `QApplication` is *not* a
themed root. So in app mode `register_themed_root(widget)` returns before
setting `ROOT_PROPERTY` (`"fxThemedRoot"`), and the fade check never
passes. Where else `ROOT_PROPERTY` is read: `_is_themed` (2916-2924, which
returns True for everything in app mode before it looks at the property)
and `_HOST_RULES` (2264, only applied in host mode). So setting the
property in app mode changes nothing but the fade. `_fade_in` already
returns early under `FXGUI_REDUCED_MOTION=1` (`motion()`, line 363), and
`tests/conftest.py:14` sets that for the whole suite.

Chosen behaviour: in app mode, fade exactly the windows that registered
themselves, as host mode does. Do **not** fade every top-level window
(`QMessageBox`, a floating dock, a file dialog would start fading).

Conventions: Google docstrings; comments say *why*, briefly; tests are
plain functions named as sentences.

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| One test file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_motion.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | at `b283eb13`: `3178 passed, 6 skipped`; after this plan, 3 more passed (if other plans merged first, their count + 3) |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

Never run tests or the gallery on the real Qt platform (it moves the
owner's pointer); conftest forces `offscreen`. Any ad-hoc Python must call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, and run with `PYTHONPATH=.` from the worktree root
so the worktree's `fxgui` wins over the venv's editable install (another
checkout).

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxstyle.py` — `_builtin_theme`, `_theme_data`, `font`,
  `register_themed_root` (and its docstring).
- `fxgui/fxwidgets/_tips.py` — `_code` and the `qtpy.QtGui` import line.
- `tests/test_fxstyle.py` — one new test; the comment of the test at
  192-194.
- `tests/test_fxstyle_fonts.py` — `test_font_takes_a_role` (286-290).
- `tests/test_tips.py` — `test_code_names_the_family_of_the_mono_role`
  (284-300).
- `tests/test_motion.py` — two new tests.

**Out of scope** (do NOT touch):

- `fxgui/style.yaml` values (the bundled themes keep their stated inks) and
  its comments (they already say "auto-computed if omitted", which becomes
  true).
- `_qss_family` / the `@font_mono` sheet token: the sheet still writes the
  generic `monospace` unquoted. Changing what the sheet names is a separate
  decision (Maintenance notes).
- `FXSplashScreen`'s own `fade_in` animation, `_fade_in`, `_Reveal`.
- `_is_themed` and the `_in_host` rule that a widget is not *registered*
  (added to `_themed_roots`) in app mode: only the marker property moves.
- `CHANGELOG.md`.

## Git workflow

- Work in a git worktree, never the shared checkout. No `.gitmodules` at the
  planned-at commit; if one exists by now, run
  `git submodule update --init --depth 1`.
- Branch: `fix/theme-loading-fixes`.
- Three commits, in repo style, e.g.
  `[FIX] a theme computes its own on-accent inks when it omits them`,
  `[FIX] font(role="mono") names the platform's fixed face for monospace`,
  `[FIX] a registered window fades in under FXApplication too`.
- Do not push, tag or release. Never edit `CHANGELOG.md`.

## Steps

### Step 1: Snapshot the bundled tokens (for part 1)

Create a scratch script **outside the repo**, e.g.
`%TEMP%\fxgui_dump_tokens.py`:

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

Git Bash, from the worktree root:

```bash
PYTHONPATH=. "C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python.exe" "$TEMP/fxgui_dump_tokens.py" "$TEMP/tokens_010_before.json"
```

**Verify**: stderr shows `fxgui` loaded from the worktree; the JSON file
exists.

### Step 2: Part 1 — strip dark's on-accent inks for other themes

In `fxgui/fxstyle.py`:

- Add, next to `_builtin_theme` (above it):

  ```python
  # Inks worked out from a theme's own accents when it omits them.
  _ON_ACCENT_KEYS = ("text_on_accent", "icon_on_accent")
  ```

  and use `key.startswith(_ON_ACCENT_KEYS)` in `_builtin_theme`.
- Replace `_theme_data`'s body with:

  ```python
  def _theme_data(theme_name: str) -> dict:
      """Return a theme's raw values over the file's dark and the built-in dark.

      A theme of the file other than dark takes no on-accent ink from dark:
      dark's white was chosen for dark's accent, and an omitted ink is
      computed from the theme's own. An unknown name is dark itself.
      """
      themes = get_colors().get("themes", {})
      dark = themes.get(_DEFAULT_THEME, {})
      if theme_name != _DEFAULT_THEME and theme_name in themes:
          dark = {
              key: value for key, value in dark.items()
              if not key.startswith(_ON_ACCENT_KEYS)
          }
      return {**_builtin_theme(), **dark, **themes.get(theme_name, {})}
  ```

In `tests/test_fxstyle.py`, after
`test_token_map_computes_on_accent_when_theme_omits_them` (ends line 206),
add:

```python
def test_a_theme_an_overlay_adds_computes_its_own_on_accent_inks(
        qapp, tmp_path):
    fxstyle.overlay_color_file(_yaml(tmp_path, (
        "themes:\n  sunny:\n"
        "    accent_primary: '#ffeb3b'\n    accent_secondary: '#fdd835'\n")))
    tokens = fxstyle._token_map("sunny")
    # A yellow accent reads with black, not dark's white (1.22:1).
    for key in ("text_on_accent_primary", "icon_on_accent_primary",
                "text_on_accent_secondary", "icon_on_accent_secondary"):
        assert tokens[f"@{key}"] == "#000000", key
    assert fxstyle._token_map("dark")["@text_on_accent_primary"] == "#ffffff"
```

and rewrite the comment of the test at lines 193-194 to: "dark computes
its own inks only when it omits them; another theme that omits them never
takes dark's (see the test below)".

**Verify**:

- `... -m pytest -q tests/test_fxstyle.py` → all pass, one more than before.
- Proof the test catches the bug: `git stash push -m plan010-proof -- fxgui/fxstyle.py`,
  rerun → only the new test fails; then find the `plan010-proof` entry in
  `git stash list`, `git stash apply <its sha>`, drop that entry (never a
  bare `git stash pop`: the stash is shared across worktrees).
- Re-run the Step 1 script into `$TEMP/tokens_010_after.json` and compare:

  ```bash
  "C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python.exe" -c "import json,os;b=json.load(open(os.path.expandvars('$TEMP/tokens_010_before.json')));a=json.load(open(os.path.expandvars('$TEMP/tokens_010_after.json')));print('changed:',[t for t in b if b[t]!=a[t]])"
  ```

  → `changed: []`.

Commit part 1.

### Step 3: Part 2 — `font()` names the fixed face for `monospace`

In `fxgui/fxstyle.py`, `font`, replace the line
`result.setFamilies([] if family in _GENERIC_FONT_FAMILIES else [family])`
with:

```python
    if family == "monospace" and QGuiApplication.instance() is not None:
        # Qt draws no CSS generic, rich text included: name the platform's
        # fixed face, whatever it is called.
        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        result.setFamilies([fixed.family()])
    else:
        result.setFamilies(
            [] if family in _GENERIC_FONT_FAMILIES else [family])
    if family == "monospace":
        result.setStyleHint(QFont.StyleHint.Monospace)
```

(`QGuiApplication`, `QFontDatabase` and `QFont` are already imported in
`fxstyle.py`; check with `grep -n "^from qtpy.QtGui" -A 25 fxgui/fxstyle.py`.)
Add one sentence to the docstring: a role that falls to the generic
``monospace`` names the platform's fixed-pitch family.

In `tests/test_fxstyle_fonts.py`, `test_font_takes_a_role` (286-290):

```python
def test_font_takes_a_role(qapp, monkeypatch):
    _patch_color_file(monkeypatch, fonts={"mono": ["No Such QQQ", "monospace"]})
    mono = fxstyle.font("dark", role="mono")
    fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    assert mono.families() == [fixed.family()]
    assert mono.styleHint() == QFont.StyleHint.Monospace
    assert fxstyle.font("dark", role="title").family() == (
        fxstyle._platform_default_font())
```

(`QFont` and `QFontDatabase` are already imported there, line 17.)

In `fxgui/fxwidgets/_tips.py`, `_code`: delete the two comment lines and
the `if not families ...` block, leaving:

```python
    colors = fxstyle.colors()
    families = fxstyle.font(role="mono").families()
    face = f"font-family:'{escape(families[0])}'; " if families else ""
```

and change line 23 to `from qtpy.QtGui import QAction, QKeySequence`.

In `tests/test_tips.py`, `test_code_names_the_family_of_the_mono_role`:
keep the first part (lines 285-288, a named family is written escaped);
change its import to `from qtpy.QtGui import QFont`; replace the second
part (lines 290-300) with:

```python
    # A role with no family leaves the face to the tip's own font.
    def without_a_family(role):
        font = QFont()
        font.setFamilies([])
        return font

    monkeypatch.setattr(fxstyle, "font", without_a_family)
    assert "font-family" not in _tips.tip("", code="a.key")
```

**Verify**: `... -m pytest -q tests/test_fxstyle_fonts.py tests/test_tips.py tests/test_code_block.py`
→ all pass; `grep -n "QFontDatabase\|QGuiApplication" fxgui/fxwidgets/_tips.py`
→ no output; ruff → `All checks passed!`. Commit part 2.

### Step 4: Part 3 — mark a registered window in app mode too

Decision gate: if the operator told you they prefer to *document* "no
window fade in app mode" instead, skip this step's code and instead add one
sentence to `register_themed_root`'s docstring ("Under a themed
QApplication, windows do not fade in.") plus the second test below only
(`..._does_not_fade`), then go to Step 5. Otherwise do this:

In `fxgui/fxstyle.py`, `register_themed_root`, replace lines 2234-2238
with:

```python
    if isinstance(root, QWidget):
        # Marked in both modes: a themed window fades in as it shows.
        root.setProperty(ROOT_PROPERTY, True)
        if not _in_host(root):
            return
    _themed_roots.add(root)
```

(the `_watch_focus()` and `_apply_to_root(...)` lines after it stay).
Extend the docstring paragraph "A widget is not registered while the
QApplication is a root..." with: "It is still marked as a themed window,
so it fades in as it shows, as in a host."

In `tests/test_motion.py`, after `test_a_themed_window_fades_in_when_shown`
(line ~107), add:

```python
def test_a_window_in_a_themed_application_fades_in_when_shown(
        qtbot, app_root):
    fxstyle.register_themed_root(app_root)
    app_root.show()
    qtbot.waitExposed(app_root)
    fades = _fades(app_root)
    assert fades, "the window shows with no fade"
    assert fades[0].duration() == fxstyle.WINDOW_FADE_MS


def test_an_unregistered_window_in_a_themed_application_does_not_fade(
        qtbot, app_root):
    app_root.show()
    qtbot.waitExposed(app_root)
    assert not _fades(app_root)
```

(`app_root` is the conftest fixture that makes the `QApplication` the
themed root and yields an unshown `QWidget`; the module's autouse `_motion`
fixture removes `FXGUI_REDUCED_MOTION` so fades play.)

**Verify**: `... -m pytest -q tests/test_motion.py tests/test_application.py tests/test_host_sheet.py`
→ all pass; proof: stash `fxgui/fxstyle.py` as in Step 2 (tag
`plan010c-proof`) and rerun `tests/test_motion.py` → only
`test_a_window_in_a_themed_application_fades_in_when_shown` fails; restore
by sha and drop the entry. Commit part 3.

### Step 5: Whole suite and lint

**Verify**: whole suite → previous count + 3 passed, `6 skipped`; ruff →
`All checks passed!`.

## Test plan

- `tests/test_fxstyle.py::test_a_theme_an_overlay_adds_computes_its_own_on_accent_inks`
  (new; pattern: the overlay test at `tests/test_fxstyle.py:86-95` and the
  `_yaml` helper) — a theme added by an overlay with a yellow accent gets
  black inks; dark keeps its white.
- `tests/test_fxstyle_fonts.py::test_font_takes_a_role` (changed) — the
  mono role falling to `monospace` names the system fixed family and the
  `Monospace` style hint.
- `tests/test_tips.py::test_code_names_the_family_of_the_mono_role`
  (changed) — the tip writes the family `font()` names, and none when it
  names none.
- `tests/test_motion.py` (two new; pattern: `test_a_themed_window_fades_in_when_shown`)
  — app mode: a registered window fades, an unregistered one does not.
- Existing that must keep passing unchanged:
  `test_a_partial_or_unknown_theme_fills_from_dark`,
  `test_token_map_computes_on_accent_when_theme_omits_them`,
  `test_a_colour_file_without_dark_fills_from_the_default`,
  `test_reduced_motion_turns_every_fade_off`, `tests/test_host_sheet.py`.

## Done criteria

- [ ] Whole suite: previous count + 3 passed, 6 skipped
- [ ] Ruff: `All checks passed!`
- [ ] Step 2's token comparison prints `changed: []`
- [ ] `grep -n "QFontDatabase" fxgui/fxwidgets/_tips.py` → no output
- [ ] `grep -n "families() == \[\]" tests/test_fxstyle_fonts.py` → no output
- [ ] `git log --oneline -3` shows the three `[FIX]` commits
- [ ] `git status` lists only in-scope files
- [ ] `plans/2026-11-14-audit/README.md` status row for 010 updated

## STOP conditions

Stop and report (do not improvise) if:

- The code at the quoted lines does not match the excerpts (beyond plans
  001/002's edits elsewhere in `fxstyle.py`).
- Step 2's comparison lists any bundled theme: a bundled theme relied on
  dark's inks, which the probe said none does.
- `test_a_partial_or_unknown_theme_fills_from_dark` fails: the unknown-name
  guard is wrong.
- In Step 4, any test outside `tests/test_motion.py` fails, or a test shows
  a window that did *not* call `register_themed_root` (a `QMessageBox`, a
  floating dock, a QtAds floating container) now fading.
- The operator has not said which they prefer for part 3 *and* has asked
  to be consulted on behaviour changes: ask "In app mode (FXApplication),
  should registered windows fade in as they do in host mode, or should the
  docs say windows never fade in app mode?" before Step 4.

## Maintenance notes

- Part 1 makes the yaml comment "auto-computed if omitted" true for every
  theme. A theme that wants dark's white on a light accent must now state
  it.
- Part 2 covers `font(role=...)` (QFont users, rich text via `_tips`). The
  sheet's `@font_mono` still writes the generic `monospace`, which Qt's
  sheet font matching may also miss on machines without Consolas/Courier
  New (`fxgui/qss/style.qss:549`, `fxwidgets/_code_block.py:265`); a
  follow-up could resolve it to the same fixed family in `_qss_family`.
- Part 3: `FXSplashScreen` registers itself, so in app mode it now gets the
  250 ms fade as well as its own optional 1000 ms one (`fade_in=True`),
  exactly as it already does in host mode; both animate `windowOpacity`
  0 to 1.
- Reviewer: check that setting `fxThemedRoot` in app mode adds nothing to
  `_themed_roots` (the docstring's reason for not registering still holds).
- Pascal: once this ships, Pascal can delete the restated on-accent keys
  from its `lotchi_colors.yaml` (`lotchi_dark`: `text_on_accent_primary`,
  `icon_on_accent_primary`; `lotchi_light`: all four) and the comment
  "Stated, since a theme inherits dark's white": the computed inks are the
  same values (black on `#FF4200` and `#FF7140`, white on `#C33605`).
