# Plan 018: CI tests every platform, binding and version floor fxgui claims

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- .github/workflows/tests.yml pyproject.toml README.md docs/installation.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none (plan 017 edits `release.yml` and other README lines;
  plan 007 adds `mypy` to the `test` extra — both compatible with this plan)
- **Category**: tests
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

fxgui says it supports PyQt6, Python 3.9 and up, and dependency floors
`QtPy>=2.4.2`, `PyYAML>=6.0`, `Pygments>=2.0`. CI checks none of that: it
runs only on Linux, only with PySide6, only on Python 3.11 and 3.12, with the
newest dependencies. So the PyQt6-only code branches have never run, and a
user on Python 3.9 or with an old Pygments may get a broken install that CI
would have caught. Pascal, fxgui's main consumer, is a Windows pipeline, yet
fxgui's Windows-only code (rounded window corners, the taskbar application
id) runs in CI only under monkeypatches (tests that fake `sys.platform`).
Also, a release tag runs the whole suite twice.

After this plan, CI has a Windows row, a PyQt6 row and a "floors" row (the
oldest Python and dependency versions `pyproject.toml` accepts), each proved
green locally first; any row that cannot be made green goes to the operator
with the failure list and a choice (fix later, or stop claiming it). A tag
push runs the suite once.

**Public behaviour that changes**: none in the package, unless the operator
picks the "drop the claim" or "raise the floor" option (then the docs and
`pyproject.toml` change, listed below).

## Current state

Files:

- `.github/workflows/tests.yml` — the only test workflow; also called by
  `release.yml` (`release.yml:185-187`, `uses: ./.github/workflows/tests.yml`).
- `pyproject.toml` — `requires-python` and dependency floors (lines 39-46),
  Python classifiers (lines 33-37), `test` extra (lines 59-71).
- `README.md:73-74`, `docs/installation.md:13-14`, `docs/moving-from-12.md:15`,
  `pyproject.toml:18` (keywords), `fxgui/__init__.py:30` (error message) —
  where PyQt6 support is claimed.

```yaml
# .github/workflows/tests.yml (whole file, 59 lines)
name: Tests

on:
  push:
  pull_request:
  workflow_dispatch:
  workflow_call:

jobs:
  pytest:
    name: pytest (${{ matrix.name }}, offscreen)
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          # Python 3.12: PySide6 6.12.0 frees None on 3.11 (each void call
          # drops a reference) and aborts a long run; pyproject excludes it.
          - name: latest PySide6, docking
            extras: test
            pin: PySide6-QtAds
            python: "3.12"
          # Houdini 21's PySide6: nothing newer may slip in. No docking:
          # no QtAds wheel was built for it.
          - name: PySide6 6.5.3
            extras: test
            pin: PySide6==6.5.3
            python: "3.11"
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}

      # Qt's offscreen platform still loads EGL, GL and fontconfig.
      - name: Install Qt system libraries
        run: |
          sudo apt-get update
          sudo apt-get install -y libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3

      - name: Install fxgui with the ${{ matrix.extras }} extras
        run: |
          python -m pip install --upgrade pip
          pip install ".[${{ matrix.extras }}]" ${{ matrix.pin }}

      - name: Lint
        run: |
          pip install ruff
          ruff check --select F,B,BLE .

      - name: Run tests
        env:
          QT_QPA_PLATFORM: offscreen
        run: python -m pytest -q
```

`on: push:` with no filter fires for branch pushes **and tag pushes**; a
`v*.*.*` tag also starts `release.yml`, which calls this workflow again.

```toml
# pyproject.toml:39-46
requires-python = ">=3.9"
# A Qt 6 binding is required but not listed: a DCC ships its own PySide6,
# and a second one installed beside it breaks the host.
dependencies = [
    "QtPy>=2.4.2",
    "PyYAML>=6.0",
    "Pygments>=2.0",
]
```

The `test` extra (`pyproject.toml:59-71`) installs **PySide6** besides the
pytest plugins. So a PyQt6 row must not use it: with PySide6 also present,
pytest-qt picks PySide6 while qtpy may pick PyQt6, and tests that import
`shiboken6` (`tests/test_singleton.py:22`, `tests/test_framed_window.py:295`,
`tests/test_frame_controls.py:339`) would run against PyQt6 objects. With
PyQt6 alone, those tests and the docking tests skip on their own
(`pytest.importorskip("shiboken6")`, `pytest.importorskip("PySide6QtAds")`,
`tests/test_fxdocking.py:12`), and `tests/test_binding_floor.py:12` skips
when the binding is not PySide6.

PyQt6-only branches that never run in CI today:

```python
# fxgui/_compat.py:31-48
try:
    # PySide6
    from qtpy.shiboken import createdByPython as created_by_python
    from qtpy.shiboken import isValid as is_valid  # noqa: F401

except ImportError:
    # PyQt6: every wrapper is filed where Qt files its object.
    from qtpy.sip import isdeleted as _isdeleted

    created_by_python = None

    def is_valid(obj) -> bool:
        """Return `True` if the underlying C++ object is still alive."""
        try:
            return not _isdeleted(obj)
        except TypeError:
            # Not a sip-wrapped object; assume alive.
            return True
```

```python
# fxgui/fxutils.py:111-120
    try:
        # Not shipped by PyQt6, hence the deferred import.
        from qtpy.QtUiTools import QUiLoader
    except ImportError:
        from qtpy.uic import loadUi

        loaded_ui = loadUi(ui_file)
        loaded_ui.setParent(parent)
        return loaded_ui
    return QUiLoader().load(str(ui_file), parent)
```

Facts checked on PyPI on 2026-11-14:

- `PySide6` / `PySide6-Essentials` 6.5.3: `requires_python <3.12,>=3.7`,
  `cp37-abi3` wheels for Linux x86_64, Windows and macOS: **they install on
  Python 3.9**, so a Python 3.9 row with Houdini 21's PySide6 is possible.
- `PyQt6` 6.12.1: `requires_python >=3.10`, `cp310-abi3` wheels: the PyQt6
  row uses Python 3.12.
- `PySide6-QtAds` 5.1.1.1: `requires_python >=3.10`, requires exactly
  `PySide6-Essentials==6.12.0`, has `win_amd64` wheels: the Windows row can
  include docking on Python 3.12, like the Linux docking row.
- `PyYAML` 6.0 has `cp39` wheels (Linux, Windows); `Pygments` 2.0 is a
  pure-Python `py3-none-any` wheel.
- Static check: every file in `fxgui/` and `tests/` parses as Python 3.9
  (`ast.parse(..., feature_version=(3, 9))`); no `X | None` annotations, no
  `match` statements. Runtime behaviour on 3.9 and on the floors is
  **unknown** until the local runs in Steps 3-4.

Local tools on the planning machine: the project venv runs Windows,
Python 3.11.9, PySide6 6.11.2, QtPy 2.4.3, PyYAML 6.0.3, Pygments 2.21.0,
with `PySide6QtAds` (so `3178 passed, 6 skipped` there is already a Windows
run). No PyQt6 in it. `uv` 0.13.5 is installed (`uv venv --python 3.9`
downloads a managed CPython 3.9 when none is installed; only 3.10-3.13 are
installed system-wide). `actionlint` is not installed.

## Commands you will need

Run everything from the worktree root (so the worktree's `fxgui` is
imported first). `PY` means
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe`.
Throwaway venvs go under `%TEMP%` (Git Bash: `$TEMP`) and are deleted at the
end; never install anything into the project venv.

| Purpose | Command | Expected on success |
|---|---|---|
| YAML parses | `PY -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yml', encoding='utf-8')); print('ok')"` | `ok` |
| Project-venv suite | `PY -m pytest -q -n 8` | `3178 passed, 6 skipped` |
| Make a throwaway venv | `uv venv --python <X.Y> %TEMP%\fxgui-018-<row>` | exit 0 |
| Install into it | `uv pip install --python %TEMP%\fxgui-018-<row>\Scripts\python.exe <the row's install args>` | exit 0 |
| Run a row | `%TEMP%\fxgui-018-<row>\Scripts\python.exe -m pytest -q -n 8 -rfE` | `N passed, M skipped`, no `failed`/`error` |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

`tests/conftest.py` forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test; never override it (the real platform moves the owner's pointer).

## Scope

**In scope**:

- `.github/workflows/tests.yml`
- Only if the operator picks it at a STOP: `pyproject.toml` (floors,
  `requires-python`, classifiers, keywords), and the PyQt6 claim lines in
  `README.md:73-74`, `docs/installation.md:13-14`, `docs/moving-from-12.md:15`,
  `fxgui/__init__.py:30`.

**Out of scope** (do NOT touch):

- `.github/workflows/release.yml` — plan 017 owns it; its `tests:` job keeps
  calling `tests.yml`.
- Fixing PyQt6 or Python 3.9 failures in fxgui's code — if the rows fail,
  that is a follow-up plan the operator decides on.
- macOS rows — fxgui claims no macOS-specific code; not requested.
- `CHANGELOG.md`.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists.
- Branch: `fix/ci-covers-claims`.
- Commits in the repo style, e.g. `[BUILD] tests: Windows, PyQt6 and floor rows; no second run on a tag`.
- Do not push: the operator pushes and reads the first CI run, which is the
  final proof for the Linux rows.

## Steps

### Step 1: Stop the tag-push double run

In `tests.yml`, replace lines 3-7 with:

```yaml
on:
  # Branches only: a release tag runs these tests through release.yml.
  push:
    branches: ["**"]
  pull_request:
  workflow_dispatch:
  workflow_call:
```

(GitHub rule: when a `push` trigger lists only `branches`, tag pushes do not
start it.)

**Verify**: YAML parse → `ok`;
`PY -c "import yaml; print(yaml.safe_load(open('.github/workflows/tests.yml', encoding='utf-8'))[True]['push'])"`
→ `{'branches': ['**']}` (PyYAML reads the key `on` as `True`).

### Step 2: One `install` string and an `os` per row; add the Windows row

Rewrite the job header and matrix (lines 10-28) and the install step
(lines 46-49). Target:

```yaml
jobs:
  pytest:
    name: pytest (${{ matrix.name }}, offscreen)
    runs-on: ${{ matrix.os }}
    defaults:
      run:
        shell: bash
    strategy:
      fail-fast: false
      matrix:
        include:
          # Python 3.12: PySide6 6.12.0 frees None on 3.11 (each void call
          # drops a reference) and aborts a long run; pyproject excludes it.
          - name: latest PySide6, docking
            os: ubuntu-latest
            python: "3.12"
            install: '".[test]" PySide6-QtAds'
          # Houdini 21's PySide6: nothing newer may slip in. No docking:
          # no QtAds wheel was built for it.
          - name: PySide6 6.5.3
            os: ubuntu-latest
            python: "3.11"
            install: '".[test]" PySide6==6.5.3'
          # Pascal runs on Windows: the Windows-only paths run for real here.
          - name: Windows, latest PySide6, docking
            os: windows-latest
            python: "3.12"
            install: '".[test]" PySide6-QtAds'
```

and the steps:

```yaml
      # Qt's offscreen platform still loads EGL, GL and fontconfig.
      - name: Install Qt system libraries
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3

      - name: Install fxgui
        run: |
          python -m pip install --upgrade pip
          pip install ${{ matrix.install }}
```

Keep `Checkout`, `Set up Python`, `Lint` and `Run tests` as they are.

Local proof for the Windows row (the project venv is already Windows,
PySide6 6.11.2 with QtAds; CI will resolve PySide6 6.12.0 on Python 3.12, so
mirror it):

```
uv venv --python 3.12 %TEMP%\fxgui-018-win
uv pip install --python %TEMP%\fxgui-018-win\Scripts\python.exe ".[test]" PySide6-QtAds
%TEMP%\fxgui-018-win\Scripts\python.exe -m pytest -q -n 8 -rfE
```

**Verify**:
- YAML parse → `ok`.
- The local Windows run ends with `passed` and a `skipped` count, no
  `failed` or `error`. Note the exact counts for the report.
- `PY -c "import yaml; m=yaml.safe_load(open('.github/workflows/tests.yml', encoding='utf-8'))['jobs']['pytest']['strategy']['matrix']['include']; print([(r['name'], r['os'], r['python']) for r in m])"`
  → the three rows above.

### Step 3: The PyQt6 row (proved locally first)

Local run:

```
uv venv --python 3.12 %TEMP%\fxgui-018-pyqt6
uv pip install --python %TEMP%\fxgui-018-pyqt6\Scripts\python.exe . PyQt6 pytest pytest-qt pytest-randomly pytest-xdist
%TEMP%\fxgui-018-pyqt6\Scripts\python.exe -c "import qtpy; print(qtpy.API_NAME)"
%TEMP%\fxgui-018-pyqt6\Scripts\python.exe -m pytest -q -n 8 -rfE
```

The `qtpy.API_NAME` line must print `PyQt6`; if it prints anything else,
STOP.

- **If the run is green** (no `failed`, no `error`): add the row to the
  matrix:

  ```yaml
          # PyQt6 alone: the test extra would bring PySide6 beside it.
          - name: PyQt6
            os: ubuntu-latest
            python: "3.12"
            install: '. PyQt6 pytest pytest-qt pytest-randomly pytest-xdist'
  ```

- **If it fails**: do NOT add the row and do NOT fix fxgui code. Save the
  `-rfE` summary (the `FAILED ...` / `ERROR ...` lines), group them by cause
  (first line of each traceback), and STOP for the operator with two options:
  1. *Keep the PyQt6 claim*: a follow-up plan fixes the listed failures,
     then adds the row above.
  2. *Drop the PyQt6 claim*: change "PySide6 6.5 or newer, or PyQt6" to
     "PySide6 6.5 or newer" in `README.md:73-74`, `docs/installation.md:13-14`,
     `docs/moving-from-12.md:15` and the `ImportError` text at
     `fxgui/__init__.py:30` (then `tests/test_package_layout.py` still passes:
     it checks only for "Qt 6"); remove `"PyQt6"` from the keywords at
     `pyproject.toml:18`. The PyQt6 code branches can stay (harmless).
  Carry on with Step 4 and Step 5 meanwhile; they do not depend on this.

**Verify**: green run and row added, or the STOP report written with the
failure list.

### Step 4: The floors row (Python 3.9 and the lowest dependencies)

Local run:

```
uv venv --python 3.9 %TEMP%\fxgui-018-floors
uv pip install --python %TEMP%\fxgui-018-floors\Scripts\python.exe ".[test]" PySide6==6.5.3 QtPy==2.4.2 PyYAML==6.0 Pygments==2.0
%TEMP%\fxgui-018-floors\Scripts\python.exe -c "import sys, qtpy, yaml, pygments, PySide6; print(sys.version_info[:2], qtpy.__version__, yaml.__version__, pygments.__version__, PySide6.__version__)"
%TEMP%\fxgui-018-floors\Scripts\python.exe -m pytest -q -n 8 -rfE
```

The version line must print `(3, 9) 2.4.2 6.0 2.0 6.5.3`; if pip resolved
something else, STOP and report what it resolved.

- **If the run is green**: add the row:

  ```yaml
          # The oldest Python and dependencies pyproject.toml accepts.
          - name: floors, Python 3.9
            os: ubuntu-latest
            python: "3.9"
            install: '".[test]" PySide6==6.5.3 QtPy==2.4.2 PyYAML==6.0 Pygments==2.0'
  ```

- **If it fails**: do not add the row; find which floor breaks by
  re-running with one floor at a time lifted to the project venv's version
  (`QtPy==2.4.3`, `PyYAML==6.0.3`, `Pygments==2.21.0`), and, if all three
  lifted still fail, Python itself (`uv venv --python 3.10`, same pins).
  For a failing Pygments floor also try `Pygments==2.10.0` and
  `Pygments==2.15.0` to give the operator a candidate floor. Then STOP for
  the operator with the evidence and the options:
  1. *Raise the floor(s)* in `pyproject.toml:42-46` to the lowest version
     that passed, and add the row with those pins (recommended: the floor
     then means something).
  2. *Raise `requires-python`* to `">=3.10"` (and drop
     `"Programming Language :: Python :: 3.9"`, `pyproject.toml:34`) if
     Python 3.9 itself is the cause; the row then uses Python 3.10.
  Raising a floor can break a vendor whose DCC ships an older package, so
  the operator decides.

**Verify**: green run and row added, or the STOP report written.

### Step 5: Lint and final checks

**Verify**:
- YAML parse → `ok`; `actionlint .github/workflows/tests.yml` if installed
  (not installed on the planning machine: skip and say so; do not install it).
- `...\ruff.exe check --select F,B,BLE .` → `All checks passed!`
- `PY -m pytest -q -n 8` → `3178 passed, 6 skipped` (unchanged).
- `git status --porcelain` → only `.github/workflows/tests.yml` (plus the
  operator-chosen files, if any).
- Delete the throwaway venvs: `%TEMP%\fxgui-018-win`, `-pyqt6`, `-floors`.

## Test plan

No new test files: the change is the CI matrix. Each new row is proved by a
local run of the whole suite in a throwaway venv that installs exactly what
the row installs (Steps 2-4); the Linux rows' final proof is the first CI run
after the operator pushes. Expected skips per row: docking tests skip
wherever `PySide6QtAds` is absent (PySide6 6.5.3, PyQt6 and floors rows);
`shiboken6` tests and `test_binding_floor.py` skip in the PyQt6 row; the
plan-007 mypy tests (if 007 landed) skip in the PyQt6 row, which installs no
mypy.

## Done criteria

- [ ] `tests.yml` push trigger is `branches: ["**"]` only (Step 1 print)
- [ ] The matrix has the Windows row; the PyQt6 and floors rows are present,
      or the report holds their failure lists and the operator's options
- [ ] Every row added was green locally, with its pass/skip counts in the report
- [ ] `ruff check --select F,B,BLE .` exits 0; project-venv suite unchanged
- [ ] Throwaway venvs deleted; the project venv untouched
- [ ] `plans/2026-11-14-audit/README.md` status row updated (BLOCKED with a
      one-line reason if a row waits on the operator)

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts.
- The PyQt6 or floors local run fails (see Steps 3-4: report, give the
  options, do not fix fxgui code and do not add the row).
- In the PyQt6 venv `qtpy.API_NAME` is not `PyQt6`, or pip installed
  PySide6 into it.
- `uv venv --python 3.9` cannot get a Python 3.9: report it; the floors row
  then waits on the operator (they may choose option 2 of Step 4).
- The local Windows run (Step 2) fails: CI would go red on Windows; report
  the failures instead of adding the row.
- A change seems to need `release.yml`.

## Maintenance notes

- A new optional dependency or binding-specific test must think about the
  PyQt6 row: it installs no extras, so anything new in the `test` extra is
  absent there (use `pytest.importorskip`).
- When the PySide6 floor moves (a new Houdini), update the `PySide6 6.5.3`
  and floors rows together.
- The floors row pins exact versions; raising a floor in `pyproject.toml`
  must raise the pin in that row in the same commit.
- Each row runs the linter; that repetition is harmless and out of scope.
- Reviewers: check the Windows row's `defaults.run.shell: bash` (the install
  line's quoting relies on it) and that `apt-get` is guarded by
  `runner.os == 'Linux'`.
- Pascal: nothing to delete; Pascal can rely on fxgui's Windows-only code
  being tested on Windows, and stop treating those paths as untested in its
  own reviews.
