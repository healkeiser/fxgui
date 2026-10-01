# Fix groups after the complexity audit

Each group fixes every finding of plans/2026-10-01-complexity-audit.md in
the files it owns, plus the extra items below. Base: branch `integrate`.

## Rules for every group

- Never mention VS Code ("VSCode", "Visual Studio Code") in fxgui code, comments, docstrings, tests or docs pages; describe looks in fxgui's own terms. Plans may cite it as a source.
- NEVER kill processes by image name (`taskkill /IM python.exe`, `Stop-Process -Name python`, `pkill python`): it kills other agents, other sessions and the owner's own apps. Kill only a PID you started yourself, or use a pytest timeout.
- Own worktree and branch; touch only your files. A change a caller in
  another group's file needs: list it (file:line -> new call), don't edit.
- Owner rules: anything wrong, costly or too complicated requires a
  change; one mechanism per job; 13.0.0 is a major, so one public name per
  job; defer nothing; test first, failing first where behaviour changes.
- Qt 6 only (PySide6 6.5 floor, PyQt6 through qtpy): delete every Qt 5
  branch in your files; use `exec()`, not `exec_()`, except where a test
  patches `exec_` on QMenu; slot lambdas take `_=False, ...` because
  PySide6 6.5 calls a `clicked` slot with no argument.
- Test cost: while working run only the covering test files; run the full
  suite once before your report (`C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python -m pytest -q -p no:cacheprovider`).
  Renders: dark and light only. A 6.5.3 venv recipe: `py -3.11 -m venv
  <dir>` then `pip install -e . "PySide6==6.5.3" pytest pytest-qt
  pytest-randomly`; run your covering tests there too.
- Theming contract: docs/how-to/theming.md (pull model, The Control
  Language). Icons beside a title or label use the `icon` token,
  `text_muted` only beside secondary text.
- Delete the private shims that fix-b left for your files (marked TODO in
  fxutils, fxicons, fxwidgets/_constants.py, fxdcc.py) by updating your
  callers; plans/2026-10-01-fix-b.md lists them.
- Commit style `[FIX]/[REFACTOR]/[FEAT] <what now works>`; no CHANGELOG;
  ASCII only. Finish with your report in plans/2026-10-01-fix-<group>.md:
  every finding (done / not done and why), commits, and every ls-pipeline
  call site that changes (file:line at ls 5a290087 -> new call).

## Group c: item views

Files: fxwidgets/_delegates.py, _tree_items.py, fxcore.py,
_fuzzy_search_list.py, _fuzzy_search_tree.py.
Extra: delete FXColorLabelDelegate (and fxicons.change_pixmap_color's shim
use); `_find_cached` -> `_compat.find_pixmap`; delete the delegate's
markdown_to_plain_text (fxutils has it); `_bordered_thumbnail` uses
fxicons.rounded_pixmap or its token ring at the device ratio; IMAGES_ROOT
for the hand-built path (_delegates.py:55); one hover look
(@accent_secondary); merge the fuzzy list into the tree if the audit's
case holds.

## Group d: tooltips and tips

Files: fxwidgets/_tooltip.py (delete), _tips.py, their tests.
Owner rulings: FXTooltip is not needed; `apply_tip` (native rich tooltip
with title, body, keys) is the one tooltip and covers item views (build
an item's tip when it shows). One keycap per key, close together (`Ctrl`
`S`), wider gap between chords; FXKeycap and keycap() both; key names
from QKeySequence NativeText. test_tips.py:258 and :277 fail on Linux CI:
fix at the cause. FXMainWindow's rich_tooltips belongs to group e; list
what e must remove.

## Group e: window chrome

Files: fxwidgets/_main_window.py, _status_bar.py, _application.py,
_dialogs.py, _splash_screen.py, _notification_banner.py, _system_tray.py,
_progress_card.py, _loading_spinner.py, _widget.py, _singleton.py,
_single_instance.py, fxdocking.py.
Extra: 6.5.3 failures: _main_window.py:426 lambda; a spinner on a closed
branch still animates; FXFloatingDialog not deleted within 1 s of its
close button. Remove rich_tooltips and every FXTooltip use. Delete
parent_package and the Houdini branch in _dialogs (then fxdcc.py goes).
FXProgressCard's task icon uses the `icon` token. Callers of the
create_action, add_shadows, get_formatted_time and _constants shims.
fxdocking imports later/rehome/focus_step from fxutils.

## Group f: inputs

Files: fxwidgets/_inputs.py, _search_bar.py, _validators.py (and the
password field).
Extra: one icon-in-a-line-edit mechanism, QLineEdit.addAction (+
setClearButtonEnabled); list the callers in other groups' files.

## Group g1: big widgets

Files: fxwidgets/_log_widget.py, _timeline_slider.py, _drop_zone.py,
_file_path_widget.py, _breadcrumb.py, _code_block.py, _collapsible.py,
_tag_input.py, _accordion.py.
Extra: 6.5.3: _breadcrumb.py:580 lambda. One accessor style per value
(x() + set_x()); e.g. FXFilePathWidget's path property beside
get_path/set_path goes.

## Group g2: small widgets and the gallery

Files: every other fxwidgets module not listed above, plus
fxgui/examples.py.
Extra: one accessor style per value in your files; examples.py uses
fxconstants paths, token names and no hard-coded colours; the gallery
shows every public widget (its test enforces it).

## Later, in order

- Group a (fxstyle.py, style.qss, style.yaml, conftest) after the chrome
  pass: shadow tokens (@shadow, @shadow_blur) that follow a switch; 6.5.3
  item BackgroundRole blended (#a8454a vs #aa3333) and spin boxes 23 px;
  conftest flushes deferred deletes after every test; fxstyle
  `_apply_to_root` sets the palette before the sheet, so a root with a
  child switched before its first show shows the old theme: set the sheet
  first (measured by group d); the empty slider track's 3:1 (if the chrome
  pass leaves it); slider_thumb/slider_thumb_hover tokens are unused.
  On 6.5.3, test_host_sheet has "_Probe already deleted" teardown errors (18, then 20 after 7e5cdf0a; the 2 extra unexplained) and the blended #a7454a item background: fix at the cause.
  Theme contrast: solarized_light's own @text reads 4.13:1 on @surface (3.64:1 on the tab pill); every bundled theme's text tokens must reach 4.5:1 on the surfaces they sit on. Fix the theme values (or derive text inks as @tab_muted is), with a test over every theme.
- Group h: test clean-up (duplicates, shared helpers, order hang, flaky
  busy-line test) after everything else lands.
  Also: after a test builds the gallery, later offscreen renders draw empty boxes for text and come out wider (a leak, seen by the chrome agent); find and fix it. One full run had 20 hover failures and took 157 s instead of 86 (not reproduced; maybe machine load).
