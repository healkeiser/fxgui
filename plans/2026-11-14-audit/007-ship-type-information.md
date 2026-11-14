# Plan 007: fxgui ships its type information, and a type checker reads it

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/__init__.py pyproject.toml MANIFEST.in tests/test_package_layout.py`
> and `git ls-files fxgui/py.typed tests/test_type_information.py` (expect no
> output: neither exists yet).
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

fxgui's code is fully annotated, but it does not ship a `py.typed` file.
`py.typed` is an empty marker file defined by PEP 561 (the Python standard for
"this installed package carries its own types"). Without it, a type checker
such as mypy refuses to read an installed package: it reports
`import-untyped`, and everything imported from fxgui becomes `Any` (no type
at all). So consumers get no checking of their fxgui calls, and their own
annotations around fxgui are guesses. Pascal, fxgui's main consumer, works
around it today with `ignore_missing_imports` for `fxgui.*` and three
`# type: ignore[misc]` comments.

After this plan, the marker ships in the wheel and the sdist, a hidden
typing trap in `fxgui/__init__.py` is closed, and a test proves a type
checker sees fxgui's real types.

**Public behaviour that changes**: none at runtime. Type checkers of
consumers now read fxgui's annotations, so a consumer running mypy may see
new, real errors in its own code (that is the point). fxgui itself is NOT
made mypy-clean (mypy over all of fxgui reports roughly 981 errors today,
mostly short Qt enum names such as `QIcon.Normal` that qtpy provides at
runtime); errors inside an installed package are not shown to consumers.

## Current state

Files:

- `fxgui/__init__.py` — package root; defines a module-level `__getattr__`
  for a lazy `__version__` (lines 62-74).
- `pyproject.toml` — packaging; package-data globs at lines 85-86; the `test`
  extra at lines 59-71.
- `MANIFEST.in` — sdist contents (lines 1-7 include package resources).
- `tests/test_package_layout.py` — packaging tests; the pattern for the new
  test file (plain functions, `subprocess.run([sys.executable, ...])`).
- `fxgui/py.typed` — does not exist.

```python
# fxgui/__init__.py:62-77
def __getattr__(name: str) -> str:
    """Read `__version__` on first ask: importlib.metadata costs 30 ms."""
    if name != "__version__":
        raise AttributeError(f"module 'fxgui' has no attribute {name!r}")
    from importlib.metadata import PackageNotFoundError, version

    try:
        found = version("fxgui")
    except PackageNotFoundError:
        # A source tree that was never installed.
        found = "0.0.0.dev"
    globals()["__version__"] = found
    return found

__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"
```

**The trap**: a module-level `__getattr__(name) -> str` tells a type checker
"any attribute of this module exists and is a `str`". Once fxgui is typed,
mypy would accept a misspelled `fxgui.fxwidget` (or any name) as a `str`
with no error. Verified with mypy 2.4.0: `reveal_type(fxgui.no_such_name)`
gives `"str"` and no error. Hiding `__getattr__` from type checkers behind
`TYPE_CHECKING` (a constant that is `True` only while a type checker reads
the code, `False` at runtime) and declaring only `__version__: str` fixes it:
the same probe then reports `Module has no attribute "no_such_name"
[attr-defined]`, while runtime behaviour is unchanged.

```toml
# pyproject.toml:59-71
test = [
    "pytest>=7.0",
    "pytest-qt>=4.2",
    # Every run shuffles the order, so a test leaning on another fails.
    "pytest-randomly>=3.0",
    # `-n 8` runs the suite in about a quarter of the serial time.
    "pytest-xdist>=3.0",
    # The oldest PySide6 fxgui supports is Houdini 21's 6.5.3.
    "PySide6>=6.5; sys_platform != 'linux' or python_version >= '3.12'",
    # Linux 6.12.0 drops a reference to None on every enum it hands a Python
    # override; before 3.12 None can be freed, and Python aborts.
    "PySide6>=6.5,!=6.12.0; sys_platform == 'linux' and python_version < '3.12'",
]
```

```toml
# pyproject.toml:85-86
[tool.setuptools.package-data]
"*" = ["*.yaml", "*.svg", "*.png", "*.qss", "*.zip"]
```

```
# MANIFEST.in:1-7
# Only include Python source and package resources from fxgui package
recursive-include fxgui *.py
recursive-include fxgui *.yaml
recursive-include fxgui *.svg
recursive-include fxgui *.png
recursive-include fxgui *.qss
recursive-include fxgui *.zip
```

Packaging fact (verified by building a scratch clone with a committed
`fxgui/py.typed`, 2026-11-14): the build uses `setuptools_scm`, whose file
finder already includes every git-tracked file, so the marker shipped in both
the wheel (`fxgui/py.typed`) and the sdist even without listing it. This plan
still lists it in `pyproject.toml` and `MANIFEST.in`, so it does not depend on
that plugin. The file **must be committed (or at least `git add`ed) before
building**, or the finder does not see it.

How a type checker is shown fxgui "as installed" (verified with mypy 2.4.0):
put the folder that contains `fxgui/` on `PYTHONPATH` and run mypy from a
working directory that does **not** contain `fxgui/`. mypy then treats it like
site-packages and honours (or demands) `py.typed`. If mypy runs from the repo
root, it reads `fxgui/` as plain source and the test would pass even without
the marker. The venv's own fxgui is an editable install through an import
hook, which mypy cannot follow; `PYTHONPATH` avoids it. A check of one small
consumer file takes about 2 seconds.

Conventions: Google-style docstrings; Qt only through `qtpy`; tests are plain
functions named as sentences; subprocess tests look like
`tests/test_package_layout.py::test_importing_fxgui_on_qt5_says_it_needs_qt6`.

## Commands you will need

Run everything from the worktree root. `PY` below means
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe`.

| Purpose | Command | Expected on success |
|---|---|---|
| Install mypy in the venv (once) | `PY -m pip install "mypy>=1.8"` | exit 0. Only this; never `pip install -e .` (it would repoint the venv's editable install, which serves another checkout) |
| New test file | `PY -m pytest -q tests/test_type_information.py` | `3 passed` |
| Whole suite | `PY -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it `3181 passed, 6 skipped` |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |
| Build | `PY -m build -o <scratch>\dist .` (`<scratch>` = a new empty temp folder outside the repo) | `Successfully built fxgui-<version>.tar.gz and fxgui-<version>-py3-none-any.whl` (needs network: it fetches setuptools and setuptools_scm into an isolated build environment) |

Never run tests on the real Qt platform: `tests/conftest.py` forces
`offscreen`; do not override it.

## Scope

**In scope** (the only files you should modify or create):

- `fxgui/py.typed` (create, empty)
- `fxgui/__init__.py` (guard `__getattr__`)
- `pyproject.toml` (package-data glob; `mypy` in the `test` extra)
- `MANIFEST.in` (one `include` line)
- `tests/test_type_information.py` (create)

**Out of scope** (do NOT touch):

- Any type error inside fxgui itself (the ~981 mypy reports). Making fxgui
  mypy-clean is a separate, large job; consumers do not see those errors.
- Adding mypy to CI as a check over fxgui's own code.
- `.github/workflows/*` — the new test runs in the existing pytest job,
  since `mypy` joins the `test` extra the workflow installs.
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists.
- Branch: `feat/ship-type-information`.
- Commits in the repo style, e.g. `[FEAT] Ship py.typed: consumers' type checkers read fxgui`
  and `[FIX] __getattr__ no longer types every fxgui attribute as str`.
- Do not push, tag or release: the operator does.

## Steps

### Step 1: Guard the lazy `__version__` from type checkers

In `fxgui/__init__.py`, replace lines 62-74 (the whole `def __getattr__`
function) with:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # A module __getattr__ would type every misspelled fxgui.<name> as str.
    __version__: str
else:

    def __getattr__(name: str) -> str:
        """Read `__version__` on first ask: importlib.metadata costs 30 ms."""
        if name != "__version__":
            raise AttributeError(f"module 'fxgui' has no attribute {name!r}")
        from importlib.metadata import PackageNotFoundError, version

        try:
            found = version("fxgui")
        except PackageNotFoundError:
            # A source tree that was never installed.
            found = "0.0.0.dev"
        globals()["__version__"] = found
        return found
```

Put `from typing import TYPE_CHECKING` with the other imports instead if you
prefer: under a `# Built-in` comment above `# Third-party` / `import qtpy`
(line 25), following the file's import grouping. Leave `__author__` and
`__email__` as they are.

**Verify**:
- `PY -m pytest -q tests/test_package_layout.py` → all pass (it checks
  `fxgui.__version__` and the lazy import).
- `PY -c "import os; os.environ['QT_QPA_PLATFORM']='offscreen'; import fxgui; print(fxgui.__version__); fxgui.nope"` →
  prints a version, then `AttributeError: module 'fxgui' has no attribute 'nope'`.
  (Run from the worktree root so its `fxgui` is imported; check the printed
  traceback path is under the worktree.)

### Step 2: Add the marker and list it in the packaging

1. Create `fxgui/py.typed` as an empty file (zero bytes).
2. In `pyproject.toml:86`, append `"py.typed"`:
   `"*" = ["*.yaml", "*.svg", "*.png", "*.qss", "*.zip", "py.typed"]`
3. In `MANIFEST.in`, after line 7 (`recursive-include fxgui *.zip`), add:
   `include fxgui/py.typed`
4. In `pyproject.toml`, `test` extra, after the `pytest-xdist` line, add:

   ```toml
       # tests/test_type_information.py checks consumers see fxgui's types.
       "mypy>=1.8",
   ```

5. `git add fxgui/py.typed` and commit Steps 1-2.

**Verify**: `git ls-files fxgui/py.typed` → `fxgui/py.typed`; and
`PY -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['tool']['setuptools']['package-data'])"`
→ `{'*': ['*.yaml', '*.svg', '*.png', '*.qss', '*.zip', 'py.typed']}`.

### Step 3: Build and check the marker ships

Make a new empty folder outside the repo, e.g. `%TEMP%\fxgui-007-dist`, then:

```
PY -m build -o %TEMP%\fxgui-007-dist .
PY -c "import glob,zipfile,tarfile,os; d=os.path.expandvars(r'%TEMP%\fxgui-007-dist'); print([n for n in zipfile.ZipFile(glob.glob(d+r'\*.whl')[0]).namelist() if n.endswith('py.typed')]); print([n for n in tarfile.open(glob.glob(d+r'\*.tar.gz')[0]).getnames() if n.endswith('py.typed')])"
```

(In Git Bash, use `"$TEMP/fxgui-007-dist"` instead of `%TEMP%\...`.)

**Verify**: the build ends with `Successfully built ...`; the second command
prints `['fxgui/py.typed']` then `['fxgui-<version>/fxgui/py.typed']`.
If the build fails only because there is no network, note it in your report
and continue (the test in Step 4 still proves the marker works); delete the
temp folder afterwards.

### Step 4: Add the consumer type check

Install mypy in the venv once: `PY -m pip install "mypy>=1.8"`.

Create `tests/test_type_information.py`:

```python
"""fxgui ships its type information (PEP 561), and a type checker reads it."""

# Built-in
import os
import re
import subprocess
import sys
from pathlib import Path

# Third-party
import pytest

# Internal
import fxgui

ROOT = Path(fxgui.__file__).resolve().parent.parent


def _mypy(tmp_path: Path, source: str) -> str:
    """Return mypy's report on `source`, with fxgui seen as installed."""
    pytest.importorskip("mypy")
    consumer = tmp_path / "consumer.py"
    consumer.write_text(source)
    # On PYTHONPATH fxgui counts as installed, so mypy reads it only through
    # py.typed; run elsewhere, or mypy reads fxgui/ as plain source.
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    result = subprocess.run(
        [
            sys.executable, "-m", "mypy", "--no-incremental",
            "--python-executable", sys.executable, str(consumer),
        ],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    return result.stdout + result.stderr


def test_the_package_carries_the_py_typed_marker():
    assert (ROOT / "fxgui" / "py.typed").is_file()


def test_a_type_checker_sees_fxguis_own_types(tmp_path):
    report = _mypy(
        tmp_path,
        "from fxgui import fxstyle\n"
        "from fxgui.fxwidgets import FXMainWindow\n"
        "reveal_type(fxstyle.get_theme())\n"
        "reveal_type(FXMainWindow)\n",
    )
    assert "import-untyped" not in report, report
    assert 'Revealed type is "Any"' not in report, report
    assert report.count("Revealed type is") == 2, report


def test_a_misspelled_fxgui_attribute_is_a_type_error(tmp_path):
    report = _mypy(
        tmp_path,
        "import fxgui\n"
        "reveal_type(fxgui.__version__)\n"
        "fxgui.no_such_name\n",
    )
    assert re.search(r'Revealed type is "(builtins\.)?str"', report), report
    assert 'has no attribute "no_such_name"' in report, report
```

**Verify**: `PY -m pytest -q tests/test_type_information.py` → `3 passed`.
Then prove each test can fail:
- temporarily rename `fxgui/py.typed` to `fxgui/py.typed.off` → the first two
  tests fail (the second with `import-untyped` in its report); rename it back;
- temporarily restore the unguarded `__getattr__` (`git stash` is shared with
  other sessions: instead copy the old function from
  `git show b283eb13:fxgui/__init__.py` by hand) → the third test fails;
  restore the guard.
After restoring: `3 passed` again.

### Step 5: Full suite and lint

**Verify**:
- `PY -m pytest -q -n 8` → `3181 passed, 6 skipped` (base 3178 + 3). If the
  base count differs today, expect base + 3.
- `...\ruff.exe check --select F,B,BLE .` → `All checks passed!`
- `git status` → only the five in-scope paths changed or added.

## Test plan

New file `tests/test_type_information.py` (pattern:
`tests/test_package_layout.py`):

- the marker exists in the package;
- a consumer file checked by mypy, with fxgui found as an installed package,
  reports no `import-untyped` and no `Any` for `fxstyle.get_theme()` and
  `FXMainWindow` (proves `py.typed` works);
- `fxgui.__version__` is `str` and a misspelled `fxgui.no_such_name` is an
  `attr-defined` error (proves the `__getattr__` guard).

The two mypy tests skip when mypy is not installed (`pytest.importorskip`);
CI installs it through the `test` extra.

## Done criteria

- [ ] `git ls-files fxgui/py.typed` prints `fxgui/py.typed`
- [ ] `PY -m pytest -q tests/test_type_information.py` → `3 passed` (none skipped)
- [ ] `PY -m pytest -q -n 8` exits 0 with base + 3 passed, 6 skipped
- [ ] `ruff check --select F,B,BLE .` exits 0
- [ ] The built wheel lists `fxgui/py.typed` (Step 3), or the report says the build could not reach the network
- [ ] `git status` shows only in-scope files changed
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts.
- `test_a_type_checker_sees_fxguis_own_types` reports errors other than
  reveal notes (for example errors inside fxgui's files): mypy is reading
  fxgui as source, not as installed. Check the working directory is
  `tmp_path` and report; do not start fixing fxgui's own type errors.
- The build in Step 3 succeeds but the wheel does not contain
  `fxgui/py.typed`.
- Guarding `__getattr__` breaks a test in `tests/test_package_layout.py`
  (runtime `fxgui.__version__` must behave exactly as before).
- Installing mypy into the venv would upgrade or downgrade PySide6, qtpy or
  pytest (read pip's output): stop before confirming.

## Maintenance notes

- New module-level names in `fxgui/__init__.py` that are computed lazily must
  be declared in the `TYPE_CHECKING` branch too, or type checkers will not
  know them.
- Every public annotation is now part of the contract consumers type-check
  against: a loosened or wrong annotation is a visible change for them.
- Deferred: making fxgui itself mypy-clean and adding a mypy job to CI.
- Reviewers: check `fxgui/py.typed` is in the commit, and that no runtime
  import moved under `TYPE_CHECKING`.
- Pascal: once this ships, Pascal can drop `"fxgui.*"` from its
  `ignore_missing_imports` override (`pyproject.toml:579` on origin/main) and
  delete the three `# type: ignore[misc]` with their "fxgui has no stubs"
  comments (`src/ls_pascal/apps/views/tree.py:251-252`,
  `src/ls_pascal/apps/widgets/rows.py:153-154`,
  `src/ls_pascal/apps/hub/views/detail_blocks.py:844-845`); a probe with
  `--strict` showed `class X(FXKeyboardTree, QTreeWidget)` checks clean, so
  under `warn_unused_ignores` those ignores become errors and must go in the
  same Pascal change. Expect some new, real mypy findings in Pascal code.
