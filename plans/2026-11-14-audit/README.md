# Implementation plans: audit of 2026-11-14

Written by the improve skill (deep audit, lens: what Pascal needs from fxgui) at
commit `b283eb13`, right after fxgui 14.1.0 (tooltip layout A) was released.
Execute in the order below unless the dependencies say otherwise. Each executor:
read the plan fully before starting, honour its STOP conditions, update your row.

## Execution order and status

| Plan | Title | Priority | Effort | Depends on | Status |
|------|-------|----------|--------|------------|--------|
| 001 | State fills hold on every ground (pressed beyond hover, frame, surface_alt, selection) | P1 | S-M | none | TODO |
| 002 | One state convention for buttons; overlay fills for flat buttons on any surface | P1 | M | 001 | TODO |
| 003 | A primary button owns its icon ink, whoever sets the icon | P1 | S | none | TODO |
| 004 | Timeline: loop-off after a wrap, Space on a focused button, a public track toggle | P1 | S | none | TODO |
| 005 | The theme choice is saved only when a person chooses it | P1 | S | none | TODO |
| 006 | FXBreadcrumb: public segment labels | P1 | S | none | TODO |
| 007 | Ship type information (py.typed) | P2 | M | none | TODO |
| 008 | Type-to-filter takes AltGr characters (AZERTY, QWERTZ) | P1 | S | none | TODO |
| 009 | A neutral label pill in FXThumbnailDelegate | P2 | S | none | TODO |
| 010 | Theme loading: on-accent inks, the mono face, window fade in app mode | P2 | S | none | TODO |
| 011 | User text stays text (tag chip, avatar, banner) | P1 | S | none | TODO |
| 012 | No disk check blocks the UI (path widget, drop zone) | P2 | M | none | TODO |
| 013 | The log pane trims its queue to its bound (a finite default bound waits for the owner's yes) | P2 | S | none | TODO |
| 014 | Thumbnails decoded at their target size | P2 | S | none | TODO |
| 015 | Small widget defects (toggle, checkable combo, accordion, read-only edit, status dot, sort, flow layout) | P2 | S | none | TODO |
| 016 | Chrome and sheet defects (banner on a hidden parent, status bar outside FXMainWindow, malformed QSS, proxy sort documented) | P2 | S | none | TODO |
| 017 | Release and docs pipeline (permissions, pinned tools, trusted publishing, docs versions) | P2 | S | none | TODO |
| 018 | CI covers what fxgui claims (Windows, PyQt6, dependency floors) | P2 | M | none | TODO |
| 019 | Public names for what Pascal reaches into (dock hide/open, unregister root, delegate icon geometry, refilter, icon cache folder) | P2 | M | none | TODO |
| 020 | A window can scope any shortcut; a restart waits for the lock without waking the old copy (`try_claim`) | P3 | S | none | TODO |
| 021 | Single-instance hand-over is acknowledged | P3 | M | 020 | TODO |
| 022 | Linux network mounts may stall | P3 | S | 012 | TODO |

Status values: TODO | IN PROGRESS | DONE | BLOCKED (one-line reason) | REJECTED (one-line rationale).

## Dependency notes

- 002 needs 001: the button rules use the state tokens 001 re-derives, and 002's
  pixel tests assume 001's floors.
- 021 after 020: both touch `_single_instance.py`; 020 adds `try_claim`, 021 changes
  the hand-over protocol.
- 022 after 012: 012 makes `_compat.can_stall` decide which checks go off-thread;
  022 widens what `can_stall` returns.
- 010 removes the mono-face workaround in `_tips.py` (added in 14.1.0); it must keep
  `tests/test_tips.py` green.
- 011 and 020 both mention the notification banner: 011 owns banner text and action
  icons; 020 leaves the banner alone.
- Release batching: plans 001-006, 008 and 011 are what Pascal waits on (each names
  the Pascal workaround it retires). Release after each batch: tests, push to main,
  tag `vX.Y.Z`, check the release run and `pip index versions fxgui`, then
  `lsd pip fxgui==X.Y.Z --target development --no-deps`.

## Decisions waiting for the owner, inside plans

- 002 adds a derived `state_checked_hover` and translucent fills as `#AARRGGBB` in
  `fxstyle.colors()`; code that assumes every colour there is `#RRGGBB` must be checked
  (fxgui's suite covers fxgui; Pascal is not checked).
- 005 changes behaviour for headless callers only: no save under `offscreen`/`minimal`
  unless `save=True`.
- 010 step 3: fade app-mode windows, or document that app mode has no fade.
- 013: the default bound (proposed 20000 blocks) changes a documented default.
- 017: PyPI trusted publishing needs a trusted publisher added on PyPI first; then
  rotate (revoke) the old PyPI token.
- 018: if the PyQt6 row cannot be made green, keep the claim with a known-issues note,
  or drop it.
- 008 maintenance: whether typing on a tree should beat a window's single-letter
  shortcut.

## Findings considered and rejected

- **Match shortcuts by physical key position (handed-over finding 4)**: rejected.
  On AZERTY the key at the US `/` position types `!`, and Qt matches shortcuts by
  character, so `!` correctly reaches the filter while Shift+`:` (which types `/`)
  fires a `/` shortcut. QShortcut cannot match scan codes, macOS has none, and a
  keycap showing `/` would lie. The real AZERTY defect is AltGr (plan 008).
- **Make `_compat.hold` public (handed-over finding 8)**: not worth doing now.
  Pascal's main has no call site; its viewport overlays go through
  `FXLoadingOverlay`, which holds itself (fxgui 13.17.1), and fxgui's resize mark
  holds itself (13.16.2). Revisit if a consumer writes its own overlay on a widget
  Qt made.
- **Cache measurements in FXThumbnailDelegate.sizeHint/paint**: measured small
  (2000 rows: 53 ms column fit, 12 ms viewport paint); the measure-equals-paint
  invariants are delicate. Revisit for trees of 10k+ rows.
- **Sheet build and the app-wide focus filter**: measured (6 ms warm sheet, 0.6 µs
  per event); not worth changing.
- **Sort by value in `FXSortFilterProxyModel` with no filter**: by design (the proxy
  sorts itself in `__init__`; `tests/test_item_views.py` pins "a tie keeps the source
  order"). Plan 016 documents it instead.
- **`menu_bar` / `status_bar` options on FXMainWindow**: dropped from 020; Pascal still
  builds its menus, and its other workarounds are single standard Qt calls.
- **A disabled QPushButton takes :hover**: measured, it does not.
- **Log search over 100k lines**: 0.02 s; not worth changing.
- **Banner losing its Python side on a Qt-made viewport**: probed, did not reproduce.
