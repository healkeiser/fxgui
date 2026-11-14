# Plan 012: No disk check waits behind a dead share, and the drop zone never reads the disk on the UI thread

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/_compat.py fxgui/fxwidgets/_file_path_widget.py fxgui/fxwidgets/_drop_zone.py fxgui/fxwidgets/_path_check.py tests/test_file_path_widget.py tests/test_drop_zone.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. (`fxgui/_compat.py` may have
> changed if plan 022 landed first: that is expected, see STOP conditions.)

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: none (plan 022 complements it; either order works)
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`FXFilePathWidget` checks a path on a worker thread, at most 4 threads at
once (`_THREAD_CAP`). When 4 checks hang on a dead network share, every new
check waits in a queue — local ones too, because a typed path always goes to
a thread. Measured: with 4 checks stuck on a dead share, a local file was not
validated within 1 s. So one dead share can freeze the validity mark of every
path field in the application.

`FXDropZone` is worse: it reads the disk on the UI thread. It calls
`exists()`, `is_dir()`, `is_file()` on every drag-enter and every drop, and
`is_dir()` plus `stat()` for every listed file each time a file is added
(it rebuilds the whole list). On a dead share, a drag over the zone freezes
the window. Adding N files one by one also costs O(N²) disk reads and an
O(N²) duplicate scan.

After this plan: the thread cap only counts checks that may stall (network
paths), so local checks never queue behind dead shares. The drop zone decides
a drag by name only, checks dropped paths through the same shared helper as
the path field (off the UI thread for a share), adds rows instead of
rebuilding, and finds duplicates with a dictionary. `FXFilePathWidget` also
gets `paths()` / `set_paths()` so a file name containing `;` survives
"files" mode.

**Public behaviour that changes**:

- `FXDropZone`: a drag is accepted by name (local URL, extension), not by a
  disk read. A folder dragged over a "files" zone with no extension filter,
  or a file dragged over a "folders" zone, now shows the "can drop" cursor
  and is refused at the drop with the error flash (before: refused at
  drag-enter). A drop of share paths is added when the check answers (a
  moment later), not inside `dropEvent`.
- `FXDropZone.set_files` drops duplicate paths (before: kept them).
- `FXFilePathWidget`: new `paths()` and `set_paths()`; `path()`/`set_path()`
  and the `path_changed` signal are unchanged.

## Current state

Files:

- `fxgui/_compat.py` — `can_stall(path)` (lines 63-70): whether reading
  `path` may wait on a network share. UNC paths always; on Windows, a drive
  Windows reports as remote.
- `fxgui/fxwidgets/_file_path_widget.py` — `FXFilePathWidget` and today's
  thread machinery (`_Relay`, `_deliver`, `_work`, `_check`, lines 52-118).
- `fxgui/fxwidgets/_drop_zone.py` — `FXDropZone`, all disk reads on the UI
  thread.
- `tests/test_file_path_widget.py` — path-field tests; the pattern for every
  new test (gates with `threading.Event`, `monkeypatch` of
  `_compat.can_stall`).
- `tests/test_drop_zone.py` — drop zone tests.

`fxgui/_compat.py:63-70`:

```python
def can_stall(path: str) -> bool:
    """Return whether reading `path` may wait on a network share."""
    if path.startswith(("\\\\", "//")):
        return True
    if sys.platform != "win32":
        return False
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    return bool(drive) and _remote_drive(drive.upper() + "\\")
```

`fxgui/fxwidgets/_file_path_widget.py:58-118` (the cap applies to every
threaded check):

```python
_relay: Optional[_Relay] = None
_lock = threading.Lock()
_live = 0
# (widget, slot) -> its newest check waiting for a thread; older ones drop.
_pending: "OrderedDict[tuple, tuple]" = OrderedDict()
# A share that does not answer holds its thread; the cap keeps dead shares
# from flooding the process with stuck threads.
_THREAD_CAP = 4
...
def _check(
    widget: QWidget,
    slot: str,
    check: Callable[[], Tuple],
    paths: Optional[List[str]] = None,
) -> None:
    ...
    if paths is not None and not any(_compat.can_stall(p) for p in paths):
        getattr(widget, slot)(*check())
        return
    global _relay, _live
    if _relay is None:
        _relay = _Relay()
        _relay.finished.connect(_deliver)
    job = (weakref.ref(widget), slot, check)
    with _lock:
        if _live >= _THREAD_CAP:
            _pending.pop((id(widget), slot), None)
            _pending[(id(widget), slot)] = job
            return
        _live += 1
    threading.Thread(
        target=_work, args=(job,), name="fxgui-path-check", daemon=True
    ).start()
```

`_file_path_widget.py:292-300` — a typed path never passes `paths`, so it
always takes a capped thread:

```python
        # Always off the UI thread: a typed path may sit on any mount.
        mode = self._mode
        self._check_ticket += 1
        ticket = self._check_ticket
        _check(
            self,
            "_on_validation_finished",
            lambda: (ticket, path, _path_is_valid(path, mode)),
        )
```

The "typed path always off the UI thread" rule is deliberate and tested
(`tests/test_file_path_widget.py:211-234`,
`test_a_typed_local_path_is_checked_off_the_ui_thread`): `can_stall` cannot
see a local folder that links to a share, or (today) an NFS mount on Linux.
**Keep it**: a typed local check still goes to a thread, but to one outside
the cap. Drops of local paths already run inline (line 102) and stay so.

"files" mode joins and splits on `;` (`_file_path_widget.py:39-41`, `261`,
`348`), and `;` is legal in file names:

```python
    if mode == "files":
        paths = [p.strip() for p in path.split(";") if p.strip()]
        return bool(paths) and all(os.path.isfile(p) for p in paths)
```

`fxgui/fxwidgets/_drop_zone.py` disk reads on the UI thread:

```python
# :34-43
def _local_paths(event) -> Iterator[Path]:
    for url in event.mimeData().urls():
        if url.isLocalFile():
            path = Path(url.toLocalFile())
            if path.exists():
                yield path
# :262-283  _update_file_tree: clears and rebuilds every row, is_dir()+stat() each
        self._file_tree.clear()
        for path in self._selected_files:
            item = QTreeWidgetItem()
            ...
            if path.is_dir():
            ...
                item.setText(2, _size_text(path))   # path.stat()
# :344-346  duplicate check scans the list per path
        new_files = [p for p in paths if p not in self._selected_files]
# :385-392  dragEnterEvent
        if any(self._accepts(path) for path in _local_paths(event)):
# :400-406  dropEvent
        if self._take(list(_local_paths(event))):
```

`_accepts` (`_drop_zone.py:374-383`) is the accept rule to keep:

```python
    def _accepts(self, path: Path) -> bool:
        if self._accept_mode != "files" and path.is_dir():
            return True
        if self._accept_mode != "folders" and path.is_file():
            return (
                self._extensions is None
                or path.suffix.lower() in self._extensions
            )
        return False
```

Repo conventions that apply:

- Qt only through `qtpy`. Google-style docstrings with Args/Returns.
  Comments say why, in one line.
- Private modules start with `_`; a private module's own helpers need no
  `_` prefix (see `fxgui/fxwidgets/_tips.py`'s `apply_tip`). Classes in
  `fxgui/fxwidgets/*` that do not start with `_` must be exported from
  `fxgui/fxwidgets/__init__.py` (`tests/test_fxwidgets_exports.py`), so the
  new module's only class stays `_Relay`.
- Call `_compat.can_stall(...)` through the module attribute (not
  `from fxgui._compat import can_stall`): the tests monkeypatch
  `_compat.can_stall`.
- Tests: plain functions named as sentences; files in `tests/`; pytest-qt's
  `qtbot`.

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| Path-field tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_file_path_widget.py` | all pass |
| Drop-zone tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_drop_zone.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it, 3178 + the new tests passed, 6 skipped |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

Never run tests on the real Qt platform: conftest forces `offscreen`; do not
override it. Any ad-hoc Python you run must first call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, or it overwrites the owner's real settings file.
Run ad-hoc scripts from the worktree root with `PYTHONPATH=.` so the
worktree's `fxgui` wins over the venv's editable install.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_path_check.py` (create) — the shared thread machinery.
- `fxgui/fxwidgets/_file_path_widget.py` — use it; `paths()`/`set_paths()`.
- `fxgui/fxwidgets/_drop_zone.py` — name-only drag, checked drops, row
  appends, dict of held paths.
- `tests/test_file_path_widget.py`, `tests/test_drop_zone.py` — adjust and add.

**Out of scope** (do NOT touch):

- `fxgui/_compat.py` — `can_stall` itself; Linux mounts are plan 022.
- `fxgui/fxwidgets/_delegates.py` — the thumbnail reader has its own queue
  and works.
- `fxgui/fxwidgets/__init__.py` — nothing new is exported (`_path_check` is
  private, `paths`/`set_paths` are methods).
- `fxgui/examples.py` — no new widget; the gallery needs no section.
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists (today it
  does not).
- Branch: `fix/no-disk-check-blocks-the-ui`.
- Commits in the repo style, e.g.
  `[FIX] path checks: the thread cap counts only checks that may stall`,
  `[FIX] drop zone: no disk read on the UI thread`,
  `[FEAT] FXFilePathWidget.paths and set_paths`. End each commit message with
  the attribution line the operator's environment asks for, if any.
- Do not push, tag or release: the operator does.

## Steps

### Step 1: Move the thread machinery to `_path_check.py`, capping only checks that may stall

Create `fxgui/fxwidgets/_path_check.py` with this content (it is the code of
`_file_path_widget.py:52-118`, moved, with two changes: the cap counts only
checks that may stall, and a non-stalling check can run on an uncapped
thread):

```python
"""Disk checks that never make the UI thread wait on a network share."""

# Built-in
import threading
import weakref
from collections import OrderedDict
from typing import Callable, Optional, Sequence, Tuple

# Third-party
from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import _compat
from fxgui._compat import is_valid as is_valid_object


class _Relay(QObject):
    """Carries a worker's result back to the UI thread."""

    finished = Signal(object, str, object)


_relay: Optional[_Relay] = None
_lock = threading.Lock()
_live = 0
# (widget, slot) -> its newest check waiting for a thread; older ones drop.
_pending: "OrderedDict[tuple, tuple]" = OrderedDict()
# A share that does not answer holds its thread; the cap keeps dead shares
# from flooding the process with stuck threads.
THREAD_CAP = 4


def _deliver(widget_ref, slot: str, args: tuple) -> None:
    """Hand a result to its widget if the widget is still alive."""
    widget = widget_ref()
    if widget is not None and is_valid_object(widget):
        getattr(widget, slot)(*args)


def _work(job: tuple, capped: bool) -> None:
    """Run a check; a capped thread then runs any waiting one."""
    global _live
    while job is not None:
        widget_ref, slot, check = job
        try:
            _relay.finished.emit(widget_ref, slot, check())
        except Exception:  # noqa: BLE001 - a failed check must not kill the thread
            pass
        if not capped:
            return
        with _lock:
            job = _pending.popitem(last=False)[1] if _pending else None
            if job is None:
                _live -= 1


def run(
    widget: QWidget,
    slot: str,
    check: Callable[[], Tuple],
    paths: Sequence[str],
    inline: bool = True,
) -> None:
    """Call `widget.slot(*check())` without the UI thread waiting on a share.

    A check that reads a path that may stall runs on a daemon thread, at
    most `THREAD_CAP` of them at once; past the cap, each widget's newest
    check waits for a free one. Any other check runs at once, or with
    `inline` False on a thread of its own outside the cap, so dead shares
    never hold it up. Not the host's `QThreadPool`: a stuck check would
    starve it and hold its quit; a daemon thread never delays the exit.

    Args:
        widget: Takes the result; a result for a deleted widget is dropped.
        slot: The name of `widget`'s method that takes `*check()`.
        check: Reads the disk and returns the slot's arguments. It may run
            on a worker thread, so it must not touch a widget.
        paths: Every path `check` reads.
        inline: Whether a check none of whose paths may stall runs at once
            on the calling thread.
    """
    stalls = any(_compat.can_stall(p) for p in paths)
    if not stalls and inline:
        getattr(widget, slot)(*check())
        return
    global _relay, _live
    if _relay is None:
        _relay = _Relay()
        _relay.finished.connect(_deliver)
    job = (weakref.ref(widget), slot, check)
    if stalls:
        with _lock:
            if _live >= THREAD_CAP:
                _pending.pop((id(widget), slot), None)
                _pending[(id(widget), slot)] = job
                return
            _live += 1
    # shortcut: a local path that links to a share takes an uncapped thread; cap it too if stuck threads pile up.
    threading.Thread(
        target=_work, args=(job, stalls), name="fxgui-path-check", daemon=True
    ).start()
```

Then in `fxgui/fxwidgets/_file_path_widget.py`:

1. Delete `_Relay`, `_relay`, `_lock`, `_live`, `_pending`, `_THREAD_CAP`,
   `_deliver`, `_work` and `_check` (lines 52-118) and the imports only they
   used (`threading`, `weakref`, `OrderedDict`, `QObject`, `Callable`,
   `Tuple`, `is_valid_object`, `_compat` — ruff will tell you which are
   left unused).
2. Add `from fxgui.fxwidgets import _path_check` to the `# Internal` imports.
3. In `dropEvent` (line 338) replace `_check(` with `_path_check.run(` (the
   arguments stay: the drop already passes `paths`, and `inline` defaults to
   True, so local drops stay inline).
4. In `_do_validation` (lines 292-300) pass the paths and `inline=False`:

```python
        # Off the UI thread even when local: a local folder may link to a share.
        mode = self._mode
        self._check_ticket += 1
        ticket = self._check_ticket
        _path_check.run(
            self,
            "_on_validation_finished",
            lambda: (ticket, path, _path_is_valid(path, mode)),
            [p.strip() for p in path.split(";")] if mode == "files" else [path],
            inline=False,
        )
```

(Step 3 replaces the `split(";")` with `self.paths()`.)

In `tests/test_file_path_widget.py`, `test_at_the_thread_cap_only_the_newest_check_waits`
patches `_file_path_widget._THREAD_CAP`; change it to patch
`_path_check.THREAD_CAP` (`from fxgui.fxwidgets import _path_check`). Its
paths `"a"`, `"b"` and `str(tmp_path)` are local, so they no longer queue:
rewrite the loop to queue share paths only, and assert the newest share
check is the one that ran:

```python
    try:
        widget.set_path(r"\\dead\share")
        widget._do_validation()
        qtbot.waitUntil(lambda: bool(checked))
        for name in (r"\\dead\a", r"\\dead\b", r"\\dead\c"):
            widget.set_path(name)
            widget._do_validation()
    finally:
        gate.set()

    qtbot.waitUntil(widget.is_valid)
    assert checked == [r"\\dead\share", r"\\dead\c"]
```

(`_dead_share` makes a `\\`-path check wait on the gate and then answer
True, so `\\dead\c` ends valid.)

In `test_stuck_share_checks_never_hold_up_a_local_one` (lines 141-160),
fill the cap instead of stopping one short, and give the local check 1 s:

```python
        for index in range(_path_check.THREAD_CAP):
            stuck.set_path(rf"\\dead\{index}")
            stuck._do_validation()
        ...
        qtbot.waitUntil(widget.is_valid, timeout=1000)
```

**Verify**:
`...\python.exe -m pytest -q tests/test_file_path_widget.py` → all pass
(14 tests). Then prove the cap test fails without the fix: temporarily
change `if stalls:` to `if True:` in `_path_check.run`, rerun only
`-k never_hold_up` → it FAILS (timeout); revert → passes.

### Step 2: Commit

`git add -A && git commit -m "[FIX] path checks: the thread cap counts only checks that may stall"`
**Verify**: `git status --short` → empty.

### Step 3: `paths()` and `set_paths()` on `FXFilePathWidget`

In `fxgui/fxwidgets/_file_path_widget.py`:

1. In `__init__`, next to `self._check_ticket = 0`, add
   `self._paths: List[str] = []` with the comment
   `# The list "files" mode showed last, so a ";" in a name survives.`
2. After `set_path`, add:

```python
    def paths(self) -> List[str]:
        """Return the paths in the field: several in "files" mode, else one.

        In "files" mode the field shows them joined by ";". A list given to
        `set_paths`, or picked or dropped, comes back whole even when a
        name holds a ";"; text typed by hand is split on ";".
        """
        text = self._input.text()
        if self._mode != "files":
            return [text] if text else []
        if self._paths and text == ";".join(self._paths):
            return list(self._paths)
        return [p.strip() for p in text.split(";") if p.strip()]

    def set_paths(self, paths: List[str]) -> None:
        """Show `paths`, joined by ";" in "files" mode.

        Raises:
            ValueError: More than one path outside "files" mode.
        """
        if self._mode != "files" and len(paths) > 1:
            raise ValueError(
                f"mode {self._mode!r} holds one path, got {len(paths)}")
        self._paths = list(paths)
        self._input.setText(";".join(paths))
```

3. In `_browse`, "files" branch, replace
   `path = ";".join(paths) if paths else ""` so the list goes in whole
   (keep the other branches as they are):

```python
        elif self._mode == "files":
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Files", start_path, self._file_filter
            )
            if paths:
                self.set_paths(paths)
            return
```
4. In `_on_drop_checked`: replace `self._input.setText(";".join(paths))`
   with `self.set_paths(paths)`.
5. Validation: drop the `"files"` branch from `_path_is_valid` (lines 39-41)
   and validate each path as a file in `_do_validation`:

```python
        mode = self._mode
        paths = self.paths()
        self._check_ticket += 1
        ticket = self._check_ticket

        def check() -> tuple:
            if mode == "files":
                found = bool(paths) and all(
                    _path_is_valid(p, "file") for p in paths)
            else:
                found = _path_is_valid(path, mode)
            return ticket, path, found

        # Off the UI thread even when local: a local folder may link to a share.
        _path_check.run(
            self, "_on_validation_finished", check, paths, inline=False)
```

   `_path_is_valid` keeps its `(path, mode)` signature: tests monkeypatch it.

**Verify**: `...\python.exe -m pytest -q tests/test_file_path_widget.py` →
all pass (the new tests come in Step 6).

### Step 4: Commit

`git commit -am "[FEAT] FXFilePathWidget.paths and set_paths keep a ; in a file name"`

### Step 5: The drop zone reads the disk only through `_path_check`

In `fxgui/fxwidgets/_drop_zone.py`:

1. Imports: add `QUrl` to the `qtpy.QtCore` import, `Dict, Tuple` to
   `typing`, and `from fxgui.fxwidgets import _path_check` to `# Internal`.
   Remove what becomes unused (`Iterator`); ruff tells you.
2. Replace `_local_paths` and `_size_text` (lines 34-53) with:

```python
# A listed path, whether it is a folder, and its size if a readable file.
_Row = Tuple[Path, bool, Optional[int]]


def _probe(path: Path) -> _Row:
    """Return `path`'s row: the disk reads a listed path needs."""
    if path.is_dir():
        return path, True, None
    try:
        return path, False, path.stat().st_size
    except OSError:
        return path, False, None


def _vet(
    paths: List[Path], accept_mode: str, extensions: Optional[Set[str]]
) -> List[_Row]:
    """Return the rows of the paths a zone in `accept_mode` takes.

    Reads the disk, so it may run on a worker thread: it takes no widget.
    """
    rows = []
    for path in paths:
        row = _probe(path)
        if row[1]:
            taken = accept_mode != "files"
        else:
            taken = (
                accept_mode != "folders"
                and path.is_file()
                and (extensions is None or path.suffix.lower() in extensions)
            )
        if taken:
            rows.append(row)
    return rows


def _size_text(size: Optional[int]) -> str:
    """Return a file size in Qt's own format, or "-" when unknown."""
    if size is None:
        return "-"
    return QLocale().formattedDataSize(
        size, 1, QLocale.DataSizeTraditionalFormat)
```

3. `__init__`: replace `self._selected_files: List[Path] = []` with

```python
        # Ordered like the list; a dict, so a duplicate is found at once.
        self._selected_files: Dict[Path, None] = {}
        # In single mode, only the newest drop's check lands.
        self._take_ticket = 0
```

4. Replace `_update_file_tree` (lines 262-291) with two methods — rows are
   appended, never rebuilt:

```python
    def _rows(self, paths: Iterable[Path]) -> List[_Row]:
        """Return rows for `paths`, reading the disk only for a shown list."""
        if self._show_tree:
            return [_probe(path) for path in paths]
        return [(path, False, None) for path in paths]

    def _add_rows(self, rows: List[_Row]) -> None:
        """Append a list row per row."""
        if not self._show_tree:
            return
        for path, is_dir, size in rows:
            item = QTreeWidgetItem()
            item.setText(0, path.name)
            item.setData(0, Qt.UserRole, path)
            if is_dir:
                item.setText(1, "Folder")
                item.setIcon(0, fxicons.get_icon("folder"))
            else:
                item.setText(1, path.suffix.upper().lstrip(".") or "File")
                item.setIcon(0, fxicons.get_icon("file-text"))
            item.setText(2, _size_text(size))
            self._file_tree.addTopLevelItem(item)

    def _show_count(self) -> None:
        """Show the list and its count, or the placeholder."""
        has_files = bool(self._selected_files)
        if self._show_buttons:
            self._clear_btn.setEnabled(has_files)
        if not self._show_tree:
            return
        count = len(self._selected_files)
        self._count_label.setText(
            "1 file selected" if count == 1 else f"{count} files selected"
        )
        self._drop_area.setVisible(not has_files)
        self._file_tree.setVisible(has_files)
        self._count_label.setVisible(has_files)
```

   (A folder's size column was "-" before; `_size_text(None)` keeps it.)

5. `_remove_file`: take only its row.

```python
        if path in self._selected_files:
            index = list(self._selected_files).index(path)
            del self._selected_files[path]
            if self._show_tree:
                self._file_tree.takeTopLevelItem(index)
            self._show_count()
            self.file_removed.emit(path)
            ...
```

6. `_on_files_added(self, rows: List[_Row]) -> bool`: takes rows now.

```python
        fresh: Dict[Path, _Row] = {}
        for row in rows:
            if row[0] not in self._selected_files:
                fresh.setdefault(row[0], row)
        if not fresh:
            return False
        new_rows = list(fresh.values())
        if not self._multiple:
            # One file replaces the last; the signal names what was kept.
            new_rows = new_rows[:1]
            self._selected_files.clear()
            if self._show_tree:
                self._file_tree.clear()
        for row in new_rows:
            self._selected_files[row[0]] = None
        self._add_rows(new_rows)
        self._show_count()
        self.files_dropped.emit([row[0] for row in new_rows])
        return True
```

7. Replace `_take` and `_accepts` with the checked path:

```python
    def _take(self, paths: List[Path]) -> None:
        """Add the paths the zone takes, reading a share off the UI thread.

        Flashes in error when it takes none of `paths`.
        """
        if not paths:
            return
        self._take_ticket += 1
        ticket = self._take_ticket
        mode, extensions = self._accept_mode, self._extensions
        _path_check.run(
            self,
            "_on_vetted",
            lambda: (ticket, _vet(paths, mode, extensions)),
            [str(path) for path in paths],
        )

    def _on_vetted(self, ticket: int, rows: List[_Row]) -> None:
        """Add the rows a check passed; a stale single-mode drop drops out."""
        if not self._multiple and ticket != self._take_ticket:
            return
        if not rows:
            self._flash_feedback("error")
            return
        if self._on_files_added(rows) and not self._show_tree:
            self._flash_feedback("success")

    def _may_take(self, url: QUrl) -> bool:
        """Return whether a drag's `url` may name a path this zone takes.

        By name only, so a drag over a dead share never waits: the drop
        reads the disk.
        """
        if not url.isLocalFile():
            return False
        if self._accept_mode != "files" or self._extensions is None:
            return True
        return Path(url.toLocalFile()).suffix.lower() in self._extensions
```

8. `dragEnterEvent` and `dropEvent`:

```python
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept a drag that names a path the zone may take."""
        if any(self._may_take(url) for url in event.mimeData().urls()):
            event.acceptProposedAction()
            self._set_drop_state("drag")
            self.drag_entered.emit()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Add the accepted paths; edge the area in error if none were."""
        self._set_drop_state("idle")
        urls = event.mimeData().urls()
        if any(self._may_take(url) for url in urls):
            event.acceptProposedAction()
        else:
            event.ignore()
        self._take([Path(url.toLocalFile()) for url in urls if url.isLocalFile()])
```

9. Public API:
   - `selected_files()` → `return list(self._selected_files)`.
   - `set_files(paths)`:

```python
        self._selected_files = dict.fromkeys(paths)
        if self._show_tree:
            self._file_tree.clear()
            self._add_rows(self._rows(self._selected_files))
        self._show_count()
```

   - `add_files(paths)` →
     `self._on_files_added(self._rows(p for p in paths if p not in self._selected_files))`.
   - `_browse` keeps calling `self._take(...)`; it returned a value nobody
     reads, so nothing else changes there.
   - `has_files()`, `clear()` and `_show_context_menu` work unchanged on the
     dict (`bool`, `len`, `in`).

10. `grep -n "_update_file_tree\|_accepts\|_local_paths" fxgui/` → no output.

**Verify**: `...\python.exe -m pytest -q tests/test_drop_zone.py` → the
tests that still call `_accepts` fail with `AttributeError`, and
`test_a_drag_stops_checking_the_disk_at_the_first_path_taken` fails
(`len(checked) == 0`); every other test passes. Step 6 updates those three.

### Step 6: Tests

In `tests/test_drop_zone.py` (add `from fxgui.fxwidgets import _drop_zone`):

- `test_zone_and_tree_accept_the_same_paths`: replace
  `assert zone._accepts(path) is taken` with
  `assert bool(_drop_zone._vet([path], zone.accept_mode(), zone.extensions())) is taken`,
  and the last line with the same call on `tmp_path / "missing.png"` being
  falsy. The drag assertions stay: `tmp_path` has no suffix, so a
  `{".png"}` zone still refuses it by name.
- `test_extensions_take_any_case_and_dot`: same replacement.
- Rename `test_a_drag_stops_checking_the_disk_at_the_first_path_taken` to
  `test_a_drag_never_reads_the_disk`; also patch `Path.is_dir`,
  `Path.is_file` and `Path.stat` with the same recording wrapper; assert the
  event is accepted and `checked == []`.

New tests in `tests/test_drop_zone.py`:

1. `test_a_drop_from_a_share_never_waits_on_the_disk` — patch
   `_compat.can_stall` to `lambda _path: True` and `_drop_zone._probe` with a
   wrapper that waits on a `threading.Event` (`gate.wait(5)`) then calls the
   real one; build a drop of one `a.png` (see
   `test_a_drop_on_the_zone_adds_one_file_in_single_mode` for the
   `QDropEvent` construction); time `zone.dropEvent(event)` with
   `time.monotonic()`; `gate.set()`; assert it took `< 1` s, then
   `qtbot.waitUntil(zone.has_files)` and `zone.selected_files() == [a]`.
   Pattern: `tests/test_file_path_widget.py::test_a_drop_checks_the_disk_off_the_ui_thread`.
2. `test_a_path_given_twice_is_listed_once` — `add_files([a, a, b])`, then
   `add_files([b, c])`; assert `selected_files() == [a, b, c]`, the
   `files_dropped` payloads are `[[a, b], [c]]`, and
   `file_tree().topLevelItemCount() == 3`.
3. `test_adding_files_keeps_the_rows_already_listed` — count calls of
   `_drop_zone._probe` with a recording wrapper; `add_files([a])`, mark the
   row (`file_tree().topLevelItem(0).setData(0, Qt.UserRole + 1, "kept")`),
   `add_files([b])`; assert the probes were `[a, b]` (not `[a, a, b]`) and
   `topLevelItem(0).data(0, Qt.UserRole + 1) == "kept"`.
4. `test_removing_a_file_takes_only_its_row` — `set_files([a, b, c])`,
   `zone._remove_file(b)`; assert the row names are `["a.png", "c.png"]` and
   the count label reads `"2 files selected"`.
5. `test_in_single_mode_only_the_newest_drop_lands` — `multiple=False`;
   patch `_compat.can_stall` to `lambda p: "slow" in p` and
   `_drop_zone._probe` to wait on a gate for paths whose name contains
   `"slow"`; drop `slow.png`, then `fast.png`; assert
   `selected_files() == [fast]`; `gate.set()`; `qtbot.wait(300)`; still
   `[fast]`.

New tests in `tests/test_file_path_widget.py`:

6. `test_files_mode_keeps_a_semicolon_in_a_file_name` — files `a;b.txt` and
   `c.txt` in `tmp_path`; `widget = FXFilePathWidget(mode="files")`;
   `widget.set_paths([str(first), str(second)])`; assert
   `widget.paths() == [str(first), str(second)]`; `widget._do_validation()`;
   `qtbot.waitUntil(widget.is_valid)`.
7. `test_paths_splits_text_typed_in_files_mode` — `set_path("x; y")` →
   `paths() == ["x", "y"]`; in "folder" mode `set_path("x;y")` →
   `paths() == ["x;y"]`, and `set_path("")` → `paths() == []`.
8. `test_set_paths_takes_one_path_outside_files_mode` — "folder" mode:
   `set_paths(["a", "b"])` raises `ValueError`; `set_paths(["a"])` →
   `path() == "a"`.

**Verify**:
`...\python.exe -m pytest -q tests/test_drop_zone.py tests/test_file_path_widget.py`
→ all pass (5 + 3 new tests). Then prove test 1 guards the fix:
temporarily make `_take` call `self._on_vetted(ticket, _vet(paths, mode, extensions))`
directly, rerun `-k never_waits` → FAILS; revert → passes.

### Step 7: Full suite, lint, commit

**Verify**: whole suite → 3178 + 8 passed, 6 skipped; lint →
`All checks passed!`. Then
`git add -A && git commit -m "[FIX] drop zone: no disk read on the UI thread, rows appended"`.

## Test plan

- Changed: `test_stuck_share_checks_never_hold_up_a_local_one` (fills the
  cap, 1 s budget), `test_at_the_thread_cap_only_the_newest_check_waits`
  (patches `_path_check.THREAD_CAP`, queues shares only),
  `test_zone_and_tree_accept_the_same_paths`,
  `test_extensions_take_any_case_and_dot`, and
  `test_a_drag_stops_checking_the_disk_at_the_first_path_taken` (renamed
  `test_a_drag_never_reads_the_disk`).
- New: the 8 tests of Step 6.
- Unchanged and must still pass: `test_a_typed_local_path_is_checked_off_the_ui_thread`
  (typed checks stay off the UI thread), `test_a_stuck_check_leaves_the_host_pool_free`,
  `test_only_the_latest_drop_lands`, `test_a_drop_on_the_zone_adds_one_file_in_single_mode`
  (a local drop is still added inside `dropEvent`),
  `test_browse_keeps_the_filter_and_flashes_when_nothing_is_left`.
- Pattern: `tests/test_file_path_widget.py` (gates, `_dead_share`, timing).

## Done criteria

- [ ] Whole suite exits 0 with 3178 + 8 passed, 6 skipped
- [ ] Lint exits 0
- [ ] `grep -n "_THREAD_CAP\|def _check\|class _Relay" fxgui/fxwidgets/_file_path_widget.py` → no output
- [ ] `grep -n "is_dir()\|exists()\|stat()" fxgui/fxwidgets/_drop_zone.py` → matches only inside `_probe` and `_vet`
- [ ] `grep -n "def paths\|def set_paths" fxgui/fxwidgets/_file_path_widget.py` → 2 matches
- [ ] `git status` shows only the in-scope files changed
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts.
  Exception: if plan 022 landed, `can_stall` in `fxgui/_compat.py` has a
  Linux branch; that is expected and changes nothing here.
- `test_a_typed_local_path_is_checked_off_the_ui_thread` fails: the typed
  check ran inline; do not change that test, re-check `inline=False`.
- `test_a_result_for_a_deleted_widget_is_dropped` or any test crashes the
  interpreter (access violation): a result reached a deleted widget; the
  `_deliver` liveness check was lost in the move.
- A drop-zone test outside the ones listed in Step 5's Verify fails after
  Step 5 — some caller relied on the old synchronous or list behaviour; list
  them.
- The fix seems to need `fxgui/_compat.py`, `_delegates.py` or
  `fxwidgets/__init__.py`.

## Maintenance notes

- `_path_check.run` is now the one way fxgui widgets read a path; a future
  widget that touches the disk on a user action should use it, not its own
  thread.
- The `shortcut:` comment in `_path_check.run`: a local path that is really
  a link to a share takes an uncapped thread. Each such check is debounced
  (300 ms) per field, so pile-ups need a person typing for a long time at a
  dead link. Plan 022 shrinks the case on Linux by detecting NFS/SMB mounts.
- Reviewers: check that `_vet` and `_probe` touch no widget (they run on
  worker threads) and that `_take` snapshots `accept_mode`/`extensions`
  before the lambda.
- Deferred: the size column of a share file listed through `set_files` /
  `add_files` (public, synchronous API) still `stat()`s on the calling
  thread; those calls are the caller's own choice of thread.
- Pascal: nothing to change; `git grep FXDropZone FXFilePathWidget` on
  ls-pascal `origin/main` finds no use in code (only a design note).
