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

### Report r1

Branch `fix-r1` off `audit-fixes` 6e3b8754. Full suite on the worktree
venv (PySide6 6.11.1): 2472 passed, 6 skipped. Covering files on PySide6
6.5.3 (scratchpad `venv65`, PYTHONPATH on the worktree): 518 passed, 12
skipped, 1 failure that is that venv's editable install still pointing at
fix-b's tree (`fxgui.fxdcc` found there), not this branch.

| Item | State | What now holds |
|---|---|---|
| A2 | done | `set_color_file` parses into a local first: a missing file raises `FileNotFoundError`, a broken one `yaml.YAMLError`, at the call; the loaded colours stay. |
| A10 | done | Every FXIconButton side 8-96 px gets its radius rule once at import; a new size re-sheets nothing. A side outside clamps to the nearest end (`ponytail:` note). |
| A16 | done | `mark_as_frame` repolishes `FindDirectChildrenOnly` children. |
| A19 | done | The drop cross wears `@shadow`; the loading overlay a new `scrim` token (`#80000000`, every theme through dark). |
| A21 | done | `fxstyle.qcolor(value)`: token name, colour or QColor in, QColor out (invalid for anything else). `fxicons._theme_ink`, `FXThumbnailDelegate._as_color`, the timeline's `_ink` go through it; FXToggleSwitch's on/off/thumb colours take tokens. |
| A22 | done | `@lru_cache` on `readable_ink`; `_log_widget._readable_ink` deleted. |
| A25 | done | `get_feedback_colors` deleted (callers: examples.py, _status_dot.py, 4 tests); `_compat.QT_VERSION` is the one version parse; `focus_visible` starts the focus watch, no widget calls `_watch_focus` (FXJoinedGroup asks `focus_visible(self)` once when built, since it reads only on focus change). |
| A27 | done | fxstyle uses `fxconstants.PACKAGE_ROOT` / `ICONS_ROOT`. |
| A24 (part) | done | `fxutils.NO_CAP`, used by _labels.py and _collapsible.py; the class constant is gone. |
| B1 | done | Completer list: padding 2px 4px, and it is themed at its Polish (Qt measures rows before it shows it), owner found through its focus proxy. Four rows, no scroll, host and app. |
| B2 | done | Popup hover rules sit after the view rules, plus `:!selected:hover` for combos: the hovered row is the accent. |
| B4 | half | Combo and completer rows are a menu row: text plus 4 px each side (24 px at the 12 px font), host and app. Text inset: waiting on the owner's ruling, untouched. |
| B5 | done | The combo popup frame is painted as the card (`_ComboCard`: `@surface`, `@border`, `CARD_RADIUS`); Qt's sheet never reaches that frame. |
| B3 | done | QToolTip is the menu card (`@border`, `@surface`, `@card_radius`) and a themed tooltip window is rounded like a popup. A host's tooltips are left alone (Qt keeps one for the whole app). |
| B6 | done | Title-bar buttons: `margin: 4px 0px` and a vertical Ignored policy, so they light as a tab pill and never set the bar's height. |
| B7 | done | `QTabWidget::tab-bar { left: 1px; }`: tab-bar tabs start 3 px from the pane's outer edge, as dock tabs do. The test now measures both from the outer edge. |
| Docs | done | icons.md (no set_default_icon_library, set_icon_defaults, superpose_icons; `badged`; the Active ink and button rule as the code has them), exec() on every page, theming.md (feedback tokens, qcolor, scrim, the popup/tooltip card, colour-file errors, focus watch). |
| Splash 400 ms on 6.5.3 | done | The `card` rank is 700. 6.5.3 real desktop, first show: 404-414 ms at 600, 24 ms at 700; the look holds (rendered dark and light). The 600 cost moves to the first 600 text, which in an app is built behind the splash. |
| Gallery 916 vs 406 ms | done | Cause: Qt on Windows takes about 0.4 s to resolve the first font naming two families, and the mono role named three (the Display page's code block paid it). Each font role now resolves to its first installed family alone. Real desktop build: 750-900 ms before, 230-340 ms after. |

Not mine, found on the way, for r2: `_loading_spinner.py:124`
`vars(colors).get(self._color, self._color)` is another token-or-colour
copy; it becomes `fxstyle.qcolor(self._color)`.

ls-pipeline call sites that change (main at 76f6b9eb):
`fxstyle.get_feedback_colors()` is gone; read
`fxstyle.colors().feedback_<level>_<part>` or `fxstyle.qcolor(...)`:
python/ls_pipeline/apps/widgets/status_items.py:129,
apps/hub/views/comments.py:514, :882, :967, apps/hub/views/task_info.py:370,
apps/views/tree.py:53 (a level check: `hasattr(fxstyle.colors(),
f"feedback_{role}_foreground")`), apps/launcher/views/rows.py:175,
apps/hub/views/composer.py:411, apps/theme.py:119,
apps/timesheet/views/window.py:151, scripts/widget_gallery.py:154, and the
tests test_dependency_page_qt.py:1109, test_workflow_window_qt.py:1334,
test_workflow_items_qt.py:539, :561, test_theme_switch_qt.py:37,
test_status_dot.py:28, test_launcher_popup_qt.py:263, :353,
test_scene_manager_qt.py:303, :313, :875-879, :952, test_hub_qt.py:879,
:931, test_launcher_qt.py:44, test_task_pane_qt.py:160,
test_graph_canvas_qt.py:715, :739, :757, :787, :833, :857, :3308.
`get_font_family` / `get_fonts` now return one family, not a stack:
apps/widgets/graph/view.py:88-92 reads it as a stack (works with one
name; its docstring example goes stale), tests/apps/test_theme.py:221, :235.

Commits: c68455cf, 0436e727, 5c51e5f4, 67c0152e, 2881ef6c, 3b261d73,
06160f00, c207d6b9, and this report.

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
