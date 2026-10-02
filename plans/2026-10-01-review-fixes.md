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

### Group r2 report

Branch `fix-r2` from `audit-fixes` 6e3b8754. Full suite 2450 passed, 6
skipped (baseline 2440 / 6). Covering tests on PySide6 6.5.3: 527 passed.
`ruff check --select F,B,BLE fxgui tests` clean.

Every item is done. Each has a test that failed first.

- A1 done, 29423821. `FXThreadLine.path()` drops faces Qt has deleted
  (`_compat.is_valid`) before it reads them.
- A3 done, b700d851 + ae8255b2. Bound methods replace the lambdas in
  `_main_window`, `_breadcrumb` (a segment navigates itself), `_emoji_picker`
  (`sender().text()`), `_fuzzy_search_tree` and `FXFilteredTree`. The same leak
  was in `FXNotificationBanner.add_action` and in `FXCommandPalette`'s
  itemClicked, so those are fixed too. Test: `tests/test_widget_leaks.py`
  drops each widget, runs gc and checks the weakref is dead.
- A4 done, e7524b7d. `_has_icon` takes the filled-in option and reads
  `option.icon`. Qt turns a QColor or a QPixmap decoration into that icon.
  All 4 paint sites paint `option.icon`.
- A5 done, 16449a6c. The highlighter marks itself dirty on
  `contentsChange`, connected before `setDocument` so the flag is set ahead
  of Qt's rehighlight. The text is read once per change. 8000 lines: 0.66 s,
  was 3.1 s.
- A6 done, f2210bed. `setKeyboardTracking(False)` in `_spinbox_for`, so
  start, end, view start and view end all apply on Enter or focus out.
- A7 done, f0b07c20. Geometry, raise and spinner start/stop moved into
  `showEvent` / `hideEvent`. The `show` and `hide` overrides are gone.
- A8 done, 35e9661a. One `_clamped(low, high)` serves the constructor and
  `set_values`. A new minimum lifts the maximum and a new maximum lowers the
  minimum, as QSlider does.
- A9 done, 4793006a. `_size_text` catches OSError and shows "-".
- A11 done, cf0e17c4. Each opening takes a ticket, and a `landed` callback
  from an older ticket does nothing. `open_commands` takes a ticket too.
- A12 done, 37456c8e. `html.escape` on the message and the tip in
  `_status_bar`, and on the confirm word. The body label is `Qt.PlainText`.
- A13 done, 37456c8e. `register_themed_root(self)`.
- A14 done, 8c4273bc. The logical rect is scaled by the screen pixmap's
  `devicePixelRatio()` before the crop.
- A15 done, 13c6d86a + 48394250. With no icon given, the splash draws
  `_FXMark`, an FXIconLabel that inks `FAVICON_LIGHT` in the `icon` token
  each time it paints. I tried registering a library in fxicons first. It
  changed the library table that `test_icon_engine_palette` pins, and the
  result depended on test order, so I dropped it.
- A17 done, 80787a75. Progress is clamped in the constructor. The first
  rating goes through `set_rating(emit=False)`. Enter on FXSplitButton
  ignores the keypad modifier.
- A18 done, b700d851. `documentation()` + `set_documentation(url)`, and the
  action's enabled state follows the setter. The public attribute is gone.
- A20 done, e7524b7d. A QPersistentModelIndex is taken before the menu runs.
  `picked` emits the row where it is now, or nothing if the row is gone.
- A23 done. `_drop_zone.py` in 4793006a. `_fuzzy_search_tree.py` is deleted
  (A26).
- A24 (part) done, e7524b7d. The description uses `text_muted`. On a
  selected row it keeps the selection's text colour, because muted ink
  would sit on the accent.
- A26 done, a17505f8. Ruling (I asked the lead and got no answer, so this
  is my default): FXFilteredTree survives and FXFuzzySearchTree is deleted.
  Only FXFilteredTree can wrap a QTreeWidget the caller already has. That is
  what ls-pipeline's planned move needs (move-d item 50, a lazy tree).
  FXFuzzySearchTree owns its model and cannot do that. Fuzzy matching stays
  public as `fxcore.FXSortFilterProxyModel`. What is lost: a ready-made
  widget with a ratio slider that ranks by match quality. The gallery now
  shows FXFilteredTree only, and `test_removed_names` lists
  FXFuzzySearchTree.

Left for others:

- r1 (docs): docs/how-to/widgets.md:97 lists FXFuzzySearchTree, and
  docs/how-to/theming.md:553 names its slider. Both go. widgets.md should
  say FXMainWindow has `documentation()` / `set_documentation()`.
- r1 (fxconstants): FAVICON_LIGHT is used only by the splash mark now.
- Not done because it is r1's line: the scrim at _loading_spinner.py:206
  (A19), and `fxstyle._watch_focus()` in _range_slider.py and
  _rating_widget.py (A25).

ls-pipeline call sites that change (checked at 76f6b9eb): none. It never
uses FXFuzzySearchTree, FXFilteredTree, `FXMainWindow.documentation`, or a
markup message to `showMessage` / `show_tip`. Move-d item 50
(widgets/rows.py:345 fold_buttons, :366 filtered_tree_panel ->
`FXFilteredTree(tree)`) still holds.

## Group r3: what reviewer B found beyond r1 and r2

Base: `audit-fixes` at b7ccd01a (r1 and r2 merged). Same rules.

- B-2 a hovered toolbar button (any QAction icon in a QToolBar, or a
  plain get_icon on a non-QAbstractButton) draws its icon in
  icon_on_accent_primary, white on the grey hover fill (1.4:1 on
  light). Make Active default to the Normal ink everywhere; give the
  on-accent ink only where a row is drawn on the accent (menu current
  row, combo/completer current row). A test that hovers a real QToolBar
  action through tests/_helpers.hover and reads the icon pixel.
- B-9 docs residue: icons.md:167 states the Active ink default (fix to
  the code after B-2); theming.md:121 FXLogWidget -> FXOutputLogWidget;
  widgets.md:187 example sets SEGMENT_HOVER_TOKEN = "accent_secondary",
  which breaks "hover is never the accent": show a valid example. Run
  every Python block of docs/how-to/*.md and fix any that fails.
- B-16 one public name per job for a role's font: keep fxstyle.font(role=...),
  delete get_fonts and get_font_family (callers, docs, removed-names
  table). Put control_height and focus_visible in fxstyle.__all__ if they
  are public, so the API page lists them.
- B-17 fxgui has no test running its >>> examples: add one (doctest over
  every fxgui module, examples that state an output must pass; fragments
  without stated output may stay). Fix fxstyle.py depth_shade example
  (`colors()["surface"]` -> `colors().surface`).
- B-18 packaging: `import fxgui` refuses a binding below PySide6 6.5 with
  a clear error; the docking extra pins PySide6-QtAds so it cannot swap
  the PySide6 binding (check what its wheels pin; say plainly if no pin
  works); release.yml publish-pypi does not run when create-release
  fails. Add a docs page "Moving from 12.x" listing every removed or
  renamed name with its 13.0.0 replacement (from
  tests/test_removed_names.py and the plans' replacement tables), in
  the docs' student style.

### Group r3 report

Branch `fix-r3` from `audit-fixes` e2cf93a8. Full suite on PySide6 6.11.1:
2494 passed, 6 skipped. Covering tests on PySide6 6.5.3 (icons, buttons,
fonts, doctest, floor, readable_ink): 193 passed, 3 skipped. `ruff check
--select F,B,BLE .` clean. A suite run with QT_QPA_FONTDIR set fails 19
font and tab-pixel tests; they pass without it, so it stays out of suite runs.

- B-2 done (c3976c8a). Active now takes the normal ink everywhere. Only a
  menu's current row takes `icon_on_accent_primary`: the engine checks
  whether a top-level QMenu is in its paint event
  (`WA_WState_InPaintEvent`), because Qt asks a toolbar hover and a menu row
  for the same Active pixmap and never names the widget. A combo or
  completer current row is drawn in Selected mode, which already defaults to
  the on-accent ink (measured: a combo popup asks for Selected and Normal,
  never Active). `_icon_for_widget` and three redundant
  `inks={"active": ...}` (fxdocking, FXPrimaryButton, FXIconButton) are
  deleted. Tests: a hovered QToolBar action, through `_helpers.hover`, for
  both set_icon and get_icon (failing first), and a real QMenu row. Renders
  of a light and dark toolbar hover and menu row checked through the
  backing store, not only `grab()`.
- B-9 done (c0c7225a). icons.md states the new Active default; theming.md
  says FXOutputLogWidget; the breadcrumb example uses `text_muted` at 48.
  Every Python block of docs/how-to/*.md was run alone. 15 failed, and all
  now run except two that need the reader's own files on purpose: icons.md
  "Add a Custom Library" (its icon folder) and theming.md "Using Your Custom
  Theme" (`/path/to/my_theme.yaml`).
- B-16 done (ba06544a). get_fonts and get_font_family are deleted, and so
  are their callers and tests; both are in test_removed_names.
  `control_height` and `focus_visible` are in `fxstyle.__all__`.
- B-17 done (43af7b1d, 7b41885f). tests/test_docstring_examples.py runs
  every docstring that states an output. Only an example with a stated
  output can fail it; mutation-checked by changing one stated value.
  fxdocking is skipped when QtAds is absent (the 6.5.3 CI row). The
  depth_shade example is fixed. Every fragment was also run once: no other
  example calls a wrong API (the rest need a placeholder file).
- B-18 done.
  - dad9d54b: `import fxgui` raises `ImportError: fxgui needs PySide6 6.5
    or newer; found X`.
  - 4927eaf7: publish-pypi needs `create-release` to have succeeded.
  - d21264f4: no pin works. Every PySide6-QtAds wheel pins one exact
    PySide6-Essentials (4.0.3.1 pins 6.5.1.1, 4.3.1.3 pins 6.8.2,
    5.0.0.2 pins 6.11.1; no wheel pins 6.5.3). A pinned extra forces that
    PySide6, and an unpinned one pulls the newest. Either one replaces the
    binding. So the `docking` extra is deleted. docs/installation.md gives
    the recipe that does not swap:
    `pip install PySide6-QtAds "PySide6-Essentials==<yours>"`. pip then
    picks the matching QtAds, or answers ResolutionImpossible (dry-run
    checked with 6.8.2 and 6.5.3). tests.yml installs `PySide6-QtAds` by
    name. The lead's venv recipe `pip install -e ".[docking]"` now warns
    about an unknown extra; use `pip install -e . PySide6-QtAds`.
  - 01335ec1: docs/moving-from-12.md is in the nav after Installation. It
    was built from an API diff of v12.12.0 against this branch: 140 removed
    names and 61 changed signatures or properties. Each replacement was
    checked in the code; rows that do not break a call are left out.
- Found while writing the page, fixed (a74c84b5, plus the cache test):
  `readable_ink(QColor(...))` raised `TypeError: unhashable`, since
  lru_cache saw the QColor. It now caches on colour names, with a failing-first test.

ls-pipeline call sites that change (ls 76f6b9eb):
- python/ls_pipeline/apps/widgets/graph/view.py:92
  `fxstyle.get_font_family(role)` plus the stack split ->
  `families = fxstyle.font(role=role).families(); return families[0] if
  families else fallback`.
- tests/apps/test_theme.py:221, :235 `fxstyle.get_fonts(theme)[r]` ->
  `fxstyle.font(theme, role=r).family()`.
- tests/apps/test_workflow_items_qt.py:398 monkeypatches
  `get_font_family` -> patch `graph_view.fxstyle.font` (or the new
  family_for body).
- No change for docking: ls-pipeline pins `PySide6-QtAds==5.0.0.2` itself.

#### Group r3 extra items (owner, 2026-10-02)

Full suite after both: 2504 passed, 6 skipped. 6.5.3 covering tests: 134
passed, 9 skipped (docking skipped). ruff clean. PNGs are in the session
scratchpad: `r3/icons/{before,after}_crop_{dark,light}.png` and
`r3/tabs/{before,after}_tabs_{dark,light}.png`.

- Item-view icon size done (db8c8a1c). Measured on the gallery's Lists
  tab:
  - QListWidget asked for a 24 px box (`PM_ListViewIconSize`), so the
    folder drew 20 x 16 px beside 12 px text. A QTreeWidget item icon used
    16 px (`PM_SmallIconSize`).
  - The branch chevron filled the 20 px indentation in every tree,
    FXThumbnailDelegate's included (8 x 4 px of ink, against 6 x 3 at 16
    px). The delegate's own icons were already 16 px.
  - The rule now: every item view draws in the 16 px box. FXProxyStyle maps
    PM_ListViewIconSize to PM_SmallIconSize, so an explicit setIconSize
    still wins. The sheet pads `QTreeView::branch:has-children` by 2 px, so
    the chevron sits in 16 px.
  - Test: tests/test_item_view_icon_size.py measures the drawn ink against
    the same glyph at 16 px, for a list, a tree, and branches with and
    without the delegate, dark and light. It failed first on the list and
    on both chevrons.
  - Open: a completer popup in a host application (no FXProxyStyle) still
    gets 24 px list icons.
- Selected tab without an edge done (0dcc9344). The current tab is now a
  `@state_pressed` pill with `@text`. A hovered tab stays `@state_hover`,
  and a hovered current tab keeps `@state_pressed`. The transparent 1 px
  edge stays, so nothing moves. QTabBar and QtAds share the one rule in
  style.qss. The spec rulings and theming.md are updated.
  - Fills, dark: hover #403f3f, selected #4f4e4e. Selected is 1.27:1 off
    hover and 1.61:1 off surface; text on it 5.54:1.
  - Fills, light: hover #d8d8d8, selected #bdbdbd. Selected is 1.32:1 off
    hover and 1.65:1 off surface; text on it 8.57:1.
  - Every bundled theme keeps selected at least 1.25:1 off hover
    (`STATE_MIN_CONTRAST` is 1.2) and text on it at least 4.5:1.
  - The tab tests now find the pill by its fill: 16 of them fail on the old
    sheet. A new test covers a hovered current tab.

## Switch-over gaps

Branch `fix-gaps` from `audit-fixes` 98a2523c. ls paths are in the
fxgui13-w1 / fxgui13-w2 worktrees.

1. A floating pane in an embedded window got the host's keys.
   - Cause: `FXDockArea._key_the_float` read `self.window()`. For a main
     window embedded in a host, that is the host's window.
   - Fix: the new `_app_window` returns the nearest QMainWindow, else
     the window. Keys are copied from it.
   - Commit: 6d00d752.
   - ls can delete: `AppWindow._key_the_float` (w1 apps/window.py:738-753)
     and its connect (window.py:236-237).
2. A list header inside a pane drew on the well colour.
   - Cause: QHeaderView is a QAbstractItemView, so the
     `#fxDocks ... QAbstractItemView { @well }` rule matched it.
   - Fix: one rule, `#fxDocks ads--CDockAreaWidget QHeaderView
     { background-color: @surface; }`. The base sheet's sections stay
     transparent with their `@border` line under.
   - Tested by pixel reads, dark and light.
   - Commit: 6d00d752.
   - ls can delete: the registered header rules (w1 apps/window.py:114-119).
3. `banner_host(window)` for a window holding an FXDockArea now returns
   that area.
   - Cause: `banner_host` only walked up from the widget.
   - Fix: when the walk up finds no area, it looks down from the widget's
     app window (`_app_window`, as in item 1).
   - This also covers an embedded window: its banner goes on its own area,
     not on the host's.
   - Commit: 6d00d752.
   - ls can delete: the `findChild` fallback (w2 apps/widgets/banner.py:38-41).
4. Breadcrumb Tab stops.
   - Change: `segments_focusable` is renamed `tab_stops`. False takes the
     segments and the back and forward buttons off the Tab chain. The
     path editor keeps its stop.
   - Docs: widgets.md is updated.
   - Commit: 7e4af7bd.
   - ls change: w2 apps/views/breadcrumb.py:31 becomes
     `segments_focusable=False` -> `tab_stops=False`. Delete its NoFocus
     loop (breadcrumb.py:33-35).
5. Corner toolbar and footer.
   - Corner: this is generic chrome, and fxgui already does it.
     `QWidget#fxMenuBarCorner QToolBar` is transparent, with no border,
     padding or spacing. Its disabled tool buttons have no fill.
     `test_corner_tools_show_the_menu_bar_through` covers both, framed and
     not. ls can delete the `setStyleSheet` (w1 apps/window.py:294-297) and
     the `mark_as_frame(corner)` (window.py:298-299).
   - Footer flattening: this is a studio choice, so it stays in ls.
     fxgui flattens icon-only push buttons only on bars it knows are bars:
     the window's own toolbars, status bar and menu bar.
   - Why not `mark_as_frame`: it also marks containers such as FXDockArea
     itself, splitters and a dock column. Flattening under every marked
     widget would flatten the buttons inside panes. The footer under the
     panes is ls's own layout.
   - One gap in ls: `_on_the_frame` (window.py:125-131) overwrites a role
     a button already carries. fxgui keeps it.
6. DependencyPage native crash: NOT reproduced, so no fxgui change.
   - Tried, no crash:
     - `FXMainWindow().setCentralWidget(DependencyPage())` 15 times in a
       loop, with fix-gaps fxgui and the fxgui13 tree.
     - The offscreen and windows platforms, shown and not shown.
     - test_command_row/framed_panes/workflow_window/dependency_page with
       -n 8, twice.
   - The w1 tree no longer builds DependencyPage on current fxgui:
     view.py:92 calls `fxstyle.get_font_family`, which ba06544a removed.
   - The only crashes on record are in w1-run.txt (01:20), two kinds:
     - inside QtAds `addDockWidget`, from
       ProjectSettingsWindow.add_dock("page")
     - in Workflows `show_workflow`, at `tabs.setCurrentIndex`
   - Both spots hold a GraphCanvas, and both crashed only under xdist.
   - Open: the cause is not known. A repro command was asked for.
7. Pane sizes against a restore: correct as built, now tested.
   - Order on the first show: Qt shows the children first, so the area
     splits by weight at the size before the window grows. The weights
     are also stretch factors, so the grow keeps the proportions. A layout
     restored before the show waits for it. A layout restored in the
     window's showEvent, after the grow, applies at once.
   - Test: `test_a_saved_layout_comes_back_exactly_in_a_grown_window` runs
     both orders, with fit_to_contents and restoreGeometry. It checks that
     the window size and every splitter size match. It passed before any
     change.

6b. Follow-up on the two real crashes, time-boxed:
   - Ran: w1's own test_command_row/framed_panes/dependency_page tests,
     serially, with faulthandler. A local `get_font_family` stub (a
     pytest plugin in the scratchpad) was used against fix-gaps, then
     against fxgui e2cf93a8 (00:32, before the rename).
   - Both runs stop before any window: 196 errors on
     `FXOutputLogWidget(capture_output=...)`, a keyword gone since
     d035969e (2026-10-01 15:41). So the w1 tree as it stands matches no
     fxgui on audit-fixes.
   - Its 01:20 run cannot be replayed. No fxgui cause was found.
   - Read, with no cause found: fxdocking's `_sweep` and `mark_as_frame`
     (both touch only QtAds containers and splitters), and
     `_drop_focus_rect`, which only styles QAbstractItemView, never a
     QGraphicsView.
   - The ls frames to rerun on the merged tree:
     - ProjectSettingsWindow.__init__ -> AppWindow.add_dock
       (w1 apps/window.py:453) -> FXDockArea.add_dock -> QtAds
       addDockWidget, for the "page" pane holding the stack with the
       DependencyPage GraphCanvas.
     - WorkflowsWindow.show_workflow
       (w1 apps/workflows/views/window.py:470) `tabs.setCurrentIndex`
       on a fresh GraphCanvas tab.
8. FXFilteredTree takes `actions=` (a layout), a row of buttons under the
   tree.
   - Why under: ls's own `filtered_tree_panel` put it there ("A row of
     action buttons under the tree"), and ls's row_pane keeps it there.
     The filter bar's row already holds the fold buttons.
   - Commit: 74050be5.
   - ls change: fxgui13-t apps/widgets/rows.py:223-226 becomes
     `FXFilteredTree(tree, placeholder=placeholder, actions=actions)`.
     Delete the `panel.layout().addLayout` line.
9. `fxutils.add_submenu(menu, label, before=None)` inserts ahead of
   `before`, as `QMenu.insertMenu` does.
   - Commit: 7702b1f5.
   - ls change: fxgui13-t apps/widgets/action_menu.py:142-147 becomes one
     call, `sub = fxutils.add_submenu(menu, label, before=before)`.
10. FXEmojiButton.attach still returns None: unchanged.
    - Why: both ls calls (fxgui13-t hub/views/comments.py:682 and
      composer.py:253) already hold the button and ignore the return.
11. TREE_KEYS stays unexported.
    - Why: ls does not use it. Its lazy tree passes its own
      `_LAZY_TREE_KEYS = "+- "` (fxgui13-t apps/views/tree.py:63) to
      `type_into(qt_keys=...)`. The default stays visible in
      `type_into`'s signature and docstring.
11b. `FXStatusBar.version` / `.company` were dropped on purpose.
    - Commit: 41f9a5b8, "one name per job".
    - What replaces them: the items `version_label.text()` and
      `company_label.text()`.
    - ls change: fxgui13-t apps/window.py:285-286 becomes
      `StatusBar(self, version=plain.version_label.text(),
      company=plain.company_label.text())`.
12. app_root and the suite's NoAntialias font: the premise does not hold.
    - `fxstyle.font()` starts from `QFont()`, which copies the
      application font's values. Its resolve mask covers only families
      and size, so the style strategy carries through
      `register_themed_root(qapp)` and every `apply_theme`.
    - New test: `test_a_themed_app_keeps_its_text_antialiasing`, under
      app_root. It checks the app font and a label's font across light
      and dark, and it passes with no fxgui change.
    - It is offscreen on Windows. CI's offscreen run on Linux will
      confirm it there.
    - Commit: 7106f36e.

Merged audit-fixes 1618f76c (cd655213). Full suite: 2515 passed,
6 skipped. ruff F,B,BLE clean.
