# Plan 021: A second start counts its message as handed over only once the running copy acknowledges it

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_single_instance.py tests/test_single_instance.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition — except the changes plan 020
> makes (`_lock_file`, `_listen`, `try_claim`, a `self._lock is not None`
> guard in `claim`), which this plan expects and rewrites in place.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: none (plan 020 edits the same file; either order works)
- **Category**: bug
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`FXSingleInstance` keeps one running copy of an application. A second start
calls `claim(message)`; when another copy holds the name, the message (for
Pascal, a browser `lotchi://` link) is written to the copy's local socket
and `claim` returns False, so the second start exits. Today "written" is
taken for "delivered": the sender ignores whether the bytes were read and
returns True as soon as it connected. A probe confirmed that a copy whose
event loop is blocked still accepts connections, so when the running copy
is hung or quitting, the second start exits 0 and the link is silently
lost.

After this plan, the running copy acknowledges a message with one byte as
soon as it has read it whole. A sender that gets no acknowledgement by the
5 s deadline does not report success: `claim` keeps trying, takes the name
itself if the old copy let go meanwhile, or raises `RuntimeError` (the
error `claim` already documents for "the copy holding it never answers").

**Version tolerance — the chosen rule.** Copies with old and new fxgui
meet in practice (a long-running launcher across an fxgui update). An old
copy reads until the sender hangs up and never answers, so a new sender
cannot simply wait for an answer from everyone, and an old copy would show
any new framing bytes as part of the message. So the new copy listens on
**two names**: the bare name (old protocol, unchanged, for old senders) and
`name + "-ack"` (framed, acknowledged). A new sender tries `name-ack`
first; only when that name *does not exist* (Qt reports
`ServerNotFoundError`, or `ConnectionRefusedError` for a stale Unix socket
file) does it fall back to the old, unconfirmed way on the bare name. A
hung new copy still has `name-ack`, so it is never mistaken for an old one.

Trade-offs, stated: a new start talking to an *old* copy is exactly as
unsafe as today (nothing to do without changing the old copy). A
`RuntimeError` means "not confirmed", not "not delivered": a copy that
answers after the deadline may still have read it. Rejected alternatives:
"a clean disconnect after a full write counts as delivered" (the probe
shows a hung copy accepts the write into the pipe buffer, so this proves
nothing); "the holder greets each connection with a byte" (a hung new copy
sends no greeting and looks exactly like an old one, so the main failure
falls back to the lossy path).

**Public behaviour that changes**: `claim` may now raise `RuntimeError`
where it used to return False (a connected copy that never reads); and a
`claim` whose holder lets go during the 5 s wait now takes the name and
returns True (before: `RuntimeError`). The signature is unchanged.

## Current state

Files:

- `fxgui/fxwidgets/_single_instance.py` — the whole feature (164 lines).
- `tests/test_single_instance.py` — tests; the pattern. Read its comment
  at line 46: "A message is read while the sender waits, so the sender is
  another process." A sending `claim` blocks its thread, so the copy that
  must answer cannot live in the same thread: every new test that calls
  `claim` as a sender runs it in a subprocess (`_send`, lines 47-60), and
  in-process senders are raw, non-blocking `QLocalSocket`s
  (`test_a_message_over_the_limit_wakes_instead`, lines 84-100).

`fxgui/fxwidgets/_single_instance.py:13-22` (constants):

```python
# Long enough for a named pipe on a loaded machine, unfelt on first start.
_PROBE_MS = 300

# How long a start that lost the lock keeps knocking while the winner,
# started in the same instant, comes up to listen.
_REACH_SECONDS = 5.0
_RETRY_MS = 50

# A message is a wake-up note, not a transfer: anything longer is dropped.
MAX_MESSAGE_BYTES = 64 * 1024
```

`claim` (lines 81-115) — see plan 020 for the full excerpt; the parts that
matter here:

```python
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
            ...
```

`_hand_over` (lines 117-132) — returns True once connected; `write` and
`waitForBytesWritten` results are ignored:

```python
    def _hand_over(self, payload: bytes) -> bool:
        """Hand `payload` to the copy listening on the name, if one answers."""
        from qtpy.QtNetwork import QLocalSocket

        probe = QLocalSocket()
        probe.connectToServer(self._name)
        if not probe.waitForConnected(_PROBE_MS):
            return False
        if payload:
            probe.write(payload)
            probe.waitForBytesWritten(_PROBE_MS)
        probe.disconnectFromServer()
        # Unwritten bytes keep it closing; leaving now would lose them.
        if probe.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            probe.waitForDisconnected(_PROBE_MS)
        return True
```

`_on_connection` (lines 134-164) reads until the sender hangs up; empty or
oversized → `woken`, else `messaged(text)`:

```python
        def finished() -> None:
            # Its destructor emits `disconnected` again, into a dying object.
            connection.readyRead.disconnect(read)
            connection.disconnected.disconnect(finished)
            read()
            connection.deleteLater()
            if not received or len(received) > MAX_MESSAGE_BYTES:
                self.woken.emit()
                return
            self.messaged.emit(bytes(received).decode("utf-8", "replace"))
```

Facts measured on this machine (Windows, PySide6 6.11.2) with a probe:

- `connectToServer` to a name nobody listens on fails at once with
  `LocalSocketError.ServerNotFoundError`.
- A `QLocalServer` whose event loop never runs still lets a client connect
  (`waitForConnected` True at once), and a second client too; a
  `waitForReadyRead(500)` on it returns False after 500 ms.
- Against a live server that replies after reading: write then
  `waitForReadyRead(2000)` gets the reply in ~15 ms; no
  `waitForBytesWritten` is needed first.

Who owns the name: Qt's `QLocalSocket` has no call that tells which
process or account listens on a name. `UserAccessOption` (line 106) only
limits who may connect to *our* server. On Windows pipe names are
machine-wide, so on a host several people use at once another account
could listen on the name first and be handed a start's message. Not
checked further (LOW confidence it matters: fxgui targets single-user
workstations); this plan documents it in the class docstring.

Repo conventions: Qt only through `qtpy` (QtNetwork is imported inside the
methods on purpose, so a host without it can still import fxgui — keep
that); Google-style docstrings; comments say why, in one line; tests are
plain functions named as sentences.

## Commands you will need

Run everything from the worktree root (the tests' subprocesses import
`fxgui` from the current directory).

| Purpose | Command | Expected on success |
|---|---|---|
| Lock tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_single_instance.py` | all pass (~15-25 s: subprocesses) |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` before this plan; after it, 3178 + the new tests passed, 6 skipped |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` | `All checks passed!` |

Never run tests on the real Qt platform: conftest forces `offscreen`. Any
ad-hoc Python must first call
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before touching fxgui, and run from the worktree root with `PYTHONPATH=.`.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_single_instance.py`
- `tests/test_single_instance.py`

**Out of scope** (do NOT touch):

- The bare-name protocol (`_on_connection`'s read-until-hang-up): old
  senders depend on it byte for byte. Only refactor its final signal into
  `_deliver`.
- `MAX_MESSAGE_BYTES`, `_PROBE_MS`, `_REACH_SECONDS`, `_RETRY_MS` values.
- An owner check on the name (none exists in Qt; a Win32
  `GetNamedPipeServerProcessId` call through ctypes is a separate decision).
- `CHANGELOG.md` — a release action writes it.

## Git workflow

- Work in a git worktree, never the shared checkout. After creating it, run
  `git submodule update --init --depth 1` if `.gitmodules` exists (today it
  does not).
- Branch: `fix/single-instance-handover-is-acknowledged`.
- Commits, repo style, e.g.
  `[FIX] single instance: a hand-over counts only once acknowledged`.
  End each commit message with the attribution line the operator's
  environment asks for, if any.
- Do not push, tag or release: the operator does.

## Steps

### Step 1: Constants and the shared signal

In `fxgui/fxwidgets/_single_instance.py`, under `MAX_MESSAGE_BYTES`, add:

```python
# A copy of this fxgui also listens on the name plus this suffix, where a
# message is framed and acknowledged; an older copy listens on the bare name.
_ACK_SUFFIX = "-ack"
# A framed message: its length in this many big-endian bytes, then the text.
_HEADER = 4
# The byte a copy answers once it has read a framed message whole.
_ACK = b"\x06"
```

In `__init__`, add `self._ack_server = None` beside `self._server = None`.

Add a method used by both read paths:

```python
    def _deliver(self, payload: bytes) -> None:
        """Say what a start handed over: `woken` for nothing, else `messaged`."""
        if not payload:
            self.woken.emit()
            return
        self.messaged.emit(payload.decode("utf-8", "replace"))
```

In `_on_connection`'s `finished`, replace the last four lines (from
`if not received or ...` to the `messaged.emit`) with:

```python
            # Oversized: not a sender of ours; wake rather than show it.
            self._deliver(
                b"" if len(received) > MAX_MESSAGE_BYTES else bytes(received))
```

**Verify**: `...\python.exe -m pytest -q tests/test_single_instance.py` →
all pass (no behaviour change yet).

### Step 2: The holder listens on both names and answers framed messages

1. Make `_lock_file` and `_listen` read exactly as below. If plan 020
   landed they exist: replace `_listen`'s body. If not, create both and
   use them in `claim` (Step 3 shows `claim`'s final form).

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
        """Listen on the name, framed and bare, under the held `lock`.

        Raises:
            RuntimeError: Either name cannot be listened on.
        """
        from qtpy.QtNetwork import QLocalServer

        servers = []
        # The framed name first: a start that finds it never falls back to
        # the unconfirmed bare name.
        for name, slot in (
            (self._name + _ACK_SUFFIX, self._on_framed_connection),
            (self._name, self._on_connection),
        ):
            # A crash leaves the socket file on some platforms; on Windows a no-op.
            QLocalServer.removeServer(name)
            server = QLocalServer(self)
            # Another account on the machine cannot hand this copy a message.
            server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
            if not server.listen(name):
                error = server.errorString()
                for opened in servers:
                    opened.close()
                lock.unlock()
                raise RuntimeError(f"cannot listen on {name!r}: {error}")
            server.newConnection.connect(slot)
            servers.append(server)
        self._ack_server, self._server = servers
        self._lock = lock
        self.destroyed.connect(lock.unlock)
```

2. Add the framed reader after `_on_connection`:

```python
    @Slot()
    def _on_framed_connection(self) -> None:
        """Read one framed message, acknowledge it, then hand it on."""
        from qtpy.QtNetwork import QLocalSocket

        connection = self._ack_server.nextPendingConnection()
        if connection is None:
            return
        received = bytearray()
        state = {"answered": False, "closed": False}

        def read() -> None:
            if state["answered"]:
                return
            received.extend(bytes(connection.readAll()))
            if len(received) < _HEADER:
                return
            size = int.from_bytes(received[:_HEADER], "big")
            if size > MAX_MESSAGE_BYTES or len(received) > _HEADER + size:
                # Not a sender of ours: no answer, no signal.
                state["answered"] = True
                connection.abort()
                return
            if len(received) < _HEADER + size:
                return
            state["answered"] = True
            # Answered before the slots run: a slot may open a dialog and
            # hold the sender past its deadline.
            connection.write(_ACK)
            connection.disconnectFromServer()
            self._deliver(bytes(received[_HEADER:]))

        def finished() -> None:
            if state["closed"]:
                return
            state["closed"] = True
            # Its destructor emits `disconnected` again, into a dying object.
            connection.readyRead.disconnect(read)
            connection.disconnected.disconnect(finished)
            connection.deleteLater()

        connection.readyRead.connect(read)
        connection.disconnected.connect(finished)
        # Bytes that came before this ran raise no `readyRead`.
        read()
        if connection.state() == QLocalSocket.LocalSocketState.UnconnectedState:
            finished()
```

**Verify**: `...\python.exe -m pytest -q tests/test_single_instance.py` →
all pass (senders still use the bare name, which works as before).

### Step 3: The sender waits for the acknowledgement; `claim` retries the lock

1. Rename today's `_hand_over` to `_hand_over_unconfirmed` (body
   unchanged) and change its docstring to
   `"""Hand `payload` the old way, to a copy of an older fxgui: unconfirmed."""`.
2. Add the new `_hand_over`:

```python
    def _hand_over(self, payload: bytes, deadline: float) -> bool:
        """Hand `payload` to the copy holding the name; True once it has it.

        A copy of this fxgui acknowledges a message once read; one that has
        not by `deadline` (hung, or quitting) has not got it. Only when the
        acknowledging name does not exist, an older fxgui, is the payload
        handed over unconfirmed, as that copy expects.
        """
        from qtpy.QtNetwork import QLocalSocket

        probe = QLocalSocket()
        probe.connectToServer(self._name + _ACK_SUFFIX)
        if probe.waitForConnected(_PROBE_MS):
            probe.write(len(payload).to_bytes(_HEADER, "big") + payload)
            wait_ms = max(int((deadline - time.monotonic()) * 1000), _PROBE_MS)
            acked = probe.waitForReadyRead(wait_ms) and bytes(probe.read(1)) == _ACK
            probe.abort()
            return acked
        missing = (
            QLocalSocket.LocalSocketError.ServerNotFoundError,
            # A Unix socket file a crashed copy left, with no one listening.
            QLocalSocket.LocalSocketError.ConnectionRefusedError,
        )
        if probe.error() not in missing:
            return False
        return self._hand_over_unconfirmed(payload)
```

3. `claim`'s body after the size check becomes:

```python
        if self._lock is not None:
            # Already the holder: handing over would knock on itself.
            return True
        lock = self._lock_file()
        deadline = time.monotonic() + _REACH_SECONDS
        # Tried each round: a holder on its way out lets go meanwhile.
        while not lock.tryLock(0):
            if self._hand_over(payload, deadline):
                return False
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"the copy holding {self._name!r} does not answer")
            QThread.msleep(_RETRY_MS)
        self._listen(lock)
        return True
```

   (Remove the now-unused `from qtpy.QtNetwork import QLocalServer` at the
   top of `claim`; ruff tells you.) Update `claim`'s `Returns:` to say
   False means "another copy holds it and acknowledged `message`, or is an
   older fxgui that was handed it unconfirmed", and its `Raises:` line for
   `RuntimeError` to "...or the copy holding it does not acknowledge
   `message` within 5 s (it may still read it later)".

4. Class docstring: after "treat a message as untrusted input.", add:
   "Qt cannot tell who listens on a name: on a machine several people use
   at once, another account could listen on the name first (Windows pipe
   names are machine-wide) and be handed a start's message. This is meant
   for single-user workstations; put the user in the name."

**Verify**: `...\python.exe -m pytest -q tests/test_single_instance.py` →
all pass, including the subprocess tests
`test_a_second_process_hands_its_message_to_the_first` and
`test_a_start_racing_one_not_yet_listening_hands_over` (both now go
through the acknowledged path). Commit
`[FIX] single instance: a hand-over counts only once acknowledged`.

### Step 4: Tests

In `tests/test_single_instance.py`, add a second subprocess script and
helpers under `_send`:

```python
# Claims with a short reach, and prints what came of it.
_CLAIM = "\n".join(
    (
        "import sys",
        "from qtpy.QtCore import QCoreApplication",
        "from fxgui.fxwidgets import FXSingleInstance, _single_instance",
        "_single_instance._REACH_SECONDS = float(sys.argv[3])",
        "app = QCoreApplication([])",
        "try:",
        "    held = FXSingleInstance(sys.argv[1]).claim(sys.argv[2])",
        "    print('claimed' if held else 'handed', flush=True)",
        "except RuntimeError as error:",
        "    print('error', error, flush=True)",
    )
)


def _claim(name, message, reach=1.0):
    """Start another process that claims `name`; read what it prints."""
    return subprocess.Popen(
        [sys.executable, "-c", _CLAIM, name, message, str(reach)],
        stdout=subprocess.PIPE,
        text=True,
    )


def _hold_lock(name):
    """Hold `name`'s lock as a copy would, without listening."""
    lock = FXSingleInstance(name)._lock_file()
    assert lock.tryLock(0)
    return lock


def _finish(qtbot, process):
    """Run the event loop until `process` exits; return its output."""
    qtbot.waitUntil(lambda: process.poll() is not None, timeout=20000)
    return process.stdout.read().strip()
```

New tests (all names stand alone; `_name(tag)` keeps them apart):

```python
def test_a_framed_message_is_acknowledged_once_read(qtbot):
    from qtpy.QtNetwork import QLocalSocket

    first = FXSingleInstance(_name("ack"))
    assert first.claim()
    sender = QLocalSocket()
    with qtbot.waitSignal(first.messaged, timeout=5000) as caught:
        sender.connectToServer(_name("ack") + "-ack")
        assert sender.waitForConnected(5000)
        sender.write((4).to_bytes(4, "big") + b"link")

    assert caught.args == ["link"]
    qtbot.waitUntil(lambda: sender.bytesAvailable() > 0)
    assert bytes(sender.read(1)) == b"\x06"


def test_a_holder_that_never_answers_is_not_taken_for_reached(qtbot):
    from qtpy.QtNetwork import QLocalServer

    name = _name("hung")
    lock = _hold_lock(name)
    hung = QLocalServer()
    assert hung.listen(name + "-ack")  # takes connections, never reads
    try:
        out = _finish(qtbot, _claim(name, "link", reach=1.0))
    finally:
        hung.close()
        lock.unlock()

    assert out.startswith("error") and "does not answer" in out


def test_a_new_start_still_reaches_an_old_holder(qtbot):
    from qtpy.QtNetwork import QLocalServer

    name = _name("old-holder")
    lock = _hold_lock(name)
    old = QLocalServer()
    assert old.listen(name)  # an older fxgui: the bare name only
    received = bytearray()

    def take():
        connection = old.nextPendingConnection()
        connection.readyRead.connect(
            lambda: received.extend(bytes(connection.readAll())))

    old.newConnection.connect(take)
    try:
        out = _finish(qtbot, _claim(name, "link", reach=5.0))
        qtbot.waitUntil(lambda: bytes(received) == b"link")
    finally:
        old.close()
        lock.unlock()

    assert out == "handed"


def test_an_old_start_still_reaches_a_new_holder(qtbot):
    from qtpy.QtNetwork import QLocalSocket

    first = FXSingleInstance(_name("old-start"))
    assert first.claim()
    sender = QLocalSocket()
    with qtbot.waitSignal(first.messaged, timeout=5000) as caught:
        sender.connectToServer(_name("old-start"))
        assert sender.waitForConnected(5000)
        sender.write(b"link")
        sender.disconnectFromServer()

    assert caught.args == ["link"]


def test_a_holder_on_its_way_out_hands_the_name_on(qtbot):
    from qtpy.QtNetwork import QLocalServer

    name = _name("leaving")
    lock = _hold_lock(name)
    leaving = QLocalServer()
    assert leaving.listen(name + "-ack")
    knocks = []

    def refuse():
        connection = leaving.nextPendingConnection()
        knocks.append(True)
        connection.abort()  # quitting: hangs up without an answer

    leaving.newConnection.connect(refuse)
    starter = _claim(name, "link", reach=10.0)
    try:
        qtbot.waitUntil(lambda: bool(knocks), timeout=15000)
    finally:
        leaving.close()
        lock.unlock()

    assert _finish(qtbot, starter) == "claimed"


def test_an_oversized_frame_gets_no_answer_and_no_signal(qtbot):
    from fxgui.fxwidgets._single_instance import MAX_MESSAGE_BYTES
    from qtpy.QtNetwork import QLocalSocket

    first = FXSingleInstance(_name("big-frame"))
    assert first.claim()
    said = []
    first.messaged.connect(said.append)
    first.woken.connect(lambda: said.append("woken"))
    sender = QLocalSocket()
    sender.connectToServer(_name("big-frame") + "-ack")
    assert sender.waitForConnected(5000)

    sender.write((MAX_MESSAGE_BYTES + 1).to_bytes(4, "big"))
    qtbot.waitUntil(
        lambda: sender.state() == QLocalSocket.LocalSocketState.UnconnectedState)

    assert said == []
    assert sender.bytesAvailable() == 0
```

**Verify**: `...\python.exe -m pytest -q tests/test_single_instance.py` →
all pass (6 new). Prove the hung-holder test guards the fix: temporarily
make the new `_hand_over` `return True` right after `probe.write(...)`,
rerun `-k never_answers` → FAILS (`out == "handed"`); revert → passes.
Commit `[FIX] single instance: tests for acknowledged hand-over`.

### Step 5: Full suite and lint

**Verify**: whole suite → 3178 + 6 passed, 6 skipped; lint →
`All checks passed!`.

## Test plan

New (6), all in `tests/test_single_instance.py`:
`test_a_framed_message_is_acknowledged_once_read`,
`test_a_holder_that_never_answers_is_not_taken_for_reached`,
`test_a_new_start_still_reaches_an_old_holder`,
`test_an_old_start_still_reaches_a_new_holder`,
`test_a_holder_on_its_way_out_hands_the_name_on`,
`test_an_oversized_frame_gets_no_answer_and_no_signal`.

Unchanged and must pass: every existing test in the file, notably the
two subprocess tests (they now take the acknowledged path) and
`test_a_message_over_the_limit_wakes_instead` (bare-name protocol).

Pattern: the existing file — `_name`, `_send`, raw in-process
`QLocalSocket` senders, subprocess senders for anything that calls
`claim` against a holder in this process.

## Done criteria

- [ ] Whole suite exits 0 with 3178 + 6 passed, 6 skipped
- [ ] Lint exits 0
- [ ] `grep -n "_ACK_SUFFIX\|def _on_framed_connection\|def _hand_over_unconfirmed" fxgui/fxwidgets/_single_instance.py` → at least 4 lines
- [ ] `grep -n "single-user" fxgui/fxwidgets/_single_instance.py` → 1 match (docstring)
- [ ] `git status` shows only the two in-scope files changed
- [ ] `plans/2026-11-14-audit/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" does not match the excerpts
  (other than plan 020's helpers).
- `test_a_start_racing_one_not_yet_listening_hands_over` fails or hangs:
  that test's patched `listen` now runs twice (1.5 s each), and the racer
  waits for the acknowledgement within its 5 s; if it times out, report the
  timings instead of raising `_REACH_SECONDS`.
- `test_a_holder_that_never_answers_is_not_taken_for_reached` prints
  `handed`: the sender fell back to the bare name although `name-ack`
  exists. Report the `probe.error()` it saw (add a temporary print); do not
  change the `missing` tuple.
- Any test crashes the interpreter (access violation): a connection was
  used after `deleteLater`; check `finished`'s guard.
- On Linux CI only, the hung or leaving tests fail with
  `ConnectionRefusedError`-like output: the Unix backlog behaves
  differently; report.

## Maintenance notes

- The bare name stays for old senders. Once no copy older than this
  release can run anywhere (Pascal's launchers all updated), the bare-name
  listener and `_hand_over_unconfirmed` can go — a protocol break to
  announce in the release notes.
- On Unix the socket path is `<temp>/<name>-ack`: 4 characters longer
  than today; a name near the 107-byte `sun_path` limit would now fail to
  listen (`RuntimeError: cannot listen`).
- Reviewers: check the acknowledgement is written *before* the signals
  run, the oversized-frame branch never acknowledges, and the fallback to
  the bare name happens only for "no such name" errors.
- Deferred: closing the servers on `QCoreApplication.aboutToQuit`, so a
  quitting copy stops accepting messages it will not act on; and a Win32
  owner check of the pipe.
- Pascal: once this ships, `apps/launcher/__main__.py:_start_application`
  should catch `RuntimeError` from `claim_lock(instance.claim, ...)` and
  tell the person the running launcher is not answering, instead of
  crashing; the browser link is then no longer lost silently.
