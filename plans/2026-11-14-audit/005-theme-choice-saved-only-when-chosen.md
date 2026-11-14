# Plan 005: A theme or row size is saved only when a person chose it

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxstyle.py fxgui/fxconfig.py tests/conftest.py tests/test_fxconfig.py tests/test_row_size.py docs/how-to/theming.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MED
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Every call to `fxstyle.apply_theme(name)` and `fxstyle.apply_row_size(size)`
writes the value into the user's settings file, `%APPDATA%\fxgui\settings.ini`
on Windows. That file is shared by every tool built on fxgui that did not call
`fxconfig.set_application_name`. So a headless script, a benchmark or a test
run that applies a theme overwrites the person's real theme choice. This has
already happened once: a benchmark replaced the owner's theme.

After this plan, the two functions take a keyword `save`. Left out, they save
only when Qt draws on a real screen (a person is there to choose); on Qt's
headless platforms (`offscreen`, `minimal`) they do not save. `save=True` or
`save=False` forces the choice. Also, `fxconfig.set_value` stops rewriting the
file when the stored value is already the new one.

**Public behaviour that changes**: only for callers on a headless Qt platform.
Their `apply_theme`/`apply_row_size` no longer persist unless they pass
`save=True`. Interactive applications behave exactly as before.

## Current state

Files:

- `fxgui/fxstyle.py` — themes; `apply_theme`, `apply_row_size`, `save_theme`.
- `fxgui/fxconfig.py` — the `QSettings` wrapper (`get_value`, `set_value`,
  `set_application_name`).
- `tests/conftest.py` — per-test isolation; today it patches private
  `fxconfig` names.
- `tests/test_fxconfig.py` — fxconfig tests; the pattern for the new tests.
- `tests/test_row_size.py` — has one test that relies on `apply_row_size`
  saving, which breaks under the new default.
- `docs/how-to/theming.md` — the "Switching Themes at Runtime" section says
  `apply_theme` saves the choice.

The write path today:

```python
# fxgui/fxstyle.py:1569-1578
def save_theme(theme: str) -> None:
    """Save the current theme to persistent storage.
    ...
    """
    fxconfig.set_value(_SETTINGS_THEME_KEY, theme)
```

```python
# fxgui/fxstyle.py:1686-1701
def apply_row_size(size: str) -> str:
    """Make every list and tree row `size` tall, save it, and re-style.

    Raises:
        ValueError: If `size` is not a `ROW_SIZES` name.

    Examples:
        >>> fxstyle.apply_row_size("small")
    """
    global _row_size
    if size not in ROW_SIZES:
        raise ValueError(f"Row size '{size}' not found: {sorted(ROW_SIZES)}")
    _row_size = size
    fxconfig.set_value(_SETTINGS_ROW_SIZE_KEY, size)
    _colors_changed()
    return size
```

```python
# fxgui/fxstyle.py:1742-1771
def apply_theme(theme: str) -> str:
    """Apply a theme to every themed root and emit ``theme_changed``.

    Args:
        theme: The theme name to apply (e.g., "dark", "light").
    ...
    """
    global _theme

    if not isinstance(theme, str):
        raise TypeError("apply_theme() takes a theme name")
    available_themes = get_available_themes()
    if theme not in available_themes:
        raise ValueError(
            f"Theme '{theme}' not found. Available themes: {available_themes}"
        )

    _theme = theme
    save_theme(theme)
    _colors_changed()
    return theme
```

`fxstyle.py` already imports `os` (line 28) and `QGuiApplication` from
`qtpy.QtGui` (line 59). The keys are `_SETTINGS_THEME_KEY = "theme/current"`
and `_SETTINGS_ROW_SIZE_KEY = "rows/size"` (lines 216-217).

The docstring of `set_default_theme` (`fxgui/fxstyle.py:1596-1599`) shows a
startup pattern that, today, writes the default into the file and so turns
it into a "saved choice":

```python
    Examples:
        >>> fxstyle.set_color_file("studio_colors.yaml")
        >>> fxstyle.set_default_theme("studio")
        >>> fxstyle.apply_theme(fxstyle.load_saved_theme())
```

fxconfig:

```python
# fxgui/fxconfig.py:46-71
    global _APP_NAME, _settings_instance
    ...
    name = name.strip()
    changed = name != _APP_NAME
    _APP_NAME = name
    _settings_instance = None
    # fxstyle holds the theme and row size it read from the old file.
    fxstyle = sys.modules.get("fxgui.fxstyle")
    if changed and fxstyle is not None:
        fxstyle._forget_saved_settings()


def _settings() -> QSettings:
    """Return the cached QSettings on this application's INI file."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = QSettings(
            QSettings.IniFormat, QSettings.UserScope, _APP_NAME, "settings"
        )
    return _settings_instance
```

```python
# fxgui/fxconfig.py:94-108
def set_value(key: str, value: Any) -> None:
    """Set a setting value.

    The value is immediately synced to disk.
    ...
    """
    settings = _settings()
    settings.setValue(key, value)
    settings.sync()
```

Important facts (verified with a probe on Windows, PySide6, 2026-11-14):

- Qt finds `%APPDATA%` through the Windows shell. Changing the `APPDATA`
  environment variable does **not** move the file. Only
  `QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, folder)` or a
  different application name does.
- `_settings()` caches its `QSettings`. A `QSettings.setPath` made after the
  first read is ignored by the cached object. `set_application_name` always
  drops the cache (line 57, unconditionally), so calling it after `setPath`
  makes the new folder take effect. This plan documents that and uses it; it
  does **not** add a new `reset()` function (it would duplicate line 57).
- Without a `QGuiApplication`, `QGuiApplication.platformName()` returns the
  default platform (`"windows"`), not `QT_QPA_PLATFORM`. With an application
  made under `QT_QPA_PLATFORM=offscreen` it returns `"offscreen"`. So the
  headless check must read the environment variable when no application
  exists.
- After `QSettings.sync()`, if nothing changed, the file is not rewritten
  (its modification time stays). `sync()` also reloads values another process
  wrote to the file.

Test isolation today:

```python
# tests/conftest.py:51-59
    from qtpy.QtCore import QSettings

    # Every user-scope INI file, fxconfig's included, lands in this test's
    # own folder; the previous test's QSettings is dropped first.
    QSettings.setPath(
        QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings")
    )
    monkeypatch.setattr(fxconfig, "_APP_NAME", "fxgui")
    monkeypatch.setattr(fxconfig, "_settings_instance", None)
```

conftest also sets `QT_QPA_PLATFORM=offscreen` (line 11), so **every test runs
headless**: after this plan, `apply_theme`/`apply_row_size` in tests do not
save unless `save=True` is passed. The one test that relies on saving:

```python
# tests/test_row_size.py:27-32
def test_the_row_size_is_saved_and_read_back(set_row_size):
    set_row_size("small")
    assert fxconfig.get_value("rows/size") == "small"
    # A fresh process reads it from the settings, not the cache.
    fxstyle._row_size = None
    assert fxstyle.row_size() == "small"
```

(`set_row_size` is a conftest fixture that yields `fxstyle.apply_row_size`,
`tests/conftest.py:113-119`.)

Callers of `apply_theme`/`apply_row_size` inside fxgui, all left unchanged:
the theme menu (`fxgui/fxwidgets/_main_window.py:291`), the row-size menu
(`_main_window.py:304`) and `FXMainWindow.toggle_theme`
(`_main_window.py:549`). They run on a person's click in a real window, so the
default (`save=None`) already saves there; under `offscreen` (tests) they will
not, which is the point.

Conventions: Google-style docstrings with `Args`/`Returns`; type annotations;
comments explain why, in one line; `###### Section` separators already exist
in `fxstyle.py`. Tests are plain functions named as sentences, in the style of
`tests/test_fxconfig.py`.

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| One test file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_fxconfig.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it, 3178 + the new tests passed, 6 skipped |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |
| Docs build | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m zensical build` (only if zensical is installed in the venv; otherwise skip and say so) | exit 0 (`strict = true`: a broken link fails) |

Never run tests on the real Qt platform: conftest forces `offscreen`; do not
override it. Any ad-hoc Python you run must first call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, or it overwrites the owner's real settings file.
Run ad-hoc scripts with `PYTHONPATH=.` so the worktree's `fxgui` wins over the
venv's editable install (which points at another checkout).

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxstyle.py` — `apply_theme`, `apply_row_size`, a new private
  `_interactive()`, the `set_default_theme` docstring example.
- `fxgui/fxconfig.py` — `set_value` (skip unchanged), `set_application_name`
  docstring.
- `tests/conftest.py` — replace the two private patches.
- `tests/test_fxconfig.py` — new tests.
- `tests/test_row_size.py` — pass `save=True` in the one saving test.
- `docs/how-to/theming.md` — the "Switching Themes at Runtime" section.

**Out of scope** (do NOT touch):

- `fxgui/fxwidgets/_main_window.py` — the menu and `toggle_theme` call sites
  stay on the default; they are interactive by nature.
- `fxgui/examples.py` — the gallery's Ctrl+T toggle is a person's choice on a
  real screen; scoping the gallery to its own application name is a separate
  decision.
- `save_theme` — public; keep its signature and behaviour (it always saves).
- A new `fxconfig.reset()` — not needed; `set_application_name` already drops
  the cache.
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists.
- Branch: `fix/theme-saved-only-when-chosen`.
- Commit messages in the repo style, e.g. `[FIX] apply_theme saves only when a person chose the theme`,
  `[DOC] theming: when a theme is saved`. End each commit message with the
  attribution line the operator's environment asks for, if any.
- Do not push, tag or release: the operator does.

## Steps

### Step 1: Add the headless check and the `save` keyword in `fxstyle.py`

1. Just above `def save_theme` (in the `###### Theme Functions` section,
   `fxgui/fxstyle.py:1566`), add:

   ```python
   # Qt platforms that draw on no screen: nobody there chose a theme.
   _HEADLESS_PLATFORMS = frozenset({"offscreen", "minimal"})


   def _interactive() -> bool:
       """Return whether Qt draws on a real screen, so a person is choosing."""
       if QGuiApplication.instance() is not None:
           name = QGuiApplication.platformName()
       else:
           # Without an application, platformName() names the default platform.
           name = os.environ.get("QT_QPA_PLATFORM", "")
       # QT_QPA_PLATFORM may carry fallbacks ("a;b") and options ("a:x=1").
       return name.split(";")[0].split(":")[0] not in _HEADLESS_PLATFORMS
   ```

2. Change `apply_theme` to:

   ```python
   def apply_theme(theme: str, *, save: Optional[bool] = None) -> str:
   ```

   Add to its docstring `Args`:

   ```
       save: Whether to save the theme as the person's choice. None (the
           default) saves unless Qt runs headless (the "offscreen" or
           "minimal" platform), so a script or a test never overwrites it.
   ```

   and replace `save_theme(theme)` with:

   ```python
       if _interactive() if save is None else save:
           save_theme(theme)
   ```

   (Or the plainer two-line form `if save is None: save = _interactive()` /
   `if save: save_theme(theme)`. Pick one and use it in both functions.)

3. Change `apply_row_size` the same way: signature
   `def apply_row_size(size: str, *, save: Optional[bool] = None) -> str:`,
   the same `save` entry in an `Args` section (add `size: A ROW_SIZES name.`
   too, since it has none), and wrap
   `fxconfig.set_value(_SETTINGS_ROW_SIZE_KEY, size)` in the same condition.
   Change its summary line from "save it, and re-style" to
   "save it when chosen, and re-style".

4. In the `set_default_theme` docstring example, change the last line to:

   ```python
           >>> fxstyle.apply_theme(fxstyle.load_saved_theme(), save=False)
   ```

   Reason: applying the loaded theme at startup must not write the default
   into the file, or the default becomes a "saved choice" and
   `set_default_theme` stops working on the next run.

`Optional` is already imported in `fxstyle.py` (line 36:
`from typing import Callable, Dict, Iterable, Optional, Tuple, Union`).

**Verify**: `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_row_size.py`
→ exactly one failure, `test_the_row_size_is_saved_and_read_back`
(it relied on saving under `offscreen`). Any other failure: STOP.

### Step 2: Fix the one test that relied on saving

In `tests/test_row_size.py:28`, change `set_row_size("small")` to
`set_row_size("small", save=True)`.

**Verify**: `...\python.exe -m pytest -q tests/test_row_size.py` → all pass.

### Step 3: Skip rewriting an unchanged value in `fxconfig.set_value`

Replace the body of `set_value` (`fxgui/fxconfig.py:106-108`) with:

```python
    settings = _settings()
    # Reload first: another process may have written the file since.
    settings.sync()
    if settings.contains(key) and settings.value(key) == value:
        return
    settings.setValue(key, value)
    settings.sync()
```

Add one sentence to its docstring after "The value is immediately synced to
disk.": "A value already stored is not written again."

**Verify**: `...\python.exe -m pytest -q tests/test_fxconfig.py tests/test_fxstyle_default_theme.py tests/test_row_size.py` → all pass.

### Step 4: Document that `set_application_name` re-reads where settings live

In the `set_application_name` docstring (`fxgui/fxconfig.py:32-45`), after
"Call this early at startup.", add:

```
    It also drops the settings file read so far, so a
    `QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, folder)`
    made before it takes effect (tests use this to keep the person's real
    settings untouched).
```

No code change in this function.

**Verify**: `git diff --stat fxgui/fxconfig.py` → only docstring lines and the
`set_value` body changed.

### Step 5: Use the public call in `tests/conftest.py`

Replace `tests/conftest.py:58-59`:

```python
    monkeypatch.setattr(fxconfig, "_APP_NAME", "fxgui")
    monkeypatch.setattr(fxconfig, "_settings_instance", None)
```

with:

```python
    fxconfig.set_application_name("fxgui")
```

Keep it after the `QSettings.setPath(...)` call and before
`fxstyle._theme = fxstyle._DEFAULT_THEME` (the order matters: the name call
must see the new folder, and the theme reset must come after it).

**Verify**:
- `grep -n "_APP_NAME\|_settings_instance" tests/conftest.py` → no output.
- `...\python.exe -m pytest -q tests/test_fxconfig.py tests/test_fxstyle.py tests/test_fxstyle_default_theme.py tests/test_row_size.py` → all pass.

### Step 6: Add the new tests

Append to `tests/test_fxconfig.py` (add `import os` to its `# Built-in`
imports, and `from fxgui import fxstyle` beside the fxconfig import if you
prefer it at module level). The tests, each a plain function:

```python
def test_a_theme_applied_headless_is_not_saved(qapp):
    from fxgui import fxstyle

    fxstyle.apply_theme("light")
    fxstyle.apply_row_size("small")

    assert fxconfig.get_value("theme/current") is None
    assert fxconfig.get_value("rows/size") is None
    fxstyle.apply_row_size("normal")


def test_save_true_saves_even_headless(qapp):
    from fxgui import fxstyle

    fxstyle.apply_theme("light", save=True)
    fxstyle.apply_row_size("small", save=True)

    assert fxconfig.get_value("theme/current") == "light"
    assert fxconfig.get_value("rows/size") == "small"
    fxstyle.apply_row_size("normal")


def test_a_real_screen_saves_by_default(qapp, monkeypatch):
    from fxgui import fxstyle

    monkeypatch.setattr(fxstyle, "_interactive", lambda: True)
    fxstyle.apply_theme("light")

    assert fxconfig.get_value("theme/current") == "light"


def test_save_false_never_saves(qapp, monkeypatch):
    from fxgui import fxstyle

    monkeypatch.setattr(fxstyle, "_interactive", lambda: True)
    fxstyle.apply_theme("light", save=False)

    assert fxconfig.get_value("theme/current") is None


def test_the_offscreen_platform_counts_as_headless(qapp):
    from fxgui import fxstyle

    assert fxstyle._interactive() is False


def test_an_unchanged_value_is_not_written_again(qapp):
    fxconfig.set_value("probe/key", "value")
    path = fxconfig._settings().fileName()
    os.utime(path, (1_000_000_000, 1_000_000_000))

    fxconfig.set_value("probe/key", "value")
    assert os.path.getmtime(path) == 1_000_000_000

    fxconfig.set_value("probe/key", "other")
    assert os.path.getmtime(path) != 1_000_000_000


def test_a_value_another_process_changed_is_written_back(qapp):
    fxconfig.set_value("probe/key", "mine")
    path = Path(fxconfig._settings().fileName())
    # Another process: a different length and a later time, so Qt sees it.
    path.write_text("[probe]\nkey=theirs\n")
    later = path.stat().st_mtime + 10
    os.utime(path, (later, later))

    fxconfig.set_value("probe/key", "mine")

    assert "key=mine" in path.read_text()


def test_set_application_name_picks_up_a_new_settings_folder(qapp, tmp_path):
    fxconfig.set_value("probe/key", "value")
    folder = tmp_path / "moved"
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(folder))

    fxconfig.set_application_name("fxgui")

    assert Path(fxconfig._settings().fileName()).is_relative_to(folder)
    assert fxconfig.get_value("probe/key") is None
```

The `apply_row_size("normal")` lines put the row size back, as the
`set_row_size` fixture does elsewhere.

**Verify**: `...\python.exe -m pytest -q tests/test_fxconfig.py` → all pass,
8 more tests than before (`--collect-only` reported 12 at the planned-at
commit: 7 plain tests + 5 parametrized cases; it now reports 20).

### Step 7: Update the docs

In `docs/how-to/theming.md`, section "## Switching Themes at Runtime"
(lines 251-269 today): change "It saves the choice, rebuilds" to "It saves
the choice (see below), rebuilds", and replace the `!!! tip` block with:

```markdown
!!! tip
    The choice is saved through `fxconfig`, and the next time the
    application starts, `FXApplication` loads it again. It is saved only
    when a person can have chosen it: on Qt's headless platforms
    (`offscreen`, `minimal`, as in tests and scripts) `apply_theme` does not
    save. Pass `save=True` to save anyway, or `save=False` to never save,
    for example when applying `load_saved_theme()` at startup.
    `apply_row_size` takes the same `save` keyword.
```

**Verify**: `grep -n "save=False" docs/how-to/theming.md` → one match. If
zensical is installed in the venv, `...\python.exe -m zensical build` → exit 0.

### Step 8: Full suite and lint

**Verify**:
- `...\python.exe -m pytest -q -n 8` → `3186 passed, 6 skipped` (3178 + 8 new).
  If the base count today differs from 3178, the expectation is "base + 8".
- `...\ruff.exe check --select F,B,BLE .` → `All checks passed!`

## Test plan

New tests in `tests/test_fxconfig.py` (Step 6), modelled on the existing
tests in that file:

- headless `apply_theme`/`apply_row_size` do not save (the bug);
- `save=True` saves even headless;
- default on a real screen saves (via patching `fxstyle._interactive`);
- `save=False` never saves;
- the `offscreen` platform counts as headless;
- an unchanged value does not rewrite the file (modification time held);
- a value another process changed is still written back (the `sync()`
  before the comparison);
- `set_application_name` after `QSettings.setPath` uses the new folder.

Changed test: `tests/test_row_size.py::test_the_row_size_is_saved_and_read_back`
passes `save=True`.

## Done criteria

- [ ] `...\python.exe -m pytest -q -n 8` exits 0 with base + 8 passed, 6 skipped
- [ ] `...\ruff.exe check --select F,B,BLE .` exits 0
- [ ] `grep -n "save: Optional\[bool\] = None" fxgui/fxstyle.py` → 2 matches
- [ ] `grep -n "_APP_NAME\|_settings_instance" tests/conftest.py` → no output
- [ ] `git status` shows only the six in-scope files modified
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts.
- After Step 1, any test other than
  `test_the_row_size_is_saved_and_read_back` fails: some other test relies on
  headless saving; list them, do not patch them one by one.
- `test_an_unchanged_value_is_not_written_again` fails on the first
  assertion: `QSettings.sync()` rewrites the file even with nothing changed
  on this Qt version; report the PySide6 version
  (`...\python.exe -c "import PySide6; print(PySide6.__version__)"`).
- `test_a_value_another_process_changed_is_written_back` fails: Qt did not
  notice the hand-written change; report, do not drop the `sync()` before
  the comparison.
- Making it work seems to need a change in `_main_window.py`, `examples.py`
  or `save_theme`.

## Maintenance notes

- A future headless platform name (for example `"vnc"`, if someone uses it
  for tests) would need adding to `_HEADLESS_PLATFORMS`.
- Reviewers: check that `save_theme` itself still always saves (it is public),
  and that no fxgui code path now passes `save=True` on its own.
- `set_value` now reads before it writes: a value whose stored form differs
  from the Python value (an `int` read back as `"3"`) is simply written again,
  which is harmless.
- Deferred: scoping the gallery (`python -m fxgui.examples`) to its own
  application name, so demoing it never changes other tools' theme.
- Pascal: `src/ls_pascal/apps/theme.py:76` (`apply_lotchi_theme`) can pass
  `save=False` to `fxstyle.apply_theme(theme)`, so a launch no longer turns
  the studio default into a saved choice; `tests/apps/conftest.py:832`
  sets `APPDATA`, which Qt ignores, and can instead call
  `QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, <tmp>)` before
  its existing `fxconfig.set_application_name("fxgui")` (line 833).
