# Review fixes

Every finding of the two whole-branch reviews, split into two groups by file.
Base: branch `audit-fixes`. The rules of plans/2026-10-01-fix-groups.md
apply (never kill by name, never name VS Code, Qt 6 only, test first and
failing first, one mechanism per job, ASCII, no CHANGELOG, `git commit
--only`). Use the worktree's own `.venv/Scripts/python`. Finish with a
report section in this file under your group: each item done / not done
and why, commits.

Reviewer A scratch scripts (repros): the session scratchpad's `revA/`,
`forkA1/`, `forkA2/`; reviewer B's: `reviewB/`.

## Group r1: theme, sheet, docking, shared helpers

Files: fxgui/fxstyle.py, fxgui/qss/*, fxgui/fxdocking.py, fxgui/fxicons.py,
fxgui/fxutils.py, fxgui/fxconstants.py, docs/. r1 also owns the call sites
named in items 21 and 25 below, in any file.

- A2 `set_color_file("missing.yaml")` returns quietly, then every
  `colors()` raises. Parse into a local first; raise at the call.
- A10 every FXIconButton size calls register_widget_style, which
  re-sheets QApplication. One rule that does not depend on the size
  (or a fixed set at import); FXIconButton is in _buttons.py, which r1
  owns for this item only.
- A16 `mark_as_frame` walks every descendant (115 QtAds widgets wrapped
  in a 4-pane area). Direct children only (Qt.FindDirectChildrenOnly).
- A19 drop-cross shadow (fxdocking.py:144) and the loading overlay scrim
  (_loading_spinner.py:206) hard-code black. Read a theme token (add a
  `scrim` token if `shadow` is the wrong weight). r1 owns that line.
- A21 one public token-or-colour resolver in fxstyle (a token name or a
  colour string in, a QColor out). Replace fxicons._theme_ink, the copy
  at _delegates.py:521 (`_as_color`), the use at _timeline_slider.py:53,
  and make FXToggleSwitch's on/off/thumb colours accept tokens through it.
- A22 `@lru_cache` on fxstyle.readable_ink; delete the cached copy in
  _log_widget.py:113.
- A25 get_feedback_colors duplicates colors().feedback_*: delete it, move
  its callers. One Qt version parse (fxstyle.py:250 vs fxicons.py:70).
  `_watch_focus` called from widgets (_range_slider.py:97,
  _delegates.py:368): make the focus watch start where focus_visible is
  first needed, so no widget calls a private name.
- A27 fxstyle.py:175 uses fxconstants.PACKAGE_ROOT.
- A24 (part) one name for 16777215: NO_CAP from one place, used at
  _labels.py:110 and _collapsible.py:73.
- B1 completer list scrolls with 4 items: popup padding 2px 4px
  (style.qss:1099).
- B2 hovered completer row is grey, menu rows are accent: popup hover
  rule must win (order or :!selected).
- B3 tooltip has its own look: same edge, fill and radius as menus; round
  the Qt.ToolTip window where menus are rounded (fxstyle.py:1821).
- B4 combo and completer rows 24 px like menu rows.
  Text inset: OWNER DECISION PENDING, the lead will message you.
- B5 combo popup corners: make it round the way menu and completer are.
- B6 dock title-bar buttons light as a full-height box: margin 4px 0px
  (fxdocking.py:61), so they match the tab pills.
- B7 docked tabs start 1 px further in than tab-bar tabs: same inset.
- Docs: docs/how-to/icons.md:38-75 and :123 name set_default_icon_library,
  set_icon_defaults and superpose_icons, which do not exist; exec_() in
  icons.md:242,261, styling.md:71,108, theming.md:236, index.md:38.
  Fix every page to the current API; grep docs/ for every name 13.0.0
  removed (tests/test_removed_names.py lists them).
- Timing open items: on PySide6 6.5.3 the first splash show costs 400 ms
  because Qt 6.5 on Windows loads a font weight other than 400/700 slowly;
  the splash title is 600. Decide and fix (a weight the theme already
  uses elsewhere, if the look holds). The gallery builds in 916 ms on the
  real desktop vs 406 ms offscreen: trace where the time goes and fix
  what is ours.

## Group r2: widgets

Files: every fxgui/fxwidgets module except the lines r1 owns above.

- A1 crash: FXThreadLine (_comments.py:535, :551-559) paints a deleted
  avatar. Drop it on destroyed, or skip invalid ones.
- A3 leaks: lambdas capturing self on a child's signal:
  _main_window.py:282, _fuzzy_search_tree.py:146-148 and :156-158,
  _breadcrumb.py:584-586, _emoji_picker.py:157. Bound methods; a test
  that the widget is freed after drop + gc.
- A4 _delegates.py:750-753 `_has_icon` raises on a QColor DecorationRole;
  same at :1217, :1387, :1412. Use opt.icon.
- A5 FXCodeBlock re-lexes the whole document per block (8k lines 3.1 s).
  Lex once per change.
- A6 timeline start/end spinboxes apply every keystroke:
  setKeyboardTracking(False).
- A7 FXLoadingOverlay.setVisible(True) skips the show()/hide() overrides:
  geometry and start/stop in showEvent/hideEvent.
- A8 FXRangeSlider set_minimum/set_maximum and the constructor do not
  clamp low/high.
- A9 FXDropZone: unguarded path.stat() on a missing file: catch OSError,
  size "-".
- A11 command palette: a slow go-to load overwrites a newer one: ticket.
- A12 html.escape user text in rich labels: _status_bar.py:276, :348,
  :415-416; _confirm_delete.py:69-71.
- A13 FXConfirmDeleteDialog: register_themed_root(self).
- A14 _screen_grab.py:62 logical rect on a device-pixel pixmap: scale by
  devicePixelRatio.
- A15 splash default icon invisible on light and baked at build: pick
  at paint, or draw through fxicons.
- A17 FXProgressCard clamps progress; FXRatingWidget routes the initial
  rating through set_rating(emit=False); keypad Enter clicks
  FXSplitButton (_keyboard.py:159).
- A18 `window.documentation = url` after construction leaves Help >
  Documentation disabled: one accessor style (documentation() +
  set_documentation()), the action follows it.
- A20 _delegates.py:1323-1328: QPersistentModelIndex across the modal.
- A23 delete setAlternatingRowColors(True) at _drop_zone.py:185 and
  _fuzzy_search_tree.py:139.
- A24 (part) muted description text uses alpha 180 (_delegates.py:1181):
  use text_muted.
- A26 FXFilteredTree (_keyboard.py:172-199) and FXFuzzySearchTree are two
  public search-over-a-tree widgets: merge into one public name.
  List the ls-pipeline call sites that change.
