# fxgui complexity audit (13.0.0)

A read-only audit of the audit-fixes tree at e24d13db. Nothing in the code
was edited.

Owner rule: anything wrong, costly or too complicated changes, and each job
gets one mechanism. 13.0.0 is a major release, so being on PyPI is no reason
to keep a duplicate.

## How to read this

- Findings are grouped by file, so fixers can split the work without
  touching the same file.
- Inside each file the order is: bugs-in-waiting (B), then duplication (D),
  then size and dead code (S).
- Each finding gives the place (file:line), the one mechanism or deletion
  that replaces it, the callers that change, and a confidence: H, M or L.
- "ls" means ls-pipeline/python/ls_pipeline/apps/. ls-pipeline pins fxgui
  12.12.0, so every ls change waits for the pin bump.
- "IN PROGRESS" means another agent is already fixing it: t5c-switch or
  t5c-visual.
- Sources: fxstyle.py, style.qss, the host rules and tests/ were read
  directly. Four sub-auditors read every other file line by line. The
  cross-file claims were re-checked; most per-widget findings were not
  re-read one by one.

## Counts per file

| File | Findings |
|---|---|
| fxstyle.py | 14 |
| qss/style.qss + _HOST_RULES | 5 |
| style.yaml | 1 (counted with fxstyle D2) |
| fxicons.py | 11 |
| fxutils.py | 7 |
| fxdcc.py | 1 (delete the module) |
| fxconfig.py | 3 |
| _compat.py / fxconstants.py / __init__.py / _version.py / _constants.py | 5 |
| _delegates.py | 18 |
| _tree_items.py | 2 |
| fxcore.py | 5 |
| _fuzzy_search_list.py / _fuzzy_search_tree.py | 6 |
| _tooltip.py | 8 |
| _tips.py | 1 |
| _main_window.py | 10 |
| _status_bar.py | 6 |
| fxdocking.py | 4 |
| _dialogs.py | 4 |
| _splash_screen.py | 8 |
| _notification_banner.py | 6 |
| _system_tray.py | 3 |
| _progress_card.py | 3 |
| _loading_spinner.py | 3 |
| _widget.py / _singleton.py / _single_instance.py | 3 |
| Cross-widget (inputs, accessors, QSS, colours) | 9 |
| _log_widget.py | 7 |
| _timeline_slider.py | 8 |
| _drop_zone.py | 7 |
| _file_path_widget.py | 4 |
| _breadcrumb.py | 5 |
| _code_block.py | 4 |
| _collapsible.py | 4 |
| _tag_input.py | 2 |
| Small widgets (rating, range slider, inputs, buttons, palette, emoji, avatar, keyboard, combo, accordion, scroll area, flow layout, validators, screen grab, status dot, comments) | 20 |
| examples.py | 5 |
| tests/ | 13 |
| ls-pipeline copies (inventory) | 25 |

Total: about 266 findings, counting the ls inventory. Nothing is over 1 s
except the two tests named under tests/.

## Top bugs-in-waiting (all files)

1. _status_bar.py:412 tint reads top-level feedback, not the theme's.
   IN PROGRESS (t5c-switch).
2. _status_bar.py:300/433 a theme switch wipes the message. IN PROGRESS
   (t5c-switch).
3. _tips.py:73,114 tip HTML bakes the old theme's colours. IN PROGRESS
   (t5c-switch).
4. _delegates.py:1515 column ends use logical columns: wrong cells after a
   header drag.
5. _delegates.py:2623 sizeHint ignores per-item fonts: titles clip.
6. _delegates.py:168 two item roles share UserRole+5.
7. fxicons.py:959 disabled icon ink is always #59808080.
8. fxicons.py:647 QPixmapCache.find(key) may blank every icon on PySide2.
9. fxutils.py:469 fit_columns ignores iconSize.
10. _tooltip.py:286 every hover re-reads style.qss and re-themes a window.
11. _tooltip.py:1481 a second set_tooltip stacks a second tooltip.
12. _main_window.py:728 About shows stale project/version/company.
13. _file_path_widget.py mode not validated; the gallery folder picker
    picks files.
14. _tag_input.py:200 remove_tag leaves ghost or double-deleted chips.
15. _log_widget.py:282 Shift+Enter "previous" is not wired.
16. _timeline_slider.py:229 the promised shortcut keys do nothing; the fps
    timer drifts.
17. fxcore.py:169 filter and sort score differently.
18. _tree_items.py:30 __lt__ can be cyclic.
19. _fuzzy_search_list.py:249 setFocus(self) breaks setFocus(reason).
20. _splash_screen.py: pixmap shadowing, dead theme border, two crashes,
    "click to close" does nothing.
21. _drop_zone.py:309 an unowned singleShot; a QMenu leaks per right-click.
22. _single_instance.py:51 a failed listen() looks like success.
23. _notification_banner.py:544 set_timeout leaves the old timer running.
24. tests/conftest.py does not reset the loaded colour file.

---

## fxstyle.py

- D1 [H] fxstyle.py:456-609, 523: seven public getters read one colour
  cache: colors(), get_theme_colors(), get_accent_colors, get_icon_color,
  get_icon_on_accent_primary/secondary and get_feedback_colors.
  - get_theme_colors() copies the whole dict on every call, some of them
    inside paint paths.
  - Keep colors().
  - Delete get_icon_color (fxicons.py:940-956 wraps it too),
    get_icon_on_accent_*, and get_accent_colors (ls
    submitter/views/checks.py:59).
  - get_feedback_colors (10 ls calls): keep it as the one dict view, or
    move every caller to colors().feedback_x_y. Pick one.
  - get_theme_colors (79 ls calls) stays callable, but no paint path calls
    it (see Cross-widget X5).
- D2 [H] fxstyle.py:310, 508-520 and style.yaml:29-45, 221: the feedback
  colours are written three times with the same values (yaml top level,
  dark's own block, _DEFAULT_FEEDBACK).
  - With the shipped file, neither the top-level block nor _DEFAULT_FEEDBACK
    is ever reached.
  - Fix: delete _DEFAULT_FEEDBACK and the yaml top-level block. _feedback
    becomes theme, then dark, then built-in.
  - Callers: _status_bar.py:412 and ls widgets/status_items.py:234 read the
    top level.
- D3 [H] fxstyle.py:1661: two public token resolvers, resolve() and
  replace_colors(qss, dict).
  - The only outside caller is ls widgets/docking.py:81, which is
    resolve(sheet).
  - Fix: delete replace_colors.
- D4 [H] fxstyle.py:1719, 2007: three ways to get a sheet: build_stylesheet,
  load_stylesheet(style_file, extra, theme) and register_themed_root.
  - build_stylesheet and load_stylesheet have no caller in fxgui or ls,
    only in tests.
  - register_themed_root already adds _HOST_RULES inside a host.
  - Fix: delete load_stylesheet and its `extra` parameter. Make
    build_stylesheet private.
  - Tests to change: test_fxstyle.py:18-27, test_theming_core.py:44.
- D5 [H] fxstyle.py:101-116 and fxwidgets/__init__.py:7-11, 190: one signal
  has two names (theme_manager.theme_changed and theme_changed), and
  notify_theme_changed only calls emit.
  - Fix: keep fxstyle.theme_changed on a private QObject. Drop
    theme_manager, FXThemeManager.notify_theme_changed and the fxwidgets
    re-exports.
  - ls callers: none.
- D6 [M-H] fxstyle.py:1274-1278: two radius tokens for one value,
  @button_radius ("4px") and @radius ("4", used only as @radiuspx at
  fxdocking.py:53).
  - style.qss hard-codes 41 radii (2px x16, 3px x6, 4px x15, 6px x2), and
    widget QSS hard-codes 13 more (see Cross-widget X4).
  - Fix: one token with its unit, used wherever 4px is meant. Decide
    whether 2px and 3px become a second, smaller token.
- D7 [H] fxstyle.py:1315 and 1282-1285: the light-or-dark rule is written
  twice, in is_light_theme() (not in __all__) and in the ~icons folder
  choice.
  - Fix: one private helper.
  - Caller: _code_block.py:120.
- D8 [M-H] fxstyle.py:925, 947, 984: three ways to pick ink on a
  background: get_contrast_text_color, readable_ink and _away_from.
  - get_contrast_text_color uses a 0.5 luminance midpoint, which is wrong.
    On #2196F3 it picks white at about 3:1, where black gives about 6.7:1.
    These numbers are my arithmetic; I did not run them.
  - text_on_accent_* defaults come from it, and _primary_button_fills then
    patches the result.
  - Fix: base everything on readable_ink and delete
    get_contrast_text_color.
  - Callers: _avatar.py:153, ls hub/views/comments.py:227.
- D9 [M] fxstyle.py:717-759, 1988-1997: fonts are kept in two forms.
  _resolve_font_stack builds a quoted CSS string, then font() splits it on
  commas and strips the quotes to get the names back.
  - Fix: one function returns the installed family list, and QSS joins it.
- D10 [H] fxstyle.py:672, 804, 706, 1708: the fonts block is merged twice
  (_font_config and _ranks), and the weight ValueError is written twice.
  - Fix: one merge, with ranks popped from it, and one weight check.
- D11 [M] fxstyle.py:319-341, 1448: the namespace cache has two
  invalidations, an explicit _invalidate_theme_namespace() and a key on
  (theme, id(colors)).
  - colors() also repeats _ensure_theme_loaded.
  - Fix: keep the key only. conftest calls the invalidator too.
- D12 [H] fxstyle.py:1770-1808: set_widget_style, _styled_widgets,
  WIDGET_STYLE_PROPERTY and _reapply_widget_styles are a whole mechanism
  with no caller in fxgui or ls (tests and the move-a plan only).
  - Meanwhile 11 per-widget setStyleSheet calls bake values:
    - _buttons.py:151
    - _delegates.py:733
    - _file_path_widget.py:137
    - _fuzzy_search_list.py:77
    - _splash_screen.py:210/226/238/256/436
    - _status_bar.py:433/467
  - Fix: each becomes a registered rule plus a property, or a
    set_widget_style call, so one per-widget mechanism remains.
- S1 [H] Dead code and wrong text:
  - fxstyle.py:1242-1245: the accent setdefault and the "#2196F3"/"#1976D2"
    fallbacks never run.
  - fxstyle.py:1615: the docstring names FXIconColorDelegate, which does
    not exist.
  - fxstyle.py:444: the get_colors docstring calls it "the preferred way",
    which contradicts colors().
  - fxstyle.py:241-243: an orphaned comment that belongs above
    _GENERIC_FONT_FAMILIES.
  - fxstyle.py:914-916: get_luminance parses the colour twice.
  - fxstyle.py:491-493: the get_feedback_colors docstring talks about
    "backward compatibility".
- S2 [H] fxstyle.py:1077: depth_shade calls get_theme_colors() (a dict
  copy). Use colors().
- Measured, not a cost: _token_map takes 0.19 ms, build_stylesheet 1.4 ms,
  and a theme switch on an FXMainWindow 17 ms with 3 token-map calls. No
  cache is needed. The real cost is _tooltip T2.

## qss/style.qss and _HOST_RULES

- Q1 [H for outline, M for the rest] fxstyle.py:1860: _HOST_RULES repeats
  `outline: none`, which the base QWidget rule already sets
  (style.qss:41). Delete it from the host rules; keep `margin: 0px`.
  - Every other host rule resets something the base sheet leaves open,
    checked selector by selector.
  - I can't prove they are all still needed without Houdini:
    tests/test_host_sheet.py skips its Houdini cases here.
- Q2 [H] Duplicate selectors:
  - QGroupBox::indicator at 73 and 78: merge them.
  - QToolButton::menu-button:hover at 1493 and 1532: the second overrides
    the border; merge them.
- Q3 [H] Commented-out declarations at 264, 265, 282, 670, 699, 799, 850
  (#626873), 853 (#4a4a4a) and 1597: delete them.
- Q4 [L] Comments are 8.4k of 44k characters, some of them history
  ("Measured on the dark theme..." at 33-40, "used to cover" at 419). Cut
  each to one line of why.
- Q5 [M-H] px radii throughout, QProgressBar (1-14) included: see fxstyle
  D6.
- QSlider rules: IN PROGRESS (t5c-visual).

## fxicons.py

- B1 [H, measured] fxicons.py:959-987: _get_disabled_icon_color sets
  saturation 0 and lightness 0.5, so it always returns #59808080. The
  fallback #80808060 (974) is hard-coded too.
  - Fix: delete it; the disabled ink is the text_disabled token.
  - Callers: the engine _ink (625), tests/test_icon_engine_palette.py:106.
- B2 [M, untested on PySide2] fxicons.py:647: QPixmapCache.find(key) is
  called with one argument. _delegates.py:86-94 says PySide2 needs
  find(key, pixmap). If so, the except at 636 hands back blank pixmaps.
  - Fix: one _compat helper, used here and by _delegates._find_cached.
- B3 [H] fxicons.py:1017: set_icon silently does nothing on a widget with
  no setIcon. Call it and let it raise.
- D1 [M-H] fxicons.py:471-513, 640-656, 677-681: three caches: the
  get_pixmap lru_cache(512), the engine's QPixmapCache and the
  _get_icon_cached QIcon lru_cache.
  - Fix: get_pixmap becomes the engine's scaledPixmap (a copy). Delete
    _get_pixmap_internal, _get_pixmap_cached, _get_icon_cached, the copy
    step at 780-785, and clear_icon_cache (tests can call
    QPixmapCache.clear).
  - Callers unchanged: _avatar.py:160 and 12 ls get_pixmap calls.
- D2 [H] fxicons.py:940-956: get_icon_color only wraps fxstyle; delete it
  (fxstyle D1).
- D3 [H] fxicons.py:991, 1000, 1013: the set_icon theme_color parameter is
  documented "Ignored". Delete it.
  - ls: action_menu.py:75 and workflows/views/panels.py:112 drop
    theme_color=False.
- D4 [M] fxicons.py:369-384: there are two ways to colour an icon, the
  engine ink and change_pixmap_color.
  - Its only outside caller is _delegates.py:322 (FXColorLabelDelegate,
    whose deletion is proposed).
  - Fix: make it a private _tint.
- D5 [M] fxicons.py:868-924 vs _delegates.py:2066-2083: two thumbnail
  framers that disagree.
  - rounded_pixmap has a hard-coded rgba(255,255,255,127) ring at 918 and
    only test callers.
  - _bordered_thumbnail draws an opaque white ring at 1x: soft on hi-DPI
    and invisible on light.
  - Fix: keep one framer with a token ring.
- D6 [H] fxicons.py:742-743, 521, 745-769: get_icon sets the default
  library twice and calls itself again for the fallback. Wrap only the
  path lookup in the try.
- S1 [H] superpose_icons (788-822): 0 callers, and it would IndexError at
  811. Delete it.
- S2 [M-H] set_default_icon_library and set_icon_defaults: 0 callers, tests
  included. get_available_icons_in_library (276-318): tests only;
  test_dcc_marks can call get_icon_path. Delete them.
- S3 [L] Small fixes:
  - The root default is repeated 3 times (264, 299, 353).
  - The get_icon_path docstring names a "verify" parameter that does not
    exist (336).
  - badged is missing from __all__.

## fxutils.py

- B1 [H, measured] fxutils.py:469-471: fit_columns builds a bare
  QStyleOptionViewItem, so the view's iconSize is never counted. With
  48 px icons it gives 146 px where resizeColumnToContents gives 200 px.
  - Fix: view.initViewItemOption(option) on Qt6, viewOptions() on Qt5.
  - ls rows.py:201 already does this.
- D1 [H] fxutils.py:create_action:
  - All 17 calls pass visible=True, the default, and enable is never
    changed.
  - `icon` duplicates icon_name; its one user is _system_tray.py:94, which
    passes icon_name="close" instead.
  - `parent or None` at 187 does nothing.
  - Fix: drop visible, enable and icon.
  - Callers: _main_window.py (15 calls), _system_tray.py.
- D2 [M] add_shadows: one caller (_splash_screen.py:194), with a hard-coded
  #000000 and a redundant parent.
  - Fix: make it the one shadow helper, with alpha and a token colour.
  - Use it for the tooltip (QColor(0,0,0,80)), _dialogs, the banner, the
    progress card and fxdocking _recross (alpha 64).
- D3 [L] later, rehome and focus_step have two import paths, _compat and
  fxutils (fxdocking.py:35 uses _compat). Keep one.
- D4 [L] markdown_to_plain_text lives on the delegate, but _tooltip.py:1118
  uses it. Move it here.
- S1 [H] get_formatted_time: one caller, _status_bar.py:421, with the
  defaults. Inline strftime("%H:%M").
- S2 [L] Small fixes:
  - load_ui needs no QFile: QUiLoader().load(path, parent) works.
  - set_app_user_model_id is missing from __all__.
  - The round_window_corners docstring is 40 lines.

## fxdcc.py

- S1 [H] Delete the module.
  - No caller anywhere uses get_*_main_window, get_houdini_stylesheet or
    STANDALONE/MAYA/NUKE.
  - HOUDINI's only use is _dialogs.py:218 (parent_package), which only
    tests/test_floating_dialog.py:61-63 passes.
  - Drop fxdcc from __init__.py:10, 35, 46.
  - This also removes a latent bug: the try at 89-94 wraps both the import
    and the call.

## fxconfig.py

- D1 [M-H] fxconfig.py:54-76, 109-121, 138: _get_config_dir, CONFIG_DIR,
  SETTINGS_FILE and the mkdir hand-roll
  QSettings(IniFormat, UserScope, name, "settings").
  - The Windows path stays the same; the Unix path moves to
    ~/.config/<name>.
  - conftest.py:35-37 switches to QSettings.setPath.
- S1 [H] get_application_name is used by tests only: delete it.
  SETTINGS_FILE is in __all__ only for tests. ls uses only
  set_application_name (apps/theme.py:98).
- B1 [L] get_value returns INI strings for bools and ints.

## _compat.py, fxconstants.py, __init__.py, _version.py, fxwidgets/_constants.py

- S1 [M-H] _compat.py:39-43: the innermost is_valid fallback is dead. qtpy
  covers four bindings, and PyQt always has sip.
- D1 [L] _compat.focus_step is not a compat shim: move it to fxutils.
- D2 [M] The package folder is computed in 5 places:
  fxconstants.PACKAGE_ROOT, fxstyle.py:192, _delegates.py:55,
  _system_tray.py:65 and examples.py:48.
  - Fix: one IMAGES_ROOT, used everywhere.
  - FAVICON_DARK has 0 callers.
- D3 [M] Two version sources: importlib.metadata (__init__.py:53-57) and
  _version.py, which nothing imports. Keep one.
- D4 [M] fxwidgets/_constants.py: six severity ints that belong in
  _severity.py.

## _delegates.py

- B1 [H on the bug, M-H on the fix] 1515-1540, 1528: _get_column_position
  uses the logical column number.
  - After a user drags a header, the rounded ends, border and focus ring
    land on the wrong cells.
  - The header is also walked twice per cell (1731, 1832).
  - Fix: use option.viewItemPosition, treating Invalid as OnlyOne. Delete
    _get_column_position and every column_position parameter.
  - Callers: the ls timesheet override (D6) and
    tests/test_delegate_row_shape.py.
- B2 [M-H] 2623-2709: sizeHint measures column 0 without the item's
  FontRole.
  - ls views/tree.py:479 and hub/views/detail.py:1271 set fonts per item,
    so their titles clip.
  - Fix: init the option once at the top. Delete the inner re-inits in
    _picker_rect (2261) and _check_width (2337).
- B3 [H] 168, 488, 499, 504, 421 and _tree_items.py:24: item roles live in
  three places, and two collide.
  - SKIP_DELEGATE_ROLE == STATUS_LABEL_COLOR_ROLE == UserRole+5.
  - FIRST_FREE_ROLE (+17) is kept in step with SORT_ROLE (+16) by hand.
  - The docstring says "+1 through +14", but +15 is used.
  - Fix: one role table in one module. ls names are unchanged:
    FIRST_FREE_ROLE in widgets/rows.py and row_colors.py; SORT_ROLE in
    hub/views/detail.py, scene_manager/views/window.py, widgets/rows.py and
    workflows/views/panels.py.
- B4 [M] 2644-2649, 2147, 2474, 2486: fixed row heights (50/40/30) and
  fixed text offsets clip with a larger root font. Build the height from
  the font metrics, with the thumbnail as a minimum.
- B5 [M, not measured] 2048-2053: os.path.getmtime runs on every paint of
  every thumbnail row, against the SMB share. Stat each path at most once
  per short window.
- B6 [M] 810-819: apply_minimum_thumbnail_width binds view.model() at call
  time, so a later setModel misses. See D2.
- B7 [H] 1809-1811 vs 1825-1826: the docstring says selected rows switch
  the ring token, but the code skips the ring on selected rows.
- D1 [H] 655-735: apply_transparent_selection appends about 50 lines to
  each view's own sheet, a second styling mechanism. Half the rules repeat
  (QTreeWidget beside QTreeView).
  - Fix: one registered `[fxOwnsRow="true"]` rule. The function sets the
    property and installs _DelegateOwnsTheRow. Delete
    TRANSPARENT_SELECTION_STYLE.
  - The 6 ls callers are unchanged: publisher/views/form.py:350,
    submitter/views/queue.py:144, submitter/views/targets.py:99,
    timesheet/views/window.py:358, views/tree.py:151, widgets/rows.py:103.
  - tests/test_delegate_fixes.py reads the constant and changes.
- D2 [H] 828-836 vs ls widgets/rows.py:128-160: two column-floor
  mechanisms. fxgui keeps closures in a dict stuck on the view; ls has
  _ColumnFloor, and rows.py:108-109 uses both.
  - Fix: fxgui takes the ls shape, a QObject parented to the view that
    follows setModel. ls passes floor=FIRST_COLUMN_MINIMUM and deletes
    _ColumnFloor.
- D3 [H] 1485: ink is picked by lightness under 128. Use
  fxstyle.readable_ink.
- D4 [M] 86-94 vs fxicons.py:647: two QPixmapCache lookups (fxicons B2).
- D5 [H] 1406, 1461 vs 1142-1167: _draw_status_dot and _draw_status_label
  re-validate colours that _indicator_metrics already checked. Pass the
  checked QColor.
- D6 [H] ls timesheet/views/window.py:177, 196-204, 232: the timesheet
  hand-rolls focus_ring="cell" and paint_selection=False, and its
  _is_focus_row is dead.
  - Fix: use the two knobs. Override has_focus_ring to check
    _EDITABLE_ROLE.
- D7 [H] Copied blocks:
  - icon placement, 2447-2451 and 2533-2537
  - title and description, with different offsets, 2156-2195 and
    2463-2496
  - overlay size and margin (15, 6), 1943-1944 and 2118-2119: make them
    constants
  - thumbnail rect, 1947-1951 and 2108-2112
  - the "widget style or app style" line, 144, 232 and 2219
  - Fix: one helper or constant per block.
- D8 [H] 2760-2774: paint fills surface_sunken in both branches. Hoist it
  out. Thumbnail row fill: IN PROGRESS (t5c-visual).
- D9 [owner's call] 1720-1727 vs style.qss:1385: two hover looks. The
  delegate uses accent_primary at alpha 80; plain lists use
  @accent_secondary.
- S1 [M] Hard-coded looks:
  - 2081: the frame is Qt.white, invisible on light.
  - 2806: the star defaults to #FFD700.
  - 103: the QColor(80,80,80) placeholder is dead.
  - The star (1977-1993), chevron (2597-2606) and tick (2389-2413) are
    hand-drawn polygons. Use get_icon(color=token); the tick may need its
    two-tone look.
- S2 [H] Dead option=None defaults on _badge_font, _status_label_width,
  _indicator_metrics, _child_count_badge_width, _child_count_width and
  _draw_child_count, plus the label_font fallback at 1473. Only
  tests/test_delegate_layout.py omits the option; make it required.
- S3 [H] Unused API, with no caller in fxgui, ls or tests: show_child_count,
  show_starred, STARRED_COLOR_ROLE, and STATUS_LABEL_ICON_ROLE with its
  branches (1103-1108, 1487-1500). The star feature is examples and tests
  only.
- S4 [H] 164-371: FXColorLabelDelegate is used only by examples.py:492 and
  tests.
  - It duplicates the status pill, hard-codes px sizes, recolours a pixmap
    on every paint, and its role collides (B3).
  - Delete it. Update examples.py, fxwidgets/__init__.py and the tests.
- S5 [H] 593-633: show_thumbnail, show_status_dot, show_status_label and
  picker_column are trivial properties beside the plain attribute
  paint_selection.
  - Make them plain attributes; focus_ring stays a property because it
    validates.
  - ls names are unchanged.
- S6 [L] 1585-1634: the col0_index "pre-computed" parameters only save a
  cheap call. Drop them.

## _tree_items.py

- B1 [M] _tree_items.py:30-39: __lt__ compares by key only when both rows
  have one, and by text otherwise. Mixing keyed and keyless rows can loop
  (A < B < C < A), and Qt's sort is then undefined.
  - Fix: keep keyless rows in one block, before or after the keyed ones.
  - I'm not sure any ls column mixes them.
- D1 [H] SORT_ROLE goes into the one role table (_delegates B3).

## fxcore.py

- B1 [M-H] 169 vs 176-199: the filter accepts any substring hit, but the
  sort ranks by quick_ratio only. So "character_hero_main" sorts below
  "heron" for "hero".
  - Fix: one scoring function for filter, sort and colour, where a
    substring hit scores 1.0.
- D1 [M] 194-197, 220-230: quick_ratio is recomputed twice per sort compare
  and again on every paint. Cache it per (filter, text); clear the cache in
  set_filter_text.
- S1 [H] 126-135, 161, 187: set_show_all and _show_all have 0 callers.
  Delete them.
- S2 [H] 245: the lazy import claims a circular import that does not
  exist. Import at the top.
- S3 [L] 203: the data() return annotation is wrong.

## _fuzzy_search_list.py, _fuzzy_search_tree.py

- B1 [H] _fuzzy_search_list.py:249-251: setFocus(self) shadows
  QWidget.setFocus(reason), so setFocus(Qt.TabFocusReason) raises.
  - Fix: setFocusProxy(self._search_bar); delete the override.
- D1 [M, a design merge] The two widgets do one job.
  - list items (327-334) is the same code as tree top_level_items
    (202-209).
  - select_item and remove_item exist twice, written differently.
  - list_view and tree_view are two names for _view.
  - Fix: one FXFuzzySearch on a tree view (setRootIsDecorated(False) when
    flat) with one `view` property.
  - Callers: examples.py, fxwidgets/__init__.py,
    tests/test_fuzzy_search.py, test_smooth_scroll.py, test_tips.py.
  - ls: none.
- D2 [H] list 54, 225-230, 238: the ratio is kept in the widget and in the
  proxy, and the setter sets the proxy twice. _color_match is written and
  never read.
  - Fix: the proxy holds the ratio.
- D3 [M] list 77: _ratio_icon is a do-nothing QPushButton with its own
  setStyleSheet.
  - Fix: a label or a registered rule. tests/test_tips.py:316 reads it.
- D4 [L] tree 74-80: _make_view silently turns on recursive filtering on
  the proxy. Do it where the proxy is built.
- S1 [H] color_match, set_color_match, set_selection_mode,
  set_placeholder, clear_search and visible_items have no outside callers.
  setFixedWidth(35) at list:97 can overflow "100%" (L).

## _tooltip.py

- B1 [H] 1481-1495, 1470-1478: a second set_tooltip call stacks a second
  FXTooltip.
  - On the manager path, title, shortcut and icon go stale, because they
    are only set when not None.
  - Which path runs depends on whether the manager was installed first.
- T2 [H] 286 with fxstyle._build: every hover builds a new FXTooltip, and
  each one calls register_themed_root.
  - That re-reads style.qss from disk and sets the full sheet, palette and
    font.
  - The comment "parentless window is outside every themed root" is false
    under FXApplication.
  - Fix: one reused popup, or none (D1). If one stays, it registers only
    outside FXApplication (_main_window D1).
- B3 [M] 1033-1111: the manager tooltips every row of every item view, DCC
  host views included, with the row's own text in bold. It also doubles
  with _ItemTooltipHandler items, which are not marked _EXPLICIT.
  - Fix: make it opt-in.
- B4 [M] 774-782: set_content ignores parts that did not exist at
  construction.
- D1 [H on the duplication; the cut size is an estimate] There are five
  tooltip mechanisms:
  - apply_tip
  - FXTooltipManager
  - set_tooltip through fx_tooltip_* properties
  - set_tooltip through a per-widget FXTooltip
  - _ItemTooltipHandler
  - On top: show_for_widget, show_for_rect and show_at_point wrap
    show_at_rect. There are three timer sets (238, 1004, 1307), four
    keep-alive holders (_SHOWN, _fx_tooltips, manager._tooltip,
    handler._tooltip) and two app-wide click filters (383-393, 1070-1072).
  - Fix: keep apply_tip plus at most one small popup. That deletes 900+
    lines.
  - fxgui callers: _main_window.py:29, 184, 251 (rich_tooltips),
    fxwidgets/__init__.py:91-95 and 180-188, examples.py:319-356, tests.
  - ls: 0 callers of any public name.
- D2 [H] 371-378, 704, 782, 818: the icon is baked in an accent hex.
  - Fix: FXIconLabel with get_icon(name, color="accent_primary"). Delete
    _refresh_icon and its calls.
- S1 [M] Leftovers:
  - _one_shot is set from outside the class (893, 952, 1182, 1368).
  - persistent=True doubles as "no hover", and show_delay/hide_delay are
    dead under it.
  - Line 212 is dead.
  - The margins disagree (518 vs 548).
  - The corner positions are unused.
  - The shortcut uses `monospace` where @font_mono exists, and its @border
    badge differs from keycap's state_hover.
  - The title is bold through setFont while its size comes from QSS.
  - The shadow hard-codes QColor(0,0,0,80) (fxutils D2).
- S2 [L] The module is 1502 lines; D1 is what shrinks it.

## _tips.py

- B1 [H] _tips.py:73, 114: apply_tip writes theme hex colours into the
  tooltip HTML, and nothing rewrites them on a switch. Building the HTML on
  QEvent.ToolTip is the fix. IN PROGRESS (t5c-switch: keycap and tooltip
  HTML colours).

## _main_window.py

- B1 [H] 728, 994-1016, 274-276: About reads project, version and company
  attributes that set_*_label never updates. ls window.py:283 reads them
  too.
  - Fix: one store, the labels or the attributes, read by both.
- B2 [L] 381 vs 750: "Always On Top" vs "Always on Top".
- D1 [M] 246, _dialogs.py:149, _splash_screen.py:146, _system_tray.py:106,
  _tooltip.py:286: the themed-root rule is decided in five places. The
  window and tooltip register unconditionally; the dialog, splash and tray
  only outside FXApplication.
  - Fix: register_themed_root decides (no-op when the app is already a
    root).
- D2 [H] 247, 786-789: _theme_switched exists only to drop the argument,
  yet _on_theme_changed also takes _theme_name.
  - Fix: one no-argument hook doing the action check sync and
    _fit_title_corner. Drop bar.update().
  - ls overrides: scene_manager/views/window.py:313, status_items.py:238.
- D3 [H] 625-633: menu_bar and status_bar alias Qt's menuBar() and
  statusBar(). Delete them.
  - ls: file_save/views/window.py:88, project_settings/views/window.py:287,
    scene_manager/views/window.py:206.
- D4 [H] set_theme and get_available_themes wrap fxstyle. Delete them.
- D5 [H] 961-1016: six status-bar wrappers that disagree on raising.
  - Fix: call the bar.
  - ls: window.py:334; set_project_label at window.py:303 and 480,
    scene_manager/app.py:39, views/navigation.py:124, 144, 253.
- S1 [H] 328-473: placeholder actions (check_updates, hide, hide_others,
  settings, home, previous, next) and the default toolbar. Delete them all.
  - Keep refresh_action, which ls uses (window.py:341, 361, 384, 421;
    scene_manager/views/window.py:240).
  - ls already passes toolbar=False (window.py:271).
- S2 [H] 635: use_corner_title is a no-op. Delete it, plus the ls call at
  window.py:311 and the test calls (test_corner_title.py,
  test_framed_window.py, which also call set_banner_text).
- S3 [H] Dead state and small cuts:
  - 165-170: severity constants on the class. ls callers:
    hub/views/window.py:346, 409; window.py:1128.
  - window_icon, window_title and window_size are dead state; the
    len >= 2 check at 290 is odd.
  - The ui_file loader is a copy of FXWidget's.
  - The About dialog leaks a QDialog per opening; use QMessageBox.about.
  - _is_valid_url has a dead except.
  - rich_tooltips is a tri-state flag with two states.
  - FXCommandRow margins: ls says the swap is moot but passes
    right != bottom. I am not sure who is right.

## _status_bar.py

- B1 [H] 412: the tint reads get_colors()["feedback"], the top-level yaml
  block. 165 and 415 read the theme's own block, so on light the bar takes
  dark's tint. ls status_items.py:233 copies it. IN PROGRESS (t5c-switch).
- B2 [H] 300, 433-440, 482-489: the tint is a per-widget setStyleSheet of
  baked hex, so a theme switch wipes the message.
  - Fix: a `severity` property plus registered
    `FXStatusBar[severity=x]` rules.
  - Then delete _tint, the setStyleSheet calls, _theme_switched,
    _on_theme_changed and the connect.
  - IN PROGRESS (t5c-switch).
- B3 [L] 318: the insert index is hard-coded as 3 + _right_items, and the
  count never goes down.
- D1 [M] 331-338: ground() repeats style.qss 1675/1748. The top border has
  two colours: @scrollbar_track in QSS, theme.border when painted. Pick
  one.
- D2 [M] The defaults "0.0.0" and "(c) Company" are copied in the status
  bar, the main window and the splash, and the splash's project is
  "Project" where the window's is "". One set of defaults.
- S1 [H] The background_color and pixmap parameters of showMessage are
  tests only. Delete them (coordinate with t5c-switch).

## fxdocking.py

- K1 Keep: _rethemed (285) is a real side effect (it calls the QtAds API).
  _inset is borderline.
- D1 [M] _recross uses get_theme_colors where colors() would do, and
  hard-codes its shadow at alpha 64 (fxutils D2).
- D2 [M] 50-54 vs examples.py:578-600: the pane-card QSS is copied, with
  @radiuspx here and @button_radius in the gallery.
  - Fix: one pane style in fxgui (for example mark_as_pane) and one radius
    token (fxstyle D6).
- S1 [L] _resweep queues one sweep per signal, with no merging. Coalesce
  them.

## _dialogs.py

- B1 [M] 166: a fresh QFont() drops the theme font. Use mark_as_title or
  QSS.
- S1 [H] 77-87, 218: parent_package and the Houdini rules are tests only.
  Delete them (with fxdcc).
- S2 [H] dialog_icon and dialog_title are dead state.
- D1 [M] The shadow is hand-made. Use fxutils.add_shadows (fxutils D2).

## _splash_screen.py

- B1 [H] 119, 328, 502: self.pixmap hides QSplashScreen.pixmap().
- B2 [H] 113, 462, 57: border_color defaults to "#4a4949", so the theme
  fallback at 57 never runs, and set_border defaults to "#555555". Default
  both to None.
- B3 [H] 309, 364: set_progress and toggle_progress_bar_visibility raise
  AttributeError when there is no progress bar.
- B4 [H] 505 with examples.py:661, 669: the gallery says "click to close",
  but mousePressEvent is empty. Close on click, and use
  fxutils.later(4000, splash, splash.close).
- B5 [L] 169: an image that exists but fails to load divides by zero.
- D1 [M] 152, 423-445: the overlay theme_changed connection is only a look.
  Paint the overlay in paintEvent instead.
- D2 [M] 210, 226, 238, 256: per-widget font-size sheets become one
  registered rule. The mask and the clip both round the corners: keep one.
- S1 [M] Twelve setters have no callers. The fade_in attribute sits beside
  toggle_fade_in(). Delete the setters or the attribute.

## _notification_banner.py

- B1 [M] 544: set_timeout does not stop a running _dismiss_timer. ls
  banner.py:93 calls it before show, which is also redundant: ERROR already
  defaults to 0.
- D1 [M] SEVERITY_ICONS and SEVERITY_TITLES copy SEVERITIES.
- D2 [M] action_text and action_clicked duplicate `actions`.
- D3 [M] _notification_width copies width(), and the literal 16 copies the
  margin default.
- D4 [M] One `margin` parameter sets both top and side; split it. The card
  look (px radii, no token) is copied with FXProgressCard.
- S1 [L] ls banner.py: closed.connect(deleteLater) is redundant with :451.

## _system_tray.py

- S1 [M] 68-75: a history comment plus a branch that does nothing.
- D1 [M] closeEvent is not an event; it is the quit trigger. Rename it.
- D2 [M] Subclass QSystemTrayIcon and drop the wrappers. Line 94 is the
  create_action icon= user (fxutils D1).

## _progress_card.py

- D1 [M] STATUS_ICONS copies SEVERITIES.
- S1 [M] Dead state and an orphan _icon_label.
- S2 [M] increment, reset and progress are unused.

## _loading_spinner.py

IN PROGRESS (t5c-visual: spinner). The findings below are for that fixer to
check off.

- S1 [M] The dots and pulse styles plus set_style are about 90 lines with
  no callers.
- D1 [M] `color` takes a raw hex, not a token.
- D2 [M] The dim colour is hard-coded.

## _widget.py, _singleton.py, _single_instance.py

- S1 [M] _widget.py: FXWidget has 0 ls callers, and its ui_file loader is
  duplicated in _main_window. Delete it, or keep one loader.
- B1 [L] _singleton.py: a repeat call silently drops its arguments.
- B2 [M] _single_instance.py:51: a failed listen() returns False, the same
  answer as "woke the running copy", so the caller exits. Raise or return
  a distinct value.

## Cross-widget findings (fxwidgets)

- X1 [H] There are three ways to put an icon in a text field. Qt's own way
  is QLineEdit.addAction plus setClearButtonEnabled, which FXCommandPalette
  already uses (_command_palette.py:117).
  - FXIconLineEdit (_inputs.py:72-129) moves a QPushButton by hand, with
    the magic numbers 5, 18 and 22.
  - FXSearchBar (_search_bar.py:79-139, QSS 211-237) fakes a line edit: a
    container, two buttons, and an eventFilter + property + repolish for
    the focus ring.
  - FXPasswordLineEdit (_inputs.py:29-69) becomes a QLineEdit with one
    checkable action; .line_edit and .reveal_button go.
  - fxgui callers: _log_widget.py:260, _keyboard.py:194,
    _fuzzy_search_list.py:213 and 218, examples.py:183, tests
    (test_search_bar.py:55, test_keyboard_widgets.py:187, plus many
    icon_button/line_edit/reveal_button reads).
  - ls: views/login.py:52-56; focus.single_stop (focus.py:28) and its uses
    at navigation.py:84 and rows.py:488 go.
- X2 [H] Accessors are mixed four ways. Recommend x() + set_x()
  everywhere.
  - Triplets:
    - FXFilePathWidget path + get_path + set_path
      (_file_path_widget.py:173-193; tests/test_file_path_widget.py:18,
      38, 53)
    - FXRatingWidget rating + get_rating + set_rating
    - FXCollapsibleWidget title + get_title + set_title
      (_collapsible.py:212, 416-431)
    - FXTimelineSlider current_frame + set_frame
  - Properties with setters: FXSearchBar.text (makes bar.text() raise),
    FXDropZone, FXRangeSlider low/high, FXAccordion.exclusive,
    FXElidedLabel.mode.
  - Read-only property + set_x: FXBreadcrumb.path, FXTagInput.tags.
  - Qt style already: FXAvatar, FXEmojiPicker, FXCodeBlock.
- X3 [H] Flat buttons are styled four ways: _file_path_widget.py:137-139
  (per-widget sheet), _inputs.py:133-136, _search_bar.py:220-223 and
  _breadcrumb.py:34-42. Use fxRole="flat" (style.qss:1817-1833).
- X4 [M-H] Hard-coded sizes and colours:
  - Font sizes (break the root-font contract): _drop_zone.py:715, 722,
    728, 734; _tag_input.py:248; _emoji_picker.py:96; _tips.py:48;
    _range_slider.py:301; _timeline_slider.py:1165.
  - Radii: _breadcrumb.py:40; _code_block.py:289; _inputs.py:138, 237;
    _search_bar.py:215; _tag_input.py:261; _emoji_picker.py:89, 93;
    _rating_widget.py:229; _range_slider.py:318;
    _timeline_slider.py:982, 1181.
  - Colours: _timeline_slider.py:164 (#ff9800, keyframes ignore the
    theme), _search_bar.py:235, _tag_input.py:256, _range_slider.py:268,
    _avatar.py:147.
  - Tag chip border and range slider: IN PROGRESS (t5c-visual).
- X5 [H] get_theme_colors() (a dict copy) is called in paint paths. Use
  colors(), or getattr(colors(), token) when the token is in a variable.
  - _breadcrumb.py:131 and 313 (with 5 readable_ink calls per segment
    paint)
  - _command_palette.py:262
  - _comments.py:275
  - _status_dot.py:61
  - _tips.py:73, 114
  - get_feedback_colors() is read at _inputs.py:224 and _log_widget.py:121.
    Move ANSI_ROLES (_log_widget.py:92-109) to full token names.
- X6 [H] Colours fixed at build time miss a theme switch.
  - examples.py:408, 429-431 and 487-509 store QColor values in delegate
    roles.
  - set_marker_frames does QColor() at set time (_timeline_slider.py:682),
    so a token name gives an invalid colour; its docstring (669) calls
    get_feedback_colors "theme-aware".
  - FXThumbnailDelegate._as_color (_delegates.py:943-947) only takes a
    colour string.
  - Fix: make fxicons._theme_ink (387-393) the one public "token or colour"
    resolver, called at paint time. The gallery then passes tokens, not
    "#22c55e" and "#ef4444" (examples.py:547, 551).
- X7 [H] Repeated or dead widget QSS:
  - _code_block.py:283-292 repeats style.qss:731-738.
  - QFont("Consolas", 9) at _code_block.py:231-233 and
    _log_widget.py:244-246 is dead, because the stylesheet font wins.
    Delete both; _adjust_height then needs ensurePolished().
  - _buttons.py:227-238 restates the primary fills from style.qss:919-945,
    only because the transparent rule at 216-220 wins. Scope that rule.
    (M)
- X8 [H] 16777215 (QWIDGETSIZE_MAX) is written 3 times
  (_collapsible.py:79, _labels.py:175, _log_widget.py:371). The
  "icon_name" property is set at _collapsible.py:116, 249, 268 and
  _log_widget.py:275, 289, 303, 323, and read nowhere: delete it.
- X9 [M] Qt6-only calls while CLAUDE.md promises Qt5:
  - event.position(): _range_slider.py:383, 395; _rating_widget.py:235,
    241; _timeline_slider.py:1192, 1194, 1200, 1246
  - globalPosition(): _emoji_picker.py:203
  - .modifiers().value: _keyboard.py:157
  - Decide whether Qt5 is still promised. I'm not sure it is.

## _log_widget.py

- K1 Keep: theme_changed -> _recolour (215) is a real side effect.
- B1 [H] 282 vs 262: the Shift+Enter hint is not wired; Enter always goes
  next.
- D1 [M] 385-424: _update_search_count rescans the whole document on every
  keystroke. Debounce it or count incrementally.
- D2 [M] 426-462: _find_next and _find_previous are one function with a
  direction.
- D3 [M] 348-353, 364-369: six widgets are shown and hidden one by one. Use
  one container.
- D4 [M] 316-318, 333, 337-344, 355, 371, 378-383: the spacer hack should
  be a stretch.
- S1 [M] 115: move the lru_cache onto fxstyle.readable_ink. 642: rename
  restore_output_streams to stop_capture (tests only).
- S2 [M] 480-513: capture_output plus the 1 s logger poll, which ls refuses
  (stage_log.py:35-37). A candidate for deletion.

## _timeline_slider.py

- B1 [H] 229-355: the tips promise Home, Left, Space, Right, End, I and O,
  and there is no key handling. Add a keyPressEvent or remove the promise.
- B2 [M] 809, 820, 919: 1000 // fps drifts (24 plays at 24.39 fps), and
  int fps cannot express 23.976. Use a float fps and an elapsed timer.
- D1 [M] 164, 669, 682: marker and region colours are hex. Accept token
  names (X6).
- D2 [M] 798-820, 897-907: _fps, _loop_playback and start/end are kept
  twice, with blockSignals. Keep one copy.
- D3 [M] 761, 786, 900, 920, 929: hasattr is used as a flag. Initialise the
  attributes instead.
- D4 [M] 220-356: ten copies of a 6-line button block. A helper saves about
  110 lines.
- D5 [M] 1219-1221, 1276-1278: the x-to-frame conversion is written twice.
  429-431, 516-549: the centring hack should be a 3-column QGridLayout.
- S1 [M] 551-569: four colour wrapper properties. set_range here sets
  bounds, while FXRangeSlider.set_range sets values (see the range slider
  entry under Small widgets).

## _drop_zone.py

- B1 [H] 309: QTimer.singleShot with no owner fires on a deleted widget,
  and two flashes overlap. Use _compat.later.
- B2 [H] 397-415: a QMenu(self) is made on every right-click and never
  freed. Use fxutils.popup_menu.
- D1 [M] 72-90 vs 512-563, 74, 532: drag and drop is handled two ways, with
  the accept test duplicated. Keep one path-acceptance function.
- D2 [M] The clear button is toggled in four places. _on_clear_clicked is
  set_files([]) plus emit.
- D3 [M] 366-376: the size formatting is QLocale().formattedDataSize.
- S1 [H] 672-684: show_placeholder and show_file_tree have no callers.
- B3 [L] 474, 485: files_dropped emits the internal list; emit a copy.
  accept_mode is not validated, and extensions must be lowercase with a
  leading dot.

## _file_path_widget.py

- B1 [H] mode is not validated. examples.py:222 passes "directory", so the
  gallery's folder picker acts as a file picker. Raise ValueError on an
  unknown mode.
- D1 [H] 173-193: the `path` property beside get_path/set_path, the owner's
  example (X2).
- D2 [M] 203-214 vs 148-151: set_mode repeats the init code and does not
  re-validate.
- D3 [M] 134-139: the indicator is a QPushButton with a per-widget sheet.
  Make it an FXIconLabel. I'm not sure whether _input.setAcceptDrops (129)
  inserts file:/// text.

## _breadcrumb.py

- D1 [H] 147, 100, 313: every segment paint calls _colors(), which copies
  the dict and runs readable_ink five times (X5).
- D2 [M] 495, 511: back and forward emit the internal list, and should be
  one _step.
- B1 [M] 597-604: a home click emits two signals.
- D3 [M] 414 vs 307, 444, 493, 509, 527: _show_navigation is checked in
  two ways.
- S1 [L] The path and home_path properties (X2). The sizes 28 and 32, and
  RADIUS 4, are hard-coded.

## _code_block.py

The working tree has uncommitted edits here: lines after 17 are +6 against
HEAD.

- K1 Keep: theme_changed (82; 76 at HEAD) is a real side effect.
- D1 [H] X7 (repeated QSS, dead QFont).
- S1 [M] self._style is only used locally. The magic numbers 32, 60 and 400
  (249-251).
- S2 [M] get_supported_languages is not exported and has no callers.

## _collapsible.py

- D1 [M] Expanded state is kept three times: _is_expanded, the checkable
  toggle, and _title beside the label.
  - Fix: make the toggle non-checkable, connect clicked to toggle, and
    delete 321-326.
- B1 [M] The max_content_height setter does not re-apply while the section
  is open. The docstring says 0 is the default; the code uses 300.
- D2 [M] The title property beside get_title/set_title, with no callers
  (X2). get_icon/set_icon: tests use get_icon.
- S1 [L] 76, 190, 306-312: the resized signal is used only by tests.

## _tag_input.py

- B1 [H] 200-206: remove_tag calls deleteLater without removeWidget, so the
  chip is still found.
  - With duplicates, clear_tags deletes the same chip twice.
  - set_tags then clear_tags in the same turn leaves a ghost chip.
  - State is held twice: _tags and the layout.
  - Fix: removeWidget first, or keep one chips list.
- D1 [L] tags_changed fires once per tag on a bulk set. Chip border: IN
  PROGRESS (t5c-visual).

## Small widgets

- _rating_widget.py [M]:
  - rating + get_rating + set_rating (X2).
  - Dead enterEvent (249-251).
  - The focusIn/focusOut overrides (208-216) only call update(), which Qt
    already does.
  - Every mouse move rebuilds all the star icons (233-236).
  - The +2 at 161 copies the layout spacing.
- _range_slider.py [M]: IN PROGRESS (t5c-visual).
  - Dead focus overrides (370-378).
  - Height 70 is set three times (90, 98, 102).
  - set_range sets values, unlike QSlider; rename it set_values.
- _inputs.py [M]:
  - _is_animating duplicates the animation group's state.
  - The reset at 333 is redundant.
  - user=True (199, 219) means nothing.
  - The parent argument comes last, unlike the rest of the library.
- _buttons.py [M]:
  - A per-instance FXIconButton radius sheet (151-152); make it a
    registered rule.
  - FXJoinedGroup keeps its children in _widgets and in the layout
    (268-288).
  - 283 and 314 hand-guard a single-shot; use _compat.later.
  - The split button height: IN PROGRESS (t5c-visual).
- _command_palette.py [M]:
  - Brushes are baked at fill time (262-273).
  - _items and _shown are parallel lists; use an item data role.
  - A second fuzzy ranker beside fxcore (L).
- _comments.py [M]: the fixed height is measured before polish (90), and
  get_theme_colors is called in paint (275).
- _emoji_picker.py [M]:
  - The font is set twice (143-152 and QSS 96).
  - Hard-coded radii.
  - The popup_at clamp duplicates FXSeating.
- _avatar.py [M]: get_contrast_text_color (153) beside readable_ink
  (fxstyle D8), and the size is set three times (68-69, 105-111).
- _status_dot.py [M]: get_theme_colors in paint (61), and _FEEDBACK (15)
  restates the feedback keys.
- _keyboard.py [M]: setToolTip (210) instead of apply_tip; focusProxy()
  (194); .modifiers().value (X9).
- _checkable_combo.py [M]: blockSignals (65-70) also blocks the popup
  repaint, and the signal emits even when nothing changed.
- _accordion.py [M]: expand_all silently does nothing in exclusive mode
  (165-169). Raise, or expand the first section.
- _scroll_area.py [L]: the resized signal (32, 62-65) has no callers and
  fires before the base class resizes. Delete it.
- _flow_layout.py [M]: _gap (30) ignores setSpacing. Use QLayout's own
  spacing.
- _validators.py [L]: three regex one-liners (12-98). Only
  FXLowerCaseValidator is used outside fxgui
  (ls file_save/views/window.py:109).
- _screen_grab.py [M]: grabs the primary screen only (93-108). ls calls it
  at hub/views/capture.py:105 and detail.py:1006.
- _labels.py [M]: delete the FXElidedLabel mode-warning machinery (89-119,
  docstring 28-35 and 57-75); the only word-wrap user (_splash_screen.py:223)
  uses the default mode. The wrap branch (170-205) only works with a
  maximum height. There is no re-elide on a font change.
- _search_bar.py [M]: three ways to reach the field (line_edit(),
  focusProxy(), ls single_stop); stop() before start() at 197. See X1.
- _toggle_switch.py: not audited (another agent owns it). IN PROGRESS
  (t5c-visual: toggle).
- Clean: _seating.py, _confirm_delete.py, fxwidgets/__init__.py (apart
  from fxstyle D5), _application.py.

## examples.py

- B1 [H] 661, 669: the splash "click to close" (_splash_screen B4).
- B2 [H] 222: mode="directory" (_file_path_widget B1).
- D1 [M] 578-600, 597, 615, 632: hand-rolled pane-card QSS and margins
  (fxdocking D2).
- D2 [M] 273 vs 408, 429, 487, 50-57: feedback colour read by token and by
  dict, while _FEEDBACK and _SEVERITIES list the same levels. Hex colours
  at 547 and 551 (X6).
- S1 [L] 664-665: hard-coded splash corner_radius 12 and border_width 1.
  302-306: a shown-dict toggle. 707-729: duplicated banner and message
  comprehensions.

## tests/

- B1 [H] conftest.py: the reset covers _theme and the namespace, but not
  _colors, _color_file or _styled_widgets.
  - test_overlay_studio.py:14 fresh_colors and test_theming_core.py:15
    own_colors are the same fixture under two names, patching this gap.
  - Fix: reset all three in conftest and delete both fixtures.
- T1 [H] test_fxdocking.py:916 [toggle] takes 4.0 s and [button] 0.67 s.
  Each case spawns a whole child pytest, and the first pays a cold start.
  - Fix: one child process runs both cases.
- T2 [H] test_splash_screen.py:60 takes 2.05 s: it waits in real time on a
  1000 ms fade (_splash_screen.py:303).
  - Fix: splash._fade.setCurrentTime(splash._fade.duration()), or a short
    duration.
  - Nothing else is over 0.6 s. Fixed waits are 10-60 ms: not a cost.
- D1 [H] The same behaviour is pinned 2-3 times. Fold the files
  test_fxstyle.py, test_fxstyle_apply.py, test_fxstyle_builder.py,
  test_fxstyle_colors_api.py, test_fxstyle_roots.py, test_fxstyle_tokens.py
  and the theming half of test_theming_core.py into one test_fxstyle.py.
  The overlapping pairs:
  - longest key first: test_fxstyle.py:35, test_fxstyle_tokens.py:32
  - every token resolved: test_fxstyle.py:27, test_fxstyle_builder.py:6,
    test_theming_core.py:105
  - apply switches the theme: test_fxstyle.py:54, test_fxstyle_apply.py:9,
    test_fxstyle_colors_api.py:13
  - theme_changed fires: test_fxstyle_apply.py:31 (via theme_manager) and
    test_fxstyle_colors_api.py:20 (via theme_changed). This pins the
    fxstyle D5 alias twice.
  - roots re-sheeted: test_fxstyle_apply.py:16, test_fxstyle_roots.py:17
  - name-only signature: test_fxstyle_apply.py ("new signature"),
    test_removed_shims.py:20
  - namespace cached: test_fxstyle.py:44, test_fxstyle_colors_api.py:6,
    test_theming_core.py:76
  - partial theme fills from dark: test_fxstyle_tokens.py:27 and 45,
    test_theming_core.py:88
  - on-accent computed: test_fxstyle_tokens.py:19 and 56
- D2 [M] "Name is gone" tests pin absences: test_removed_shims.py (5),
  test_theming_core.py:184 and 190. They are low value; keep one file.
- D3 [H] app_root and host_root are copied in test_base_sheet.py:22, 40
  and test_title_ranks.py:11, 25. The copies have drifted: only
  base_sheet sets Fusion and restores the palette. Move them to conftest.
- D4 [M] Repeated helpers: _near (5 copies), _pixel (5), _ink* (5), a
  one-row delegate tree (test_delegate_checkbox, _fixes, _picker,
  _row_shape; 7 builders in all), a themed _window (8), _shown (9). Put
  them in one tests/_helpers.py.
- D5 [H] Tests that pin behaviour this audit deletes change with it:
  - test_corner_title.py and test_framed_window.py (set_banner_text,
    use_corner_title)
  - test_delegate_fixes.py (TRANSPARENT_SELECTION_STYLE)
  - test_floating_dialog.py:61 (parent_package)
  - test_file_path_widget.py (path)
  - test_tips.py:316 (_ratio_icon)

## ls-pipeline copies to delete after the 13.0 pin (inventory only)

This is not fxgui work. ls-pipeline still pins fxgui 12.12.0.

| ls-pipeline copy | Replaced by (fxgui) |
|---|---|
| widgets/docking.py (424 lines: QSS, restorable, _xml, _pane_names, _floor, _Floor, _recross, _sweep, _keep_gaps, _follow, _split, _weight, keep_open, title_bars, _configure) | fxdocking |
| widgets/status_items.py StatusItem | FXStatusItem |
| widgets/status_items.py show_tip (249-261) | _status_bar.py:340-357 |
| widgets/status_items.py ground (199-205) | _status_bar.py:331-338 |
| widgets/status_items.py showMessage/_tint overrides | fxgui's own (same attribute name) |
| window.py _CommandRow (183-207) | FXCommandRow |
| window.py eventFilter (462-471) | add_corner_widget (runs twice today) |
| window.py event (473-478) | _main_window.py:910-914 |
| window.py _key_the_float (885) | fxdocking.py:578-607 |
| widgets/loading.py LoadingOverlay, BusyLine (it imports FXThemeAware, gone in 13) | FXLoadingOverlay, FXStatusBar.set_busy |
| widgets/banner.py _clear_top, _home, _already_saying (and _Card writes the private _margin) | FXDockArea.clear_top, banner_host, show(unique=True)/message() |
| launcher/views/tray.py:38 | fxicons.badged |
| widgets/later.py (launcher/__main__.py:819, 841; submitter/views/window.py:489; widgets/docking.py:219) | fxutils.later |
| widgets/keys.py:50 | popup_menu |
| widgets/keys.py:84, 160 and views/tree.py:556 | FXKeyboardTree, FXSplitButton |
| widgets/action_menu.py:90-95, 147-151 | add_submenu |
| adapters/win32/taskbar.py:28 | set_app_user_model_id |
| widgets/tree_rows.py | children_of, filter_tree |
| widgets/rows.py:201, 237 and the filtered-tree assembly | fit_columns, TreeState, FXFilteredTree |
| widgets/rows.py:128-160 _ColumnFloor | apply_minimum_thumbnail_width(floor=) |
| widgets/focus.py | focus_step, rehome |
| launcher/views/seating.py:45, 82 | FXSeating |
| widgets/layout.py:86 | FXFlowLayout |
| widgets/confirm_delete.py:21 | FXConfirmDeleteDialog |
| widgets/status_dot.py:23 | FXStatusDot |
| widgets/record_table.py:147 | FXCheckableComboBox |
| widgets/palette.py:58, 80 | FXCommandPalette |
| hub/views/comments.py _fold:115, MentionBox:259, EmojiButton:404, ThreadLine:752 | _comments.py, FXEmojiButton.attach |
| widgets/text.py:45 ElidingLabel | FXElidedLabel(mode=ElideMiddle) |
| stage_log.py show_history/_append (private _insert_text_with_ansi) | append_many |
| widgets/row_colors.py:307 themed_pixmap; get_pixmap labels at hub/views/comments.py:713, 860, 865; composer.py:102; preview.py:147; task_info.py:328, 359, 372; submitter/views/checks.py:122 | FXIconLabel + set_icon(label, name, color=token) |
| views/breadcrumb.py overrides _fill_strip (deleted in 13), so sit_on_frame (window.py:145) bakes a sheet; navigation.py:183 sets the private _line_edit | segments_focusable=False, set_edit_placeholder |
| timesheet/views/window.py focus overrides | focus_ring="cell", paint_selection=False |

## Suggested split (no file shared)

- (a) fxstyle.py + style.qss + style.yaml + conftest.py
- (b) fxicons + fxutils + _compat + fxconstants + fxconfig, and the fxdcc
  deletion
- (c) _delegates + _tree_items + fxcore + the fuzzy widgets
- (d) _tooltip + _tips (_tips is IN PROGRESS with t5c-switch)
- (e) _main_window + _status_bar (IN PROGRESS parts with t5c-switch) +
  _dialogs + _splash + banner + tray + progress card + _widget +
  _singleton + _single_instance
- (f) inputs, search bar and password field (X1), plus the accessor rename
  (X2) across widgets
- (g) the remaining widgets + examples.py (_loading_spinner, range slider,
  split button and tag chip border are IN PROGRESS with t5c-visual)
- (h) tests consolidation, after the others land
