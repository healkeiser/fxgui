# Plan 022: On Linux, paths on network mounts count as paths that may stall

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/_compat.py tests/test_compat.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (complements plan 012; either order works)
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`_compat.can_stall(path)` decides whether fxgui may read a path on the UI
thread. Off Windows it only recognises UNC-style paths (`//server/share`),
so on Linux a path under an NFS, SMB or sshfs mount counts as local. Two
callers then read it on the UI thread: a file dropped on `FXFilePathWidget`
(`fxgui/fxwidgets/_file_path_widget.py:102`) and the thumbnail delegate's
stale-file check, which runs while painting
(`fxgui/fxwidgets/_delegates.py:181`). A dead NFS server then freezes the
window. Studios on Linux mount their projects over NFS, so the case is
real there; Pascal is Windows-first, hence P3.

After this plan, on Linux, a path under a mount whose type is a network
file system counts as one that may stall. The mount table is read from
`/proc/mounts` at most once every 30 s, because `can_stall` runs during
painting.

macOS is left as is: `os.statvfs` does not report the file system type,
and the call that does (`statfs`) needs ctypes on a platform fxgui does not
test. Said in a code comment.

**Public behaviour that changes**: none in the API (`_compat` is private).
On Linux, drops and thumbnails of files on network mounts are read on a
worker thread instead of the UI thread; a dropped network file is added a
moment after the drop instead of inside it.

## Current state

Files:

- `fxgui/_compat.py` — `can_stall` (lines 63-70) and `_remote_drive`
  (lines 53-60).
- `tests/test_compat.py` — `_compat` tests; the pattern (plain functions,
  `from fxgui._compat import ...`).
- Callers (read only, do not change): `fxgui/fxwidgets/_file_path_widget.py:102`,
  `fxgui/fxwidgets/_delegates.py:181`, and, if plan 012 landed,
  `fxgui/fxwidgets/_path_check.py`.

`fxgui/_compat.py:50-70`:

```python
_DRIVE_REMOTE = 4


@functools.lru_cache(maxsize=None)
def _remote_drive(root: str) -> bool:
    """Return whether Windows reports drive `root` (``"X:\\"``) as remote."""
    try:
        return ctypes.windll.kernel32.GetDriveTypeW(root) == _DRIVE_REMOTE
    except (AttributeError, OSError):
        return False


def can_stall(path: str) -> bool:
    """Return whether reading `path` may wait on a network share."""
    if path.startswith(("\\\\", "//")):
        return True
    if sys.platform != "win32":
        return False
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    return bool(drive) and _remote_drive(drive.upper() + "\\")
```

`/proc/mounts` format: one mount per line, fields separated by spaces:
`device mount_point fs_type options dump pass`. A space, tab, newline or
backslash in `mount_point` is written as a 3-digit octal escape (`\040`
for a space). Example lines:

```
fileserver:/export/projects /mnt/projects nfs4 rw,relatime 0 0
//nas/shows /mnt/my\040shows cifs rw 0 0
/dev/nvme0n1p2 / ext4 rw,relatime 0 0
```

CI runs on `ubuntu-latest` (`.github/workflows/tests.yml:12`), so the new
Linux branch runs there for real against the runner's `/proc/mounts` (no
network mounts; every test path stays local). The owner's machine is
Windows: tests must exercise the Linux code without being on Linux, so
the parser takes POSIX paths through `posixpath`, not `os.path` (on Linux
they are the same module; on Windows `os.path.abspath("/mnt/x")` would turn
into `C:\mnt\x`).

Repo conventions: Google-style docstrings; comments say why, in one line;
tests are plain functions named as sentences; `_compat` is imported by
every widget, so it must stay cheap to import (no Qt work at import).

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| Compat tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_compat.py` | all pass |
| Callers' tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_file_path_widget.py tests/test_item_views.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it, 3178 + the new tests passed, 6 skipped |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

Never run tests on the real Qt platform: conftest forces `offscreen`. Any
ad-hoc Python must first call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, and run from the worktree root with `PYTHONPATH=.`.

## Scope

**In scope** (the only files you should modify):

- `fxgui/_compat.py`
- `tests/test_compat.py`

**Out of scope** (do NOT touch):

- The callers (`_file_path_widget.py`, `_delegates.py`, `_path_check.py`):
  they already route a may-stall path off the UI thread.
- macOS detection — see "Why this matters".
- Symlinks into network mounts (`os.path.realpath` would itself read the
  disk, which is what this function avoids).
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists (today it
  does not).
- Branch: `fix/linux-network-mounts-may-stall`.
- Commit, repo style: `[FIX] can_stall: paths on Linux network mounts may stall`.
  End the commit message with the attribution line the operator's
  environment asks for, if any.
- Do not push, tag or release: the operator does.

## Steps

### Step 1: Read the network mounts, cached

In `fxgui/_compat.py`:

1. Imports (`# Built-in`): add `import posixpath`, `import re`,
   `import time`; add `Tuple` to the `typing` import.
2. Below `_remote_drive`, add:

```python
# File system types whose reads go over the network.
_NETWORK_FS = frozenset({
    "nfs", "nfs4", "cifs", "smb3", "smbfs", "fuse.sshfs",
    "ceph", "fuse.ceph-fuse", "glusterfs", "fuse.glusterfs",
})
# `can_stall` runs while painting: the mount table is read this seldom.
_MOUNTS_TTL = 30.0
# (when read, network mount points longest first), or None before the first read.
_mounts_cache: Optional[Tuple[float, Tuple[str, ...]]] = None


def _read_mounts() -> str:
    """Return the Linux mount table, or "" when it cannot be read."""
    try:
        with open("/proc/mounts", encoding="utf-8", errors="replace") as table:
            return table.read()
    except OSError:
        return ""


def _network_mounts() -> Tuple[str, ...]:
    """Return the network mount points, longest first, re-read every 30 s."""
    global _mounts_cache
    now = time.monotonic()
    if _mounts_cache is not None and now - _mounts_cache[0] < _MOUNTS_TTL:
        return _mounts_cache[1]
    points = []
    for line in _read_mounts().splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[2] in _NETWORK_FS:
            # The table writes a space in a mount point as \040.
            points.append(re.sub(
                r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), fields[1]))
    _mounts_cache = (now, tuple(sorted(points, key=len, reverse=True)))
    return _mounts_cache[1]


def _on_network_mount(path: str) -> bool:
    """Return whether the POSIX `path` lies under a network mount."""
    path = posixpath.abspath(path)
    for point in _network_mounts():
        if point == "/" or path == point or path.startswith(point + "/"):
            return True
    return False
```

3. Change `can_stall`:

```python
def can_stall(path: str) -> bool:
    """Return whether reading `path` may wait on a network share.

    On macOS only UNC-style paths count: `os.statvfs` does not say which
    file system a path is on.
    """
    if path.startswith(("\\\\", "//")):
        return True
    if sys.platform.startswith("linux"):
        return _on_network_mount(path)
    if sys.platform != "win32":
        return False
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    return bool(drive) and _remote_drive(drive.upper() + "\\")
```

**Verify**: `...\python.exe -m pytest -q tests/test_compat.py tests/test_file_path_widget.py tests/test_item_views.py`
→ all pass (nothing changes on Windows).

### Step 2: Tests

In `tests/test_compat.py`, add (with `import sys` and
`from fxgui import _compat` at the top if missing):

```python
_MOUNTS = "\n".join((
    "fileserver:/export/projects /mnt/projects nfs4 rw,relatime 0 0",
    r"//nas/shows /mnt/my\040shows cifs rw 0 0",
    "/dev/nvme0n1p2 / ext4 rw,relatime 0 0",
    "/dev/nvme0n1p3 /mnt/projects/local ext4 rw 0 0",
))


def _fake_mounts(monkeypatch, table=_MOUNTS):
    """Serve `table` as /proc/mounts, with nothing cached."""
    reads = []

    def read():
        reads.append(True)
        return table

    monkeypatch.setattr(_compat, "_read_mounts", read)
    monkeypatch.setattr(_compat, "_mounts_cache", None)
    return reads


def test_a_path_on_a_network_mount_may_stall(monkeypatch):
    _fake_mounts(monkeypatch)
    assert _compat._on_network_mount("/mnt/projects/shot/a.exr")
    assert _compat._on_network_mount("/mnt/projects")
    assert _compat._on_network_mount("/mnt/my shows/ep01")


def test_a_local_path_beside_a_network_mount_does_not(monkeypatch):
    _fake_mounts(monkeypatch)
    assert not _compat._on_network_mount("/home/me/a.exr")
    # A sibling whose name only starts like the mount point.
    assert not _compat._on_network_mount("/mnt/projects2/a.exr")


def test_the_mount_table_is_read_once_per_interval(monkeypatch):
    reads = _fake_mounts(monkeypatch)
    for _ in range(3):
        _compat._on_network_mount("/mnt/projects/a")
    assert len(reads) == 1

    when, points = _compat._mounts_cache
    monkeypatch.setattr(_compat, "_mounts_cache", (when - 31, points))
    _compat._on_network_mount("/mnt/projects/a")
    assert len(reads) == 2


def test_on_linux_can_stall_reads_the_mounts(monkeypatch):
    _fake_mounts(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    assert _compat.can_stall("/mnt/projects/a.exr")
    assert not _compat.can_stall("/home/me/a.exr")
    assert _compat.can_stall("//server/share/a.exr")
```

Note on the second test: `/mnt/projects/local` is an `ext4` mount nested
under the NFS one; this plan still treats it as may-stall (the longest
network prefix wins and nested local mounts are not subtracted). That is
the safe direction (a worker thread for a local file costs little) — do
not add a test that expects it local.

**Verify**: `...\python.exe -m pytest -q tests/test_compat.py` → all pass
(4 new). Prove the TTL test guards the cache: temporarily set
`_MOUNTS_TTL = 0.0`, rerun `-k once_per_interval` → FAILS (the table
is read on every call, so `len(reads)` is 3, not 1); revert → passes.

### Step 3: Full suite, lint, commit

**Verify**: whole suite → 3178 + 4 passed, 6 skipped; lint →
`All checks passed!`. Commit
`[FIX] can_stall: paths on Linux network mounts may stall`.

## Test plan

New (4) in `tests/test_compat.py`:
`test_a_path_on_a_network_mount_may_stall`,
`test_a_local_path_beside_a_network_mount_does_not`,
`test_the_mount_table_is_read_once_per_interval`,
`test_on_linux_can_stall_reads_the_mounts`. They monkeypatch
`_compat._read_mounts` (never the real `/proc/mounts`) and reset
`_compat._mounts_cache`, so they pass on Windows and on Linux CI alike.
The callers' existing tests (`tests/test_file_path_widget.py`,
`tests/test_item_views.py`) must pass unchanged on both.

## Done criteria

- [ ] Whole suite exits 0 with 3178 + 4 passed, 6 skipped
- [ ] Lint exits 0
- [ ] `grep -n "_NETWORK_FS\|def _read_mounts\|def _on_network_mount" fxgui/_compat.py` → at least 3 lines
- [ ] `git status` shows only `fxgui/_compat.py` and `tests/test_compat.py` changed
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts.
- `test_on_linux_can_stall_reads_the_mounts` breaks other tests in the same
  run (patching `sys.platform` leaked): report instead of dropping the
  test; `monkeypatch` must restore it.
- On Linux CI, `tests/test_file_path_widget.py` or `tests/test_item_views.py`
  start failing: the runner's `/proc/mounts` lists a network type over the
  temp folder (`can_stall` now True for test files); report the runner's
  mount line for `/tmp`.
- The fix seems to need a change in a caller.

## Maintenance notes

- Other network or parallel file systems used in VFX (Lustre `lustre`,
  GPFS `gpfs`, BeeGFS `beegfs`, WekaFS `wekafs`, AFS `afs`) are not in
  `_NETWORK_FS`; add their type names when a studio reports a stall.
- A mount made in the last 30 s may be missed until the table is re-read;
  the first drop onto a brand-new mount can still block once.
- A local mount nested under a network one counts as may-stall (see
  Step 2): harmless, it only moves a fast read to a worker thread.
- Reviewers: check `can_stall` stays free of disk reads besides the
  cached table (it runs while painting), and that `posixpath` is used, not
  `os.path`, inside `_on_network_mount`.
- Pascal: nothing to change; Pascal is Windows-first and gains this only
  if it runs on Linux.
