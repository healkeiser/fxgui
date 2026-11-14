# Plan 019: Public names for the private things Pascal reaches into

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxdocking.py fxgui/fxstyle.py fxgui/fxicons.py fxgui/fxwidgets/_delegates.py fxgui/fxwidgets/_keyboard.py tests/conftest.py tests/test_focus_visibility.py tests/test_fxstyle_fonts.py tests/test_selection_palette.py tests/test_tips.py tests/test_fxdocking.py tests/test_fxstyle.py tests/test_fxicons.py tests/test_delegate_layout.py tests/test_keyboard_widgets.py docs/how-to/widgets.md docs/how-to/theming.md docs/how-to/icons.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M (five small, independent additions, each with a test and a doc line)
- **Risk**: LOW
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Pascal, fxgui's main consumer (a studio pipeline), reaches into fxgui's
private names or into QtAds directly for five ordinary needs. Each reach
breaks silently when fxgui renames a private, and one breaks Pascal's own
rule (its `pyproject.toml` forbids importing `PySide6QtAds` outside
`fxgui.fxdocking`, yet it calls QtAds methods on the panes fxgui hands out).
Other vendors using fxgui have the same needs. This plan adds a small public
name for each, keeps every old private name working, and documents them.

The five reaches (ls-pascal `origin/main`):

1. Closing / asking about a pane: `manager().findDockWidget(name)` then QtAds
   `toggleView(False)` / `isClosed()` (`apps/launcher/views/popup.py:405,424`,
   `apps/window.py:386`, `apps/workflows/views/window.py:333-334`). fxgui has
   `FXDockArea.show_dock(name)` but no hide or is-open.
2. Forgetting a themed root: `fxstyle._themed_roots.discard(app)`
   (`tests/apps/conftest.py:844,1173`, commented "fxgui offers no way to
   unregister a root but its own registry"). fxgui's own tests do the same.
3. Aligning a spinner with the delegate's icon: private
   `FXThumbnailDelegate._ICON_MARGIN` / `_ICON_SIZE` (`apps/views/tree.py:424-426`).
4. Re-running the filter after refilling a tree:
   `fxutils.filter_tree(tree, bar.text())` by hand
   (`apps/hub/views/metadata.py:219`, `apps/hub/views/detail_blocks.py:262`),
   because `FXFilteredTree._filter` is private.
5. Pointing the icon cache somewhere else: tests monkeypatch `tempfile`
   inside `fxicons` and `fxstyle` (`tests/apps/conftest.py:829-831`),
   because the unzip folder is `tempfile.gettempdir()`. Also, unzipped icon
   folders of old zip versions are never deleted, so the temp folder grows
   with every fxgui release.

**Public behaviour that changes**: none for existing callers. New names:
`FXDockArea.hide_dock`, `FXDockArea.is_dock_open`,
`fxstyle.unregister_themed_root`, `FXThumbnailDelegate.ICON_SIZE` /
`ICON_MARGIN`, `FXFilteredTree.refilter`, `fxicons.CACHE_DIR_VAR`
(`"FXGUI_CACHE_DIR"`). New behaviour: unzipped icon folders of a zip
version no fxgui process has opened for 30 days are deleted.

## Current state

Files:

- `fxgui/fxdocking.py` — `FXDockArea`; `show_dock` at lines 550-566.
- `fxgui/fxstyle.py` — `_themed_roots` (line 432), `register_themed_root`
  (lines 2218-2240), `__all__` (line 140), sheet icon folder (line 1485),
  sheet cache key (line 2188).
- `fxgui/fxicons.py` — icon lookup cache key (line 302), zip extraction
  `_extracted` (lines 332-361), `__all__` (lines 51-59).
- `fxgui/fxwidgets/_delegates.py` — `FXThumbnailDelegate` metrics
  (lines 529-536); `_ICON_SIZE`/`_ICON_MARGIN` used 14 times in the file.
- `fxgui/fxwidgets/_keyboard.py` — `FXFilteredTree` (lines 175-232).
- `tests/conftest.py` — line 138 `fxstyle._themed_roots.discard(qapp)`.
- Docs: `docs/how-to/widgets.md` (docking paragraph, lines 138-139),
  `docs/how-to/theming.md` ("Registering Themed Roots", lines 322-350),
  `docs/how-to/icons.md`. API pages are generated from docstrings.

`fxgui/fxdocking.py:550-566`:

```python
    def show_dock(self, name: str) -> None:
        """Open the pane `name`, in front of its tabs and its window.

        A closed pane grows open once its window has settled.
        """
        held = self._docks.findDockWidget(name)
        if held is None:
            return
        opening = held.isClosed() and self._settled()
        held.toggleView(True)
        ...
```

`fxgui/fxstyle.py:432` and `2218-2240`:

```python
_themed_roots: "weakref.WeakSet" = weakref.WeakSet()
...
def register_themed_root(root: QObject) -> None:
    """Register a widget (or QApplication) as a themed root.
    ...
    Roots are held weakly; destroyed widgets drop out automatically.
    ...
    """
    if isinstance(root, QWidget) and not _in_host(root):
        return
    _themed_roots.add(root)
    if isinstance(root, QWidget):
        root.setProperty(ROOT_PROPERTY, True)
    _watch_focus()
    _apply_to_root(root, _build_stylesheet(), palette(), font())
```

`tests/conftest.py:108` replaces the set per test
(`fxstyle._themed_roots = type(fxstyle._themed_roots)()`) — leave that line;
line 138 and five test files call `fxstyle._themed_roots.discard(qapp)`:
`tests/conftest.py:138`, `tests/test_focus_visibility.py:92,578`,
`tests/test_fxstyle_fonts.py:325`, `tests/test_selection_palette.py:16`,
`tests/test_tips.py:39`.

`fxgui/fxwidgets/_delegates.py:529-536`:

```python
    _THUMBNAIL_MARGIN = 4
    _THUMBNAIL_BORDER = 2  # 1 px of frame on each side
    _OVERLAY_SIZE = 15
    _OVERLAY_MARGIN = 6
    _CONTENT_SPACING = 5
    _ICON_SIZE = 16
    _ICON_MARGIN = 6
    _TEXT_RIGHT_MARGIN = 10
```

`fxgui/fxwidgets/_keyboard.py:205,219-220`:

```python
        self.filter_bar.search_changed.connect(self._filter)
    ...
    def _filter(self, text: str) -> None:
        fxutils.filter_tree(self.tree, text)
```

`fxgui/fxicons.py:301-303` and `332-345`:

```python
    # A found path is checked again: a temp folder cleaner may delete it.
    key = (path, tempfile.gettempdir())
    found = _found_paths.pop(key, None)
...
def _extracted(archive: str, member: str) -> Optional[str]:
    """Return the path of `member` written out of `archive`, or None.

    Qt and stylesheets take a file, so the icon is written once to the temp
    folder, under a name that changes when the zip does.
    """
    stat = os.stat(archive)
    folder = Path(tempfile.gettempdir()) / "fxgui" / "icons" / (
        f"{Path(archive).stem}-{stat.st_size}-{stat.st_mtime_ns}"
    )
    target = folder / member
    if target.exists():
        return target.as_posix()
```

`fxgui/fxstyle.py:1485` and `2187-2188`:

```python
    folder = Path(tempfile.gettempdir()) / "fxgui" / "sheet_icons"
...
    # The sheet's images live in the temp folder, so it is part of the key.
    key = ("sheet", theme, row_size(), tempfile.gettempdir())
```

Those are `fxstyle`'s only two uses of `tempfile`. Pascal's tests patch
`fxstyle.tempfile` with `monkeypatch.setattr` (which raises if the
attribute is gone), so keep `import tempfile` in `fxstyle.py` (Step 5).

Precedent for an environment-variable constant: `fxstyle.py:360`
`REDUCED_MOTION_VAR = "FXGUI_REDUCED_MOTION"`, listed in `fxstyle.__all__`.

Repo conventions: Google-style docstrings with Args/Returns; public names in
`__all__`; Qt only through `qtpy`; comments say why in one line; tests are
plain functions named as sentences.

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| One test file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_fxdocking.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it, 3178 + the new tests passed, 6 skipped |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |
| Docs build | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m zensical build` (only if zensical is installed in the venv; otherwise skip and say so) | exit 0 (`strict = true`) |

`tests/test_fxdocking.py` needs `PySide6QtAds` (installed in that venv; the
file skips itself without it). Never run tests on the real Qt platform:
conftest forces `offscreen`. Any ad-hoc Python must first call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, and run from the worktree root with `PYTHONPATH=.`.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxdocking.py` — `hide_dock`, `is_dock_open`.
- `fxgui/fxstyle.py` — `unregister_themed_root`, `__all__`, the two cache
  folder uses.
- `fxgui/fxicons.py` — `CACHE_DIR_VAR`, `_cache_dir`, pruning, `__all__`.
- `fxgui/fxwidgets/_delegates.py` — public `ICON_SIZE`, `ICON_MARGIN`.
- `fxgui/fxwidgets/_keyboard.py` — `FXFilteredTree.refilter`.
- `tests/conftest.py`, `tests/test_focus_visibility.py`,
  `tests/test_fxstyle_fonts.py`, `tests/test_selection_palette.py`,
  `tests/test_tips.py` — use `unregister_themed_root`.
- `tests/test_fxdocking.py`, `tests/test_fxstyle.py`, `tests/test_fxicons.py`,
  `tests/test_delegate_layout.py`, `tests/test_keyboard_widgets.py` — new tests.
- `docs/how-to/widgets.md`, `docs/how-to/theming.md`, `docs/how-to/icons.md`.

**Out of scope** (do NOT touch):

- `tests/conftest.py:108` (`fxstyle._themed_roots = type(...)()`) — a
  per-test reset of the whole registry, not an unregister.
- The other private delegate metrics (`_THUMBNAIL_MARGIN`, ...) — nobody
  reaches them; publish only what a consumer needs.
- `fxgui/examples.py` — no new widget.
- Pascal's import of `apply_tip` from `fxgui.fxwidgets._tips`
  (`apps/lightbox/views/window.py:13`, `apps/widgets/player.py:17`):
  `apply_tip` is already public as `fxgui.fxwidgets.apply_tip`; that is a
  Pascal-side fix, nothing for fxgui.
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists (today it
  does not).
- Branch: `feat/public-names-for-what-pascal-reaches`.
- One commit per step, repo style, e.g. `[FEAT] FXDockArea.hide_dock and is_dock_open`.
  End each commit message with the attribution line the operator's
  environment asks for, if any.
- Do not push, tag or release: the operator does.

## Steps

### Step 1: `FXDockArea.hide_dock` and `is_dock_open`

In `fxgui/fxdocking.py`, right after `show_dock`, add:

```python
    def hide_dock(self, name: str) -> None:
        """Close the pane `name`, as its toggle does; nothing if unknown.

        Before the first show, the layout Reset goes back to keeps it closed.
        """
        held = self._docks.findDockWidget(name)
        if held is not None:
            held.toggleView(False)

    def is_dock_open(self, name: str) -> bool:
        """Return whether the pane `name` is open; False if unknown."""
        held = self._docks.findDockWidget(name)
        return held is not None and not held.isClosed()
```

In `tests/test_fxdocking.py`, after `test_show_dock_opens_a_closed_pane_in_front`,
add (uses the file's `_window` helper):

```python
def test_hide_dock_closes_a_pane_and_is_dock_open_says_so(qtbot):
    window = _window(qtbot, ("side", "more"))
    assert window.docks.is_dock_open("side")

    window.docks.hide_dock("side")

    assert not window.docks.is_dock_open("side")
    assert not window.panes["side"].isVisible()
    window.docks.show_dock("side")
    assert window.docks.is_dock_open("side")


def test_an_unknown_pane_is_neither_hidden_nor_open(qtbot):
    window = _window(qtbot)
    window.docks.hide_dock("nope")
    assert not window.docks.is_dock_open("nope")
```

In `docs/how-to/widgets.md`, after the paragraph at lines 138-139
("`fxdocking.FXDockArea` docks named panes ..."), add one sentence:
"`show_dock(name)`, `hide_dock(name)` and `is_dock_open(name)` open, close
and ask about a pane by its name, without reaching for QtAds."

**Verify**: `...\python.exe -m pytest -q tests/test_fxdocking.py -k "hide_dock or unknown_pane"`
→ `2 passed`. Commit `[FEAT] FXDockArea.hide_dock and is_dock_open`.

### Step 2: `fxstyle.unregister_themed_root`

In `fxgui/fxstyle.py`, right after `register_themed_root`, add:

```python
def unregister_themed_root(root: QObject) -> None:
    """Forget `root`: later theme switches no longer restyle it.

    Restores nothing: `root` keeps the sheet, palette and font it wears
    until you set others. Forgetting a root never registered does nothing.

    Args:
        root: A widget or QApplication given to `register_themed_root`.
    """
    _themed_roots.discard(root)
```

Add `"unregister_themed_root",` to `__all__` right after
`"register_themed_root",`.

Replace every `fxstyle._themed_roots.discard(` in `tests/` with
`fxstyle.unregister_themed_root(` (the six lines listed in Current state).
Do not touch `tests/conftest.py:108`.

In `tests/test_fxstyle.py`, after `test_dead_roots_drop_out`, add:

```python
def test_an_unregistered_root_is_left_alone_by_a_switch(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    worn = root.styleSheet()

    fxstyle.unregister_themed_root(root)
    fxstyle.apply_theme("light" if fxstyle.get_theme() != "light" else "dark")

    assert root not in fxstyle._themed_roots
    assert root.styleSheet() == worn


def test_unregistering_an_unknown_root_does_nothing(qtbot):
    stranger = QWidget()
    qtbot.addWidget(stranger)
    fxstyle.unregister_themed_root(stranger)
```

(`QWidget` and `fxstyle` are already imported at the top of
`tests/test_fxstyle.py`.)

In `docs/how-to/theming.md`, section "Registering Themed Roots", after the
paragraph ending "...which a stylesheet may select on." add:
"`fxstyle.unregister_themed_root(root)` forgets a root: later switches skip
it. It keeps the sheet, palette and font it wears; reset them yourself if
you need to, as a test fixture does."

**Verify**: `grep -rn "_themed_roots.discard" tests/` → no output;
`...\python.exe -m pytest -q tests/test_fxstyle.py tests/test_focus_visibility.py tests/test_fxstyle_fonts.py tests/test_selection_palette.py tests/test_tips.py`
→ all pass. Commit `[FEAT] fxstyle.unregister_themed_root`.

### Step 3: Public `FXThumbnailDelegate.ICON_SIZE` and `ICON_MARGIN`

In `fxgui/fxwidgets/_delegates.py`:

1. Rename every `_ICON_SIZE` to `ICON_SIZE` and every `_ICON_MARGIN` to
   `ICON_MARGIN` in this file (14 occurrences; `_TEXT_RIGHT_MARGIN` and the
   other names stay). Check with
   `grep -n "_ICON_SIZE\|_ICON_MARGIN" fxgui/fxwidgets/_delegates.py` → only
   the two alias lines below.
2. Give the two class attributes a doc comment, and keep the old names as
   aliases:

```python
    #: Side of a row's icon, and its gap from the cell's left edge, in px:
    #: what a widget laid over the icon's place (a spinner) lines up with.
    ICON_SIZE = 16
    ICON_MARGIN = 6
    # The old private names, kept for code that read them.
    _ICON_SIZE = ICON_SIZE
    _ICON_MARGIN = ICON_MARGIN
```

In `tests/test_delegate_layout.py`, add:

```python
def test_the_icon_metrics_are_public():
    from fxgui.fxwidgets import FXThumbnailDelegate

    assert FXThumbnailDelegate.ICON_SIZE == 16
    assert FXThumbnailDelegate.ICON_MARGIN == 6
    assert FXThumbnailDelegate._ICON_MARGIN == FXThumbnailDelegate.ICON_MARGIN
```

The existing tests there read `delegate._ICON_MARGIN` /
`delegate._ICON_SIZE` (lines 829, 928, 1049-1051, 1065); switch them to the
public names.

**Verify**: `...\python.exe -m pytest -q tests/test_delegate_layout.py` →
all pass. Commit `[FEAT] FXThumbnailDelegate.ICON_SIZE and ICON_MARGIN`.

### Step 4: `FXFilteredTree.refilter`

In `fxgui/fxwidgets/_keyboard.py`, after `_filter`, add:

```python
    def refilter(self) -> None:
        """Filter the tree again by the bar's text, after refilling it."""
        self._filter(self.filter_bar.text())
```

In `tests/test_keyboard_widgets.py`, after
`test_a_filtered_tree_narrows_as_its_bar_changes`, add (same helpers):

```python
def test_a_refilled_tree_keeps_the_filter_once_refiltered(qtbot):
    panel = FXFilteredTree()
    _window = _shown(qtbot, panel)
    QTreeWidgetItem(panel.tree, ["Beauty"])
    panel.filter_bar.setText("beau")
    panel.refilter()
    late = QTreeWidgetItem(panel.tree, ["Other"])
    assert not late.isHidden()

    panel.refilter()

    assert late.isHidden()
```

**Verify**: `...\python.exe -m pytest -q tests/test_keyboard_widgets.py`
→ all pass. Commit `[FEAT] FXFilteredTree.refilter`.

### Step 5: `FXGUI_CACHE_DIR`, and old unzipped icon folders pruned

In `fxgui/fxicons.py`:

1. Imports: add `import shutil` and `import time` in the `# Built-in` block;
   add `Set` to the `typing` import.
2. Add `"CACHE_DIR_VAR",` to `__all__`.
3. Near `_found_paths` (line 323), add:

```python
#: The environment variable naming the folder fxgui writes icon files to
#: (unzipped icons, stylesheet images); unset, `<temp folder>/fxgui`.
CACHE_DIR_VAR = "FXGUI_CACHE_DIR"

# A zip's unzipped folders no process has opened for this long are deleted.
_STALE_SECONDS = 30 * 24 * 3600
# The unzipped folders this process has marked in use.
_visited: Set[str] = set()


def _cache_dir() -> Path:
    """Return the folder fxgui writes icon files under."""
    named = os.environ.get(CACHE_DIR_VAR)
    return Path(named) if named else Path(tempfile.gettempdir()) / "fxgui"


def _visit(folder: Path, stem: str) -> None:
    """Mark `folder` in use once a process; delete stale versions beside it.

    Another fxgui install may share the folder with another zip version;
    its unzipped folder stays while any process opens it within
    `_STALE_SECONDS`.
    """
    if str(folder) in _visited:
        return
    _visited.add(str(folder))
    with contextlib.suppress(OSError):
        os.utime(folder)
    if not folder.parent.is_dir():
        return
    # Exactly `<stem>-<size>-<mtime>`: "material-*" must miss "material-symbols-*".
    version = re.compile(rf"{re.escape(stem)}-\d+-\d+")
    cutoff = time.time() - _STALE_SECONDS
    for sibling in folder.parent.iterdir():
        if sibling == folder or not version.fullmatch(sibling.name):
            continue
        with contextlib.suppress(OSError):
            if sibling.stat().st_mtime < cutoff:
                shutil.rmtree(sibling, ignore_errors=True)
```

4. Line 302: `key = (path, str(_cache_dir()))` (keep the comment above it,
   with "temp folder" changed to "cache folder").
5. In `_extracted`:

```python
    stat = os.stat(archive)
    stem = Path(archive).stem
    folder = _cache_dir() / "icons" / f"{stem}-{stat.st_size}-{stat.st_mtime_ns}"
    _visit(folder, stem)
    target = folder / member
```

   and in its docstring replace "to the temp folder" with "to the cache
   folder (`CACHE_DIR_VAR`)".

In `fxgui/fxstyle.py`:

6. Line 1485: `folder = fxicons._cache_dir() / "sheet_icons"`.
7. Line 2187-2188: `# The sheet's images live in the cache folder, so it is part of the key.`
   and `key = ("sheet", theme, row_size(), str(fxicons._cache_dir()))`.
8. `tempfile` is now unused in `fxstyle.py`; keep the import so code that
   patches `fxstyle.tempfile` keeps working:
   `import tempfile  # noqa: F401 - patched by callers' tests; FXGUI_CACHE_DIR replaces that`.

In `tests/test_fxicons.py`, after `test_a_deleted_extracted_icon_is_extracted_again`,
add:

```python
def test_icons_unzip_into_the_folder_the_variable_names(qapp, monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    monkeypatch.setenv(fxicons.CACHE_DIR_VAR, str(cache))

    path = Path(fxicons.get_icon_path("add", library="material"))

    assert cache / "icons" in path.parents


def test_stale_unzipped_versions_are_pruned_and_others_kept(
    qapp, monkeypatch, tmp_path
):
    import os
    import time

    cache = tmp_path / "cache"
    monkeypatch.setenv(fxicons.CACHE_DIR_VAR, str(cache))
    monkeypatch.setattr(fxicons, "_visited", set())
    icons = cache / "icons"
    stale = icons / "material-1-2"
    fresh = icons / "material-3-4"
    other = icons / "material-symbols-1-2"
    for folder in (stale, fresh, other):
        (folder / "x").mkdir(parents=True)
    old = time.time() - 40 * 24 * 3600
    for folder in (stale, other):
        os.utime(folder, (old, old))

    fxicons.get_icon_path("add", library="material")

    assert not stale.exists()
    assert fresh.exists()
    assert other.exists()
```

In `docs/how-to/icons.md`, before `## QtAwesome (Optional)`, add:

```markdown
## Where fxgui writes icon files

Icons shipped as a zip are unzipped once, into
`<temp folder>/fxgui/icons/<zip>-<size>-<date>/`, and stylesheet images go
to `<temp folder>/fxgui/sheet_icons/`. Set the `FXGUI_CACHE_DIR`
environment variable (`fxicons.CACHE_DIR_VAR`) to use another folder, such
as a test's own. An unzipped folder of a zip version no fxgui process has
opened for 30 days is deleted the next time fxgui unzips an icon.
```

**Verify**: `...\python.exe -m pytest -q tests/test_fxicons.py tests/test_fxstyle.py`
→ all pass; `grep -n "tempfile.gettempdir" fxgui/fxstyle.py` → no output;
`grep -n "tempfile.gettempdir" fxgui/fxicons.py` → one line (inside
`_cache_dir`). Commit `[FEAT] FXGUI_CACHE_DIR, and stale unzipped icons pruned`.

### Step 6: Full suite, lint, docs

**Verify**: whole suite → 3178 + 8 passed, 6 skipped; lint →
`All checks passed!`; docs build (if zensical is installed) → exit 0.

## Test plan

New tests (8): `test_hide_dock_closes_a_pane_and_is_dock_open_says_so`,
`test_an_unknown_pane_is_neither_hidden_nor_open` (test_fxdocking.py);
`test_an_unregistered_root_is_left_alone_by_a_switch`,
`test_unregistering_an_unknown_root_does_nothing` (test_fxstyle.py);
`test_the_icon_metrics_are_public` (test_delegate_layout.py);
`test_a_refilled_tree_keeps_the_filter_once_refiltered`
(test_keyboard_widgets.py);
`test_icons_unzip_into_the_folder_the_variable_names`,
`test_stale_unzipped_versions_are_pruned_and_others_kept` (test_fxicons.py).

Changed: the six `_themed_roots.discard` lines; the delegate-layout tests
that read `_ICON_*`.

Each new test sits beside the existing test of the same feature and uses
that file's helpers.

## Done criteria

- [ ] Whole suite exits 0 with 3178 + 8 passed, 6 skipped
- [ ] Lint exits 0
- [ ] `grep -rn "_themed_roots.discard" tests/` → no output
- [ ] `grep -n "def hide_dock\|def is_dock_open" fxgui/fxdocking.py` → 2 matches
- [ ] `grep -n "\"unregister_themed_root\"" fxgui/fxstyle.py` and `grep -n "\"CACHE_DIR_VAR\"" fxgui/fxicons.py` → 1 match each
- [ ] `git status` shows only in-scope files changed
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts.
- `test_hide_dock_closes_a_pane_and_is_dock_open_says_so` fails because the
  pane still shows after `hide_dock`: QtAds' `toggleView(False)` behaves
  differently on this version; report the QtAds version
  (`...\python.exe -c "import PySide6QtAds as a; print(a.__file__)"`).
- After Step 3, a test outside `test_delegate_layout.py` fails: something
  overrides `_ICON_SIZE`/`_ICON_MARGIN` in a subclass; list it.
- `test_stale_unzipped_versions_are_pruned_and_others_kept` fails because
  `stale` still exists: `os.utime` on a folder failed on this file system;
  report the error, do not lower `_STALE_SECONDS`.
- Any existing `tests/test_fxicons.py` or `tests/test_fxstyle.py` test that
  patches `tempfile` fails: that test relies on the temp folder; report it
  instead of changing it.

## Maintenance notes

- Pruning is age-based: a fxgui process that runs for more than 30 days
  without unzipping a new icon, beside another fxgui install with another
  zip version, could see that install delete its folder; its icons already
  drawn stay in Qt's pixmap cache, new draws of a deleted file come out
  blank until a restart. Lengthen `_STALE_SECONDS` if that ever happens.
- Reviewers: check the sibling regex (`material` must not match
  `material-symbols-...`) and that `_cache_dir()` is read at call time, not
  import time (tests and Pascal set the variable per test).
- `fxstyle.py` keeps an unused `import tempfile` with a `noqa`; delete it
  once no consumer patches `fxstyle.tempfile`.
- Pascal: once this ships, it can replace `manager().findDockWidget(n).toggleView(False)`
  with `hide_dock(n)` (`apps/launcher/views/popup.py:405`, `apps/window.py:386`),
  `not ...isClosed()` with `is_dock_open(n)` (`apps/workflows/views/window.py:333-334`),
  `fxstyle._themed_roots.discard(app)` with `fxstyle.unregister_themed_root(app)`
  (`tests/apps/conftest.py:844,1173`), `_ICON_MARGIN`/`_ICON_SIZE` with the
  public names (`apps/views/tree.py:424-426`), the hand-run `filter_tree`
  with `panel.refilter()` (`apps/hub/views/metadata.py:219`,
  `detail_blocks.py:262`), the two `tempfile` monkeypatches with
  `monkeypatch.setenv("FXGUI_CACHE_DIR", shared)` (`tests/apps/conftest.py:829-831`),
  and import `apply_tip` from `fxgui.fxwidgets` instead of `_tips`.
