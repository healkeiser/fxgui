# fxgui audit fixes (13.0.0)

Every finding from the 2026-09-30 read-only audit gets fixed, each with a
test written first that fails on main and passes after. Architecture that
causes bad consequences gets replaced, not patched. Ships as 13.0.0: the
spec `specs/2026-07-30-theming-pull-model-design.md` said the shims go in
the next major, and this is it.

## Rules for every task

- Work only in the files your task owns. Another implementer owns the rest.
- Test first: write the test, run it, see it fail for the stated reason,
  then fix. Mention the failing output in your report.
- Run: `C:/Users/ValentinBeaumont/Documents/GitHub/fxgui/.venv/Scripts/python -m pytest -q -p no:cacheprovider`
  from your worktree root. The whole suite must be green before you report
  (baseline: 900 passed, 3 skipped).
- Commit style: `[FIX] ...`, `[FEAT] ...`, `[REFACTOR] ...`, one sentence
  saying what now works. Do not write CHANGELOG.md (CI writes it).
- ASCII only in source. Google docstrings, one summary line; no history in
  comments.
- Public names ls-pipeline uses stay callable: `use_corner_title`,
  `add_corner_widget`, `readable_ink`, `mark_as_frame`, `FXStatusBar`
  (`hide_status_line`, `showMessage`), `FXMainWindow(framed=...)`,
  `window_menu`, `help_menu`, `main_menu`, `FXThumbnailDelegate`,
  `apply_transparent_selection`, `apply_minimum_thumbnail_width`,
  `FXOutputLogWidget`, `FXOutputLogHandler`, `FXPygmentsHighlighter`,
  `FXCollapsibleWidget`, `FXElidedLabel`, `FXSearchBar`, `FXBreadcrumb`,
  `FXPasswordLineEdit`, `FXValidatedLineEdit`, `FXLowerCaseValidator`,
  `FXPrimaryButton`, `FXIconButton`, `FXJoinedGroup`, `FXAvatar`,
  `FXEmojiPicker`, `apply_tip`, `tip`, `keycap`, `get_theme_colors`,
  `colors()`, `set_color_file`. Unused public widgets are kept and fixed,
  not deleted (fxgui is on PyPI).
- Qt traps: a Python method named `emit` on a QObject breaks its signals;
  `QMenu.exec` is unpatchable on PySide, patch `exec_`; build submenus with
  `QMenu(label, parent)`, never `addMenu(str)`; a Python walk of
  `nextInFocusChain()` kills wrappers.

## Theming contract after this work (pull model)

- Built-in widget styling lives in QSS with `@tokens`, registered from the
  widget's own module with `fxstyle.register_widget_style(qss)` at import,
  keyed by class name / objectName selectors; state via dynamic properties
  + `fxutils.repolish(widget)`.
- Custom painting reads `fxstyle.colors()` inside `paintEvent`.
- Only real side effects (re-highlight, re-render a cached pixmap) connect
  to `fxstyle.theme_changed`.
- No widget calls `setStyleSheet(load_stylesheet())` on itself.

## Tasks

### T0 - CI gate and packaging (owner: lead)
- `.github/workflows/`: a `tests` job (checkout with submodules, PySide6,
  `pip install .[test]`, pytest) on push and PR; `release.yml` publish
  depends on it.
- `pyproject.toml`: `setuptools>=77` (PEP 639 license string).

### T1 - Theming core (owns fxstyle.py, fxicons.py, fxcore.py, fxutils.py, fxconfig.py, _widget.py, qss/, style.yaml)
1. `load_stylesheet()` has no side effects and defaults to `get_theme()`;
   it never writes `_theme` or flushes icons.
2. `get_theme_colors()` = the resolved `_token_map` (no `@`), cached with
   the namespace, calls `_ensure_theme_loaded()`, fills missing keys from
   the default theme, never `KeyError`s on a colour file without "dark".
   `colors()` and `get_theme_colors()` read the same cache.
3. One token resolver: public `fxstyle.resolve(qss, theme=None)` on
   `_token_map`; `replace_colors`, `load_stylesheet` use it; knows
   `@button_radius`, `@font_*`, `@feedback_*`, `@primary_button`, `@radius`.
4. `fxstyle.overlay_color_file(path)`: deep-merges `themes` and `fonts`
   onto the default file; `set_color_file` and the overlay both re-apply
   to themed roots and emit `theme_changed`.
5. Delete `FXProxyStyle.set_icon_color` and `icon_color`,
   `_FORCE_UPDATE_WALK`. Keep `FXThemeAware` working for now (T5 removes).
6. fxicons: `get_icon` reads colours once from the cache; one recolor path
   (`_colored_copy`), drop the per-pixel transparency loop (prove opaque
   PNG icons still recolor); `get_available_icons_in_library` honours
   custom roots and returns icon names from the library pattern.
7. fxcore: filtering survives non-text data (`str(x or "")`); proxy colours
   read the cache, not a per-cell recompute.
8. `FXWidget`: sets no stylesheet; `self.layout` no longer shadows
   `layout()` (rename `main_layout`); drop the mixin.
10. `fxstyle.palette()` builds a QPalette from the same table; it is set
    on every themed root with the sheet (never on a foreign app).
11. Icons: a QIconEngine resolves its colour from `colors()` at paint
    time, cached in QPixmapCache; the widget registry and
    `sync_colors_with_theme` go; `set_icon` keeps its signature.
9. fxutils: delete `filter_tree`, `deprecated`, `set_formatted_tooltip`
   (unused in fxgui and ls-pipeline).

### T2 - Window chrome (owns _main_window.py, _status_bar.py, _application.py, _singleton.py, _dialogs.py, _system_tray.py, _splash_screen.py, _notification_banner.py, _progress_card.py, _loading_spinner.py)
Architecture:
- Banner band and the `setCentralWidget` wrapper go. The corner title is
  the only name display; `setCentralWidget`/`centralWidget` are Qt's own.
  `use_corner_title()` stays callable (becomes a no-op or the default);
  `hide_banner`/`show_banner` go.
- fxgui menus are looked up, not stored as wrappers: `main_menu`,
  `edit_menu`, `window_menu`, `theme_menu`, `help_menu` become properties
  resolving through `menuBar()` by objectName; `setMenuBar(bar)` rebuilds
  fxgui's menus on the new bar; `setMenuBar(None)` is handled.
- Status bar accent lines are painted in `paintEvent` from one state (no
  overlay frames); helpers work on any `QStatusBar` or refuse clearly;
  `statusBar()` falls back to Qt's when none is set; `showMessage` does
  not replace the whole sheet; the timeout clears the tint
  (`@Slot(str)`), `clearMessage` not re-entered.
Defects:
- `FXSingleton` never hands back a deleted instance; drop `_initialized`.
- `FXApplication.instance()` override removed or matches Qt (returns
  None when there is no app); `_instance` cleared.
- `FXProgressCard.set_description` works on a card built without one.
- `FXLoadingOverlay` follows parent resizes (event filter); dead sheet
  removed. `FXLoadingSpinner` stops its timer when hidden, resumes shown;
  dead `angle` property removed.
- `FXNotificationBanner` deletes itself after dismiss; banners shown on a
  hidden parent stack correctly.
- `FXFloatingDialog`: centred on the cursor at `show_under_cursor` time
  after `adjustSize`; no `closeEvent` override; opaque body in the
  Houdini branch; icon follows theme switches; no `layout` shadowing.
- `FXSystemTray`: menu follows the theme; Quit only quits an
  `FXApplication`; ints for QPoint/QRect.
- `FXSplashScreen`: int QRect; follows theme; dead None branch removed.
- Delete dead: `_move_window`, `_refresh_dialog_button_icons`,
  `_add_shadows`, `native_menu_bar`, `with_status_line_padding`,
  empty `closeEvent`, status_line branch.
- All owned widgets leave `FXThemeAware` for the pull model.

### T3 - Item views (owns _delegates.py, _tooltip.py, _tree_items.py, _fuzzy_search_list.py, _fuzzy_search_tree.py)
Architecture:
- Delegates: finished thumbnail pixmaps in `QPixmapCache` keyed by path +
  mtime + theme; fallback checked once; one shared badge font per class
  derived from the view font; one icon-state helper and one
  circle-behind-icon helper; `_on_theme_changed` duplicate goes;
  `sizeHint` and paint share one layout computation (check box gap, star
  slot).
- Tooltips: one handler per view (item -> content map), tooltip built on
  first show, closed and deleted when done; app-wide filter only while
  visible and click-outside works; `finished` connected once.
- Fuzzy list and tree share one base; tree proxy uses
  `setRecursiveFilteringEnabled(True)`; tree data stored under one role;
  item map keyed by item, not text.
Defects: markdown strip cached and imported once (or removed, plain text);
picker menu parented to the view and opened at a global position; focus
ring on check rows spans the full row; minimum-width enforcement not
re-measuring every resize; `FXColorLabelDelegate` really hides text/icon
and paints empty selected cells; `rich_tooltips` honours `ToolTipRole`,
escapes HTML, no file check per hover; `show_for_widget` clears
`fx_has_explicit_tooltip`; `remove_item` reads the item before removal;
`TRANSPARENT_SELECTION_STYLE` duplicate and double-append fixed.
All owned widgets leave `FXThemeAware`.

### T4 - Other widgets (owns every other file in fxwidgets/ except examples)
Log widget: handler holds the widget weakly and detaches when it is gone;
poll timer stops with the widget; flush never touches the view cursor or
selection and only auto-scrolls when already at the bottom; one ANSI
formatter. Code block: lexer keeps offsets (`stripnl=False,
stripall=False, ensurenl=False`), lexes once per change, multi-line
strings recolour, one rehighlight per theme switch. `FXElidedLabel`:
`sizeHint` from full text, `text()` returns full text. Breadcrumb:
segment click records history. File path widget: `QThreadPool`, no
per-check QThread, no UI block; multi-file drop keeps all files.
Accordion: index looked up at signal time. Range slider: ties pick the
handle by drag direction; `round()`. Timeline: zoom-out always grows;
frame 0 accepted; spinboxes route through `set_range` and clamp the view.
Validated line edit: animations deleted or built once; caller margins and
sheet preserved. Search bar: focus ring works (`setFocusProxy`, property
driven); `setFocus(reason)` works. Rating: follows theme. Tag input:
chips wrap or scroll; `tags_changed` emits a copy. Capitalized validator
fixup reachable. Drop zone: Clear enabled with `show_tree=False`; one
path-acceptance function. Header click toggles only on left button
(event filter, no instance-patched handlers). `event.position()` over
`event.x()`. Hard-coded white inks use theme tokens. All owned widgets
leave `FXThemeAware`.

### T5 - Finish (owner: lead, after T1-T4 merge)
- Remove `FXThemeAware`, `apply_theme(widget, theme)`,
  `_apply_theme_styles` shims, deprecated collapsible aliases, dead
  `setRegExp` branches.
- One gallery: per-module `example()` blocks and `fxgui/ui/` deleted,
  `examples.py` covers every widget; `CLAUDE.md` and docs describe the
  pull-model contract.
- Move-over: every generic fix, workaround or widget that lives in
  ls-pipeline but belongs in fxgui moves into fxgui (inventory first),
  with its tests; ls-pipeline deletes its copy after the pin bump.
  Every inventory item lands in one of three places: (1) generic and
  missing from fxgui: moves in; (2) generic but fxgui or Qt already does
  it: nothing new in fxgui, ls-pipeline deletes its helper and calls the
  existing one; (3) a studio choice (brand sizes, which status items,
  row kind names): stays in ls-pipeline. No duplicate survives.
  The fxgui side is written from ls-pipeline qtads-everywhere at
  b027e360 and never edits ls-pipeline. The ls-pipeline side waits for
  the design-system session to merge that branch; before it, diff the
  moved source files from b027e360 to the merge and fold new fixes in.
  QtAds code goes in an optional module: `import PySide6QtAds as ads`
  only when used, the `docking` extra never required at import, works on
  PySide6 6.5.3 (Houdini 21: no 3-argument QTimer.singleShot with a
  callable); the rez fxgui package stays no_deps (Houdini ships its own
  houdini_qtads build).
- Icon engine clones: `fxicons._clones` owns PySide clone() results. Prove
  no crash at interpreter shutdown with cloned icons alive (subprocess
  test: build an app, clone an icon, exit without cleanup), in the venv
  and in hython.
- Base sheet carries shape and state only: `QWidget { color;
  background-color; font-size }` goes; the theme palette carries default
  colours and the root font carries the default size, so `setFont`,
  item BackgroundRole and plain labels behave (inventory items 3, 33,
  69). Before/after renders of every widget in every bundled theme.
- Prove PySide drops a `fxstyle.theme_changed` connection to a bound
  method when the receiving widget is deleted (switch after delete, no
  error), since the pull model relies on it.
- docs/how-to/styling.md 127-132 still documents the banner.
- Order-dependent tests: test_primary_button's shape test fails after
  test_icon_button_and_group alone (compares id() of wrappers); some test
  leaves the theme so a switch changes nothing. Fix both; the suite must
  pass in any order (`-p randomly` or reversed).
- Owner rule: wrong, costly or too complicated all require a change. After
  the merge, one whole-repo complexity audit (duplication, dead
  flexibility, hand-rolled Qt/stdlib) over the merged tree; every finding
  fixed before the release. 13.0.0 is a major: "public on PyPI" is not a
  reason to keep a duplicate (e.g. FXFilePathWidget's `path` property
  beside `get_path`/`set_path`); keep one name per job.
- Measure a theme switch on a large window and icon drawing in a long
  list; prove the icon engine and palette in a live hython session.
- Two whole-branch reviewers; fix every finding; release 13.0.0 (tell the
  ls-pipeline design-system session first); ls-pipeline adapts (drop
  `lotchi_colors.yaml` copy for the overlay, `docking.py` manual
  `@radius`, `FXElidedLabel` subclass, manual spinner stops, banner
  `deleteLater`, `FXThemeAware` uses, the hand-made palette in
  `apps/theme.py`) and bumps its pin.
