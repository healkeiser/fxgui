# Plan 020: A window can hold any shortcut to itself, and a restart can wait for the lock without waking the old copy

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_main_window.py fxgui/fxwidgets/_single_instance.py tests/test_main_window.py tests/test_single_instance.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. (If plan 021 landed first,
> `_single_instance.py` already has `_lock_file` and `_listen`: see Step 3.)

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (plan 021 edits the same file; either order works, see Step 3)
- **Category**: direction
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Two places where Pascal (fxgui's main consumer, a studio pipeline)
re-implements what fxgui half-offers:

1. **Shortcut scoping.** When an `FXMainWindow` is embedded in a host
   window (a DCC panel), fxgui switches its five own actions (Close, Always
   on Top, Minimize, Maximize, Refresh) to `WidgetWithChildrenShortcut`, so
   their keys do not fire anywhere in the host. An application's own
   actions get no such care, so Pascal re-implements the same reparent hook
   for all of them (`apps/window.py:722-740`). A public
   `scope_shortcut(action)` lets any window opt its actions and
   `QShortcut`s into fxgui's rule.
2. **Restart.** `FXSingleInstance.claim(message)` either takes the lock or
   hands `message` to the running copy. A restart (new process started
   while the old one quits) wants neither: it must wait for the old copy to
   let go. Pascal loops on `claim(link)` (`apps/launcher/__main__.py:599-617`):
   each failed try hands the link to the exiting launcher (which may open
   it, or lose it while quitting) and wakes it, and when the old copy stops
   answering mid-quit, `claim` raises `RuntimeError` after 5 s, which that
   loop does not catch. A `try_claim()` that only takes the lock, never
   contacting the holder, makes that loop correct.

**Public behaviour that changes**: new methods only
(`FXMainWindow.scope_shortcut`, `FXSingleInstance.try_claim`). One defect
fix: calling `claim()` again on the copy that already holds the name now
returns True at once (before: it handed its message to itself and raised
`RuntimeError` after 5 s).

### Options considered and not planned

- `FXMainWindow(menu_bar=False)`: Pascal hides the bar with
  `window.menuBar().setVisible(False)` (`apps/save_form.py:48`,
  `apps/scene_manager/views/window.py:160`) — one standard Qt call — and
  still needs the menus built: its `AppWindow` passes `self.window_menu` to
  its pane manager in `__init__` (`apps/window.py:182`) and reads
  `menuBar().isHidden()` (`apps/window.py:709,868`). An option that skips
  building the bar would break that, and one that only hides it saves one
  line. Not worth an argument.
- `FXMainWindow(status_bar=...)`: Pascal installs its `StatusBar`, a
  subclass of `FXStatusBar`, with `self.setStatusBar(...)` (`apps/window.py:177-181`),
  the standard Qt call; `FXMainWindow.setStatusBar` already frames it. The
  only waste is one unused `FXStatusBar` built and deleted at start.
- Banner text and action icons (Pascal reaches the `fxBannerAction`
  objectName in `widgets/banner.py:56-58`): handled by plan 011, not here.
- `claim(message, hand_over=False)` instead of `try_claim()`: rejected
  because it changes what `claim`'s False means ("handed over" versus
  "someone else holds it") depending on a flag; a separate method keeps
  `claim`'s contract and reads plainly at the call site.

## Current state

Files:

- `fxgui/fxwidgets/_main_window.py` — `FXMainWindow`; `_scope_shortcuts`
  (lines 196-219), called from `__init__` (line 193) and from `event()` on
  `QEvent.ParentChange` (lines 594-595).
- `fxgui/fxwidgets/_single_instance.py` — `FXSingleInstance`; `claim`
  (lines 64-115).
- `tests/test_main_window.py` — has `_host_with_embedded(qtbot)` (lines
  28-48) and the two existing scoping tests (lines 51-82): the pattern.
- `tests/test_single_instance.py` — `_name(tag)` helper and single-instance
  tests: the pattern.

`fxgui/fxwidgets/_main_window.py:196-219`:

```python
    def _scope_shortcuts(self) -> None:
        """Hold the window's shortcuts to this widget while it is embedded.

        Window-wide, an embedded copy's Ctrl+Alt+Q would close it from
        anywhere in the host's window.
        """
        actions = [
            getattr(self, name, None)
            for name in (
                "close_action",
                "window_on_top_action",
                "minimize_window_action",
                "maximize_window_action",
                "refresh_action",
            )
        ]
        embedded = not self.isWindow()
        for action in filter(None, actions):
            action.setShortcutContext(
                Qt.WidgetWithChildrenShortcut if embedded else Qt.WindowShortcut
            )
            # A menu's action matches a widget scope only through a widget.
            if embedded and action not in self.actions():
                self.addAction(action)
```

`getattr(..., None)` is deliberate: Qt can send `ParentChange` while
`QMainWindow.__init__` runs, before `_create_actions`. Anything new read in
`_scope_shortcuts` must be read the same defensive way.

`fxgui/fxwidgets/_single_instance.py:81-115` (`claim`):

```python
        from qtpy.QtNetwork import QLocalServer

        payload = message.encode("utf-8")
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError(...)
        # Windows lets two servers listen on one name, so two starts in the
        # same instant would both win the probe: a lock file picks one.
        digest = hashlib.sha256(self._name.encode("utf-8")).hexdigest()[:24]
        lock = QLockFile(os.path.join(QDir.tempPath(), f"fxgui-{digest}.lock"))
        # Stale only when its process is gone, however long a copy runs.
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            deadline = time.monotonic() + _REACH_SECONDS
            while not self._hand_over(payload):
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        f"the copy holding {self._name!r} does not answer")
                QThread.msleep(_RETRY_MS)
            return False
        # A crash leaves the socket file on some platforms; on Windows a no-op.
        QLocalServer.removeServer(self._name)
        server = QLocalServer(self)
        # Another account on the machine cannot hand this copy a message.
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not server.listen(self._name):
            lock.unlock()
            raise RuntimeError(
                f"cannot listen on {self._name!r}: {server.errorString()}")
        server.newConnection.connect(self._on_connection)
        self._server = server
        self._lock = lock
        self.destroyed.connect(lock.unlock)
        return True
```

`self._lock` is None until this object holds the name (set in `__init__`,
line 62).

Pascal's code this replaces (ls-pascal `origin/main`,
`src/ls_pascal/apps/window.py:722-740`):

```python
    def changeEvent(self, event: QEvent) -> None:
        """Rescope keys when a host adopts this window."""
        super().changeEvent(event)
        if event.type() == QEvent.Type.ParentChange:
            self._scope_keys()

    def _scope_keys(self) -> None:
        """Answer this window's keys only from inside it, once embedded."""
        if self.isWindow():
            return
        inside = Qt.ShortcutContext.WidgetWithChildrenShortcut
        for shortcut in self.findChildren(
            QShortcut, options=Qt.FindChildOption.FindDirectChildrenOnly
        ):
            shortcut.setContext(inside)
        for action in self.actions():
            action.setShortcutContext(inside)
```

Repo conventions: Qt only through `qtpy` (`QShortcut` comes from
`qtpy.QtGui`, as in `fxgui/fxdocking.py:32`); Google-style docstrings;
`_compat.is_valid(obj)` tells whether a Qt object's C++ side still lives
(`fxgui/_compat.py`); tests are plain functions named as sentences.

## Commands you will need

Run everything from the worktree root.

| Purpose | Command | Expected on success |
|---|---|---|
| Window tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_main_window.py` | all pass |
| Lock tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_single_instance.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it, 3178 + the new tests passed, 6 skipped |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

Never run tests on the real Qt platform: conftest forces `offscreen`. Any
ad-hoc Python must first call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, and run from the worktree root with `PYTHONPATH=.`.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_main_window.py` — `scope_shortcut`, `_scope_shortcuts`.
- `fxgui/fxwidgets/_single_instance.py` — `try_claim`, `_lock_file`,
  `_listen`, the re-claim guard.
- `tests/test_main_window.py`, `tests/test_single_instance.py` — new tests.

**Out of scope** (do NOT touch):

- `FXMainWindow.__init__`'s signature — no `menu_bar`/`status_bar` options
  (see "Options considered and not planned").
- `_hand_over` and `_on_connection` in `_single_instance.py` — the
  hand-over protocol is plan 021.
- `fxgui/fxwidgets/_notification_banner.py` — plan 011.
- `fxgui/examples.py` — no new widget (`FXSingleInstance` is exempt from
  the gallery, `tests/test_gallery.py:20`).
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists (today it
  does not).
- Branch: `feat/window-chrome-options`.
- Commits, repo style: `[FEAT] FXMainWindow.scope_shortcut`,
  `[FEAT] FXSingleInstance.try_claim`. End each commit message with the
  attribution line the operator's environment asks for, if any.
- Do not push, tag or release: the operator does.

## Steps

### Step 1: `FXMainWindow.scope_shortcut`

In `fxgui/fxwidgets/_main_window.py`:

1. Imports: `from qtpy.QtGui import QAction, QIcon, QShortcut, QStatusTipEvent`;
   `from fxgui import _compat, fxconstants, fxicons, fxstyle, fxutils`;
   add `List` to the `typing` import.
2. In `__init__`, right after `self.row_size_actions: Dict[str, QAction] = {}`,
   add `self._scoped: List[Union[QAction, QShortcut]] = []`.
3. Replace the loop at the end of `_scope_shortcuts` with:

```python
        embedded = not self.isWindow()
        context = Qt.WidgetWithChildrenShortcut if embedded else Qt.WindowShortcut
        # Read defensively: Qt may send ParentChange before __init__ set it.
        scoped = [
            held for held in getattr(self, "_scoped", ()) if _compat.is_valid(held)
        ]
        for held in [*filter(None, actions), *scoped]:
            if isinstance(held, QShortcut):
                held.setContext(context)
                continue
            held.setShortcutContext(context)
            # A menu's action matches a widget scope only through a widget.
            if embedded and held not in self.actions():
                self.addAction(held)
```

4. In the `# Public methods` section, after `center_on_screen`, add:

```python
    def scope_shortcut(self, shortcut: Union[QAction, QShortcut]) -> None:
        """Hold `shortcut` to this window while a host embeds it.

        As for the window's own actions: window-wide while it is a window,
        and only from inside it while embedded, so its key never fires
        elsewhere in the host's window. Applies now and on every reparent.

        Args:
            shortcut: An action, or a `QShortcut` whose parent is in this
                window.
        """
        if shortcut not in self._scoped:
            self._scoped.append(shortcut)
        self._scope_shortcuts()
```

5. Update the `_scope_shortcuts` docstring's first line to
   "Hold the window's shortcuts, and the scoped ones, to it while embedded."

In `tests/test_main_window.py`, after
`test_a_window_moved_into_a_host_scopes_its_shortcuts`, add:

```python
def test_a_scoped_action_stays_out_of_the_host(qtbot):
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QAction
    from qtpy.QtTest import QTest

    _host, elsewhere, embedded = _host_with_embedded(qtbot)
    action = QAction("Run", embedded)
    action.setShortcut("Ctrl+Alt+K")
    ran = []
    action.triggered.connect(lambda: ran.append(True))
    embedded.scope_shortcut(action)

    QTest.keyClick(elsewhere, Qt.Key_K, Qt.ControlModifier | Qt.AltModifier)
    assert ran == []

    inside = embedded.centralWidget()
    inside.setFocus()
    QTest.keyClick(inside, Qt.Key_K, Qt.ControlModifier | Qt.AltModifier)
    assert ran == [True]


def test_a_scoped_shortcut_follows_the_window_into_a_host(qtbot):
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QAction, QKeySequence, QShortcut
    from qtpy.QtWidgets import QWidget

    from fxgui.fxwidgets import FXMainWindow

    window = FXMainWindow()
    qtbot.addWidget(window)
    action = QAction("Run", window)
    shortcut = QShortcut(QKeySequence("Ctrl+J"), window)
    window.scope_shortcut(action)
    window.scope_shortcut(shortcut)
    assert action.shortcutContext() == Qt.WindowShortcut
    host = QWidget()
    qtbot.addWidget(host)

    window.setParent(host)

    assert action.shortcutContext() == Qt.WidgetWithChildrenShortcut
    assert shortcut.context() == Qt.WidgetWithChildrenShortcut


def test_a_deleted_scoped_action_is_skipped(qtbot):
    from qtpy.QtCore import QEvent, Qt
    from qtpy.QtGui import QAction
    from qtpy.QtWidgets import QApplication, QWidget

    from fxgui.fxwidgets import FXMainWindow

    window = FXMainWindow()
    qtbot.addWidget(window)
    action = QAction("Run", window)
    window.scope_shortcut(action)
    action.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    host = QWidget()
    qtbot.addWidget(host)

    window.setParent(host)

    # The reparent went through the scoped list, dead action and all.
    assert window.close_action.shortcutContext() == Qt.WidgetWithChildrenShortcut
```

**Verify**: `...\python.exe -m pytest -q tests/test_main_window.py` → all
pass (3 new). Prove the first test guards the feature: temporarily make
`scope_shortcut` a bare `return`, rerun `-k scoped_action_stays` → FAILS
(`ran == [True]` after the click outside, or the inside click not
landing); revert → passes. Commit `[FEAT] FXMainWindow.scope_shortcut`.

### Step 2: Check `_single_instance.py` for plan 021's helpers

Run `grep -n "def _lock_file\|def _listen" fxgui/fxwidgets/_single_instance.py`.

- Two matches (plan 021 landed): skip Step 3's "extract" part and use them.
- No output: do Step 3 in full.

### Step 3: `FXSingleInstance.try_claim`

In `fxgui/fxwidgets/_single_instance.py`:

1. Extract the lock file and the listening into two private methods, and
   make `claim` use them (no behaviour change):

```python
    def _lock_file(self) -> QLockFile:
        """Return the lock file that picks one holder of the name."""
        # Windows lets two servers listen on one name, so two starts in the
        # same instant would both win the probe: a lock file picks one.
        digest = hashlib.sha256(self._name.encode("utf-8")).hexdigest()[:24]
        lock = QLockFile(os.path.join(QDir.tempPath(), f"fxgui-{digest}.lock"))
        # Stale only when its process is gone, however long a copy runs.
        lock.setStaleLockTime(0)
        return lock

    def _listen(self, lock: QLockFile) -> None:
        """Listen on the name under the held `lock`.

        Raises:
            RuntimeError: The name cannot be listened on.
        """
        from qtpy.QtNetwork import QLocalServer

        # A crash leaves the socket file on some platforms; on Windows a no-op.
        QLocalServer.removeServer(self._name)
        server = QLocalServer(self)
        # Another account on the machine cannot hand this copy a message.
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not server.listen(self._name):
            lock.unlock()
            raise RuntimeError(
                f"cannot listen on {self._name!r}: {server.errorString()}")
        server.newConnection.connect(self._on_connection)
        self._server = server
        self._lock = lock
        self.destroyed.connect(lock.unlock)
```

   `claim` becomes: size check; `if self._lock is not None: return True`
   (comment: `# Already the holder: handing over would knock on itself.`);
   `lock = self._lock_file()`; the unchanged `if not lock.tryLock(0): ...`
   hand-over loop; then `self._listen(lock)` and `return True`. Move the
   `from qtpy.QtNetwork import QLocalServer` line into `_listen` (claim no
   longer uses it).

2. After `claim`, add:

```python
    def try_claim(self) -> bool:
        """Take the name if no copy holds it; never contact the holder.

        For a start that must wait for a copy on its way out, such as a
        restart: call it until it returns True, pausing between calls.
        `claim` instead hands a message to a running copy.

        Returns:
            True when this process holds the name, now or already.

        Raises:
            RuntimeError: No copy holds the name, but it cannot be
                listened on.
        """
        if self._lock is not None:
            return True
        lock = self._lock_file()
        if not lock.tryLock(0):
            return False
        self._listen(lock)
        return True
```

3. Add one line to the class docstring's `Examples:` block:
   `>>> # A restart: while not instance.try_claim(): wait, then retry`.

In `tests/test_single_instance.py`, add:

```python
def test_try_claim_takes_a_free_name_and_never_wakes_the_holder(qtbot):
    first = FXSingleInstance(_name("try"))
    assert first.try_claim()
    woken = []
    first.woken.connect(lambda: woken.append(True))

    assert not FXSingleInstance(_name("try")).try_claim()
    qtbot.wait(200)

    assert woken == []


def test_try_claim_takes_a_name_once_its_holder_is_gone(qtbot):
    first = FXSingleInstance(_name("try-again"))
    assert first.claim()
    first.deleteLater()
    qtbot.wait(50)

    assert FXSingleInstance(_name("try-again")).try_claim()


def test_the_holder_claiming_again_keeps_the_name_at_once(qtbot):
    import time

    first = FXSingleInstance(_name("twice"))
    assert first.claim()

    start = time.monotonic()
    assert first.claim("again")
    assert first.try_claim()
    assert time.monotonic() - start < 1
```

**Verify**: `...\python.exe -m pytest -q tests/test_single_instance.py` →
all pass (3 new; the file takes ~10 s because some tests start
subprocesses). Prove the last test guards the fix: temporarily remove the
`if self._lock is not None: return True` guard from `claim`, rerun
`-k claiming_again` → FAILS (`RuntimeError: ... does not answer` after
~5 s); revert → passes. Commit `[FEAT] FXSingleInstance.try_claim`.

### Step 4: Full suite and lint

**Verify**: whole suite → 3178 + 6 passed, 6 skipped; lint →
`All checks passed!`.

## Test plan

- `tests/test_main_window.py`: `test_a_scoped_action_stays_out_of_the_host`,
  `test_a_scoped_shortcut_follows_the_window_into_a_host`,
  `test_a_deleted_scoped_action_is_skipped` — pattern: the two scoping tests
  at lines 51-82 and the `_host_with_embedded` helper.
- `tests/test_single_instance.py`:
  `test_try_claim_takes_a_free_name_and_never_wakes_the_holder`,
  `test_try_claim_takes_a_name_once_its_holder_is_gone`,
  `test_the_holder_claiming_again_keeps_the_name_at_once` — pattern:
  `test_a_second_claim_is_refused_and_wakes_the_first` and
  `test_a_released_name_can_be_claimed_again`.
- Existing scoping and lock tests must pass unchanged.

## Done criteria

- [ ] Whole suite exits 0 with 3178 + 6 passed, 6 skipped
- [ ] Lint exits 0
- [ ] `grep -n "def scope_shortcut" fxgui/fxwidgets/_main_window.py` → 1 match
- [ ] `grep -n "def try_claim\|def _lock_file\|def _listen" fxgui/fxwidgets/_single_instance.py` → 3 matches
- [ ] `git diff b283eb13 -- fxgui/fxwidgets/_main_window.py | grep "def __init__"` → no output (signature untouched)
- [ ] `git status` shows only in-scope files changed
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts
  (other than plan 021's `_lock_file`/`_listen`, handled in Step 2).
- `test_a_scoped_action_stays_out_of_the_host` fails on the click *inside*
  the window: the action is not reachable through a widget; do not switch
  the context to `ApplicationShortcut` — report.
- Any existing test in `tests/test_main_window*.py`, `tests/test_framed_window.py`
  or `tests/test_fxdocking.py` fails after Step 1 (they build many
  windows; a crash there means `_scope_shortcuts` touched a deleted
  object).
- `test_a_second_process_hands_its_message_to_the_first` or the race test
  fails after Step 3: the extraction changed behaviour; diff `claim`
  against the excerpt.

## Maintenance notes

- `scope_shortcut` is opt-in per action on purpose: scoping every action
  of `self.actions()` automatically would change the context of actions
  vendors set themselves (an `ApplicationShortcut` included).
- Reviewers: `_scope_shortcuts` must keep reading `_scoped` with `getattr`
  (ParentChange can arrive before `__init__` sets it) and skip dead
  wrappers.
- Plan 021 changes `claim`'s hand-over to wait for an acknowledgement; it
  reuses `_lock_file`/`_listen` from here if this lands first.
- Pascal: once this ships, `apps/launcher/__main__.py:claim_lock` can loop
  on `instance.try_claim()` for a restart (no link handed to, no wake of,
  the exiting launcher; no uncaught `RuntimeError`), then open its own
  link; and `apps/window.py:722-740` (`changeEvent` + `_scope_keys`) can
  go, with each action and `QShortcut` the window makes passed to
  `self.scope_shortcut(...)` where it is created.
