# Plan 013: The log pane's queue and document have a bound

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_log_widget.py tests/test_log_widget_throttle.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW (Step 1); MED for vendors if Step 2's default change is approved
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`FXOutputLogWidget` is the log pane; an `FXOutputLogHandler` feeds it
records from any thread. Records wait in a queue and are written at most
1000 per 16 ms tick. Neither the queue nor the document has a limit unless
the caller passes `max_blocks`, and Pascal passes none. Measured at
`b283eb13`: 100 000 records from a worker thread queue instantly, then the
pane spends 2.1 s draining them, and every record is kept forever. On a theme
switch, `_recolour` walks the whole document: 1.36 s at 50 000 ANSI lines,
with the UI frozen. A long session or a chatty library makes the pane slow
and its memory grow without end.

After this plan: when a bound is set, the queue never holds more records
than the document could keep (old ones are dropped before they cost a
write), and — if the operator approves — the pane has a finite default
bound, which also bounds the recolour.

## Current state

File: `fxgui/fxwidgets/_log_widget.py` (578 lines).

Docstring of `FXOutputLogWidget`, lines 147–152 — note the default is a
deliberate, documented choice:

```python
    Args:
        parent: Parent widget.
        max_blocks: How many lines the pane keeps before Qt prunes the
            oldest, as a terminal's scrollback does. Defaults to `0`, no
            limit: only the consumer knows whether dropping old records
            is safe.
```

Constructor, lines 179–191:

```python
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        max_blocks: int = 0,
        hang_indent: Optional[Union[str, Pattern]] = None,
    ):
        super().__init__(parent)

        self._max_blocks = max_blocks
        self._hang = re.compile(hang_indent) if hang_indent else None

        # The throttle limits repaints, never records: all are queued.
        self._pending_logs: Deque[Tuple[str, int]] = deque()
```

The document bound, lines 223–225:

```python
        if self._max_blocks > 0:
            # Qt prunes from the top once the document is this long.
            self.output_area.document().setMaximumBlockCount(self._max_blocks)
```

The queue is filled by `append_log` (line 452, `self._pending_logs.append((text, level))`)
and `append_many` (line 465, `self._pending_logs.extend(...)`), and drained
by `_flush_pending_log` (lines 406–440) with `popleft()`, at most
`MAX_RECORDS_PER_FLUSH = 1000` per call. Records arrive from other threads
through the `log_message` signal (line 170), connected to `append_log` at
line 205 (Qt queues it to the UI thread).

`_recolour` (lines 512–535) walks every block of the document on
`fxstyle.theme_changed`; its cost is proportional to the document size.

Every record is one or more blocks, so a document bounded at N blocks can
show at most the newest N records: queued records older than the newest N
would be written and then pruned. Python's `deque(maxlen=N)` drops the
oldest item on `append`/`extend` once full.

Probed at `b283eb13` with the queue replaced by `deque(maxlen=20)` on a
`max_blocks=20` pane: 60 appends leave 20 queued (`record 40`…`record 59`),
the document ends with `record 41`…`record 59` (19 lines; the 20th block is
the empty line after the last record) — the same final content as today.
A `threading.Thread` logging 3000 records through `FXOutputLogHandler`
arrives complete and in order.

Tests: `tests/test_log_widget_throttle.py`. Helpers `_pane(qtbot)` (lines
11–15) and `_lines(pane)` (lines 18–20). Relevant existing tests:

- `test_the_document_is_unbounded_by_default` (lines 148–151) asserts
  `pane.output_area.document().maximumBlockCount() == 0` — must change only if Step 2 is approved.
- `test_a_consumer_can_bound_the_document` (lines 154–167): `max_blocks=20`,
  60 records, asserts `len(lines) <= 20` and `lines[-1] == "record 59"`.
- `test_one_flush_is_bounded_however_large_the_burst` (line 100) and
  `test_a_bounded_flush_still_shows_every_record_eventually` (line 118) use
  `_pane` (no `max_blocks`) with 3000 and 2007 records — they stay valid
  with a 20 000 default.
- `test_a_record_from_the_signal_is_queued_like_any_other` (lines 68–79)
  emits on the main thread; no test uses a real worker thread.

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| Log tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_log_widget_throttle.py tests/test_log_widget_api.py tests/test_log_widget_audit.py tests/test_log_widget_colours.py tests/test_log_widget_levels.py tests/test_log_widget_spacer.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call, or it overwrites the owner's real settings.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_log_widget.py` — `FXOutputLogWidget` docstring and `__init__` only.
- `tests/test_log_widget_throttle.py` — new tests; `test_the_document_is_unbounded_by_default` only if Step 2 runs.

**Out of scope** (do NOT touch):

- `_flush_pending_log`, `MAX_RECORDS_PER_FLUSH`, the throttle interval — the
  per-tick bound already keeps each tick short.
- `_recolour` — it becomes bounded by the document bound; rewriting it
  (e.g. recolouring only the visible part) is a separate change.
- `FXOutputLogHandler` — it already hands records over by signal.
- `CHANGELOG.md`; any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch: `fix/log-pane-bound`.
  (There is no `.gitmodules`, so no submodule step.)
- One commit per step. Style: `[FIX] ...`, e.g.
  `[FIX] log pane: a bounded pane queues no more than it can keep`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: The queue keeps no more records than the document can

In `__init__`, replace the queue line and its comment with:

```python
        # A record is at least one block, so with a bound only the newest
        # `max_blocks` queued records could ever be shown; older ones go
        # before they cost a write.
        self._pending_logs: Deque[Tuple[str, int]] = deque(
            maxlen=max_blocks if max_blocks > 0 else None
        )
```

Nothing else changes: `append`, `extend` and `popleft` behave the same on a
bounded deque. Add tests 1 and 2 (Test plan).

**Verify**: `...python.exe -m pytest -q tests/test_log_widget_throttle.py` → all pass, including `test_a_consumer_can_bound_the_document`.

### Step 2 (GATED — operator decision): A finite default bound

**STOP before this step** unless the instructions that dispatched you
explicitly approve changing the default and name the value. The current
default `0` (unbounded) is a documented choice ("only the consumer knows
whether dropping old records is safe"); changing it changes behaviour for
every vendor that relies on the pane holding the whole session. Proposed
value: `20000` lines — about 0.5 s of recolour on a theme switch
(measured 1.36 s at 50 000 ANSI lines, linear), bounded memory, and far
more than a person scrolls back through; a consumer that needs everything
passes `max_blocks=0`.

If the step is NOT approved: skip it, finish Step 3, and set the README row
to `DONE (Step 2 skipped: default unchanged, awaiting decision on max_blocks default)`.

If approved with value N:

1. Change the signature default to `max_blocks: int = N,`.
2. Rewrite the docstring entry:
   `max_blocks: How many lines the pane keeps before Qt prunes the oldest, as a terminal's scrollback does. Defaults to N; \`0\` keeps every line, for a consumer that must never drop one.`
3. In `tests/test_log_widget_throttle.py`, rename
   `test_the_document_is_unbounded_by_default` to
   `test_the_document_is_bounded_by_default` asserting
   `maximumBlockCount() == N`, and add test 3.

**Verify**: `...python.exe -m pytest -q tests/test_log_widget_throttle.py` → all pass.

### Step 3: Whole suite and lint

**Verify**: whole suite → `3180 passed, 6 skipped` (3178 + 2) without Step 2,
or `3181 passed, 6 skipped` with it; 0 failed. Lint → `All checks passed!`.

## Test plan

Append to `tests/test_log_widget_throttle.py`, using `_pane` / `_lines`.
Add `import logging` and `import threading` under a `# Built-in` header at
the top, and import `FXOutputLogHandler` next to `FXOutputLogWidget`. The
handler's default formatter writes the bare message.

1. `test_records_logged_from_a_worker_thread_all_arrive_in_order` — a pane,
   a fresh logger (`logging.getLogger("fxgui.test.worker")`, `propagate = False`,
   level INFO) with `FXOutputLogHandler(pane)` added; a
   `threading.Thread(target=lambda: [log.info("%05d", i) for i in range(3000)])`,
   start and join; `qtbot.waitUntil(lambda: len(_lines(pane)) == 3000, timeout=10000)`;
   assert `_lines(pane) == [f"{i:05d}" for i in range(3000)]`. Remove the
   handler at the end (`log.removeHandler(handler)`) so no test leaks it.
2. `test_a_bounded_pane_queues_only_what_it_can_keep` —
   `pane = FXOutputLogWidget(max_blocks=20)`, `qtbot.addWidget(pane)`;
   60 `append_log(f"record {i}")` with no event loop between them; assert
   `len(pane._pending_logs) <= 20` and `pane._pending_logs[-1][0] == "record 59"`;
   then `qtbot.waitUntil(lambda: not pane._pending_logs)` and
   `_lines(pane)[-1] == "record 59"`.
3. (Step 2 only) `test_the_default_bound_applies_to_the_queue_too` —
   `_pane(qtbot)`; assert `pane._pending_logs.maxlen == N`.

## Done criteria

- [ ] Step 1's two tests exist and pass; Step 2's test exists and passes if Step 2 ran.
- [ ] Whole suite passes with the counts in Step 3.
- [ ] Lint: `All checks passed!`.
- [ ] `grep -n "deque(" fxgui/fxwidgets/_log_widget.py` shows the `maxlen=` form.
- [ ] `git status` shows only in-scope files modified.
- [ ] `plans/2026-11-14-audit/README.md` row 013 updated (with the Step 2 note if skipped).

## STOP conditions

Stop and report (do not improvise) if:

- The excerpts above do not match the live code (drift).
- Step 2 is reached without an explicit approval naming the default value.
- The worker-thread test is flaky (passes and fails across 3 runs): report
  the failure output; do not add sleeps.
- Any existing log test fails after Step 1 — the bounded queue must not
  change what an unbounded pane shows.
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- Public behaviour changes: Step 1 — none visible (a bounded pane drops
  queued records it would have pruned anyway). Step 2, if approved — the
  default pane keeps the newest N lines instead of all; vendors needing the
  whole session pass `max_blocks=0`. This must be called out in the release notes.
- Records are counted per record in the queue and per block in the
  document; a multi-line record (a traceback) takes several blocks, so the
  queue bound is an upper bound, never a loss of a record the document could show.
- `_recolour` stays O(document); if a pane is ever run with `max_blocks=0`
  and very long sessions, recolouring only the visible blocks is the follow-up.
- Pascal, once this ships: `StageLog` (`src/ls_pascal/apps/widgets/stage_log.py`,
  used by `src/ls_pascal/apps/session_log.py`) needs no change if the
  default lands; otherwise pass `max_blocks=20000` to `super().__init__`.
