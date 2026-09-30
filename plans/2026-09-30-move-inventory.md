# ls-pipeline code that moves into fxgui

Inventory: 69 pieces of ls-pipeline code that belong in fxgui, grouped by fxgui file and ranked by value. Read-only survey. [13] = already on the 13.0.0 list. Conf = confidence (H/M/L). All paths are under python/ls_pipeline/apps/ on ls-pipeline main, unless the addendum says otherwise.

## fxstyle.py (theme, colour, fonts)

1. [13] theme.py:122-142 apply_selection_colors builds a QPalette (Highlight = accent_primary, HighlightedText = text_on_accent_primary) and sets it on the app. Only launcher/__main__.py:666 and theme.py:103 call it. Nothing re-runs it on theme_changed, so a theme switch keeps the old highlight. That is a live bug until fxgui owns it. ls keeps: nothing. H
2. [13] resources/lotchi_colors.yaml is 936 lines: a full copy of fxgui style.yaml (12.12.0), the "lotchi" theme appended, and the top-level `fonts:` block edited. package.py:40-44 pins fxgui because of it, and tests/apps/test_lotchi_colors.py polices the copy. With overlay_color_file, ls keeps only the lotchi theme plus fonts. Watch out: the font override sits in the top-level block so it applies under every theme. The overlay must be able to replace top-level `fonts:`, not only add themes. H
3. theme.py:145-186 title ranks (ROW 12px, SECTION 15px, CARD 16px, DemiBold). The helpers exist because fxgui's app sheet sets 12px on every widget, and that beats setFont. So a heading size can only live in the widget's own sheet. The same trap shows at launcher/views/rows.py:63-75 and 292, and views/breadcrumb.py:5-6 ("the theme's button rules beat a parent's"). Proposed: mark_as_title(widget, rank="section"|"card") with the sizes in the theme. ls keeps: the pixel values, if the brand wants its own. H
4. theme.py:189-201 _shape_body_text sets the app font to Medium weight, no hinting. Proposed: optional weight and hinting per face in the `fonts:` config, applied by fxgui. ls keeps the values. M
5. widgets/row_colors.py:216-249 `readable()` and `_contrast()`, `_mixed()`. views/breadcrumb.py:24-34 `_stepped()`. widgets/graph/view.py:55-83 `_blend`, `_ink_for`, `_ink_hex`. All re-implement fxstyle's private _mix, _step_toward and get_contrast_ratio, or readable_ink / get_contrast_text_color. Proposed: make mix(a, b, t) and step_toward(start, toward, done) public, then delete the copies. H
6. widgets/row_colors.py:137-209 depth shading: row_colors, shaded (steps toward border_light, holds text contrast at 4.5), depth_of, DEPTH_STEP/CAP. It is generic tree-depth tinting. Proposed: FXThumbnailDelegate option or fxstyle.depth_shade(base, depth). ls keeps the "section/item/task" kind names. M
7. row_colors.py:285-349 follow_theme, themed_sheet, themed_pixmap, _ThemeFollower, and text.py:18-32 ink(). Together they redo a sheet or pixmap on each theme change, one follower per widget. This is generic, and FXThemeAware does it only for subclasses. Proposed: fxstyle.themed_sheet(widget, build) and themed_pixmap, plus a function form of FXThemeAware. Used almost everywhere in ls. H
8. widgets/graph/view.py:85-103 family_for / title_family: the first installed family from get_font_family's QSS stack, for QGraphicsTextItem, which takes one family name. fxgui already has _resolve_font_stack. Proposed: public fxstyle.installed_font_family(role). M
9. theme.py:117 feedback_ink(key). A one-line accessor, but it is used in about 10 places. Proposed: fxstyle.get_feedback_ink(key). L
10. [13] widgets/docking.py:78 `_SHEET.replace("@radius", str(fxstyle.BUTTON_RADIUS))`, then replace_colors. This is the token-resolver item. H

## fxwidgets/_status_bar.py

11. widgets/status_items.py:146-282 StatusBar(FXStatusBar) fights the base in five ways:
    - (a) It removes and deletes fxgui's project_label and version_label and rebuilds them as clickable items.
    - (b) It keeps its own `_tint` copy by re-deriving it from get_colors()["feedback"][...]["background"], because fxgui exposes no "current background".
    - (c) It overrides the private _on_theme_changed to clear that tint.
    - (d) It adds show_tip, and window.py:461-466 routes QStatusTipEvent into it, so hover tips land after the items instead of over them.
    - (e) It passes project=" " to hide fxgui's "Project" placeholder (window.py:203).

    Proposed: FXStatusBar.ground() / tinted(), clickable status items (move StatusItem, status_items.py:56-143, a flat icon+word QToolButton whose ink is readable_ink against the bar), tip routing, and project=None meaning blank. ls keeps: which items exist (log counts, artist, tracker, Refreshed) and _TRACKER. H
12. [13] window.py:318 hide_status_line on every window. H
13. widgets/loading.py:14-80 BusyLine is a 3px indeterminate bar laid over FXStatusBar's status line. It hard-codes FXStatusBar's 3px height. Its own ponytail comment says FXStatusBar re-raises its rule on resize and hides the line. Proposed: FXStatusBar.set_busy(bool). ls keeps: the set_busy calls. H

## fxwidgets/_main_window.py

14. [13] window.py:287 super().setCentralWidget(column) skips fxgui's wrapper. H
15. window.py:260-262: the base's `parent` embeds the window as a child. ls calls setParent(parent, self.windowFlags()) to keep it floating over a DCC. Proposed: FXMainWindow with a parent stays a top-level Qt.Window. H
16. window.py:450-459: when a corner widget changes size (LayoutRequest), ls hides and shows title_corner. Otherwise QMenuBar re-places the corner only on show, and a later button falls into overflow. Proposed: add_corner_widget installs this re-place itself. H
17. window.py:161-188 _CommandRow plus toolbar=False. fxgui's Home/Previous/Next toolbar is dropped for a fixed row: not movable, toggle action hidden, margins re-set on StyleChange. Proposed: FXMainWindow(toolbar="row"), or a public "command row" API. ls keeps: its actions. M
18. window.py:119-128 _on_the_frame: on a framed window, icon-only push buttons get fxRole=flat. Proposed: fxgui's framed mode does it for bands it frames. M
19. window.py:665-693 focusNextPrevChild override. Under QtAds, Qt's own Tab walk jumps outside the declared chain. It goes through focus.step so wrappers survive. Generic for any QtAds window; belongs with item 20. M
20. window.py:495-719 add_dock, show_dock, set_dock_title, set_dock_tip, reset_layout, and geometry plus dock-state save and restore (showEvent 1195-1210, closeEvent 1246-1254). Every consumer rewrites these. Only the prefs storage is ls's. Proposed: FXMainWindow.add_dock(...) plus save_state()/restore_state() hooks. M (depends on whether fxgui adopts QtAds)

## New fxgui/fxdocking.py (QtAds, optional extra)

21. widgets/docking.py, the whole module:
    - a token sheet for QtAds (@frame, @pane_border, @well);
    - themed button icons, registered as copies (the QtAds icon-delete trap);
    - overlay cross colours via setIconColor, with the updateOverlayIcons crash note;
    - tab bar inset and minimum height;
    - _floor/_Floor (an area's minimum taken from its content);
    - gap sweeps through signals (a Python eventFilter on QtAds widgets crashed natively);
    - config flags;
    - the central placeholder (removed, never deleted);
    - the restorable() layout check;
    - settle(), the proportional split.

    None of it is pipeline logic; "ls_size", "ls_area" and "ls_placeholder" are just property names. The QtAds-for-Houdini spike shows it works in hython. Proposed: fxgui.fxdocking behind extras ["docking"]. ls keeps: which panes, and their names. H if the owner accepts a PySide6-QtAds optional dependency, else M.

## fxwidgets/_labels.py

22. [13] widgets/text.py:45-73 ElidingLabel subclasses FXElidedLabel so text() returns the whole string, and sets a tooltip. The ElideMiddle default is the only ls choice. H
23. widgets/text.py:35 bold(widget). A trivial font helper. L

## fxwidgets/_notification_banner.py

24. [13] widgets/banner.py:70 closed -> deleteLater. H
25. widgets/banner.py:74-84 _already_saying reads the private `_message` ("fxgui 12.2.0 has a setter and no reader"). Proposed: a public message() getter, and optionally FXNotificationBanner.show(unique=True) to dedupe per parent. H
26. widgets/banner.py:67-69: ERROR never times out. Proposed as fxgui's default for ERROR. L
27. widgets/banner.py:19-35 severity-to-logging map. FXNotificationBanner has _log_message (line 626). Check that it covers this, then delete ls's copy. M

## fxwidgets/_loading_spinner.py

28. [13] views/tree.py:157-159, 287-304, 498-502, 524-529, 687-692, 734-738: spinners stopped by hand. They start only on expand, "a spinner running from creation never stops repainting", and must stop before clear(). H
29. widgets/loading.py:83-119 LoadingOverlay duplicates FXLoadingOverlay. ls's version is transparent to the mouse, has no dim, and has start()/stop(). fxgui's blocks and dims. Proposed: FXLoadingOverlay(dim=False, block_input=False), then delete ls's. H
30. views/tree.py placeholder-row pattern: a lazy tree child row holding a 16px spinner via setItemWidget. It is generic ("lazy tree"), but tangled with the navigation presenter. L

## fxwidgets/_delegates.py (FXThumbnailDelegate)

31. widgets/row_colors.py:34-135 own_the_row_painting and paint_branch_area. A QProxyStyle drops PE_FrameFocusRect and PE_PanelItemViewRow, plus `outline: none`, plus a hand-drawn chevron in drawBranches. Together they kill Windows 11's accent pill and the native focus rect under the delegate's ring. Used by submitter/views/targets.py:114 and others. Any fxgui user of apply_transparent_selection on Windows 11 hits this. Proposed: part of FXThumbnailDelegate.apply_transparent_selection, or a public apply_delegate_owned_rows(view). H
32. timesheet/views/window.py:191-205 overrides the private _draw_focus_indicator to force (True, True) for a per-cell ring. Also _is_focus_row:175 and paint:230, which strips State_Selected because the delegate paints selection as a solid accent box. Proposed: focus_ring="row"|"cell" and paint_selection flags. ls keeps: weekend/today washes. M
33. timesheet/views/window.py:117-118: fxgui's sheet styles QTableView::item backgrounds, and that beats setBackground. Rule: the delegate or the sheet must let BackgroundRole through. hub/views/preview.py:145 is the same trap: fxgui's sheet boxes a QLabel in its own surface. launcher/views/popup.py:651-653 too: the app sheet's QWidget rule fills children, so hover had to be re-asserted. M
34. widgets/rows.py:128-160 _ColumnFloor, a per-section minimum width (QHeaderView has none). It composes with apply_minimum_thumbnail_width. Proposed: a floor argument on it, or fxutils.floor_section(header, col, px). M
35. widgets/rows.py:201-227 fit_columns widens columns to fit collapsed rows too (resizeColumnToContents misses them), using the delegate's sizeHint and the indentation. H generic. M value.
36. widgets/rows.py:53-71 DetailTreeItem sorts by a SORT_ROLE number, else text. It dodges the super().__lt__ Shiboken recursion segfault. Proposed: merge into FXSortedTreeWidgetItem (role key first, natural sort fallback). ls keeps: the role number. M

## fxwidgets/_breadcrumb.py

37. views/breadcrumb.py:37-109 sit_on_frame. It overrides private _fill_strip and _container because the strip's own tokens fail on a framed window: pane_border can equal the fill, and solarized_light's border_light gives text 1.41:1. So an edge and ink are computed at 4.5:1 and 1.3:1. This is an fxgui colour bug on framed windows. Also line 73: restating STRIP_*_TOKEN "so fxgui cannot move them". H
38. views/breadcrumb.py:86, 115-118 plus widgets/focus.py:22-25 no_stops. Every segment takes a Tab stop, and the fix is re-applied after each private _rebuild_breadcrumb. Proposed: FXBreadcrumb(segments_focusable=False). H
39. views/navigation.py:183 breadcrumb._line_edit.setPlaceholderText(...). Proposed: a public set_edit_placeholder. H

## fxwidgets/_inputs.py

40. views/login.py:52-55: FXPasswordLineEdit's reveal button is an auto-default QPushButton. In a dialog, Enter shows the password instead of accepting. ls sets setAutoDefault(False) on every child button. This is a plain fxgui bug. H

## fxwidgets/_log_widget.py

41. [13] ANSI colours from the theme (stage_log uses the console formatter's ANSI codes).
42. widgets/stage_log.py:58-102 overrides and calls private _insert_text_with_ansi for show_history (one bulk insert) and a hanging indent under the message column. It also calls private _show_search (line 109). Proposed: public append_many(lines), a hang_indent(regex) option, and a public show_search(). ls keeps: the "HH:MM:SS LEVEL name" regex. H
43. stage_log.py:40 and window.py:489-494 hide, then re-show, clear_button. Fine as is, but a show_clear=False argument would help. L

## fxwidgets/_search_bar.py and focus

44. widgets/focus.py:28-43 single_stop: FXSearchBar brings 3 Tab stops, and ls reduces it to its line edit as focus proxy. Proposed: FXSearchBar is one stop by default and exposes line_edit(). H
45. widgets/focus.py:62-79 step() / rehomed(). This is the PySide wrapper-lifetime fix: a getter files the returned widget's wrapper under the widget asked, and "QMenuBar already deleted" follows. Generic, and fxgui already fixed siblings of it (c349c36f). Proposed: fxgui._compat.rehome() and a safe focus-chain step. H

## fxwidgets new modules / fxutils.py

46. widgets/keys.py, all generic:
    - KeyboardTree: Menu/Shift+F10 open the row menu, Enter runs a primary act, typing goes to a filter field while +-* and Space stay Qt's.
    - SplitButton: Enter, Alt+Down and Menu work on a MenuButtonPopup, opened via popup() rather than exec.
    - popup_menu: popup plus deleteLater on aboutToHide. It pairs with the QMenu.exec-is-unpatchable memory.
    - add_action.
    - scroll_by_pixel. fxgui 1c35c5b4 does per-pixel scrolling only in its own views. An app-wide default in FXApplication would retire ls's calls.

    Proposed: fxwidgets/_keyboard.py (FXKeyboardTree, FXSplitButton) and fxutils.popup_menu. H
47. widgets/action_menu.py:90-95 and 147-149: build submenus with QMenu(label, parent) because an addMenu(str) submenu dies with the first dropped wrapper (the pyside-addmenu-str-dies memory). settle_split_button (316-333) is generic too. Proposed: fxutils.add_submenu(menu, label). The rest of action_menu is pipeline Action logic and stays. M
48. widgets/tree_rows.py:24-61 filter_rows: any column, and a match keeps its subtree and its ancestors. fxutils.filter_tree is deprecated, checks one column and one level only, and is wrong for deep trees. Proposed: replace filter_tree's body with this, and move children_of too. H
49. widgets/rows.py:236-343 TreeState, tree_state, restore_tree_state. Snapshot and restore of expanded, selected, current and scroll by row text, which survives a rebuild. Generic. Proposed: fxutils or fxcore. M
50. widgets/rows.py:345-395 fold_buttons and filtered_tree_panel (expand/collapse all, filter bar over a tree). Proposed: FXFilteredTree, a small composite. M
51. widgets/layout.py:113-186 FlowLayout, a wrapping layout with height-for-width. fxgui has none; FXTagInput may carry its own. Proposed: fxwidgets FXFlowLayout. H. The rest of layout.py stays in ls: WINDOW_MARGIN, GAP and the card numbers are brand metrics. hairline() (a painted 1px rule, not the QFrame HLine bevel) is generic. L
52. widgets/palette.py CommandPalette plus rank(): a frameless popup over window commands with fuzzy word-order ranking and sections, keys and disabled tips. Generic, ls-free except the "shots and tasks" strings. Proposed: FXCommandPalette. M
53. widgets/portrait.py round_face / round_rect: cover-crop to a circle or rounded rect at the device pixel ratio, with the delegate-matching outline. FXAvatar may already do the circle, so check. _CORNER = 4 restates fxgui's radius; use BUTTON_RADIUS. Proposed: fxicons or fxutils.rounded_pixmap. M
54. widgets/status_dot.py StatusDot, a clickable tone dot. Generic, but tied to ls tones. L
55. widgets/record_table.py:147-178 _CheckableCombo (the popup stays open while you tick several rows). Generic: FXCheckableComboBox. The multi-choice delegate and _TokenDelegate (`{token}` painted in the accent, bold on selection) are generic delegates. RecordTable itself is tied to ls presenters.fields. M for the combo, L for the rest.
56. submitter/views/window.py:165-220 _CappedScroll (a scroll area sized to content between a floor and a cap, updateGeometry on LayoutRequest). submitter/views/checks.py:142-150 _fix_wrapped_heights (height-for-width lost three layouts deep). launcher/views/popup.py:920-933 sizeHint via totalHeightForWidth. All Qt layout workarounds. Proposed: extend FXResizedScrollArea with floor and cap, plus fxutils.fix_wrapped_heights. M
57. submitter/views/window.py:1023-1050 _align_labels: one label column across several QFormLayouts. fxutils. L
58. launcher/views/popup.py:203-236 themed thin overlay scrollbar for a card, transparent viewport. The app sheet names QScrollArea, so a widget flag cannot undo it. Proposed: fxstyle "thin" scrollbar role. M
59. launcher/views/seating.py (anchor_point, popup_corner, Seating with its rise-and-fade entrance) and tray.py:38-63 badged(icon). A tray-anchored popup panel is generic. It pairs with FXSystemTray, which has no panel. Proposed: FXSystemTray.popup_panel(widget), and fxicons.badged. M
60. hub/views/capture.py:53-120 _RegionGrabOverlay and grab_screen_region (screen region picker that hides the window, with the quitOnLastWindowClosed trap). Generic for review tools. M
61. launcher/instance.py SingleInstance: a QLocalServer lock that wakes the running copy. adapters/win32/taskbar.py:13 name_this_process (AppUserModelID). Proposed: fxutils.single_instance and fxutils.set_app_user_model_id. M
62. hub/views/comments.py:404-432 EmojiButton re-implements FXEmojiButton plus attach(). It only differs by being a round FXIconButton at a set size. Proposed: FXEmojiButton(round=True, size=...), then delete ls's. MentionBox (259-400, an @mention completer in a text edit) and ThreadLine (752-820) are generic comment-thread widgets. Check against fxgui's comment-widgets worktree before moving. M
63. publisher/views/drop_items.py:124+ DropItemsTree, a tree with an empty-state invitation and a drag-over outline. hub/views/composer.py:72 PreviewDrop, a dashed drop strip. Both overlap FXDropZone. Proposed: FXDropZone empty-state and drag outline on any item view. L
64. widgets/columns.py (Column tuple and header icons redrawn on theme). Generic but small. L
65. confirm_delete.py ConfirmDelete (type the name to confirm, never the default button). Generic dialog: FXFloatingDialog variant or fxwidgets. Line 66 hard-codes #d05353; it should use feedback error. L

## fxicons.py and icons/dcc

66. theme.py:24-30, 204-273 plus resources/icons/dcc/svg. fxgui's `dcc` library lacks after_effects, cinema4D, davinci, unreal, vlc and xstudio. blender, houdini and nuke exist in both, but the files differ. openrv and photoshop exist under other names (open_rv, adobe_photoshop). ls registers an ls_dcc library and a two-level fallback. Proposed: add the six marks to fxgui dcc, reconcile names, then delete ls_dcc and dcc_icon's fallback chain. The launcher.ico, launcher.svg and tray marks stay in ls (studio brand). Unsure: whether those brand SVGs are licensable in fxgui. H
67. widgets/task_icons.py:29-43 _known(): tests whether an icon name exists without building a QIcon, via try get_icon_path/FileNotFoundError. Proposed: fxicons.has_icon(name). L
68. widgets/docking.py:154: register a QIcon copy because the binding hands QtAds fxgui's cached icon to delete. It also argues for fxicons returning copies, or saying so. M

## Private import

69. workflows/views/panels.py:9-11 `from fxgui.fxwidgets._code_block import FXPygmentsHighlighter`. Export it. panels.py:222-231 also sets the mono family by stylesheet, because "any sheet beats a font set in code". Proposed: fxstyle.apply_role_font(widget, "mono"). H

## Stale or nothing to move (for completeness)

- theme.py:47 says AppWindow re-sets the icon "since its base stamps its own". fxgui already takes a QIcon (_set_window_icon), and window.py:248 passes one. The comment is stale.
- launcher/views/toggle_row.py:29 (PySide `clicked` with no argument) and tree_rows.py:11 (stubs) are local Qt facts, nothing for fxgui.
- widgets/graph/* is NodeGraphQt-bound and stays in ls, except items 5 and 8 and search_stylesheet (view.py:119), which could become an fxstyle menu sheet. L
- ask.py, pickers.py, action_menu (bar item 47), rows.row_pane/RowPane, and all app views are pipeline-specific.

## Top 10 by value

40 password Enter, 31 Windows 11 row pill, 11 status bar items/tint, 21 QtAds module, 2 colour overlay, 1 palette, 45 wrapper rehome, 46 keyboard tree/split button/popup_menu, 37-39 breadcrumb, 7 themed_sheet.

## Blind spots

- I read every file in widgets/, window.py, theme.py and views/breadcrumb.py in full. I read tree.py, record_table, the launcher views, hub comments and the submitter only around their fxgui hits. There may be small Qt helpers in hub/views/detail.py (1250 lines) and project_settings/views/config_page.py that I did not open.
- I did not check fxgui's comment-widgets, at-* or audit-fixes worktrees. Some items above may already be in flight there.
- Several items are "generic" only by my judgment, not tested against a second consumer. The rule in item 3 is a design call for the owner.

## Addendum: branch qtads-everywhere (worktree .claude/worktrees/panes-ux, HEAD b027e360)

That tree is the latest version. Paths below are python/ls_pipeline/apps/ there; tests are tests/apps/ there unless named otherwise. Every item the design session named is confirmed generic.

What changed against main, for this inventory:
- Every window now docks with QtAds. window.py:273 always builds docking.manager(); the Qt-dock fallback is gone. So items 19, 20 and 21 are no longer "launcher apps only", and item 21 goes to H: QtAds becomes an optional extra in fxgui.
- Item 3: layout.titled_block is deleted.
- Item 24/25: widgets/banner.py adds _home(), which walks up to the window with dock_manager so a floating pane's banner lands in its app window. The banner is now parented to the dock manager, with margin=GAP and raise_(). This is generic for QtAds floating windows, so fold it into fxdocking. FXNotificationBanner already takes `margin` (fxgui _notification_banner.py:143). Test: test_banner_place_qt.py::test_an_error_banner_leaves_the_row_and_corner_buttons_clear.

A1. widgets/later.py:12-21 later(ms, owner, call). A QTimer child of `owner`, single shot, deleteLater on timeout. It exists because Houdini 21's PySide6 6.5 lacks QTimer.singleShot(ms, context, call). Target: fxgui/_compat.py (fxgui runs in hython too). ls keeps: nothing; its callers import fxgui's. Tests: test_later_qt.py (test_the_call_runs_once, test_a_dead_owner_skips_the_call). test_single_shot.py (test_no_single_shot_takes_a_context_object) is a source scan over ls; fxgui needs its own copy over fxgui. H

A2. widgets/keys.py:43-47 scroll_by_pixel. It is called on every ls item view: keys.py, palette.py, pickers, drop_items, queue, targets, changes. Target: FXApplication or FXProxyStyle polish sets ScrollPerPixel on every QAbstractItemView, so no call site is needed. fxgui 1c35c5b4 covers only its own views. ls keeps: nothing; delete the calls. Tests: test_smooth_scroll_qt.py (test_every_item_view_scrolls_by_the_pixel, test_views_built_after_the_window_scroll_by_the_pixel, test_one_wheel_notch_still_moves_about_three_rows; test_every_app_has_a_window_here stays in ls). fxgui's tests/test_smooth_scroll.py grows to "any view". H

A3. window.py:103-110 HOST_RESET, and window.py:829-843 changeEvent(ParentChange) plus setStyleSheet(). A Qt child inherits its parent's sheet, and Houdini 21's base.qss sets QToolButton width/height, QMenu separator and indicator margins, and a QMenuBar border and padding. fxgui's sheet leaves these rules open. While a host parents the window, the reset is prefixed to its sheet and re-applied on each ParentChange. Target: FXMainWindow does this itself when parented (with item 15), with the reset rules in fxgui's qss. ls keeps: nothing. Test: test_status_items_qt.py::test_a_host_s_sheet_stays_out_of_a_window_it_owns (line 614), and its helper at 595-605 that reads Houdini's own base.qss. H

A4. widgets/focus.py:62-79 step() / rehomed() (item 45), and window.py:607-638 AppWindow.focusNextPrevChild (item 19). On the branch the override always applies. It hands to super() when the start widget is hidden (a pane closing on the focus: a Python walk inside Qt's hide crashes) or when the walk comes back round. Target: rehome and step go to fxgui/_compat.py; focusNextPrevChild goes to the fxdocking window mixin (or FXMainWindow when docked). ls keeps: its tab-order declarations. Tests: test_focus_qt.py (test_a_step_leaves_no_wrapper_owned_by_a_widget_that_dies, test_a_bar_built_after_its_neighbour_still_takes_the_next_stop). test_pane_focus_hide_qt.py::test_a_pane_closed_on_the_focus_does_not_crash. H

A5. widgets/palette.py CommandPalette plus rank() (item 52), unchanged on the branch. Target: fxwidgets/_command_palette.py, FXCommandPalette(window, commands) with the Entry dataclass. ls keeps: the "Loading shots and tasks" string, and open_go_to's shot/task loader. Also AppWindow's palette rows (window.py _palette_rows, _run_from_palette), which read ls Actions. Tests that move: test_palette_qt.py test_matching_takes_every_word_in_order, test_word_starts_rank_before_inner_matches, test_typing_filters_and_enter_runs_the_first, test_arrow_keys_move_the_choice, test_a_disabled_command_shows_its_tip_and_does_not_run, test_escape_closes, test_a_click_outside_closes, test_a_row_with_no_tip_leaves_no_hint_line, test_a_command_s_tip_shows_under_the_list, test_the_selected_row_is_one_band_across_its_columns, test_a_leading_angle_switches_go_to_to_commands. The rest of test_palette_qt.py (Ctrl+P go-to, status items, embedded keys, publisher) stays in ls. M, raised to H since the session named it.

A6. widgets/status_items.py:56-143 StatusItem, and the left-items group (status_items.py:166-190): a transparent "status_items" widget added as a permanent widget with stretch, holding the items, then fxgui's icon and message labels, so no message hides them (item 11). Unchanged on the branch. Target: fxwidgets/_status_bar.py, FXStatusItem plus FXStatusBar.add_item(item, side="left"|"right"), ground()/tinted(), and tip routing (window.py:454-458 QStatusTipEvent). ls keeps: StatusBar's item set, _TRACKER, show_artist/show_tracker/show_log_counts, and the clicks wired in window.py _build_status_items. Tests that move: test_status_items_qt.py test_every_item_reads_on_every_theme, test_a_message_keeps_a_gap_from_the_window_s_left_edge, test_a_message_keeps_the_items_shown_and_readable, test_a_theme_switch_mid_message_keeps_the_items_readable, test_on_a_tint_the_log_icons_wear_the_text_s_ink, test_an_item_takes_the_suite_s_radius_and_icon_size, test_a_hover_tip_shows_after_the_items_not_over_them, test_a_clickable_item_lights_under_the_mouse. The tracker, artist, log-count and click tests stay in ls. H

A7. window.py:161-188 _CommandRow (item 17), and window.py:328-351 plus 443-452: the corner-tools toolbar and the eventFilter that hides and shows title_corner on its LayoutRequest (item 16). Target: FXMainWindow (toolbar="row" and add_corner_widget re-placing itself). ls keeps: what goes on the row (choosers, breadcrumb, Refresh). Tests: test_command_row_qt.py test_the_row_is_the_only_toolbar_and_holds_the_apps_controls_in_order, test_the_row_lines_up_with_the_panes_one_gap_above_them, test_the_rows_blank_sits_on_the_frame, test_a_window_with_nothing_to_choose_puts_its_tools_in_the_corner. The overflow check is at line 307, inside test_the_workflows_row_buttons_still_run; that assertion moves as its own test. test_framed_panes_qt.py corner tests move too. H

A8. widgets/docking.py (item 21), branch version. It uses later() instead of QTimer.singleShot (lines 23, 207-230), and its module docstring is now "every window". Pieces and lines on the branch:
    - manager: 258-281
    - _SHEET: 40-72, with _restyle at 75
    - GAP sweep: _sweep 197-205, _keep_gaps 207-225, _follow 227
    - _floor: 97-117, and _Floor at 119
    - MinimumSizeHintFromContent: 376-377 in dock()
    - iconProvider copy trap: _register_icons 149-155
    - restorable: 293-311
    - also _fit_bar 82, _recross 166, _reicon 187, _configure 233, central 283, settle/_split/_weight 314-354

    Target: fxgui/fxdocking.py behind extras ["docking"]. GAP becomes a parameter. ls keeps: the pane list and names, the ls_size weights, and prefs storage. Tests that move:
    - test_docking_qt.py: test_a_pane_offers_no_auto_hide, test_a_layout_saved_with_a_tucked_pane_opens_it_docked, test_the_current_tab_underline_follows_a_theme_change, test_a_pane_tabbed_with_another_shares_its_tab_bar, test_a_panes_tip_lands_on_its_tab, test_tabbing_with_a_pane_that_is_not_there_says_which, test_a_pane_the_saved_layout_never_named_opens_anyway, test_showing_a_floating_pane_raises_its_window, test_a_floating_panes_tabs_keep_their_docked_height, test_reset_layout_brings_a_closed_pane_back.
    - test_framed_panes_qt.py: test_the_tab_bar_is_inset_off_the_round_corners, test_one_gap_across_down_and_at_the_edges, test_a_moved_pane_keeps_the_gap, test_a_floated_and_redocked_pane_keeps_the_gap, test_a_pane_reopened_from_the_window_menu_keeps_the_gap, test_a_restored_layout_keeps_the_gap_and_the_mark, test_a_tabbed_pane_grows_to_the_tab_in_front, test_no_pane_of_a_dcc_app_is_squeezed_under_its_content, test_a_theme_change_after_a_layout_restore_raises_nothing, test_a_theme_change_after_the_window_closed_raises_nothing, test_corners_and_the_mark_hold_at_150_percent, test_a_pane_floats_above_the_window_it_belongs_to.

    Per-app tests stay in ls: test_every_app_that_keeps_prefs_keeps_a_layout, test_the_hub_keeps_one_gap_and_round_corners, test_workflows_keeps_one_gap_and_round_corners, test_a_dcc_app_keeps_one_gap_and_round_corners, test_a_dcc_apps_blocks_are_panes_titled_by_their_tabs. Unsure: no test by name guards the iconProvider copy or restorable alone. They are exercised only through the layout and theme tests, so fxgui needs a direct test for each. H

Addendum blind spots:
- I mapped tests by grepping names and imports, not by reading each test. A test that moves may lean on ls fixtures in tests/apps/conftest.py (AppWindow configs), which must be rebuilt on a bare FXMainWindow in fxgui.
- window.py on the branch also changed file_save, scene_manager and submitter windows (241 lines in submitter/views/window.py). I did not re-read those for new generic helpers.
