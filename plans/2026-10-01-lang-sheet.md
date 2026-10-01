# lang-sheet: the control language in the sheet and theme, and fix group (a)

Branch `lang-sheet` (from audit-fixes; audit-fixes 491f867c / c6a6d360 merged
in at 06d3d558). Files: `fxgui/qss/style.qss`, `fxgui/fxstyle.py`,
`fxgui/style.yaml`, `tests/conftest.py`, the QSS block and `_inset` in
`fxgui/fxdocking.py`, `fxgui/fxutils.py` (`add_shadow` only, lead's yes),
`docs/how-to/theming.md`, `docs/how-to/styling.md`, and the tests that
pinned what changed.

## Commits

| Commit | What |
|---|---|
| c010f1e3 | fxstyle has one name per job; derived text, pressed and on-accent inks; sheet before palette for a widget root; 6.5 spin padding; conftest resets |
| 76a2a460 | The base sheet's control language (hover, focus, menus, headers, splitters, progress, panes, tab scroll gap) |
| 68593c4e | Shadow reads `@shadow` / `@shadow_blur` when it draws; `add_shadows` gone |
| c5fd28bf | Dock tab inset equals a tab bar's; `FXProxyStyle` draws no focus rectangle |
| 481c5137 | A completer's list is a popup card with menu rows |
| d2a0ee6a | A tooltip keeps 4 px (see deviations) |
| 06d3d558 | Merge of audit-fixes (test_fxicons.py conflict: took lang-widgets' version; this commit also drops one dead `border-color` on `::item:selected:active`) |
| e5b71bec | theming.md and styling.md |
| 1c9e727b | Tests: split hover, progress pill radius, key leak between tests, 6.5 signal disconnects |
| 9c0cb0f8 | Contrast tests over every theme |

## Spec items (stylesheet and theme)

| Item | Done | How |
|---|---|---|
| Hover never accent | yes | `QWidget:item:hover`, list/tree rows, tool buttons: `@state_hover`, ink unchanged |
| Buttons hover by fill only | yes | `QPushButton:hover`, split button and its `::menu-button` keep their edge |
| Inputs and views accent only on keyboard focus | yes | combo, spin, line edit lift to `@border_light` on hover; text edits and views no hover rule |
| Disabled text | yes | push button and split button `@text_disabled` |
| Tool buttons | yes | hover `@state_hover`, pressed `@state_pressed` no edge, checked `@state_pressed` + accent edge; margin 2, padding 2 (22 px box incl. the reserved edge) |
| Menus and popups | yes | `QMenu` `@card_radius`, rows `padding: 4px 24px` (24 px), `border: none`, separator `margin: 4px 0px` full width; completer list card (new `fxstyle.POPUP_PROPERTY` set in `_dress_popup`) |
| Menu bar | yes | padding `4px 8px`; open item `@state_pressed` + `@text` |
| Flat headers | yes | transparent, `@text_muted`, one `@border` rule (vertical header: rule on the right); dock block's two header rules deleted |
| Splitters | yes | nothing at rest, `@accent_primary` on hover; `QMainWindow::separator` same; framed splitter keeps its dots |
| Progress bar | yes | 4 px pill, `@control_edge` track, `@accent_primary` chunk, text off. `QProgressBar:horizontal` does not reach the widget's size, so the size rules select `[orientation="1"]` / `[orientation="2"]` |
| Tab-widget pane, QToolBox, QDockWidget title | yes | pane card `@surface` + `@pane_border`; QToolBox 28 px flat header with chevron (`image-position: left`), hover fill, open at 600; QDockWidget title flat `@surface` |
| Type and spacing | partly | no new rank or spacing constants (see not done) |
| Contrast floor hover/pressed | yes | `state_pressed` stepped away from `surface` to 1.2:1 off `state_hover` (`STATE_MIN_CONTRAST`); moves dark, nord, github_light |
| Tabs | unchanged | option B kept; `@tab_muted` replaced by `@text_muted`, which now meets 4.5:1 itself |
| Open tab item: text behind scroll arrows | yes | scroll buttons opaque with a `border-left: 4px solid @surface` gap. Test `test_no_tab_text_shows_inside_the_scroll_buttons` failed before the rule (the gap held tab pixels), passes after |
| Owner bug: dock tabs start too far right | yes | `_inset` now insets the right side only (buttons); first pill is 2 px inside the pane's border, as a QTabBar's is inside its bar (was 6). Test `test_a_dock_tab_starts_as_far_in_as_a_tab_bar_tab` (gallery Docking page) passes on 6.11.2 and 6.5.3 |

## Group (a)

| Item | Done | How |
|---|---|---|
| Shadow tokens that follow a switch | yes | `shadow` (#AARRGGBB; dark #50000000, light #28000000) and `shadow_blur` (20) in style.yaml; `fxutils._ThemedShadow` reads them in `draw()`, only setting on change; still parented to its widget. Test switches theme and checks colour and blur with no call |
| Sheet before palette in `_apply_to_root` | yes, with a split | A widget root: sheet, then palette and font. Test with an FXKeycap child failed on the old order (dark #302f2f after a switch to light), passes. The QApplication root must keep palette first: sheet-first broke `test_a_switch_in_an_fxapplication_equals_a_fresh_build` on every page |
| 6.5.3 item BackgroundRole blend | app: yes; host: no | Cause measured: Fusion's `PE_FrameFocusRect` on the focused current cell, which 6.5 draws whatever the sheet's `outline` says. `FXProxyStyle.drawPrimitive` skips it, so app roots (FXApplication) are fixed. Host roots are not: a per-view proxy style fixed the tint but changed branch chevrons and combo row metrics (13 chrome tests), so I removed it. Still failing on 6.5.3: `test_base_sheet::test_an_item_background_shows[host_root]`, `test_host_sheet::test_a_table_cell_background_shows_under_a_host_s_sheet` (3). Whether Houdini 21's own style draws the same tint is not measured |
| 6.5.3 spin box 23 px | yes | 6.5 sizes a spin box 3 px shorter for the same padding; `@spin_padding` is `4px 0px` below Qt 6.6, `3px 0px 2px 0px` from it. Bound unproven between 6.5.3 and 6.11.2 (ponytail comment) |
| 6.5.3 test_host_sheet teardown errors | yes | cause: tests registered a child of a registered host with qtbot; pytest-qt deletes the parent first and closing the child raised. `_shown` registers only parentless windows. 0 errors now |
| Theme text contrast floor | yes | `_readable_states` steps `text` and `text_muted` toward black or white until 4.5:1 on surface, sunken, alt, well, frame, tooltip, state_hover (text also on state_pressed). solarized_light's `state_pressed` was a border colour (#93a1a1), now #ddd6c1. Test over every theme |
| slider_thumb tokens | deleted | also `separator` (no reader after the splitter change) |
| conftest | yes | flushes `DeferredDelete`, resets `_colors`, `_color_file`, and the focus watcher's last-input flag (a key in one test made the next one's focus visible); `_styled_widgets` is gone with set_widget_style; the two copied fixtures deleted |

## Audit findings in fxstyle.py and style.qss

| Finding | Done |
|---|---|
| D1 one colour getter | `colors()` only; deleted get_theme_colors, get_accent_colors, get_icon_color, get_icon_on_accent_*. Kept `get_feedback_colors()` as the dict of levels (examples.py and _status_dot.py list the levels) |
| D2 feedback three times | yaml top-level block and `_DEFAULT_FEEDBACK` deleted; theme, file's dark, built-in |
| D3 replace_colors | deleted |
| D4 three sheet builders | load_stylesheet deleted, build_stylesheet private (`_build_stylesheet`) |
| D5 two signal names | `theme_changed` on a private `_signals`; theme_manager, FXThemeManager, notify_theme_changed gone |
| D6 radius tokens | `@radius` gone; `@button_radius`, `@card_radius` only. 2 px radii left are pills at half their thickness (progress, groove, scroll thumb), decided not a token |
| D7 light rule twice | `_is_light` used by `is_light_theme` and `~icons` |
| D8 three ink pickers | get_contrast_text_color and `_away_from` deleted; `_pole_from` and `readable_ink` |
| D9 / D10 fonts | one `_fonts_block` merge, `_font_families` list, `_resolve_font_stack` joins it, one `_check_weight` |
| D11 two cache invalidations | kept the explicit one, dropped the key: `id(dict)` can be reused after a free, and a font registration changes tokens without changing the dict. `register_fonts` now invalidates |
| D12 set_widget_style mechanism | deleted (no caller left), test file deleted |
| S1 / S2 dead code and wrong text | all six fixed; depth_shade reads `colors()` |
| Q1 host `outline` | deleted |
| Q2 duplicate selectors | menu-button hover merged; the two QGroupBox::indicator rules are a shared list plus one, kept |
| Q3 commented declarations | deleted |
| Q4 history comments | cut; also the repeated `outline: none` lines (7) |
| Missing comma | `QCheckBox::indicator:indeterminate:pressed` lacked one, making a descendant selector; fixed |
| Top bug 24 | conftest resets the colour file |

## Not done, and why

- `@hover`, `@row_height`, the "meta" / "badge" ranks, spacing constants: each is a second name for one value or has no caller. Told lang-widgets.
- Tooltip at `@card_radius` (spec 5.10): kept at 4 px. A tooltip is `Qt.ToolTip`, not `Qt.Popup`, so `round_window_corners` never runs on it, and an 8 px sheet radius on an opaque window shows square corners. Microsoft's geometry page also gives tooltips 4 px.
- Host-root focus rectangle on 6.5.3 (above).
- Fold of the test_fxstyle* files (audit tests D1): group h.

## Windows 11 popup corners

Not verified on screen: renders are offscreen, and showing a popup on the
owner's desktop was not done. From Microsoft's docs: `DWMWCP_ROUND` (2) is
"round if appropriate" and `ROUNDSMALL` (3) the small radius; Windows 11
flyouts and menus are 8 px, in-page controls and tooltips 4 px
(learn.microsoft.com, "Geometry in Windows" and
"DWM_WINDOW_CORNER_PREFERENCE"). So the 8 px sheet radius and the DWM clip
now agree, by the docs.

## Contrast results (yaml value -> derived)

| Theme | text | text_muted | state_pressed |
|---|---|---|---|
| dark | #bbbbbb -> #c0c0c0 | #9a9a9a -> #acacac | #4a4949 -> #4f4e4e |
| light | same | #616161 -> #5c5c5c | same |
| one_dark_pro | #abb2bf -> #c0c5cf | #828997 -> #a8acb6 | same |
| github_light | same | #656d76 -> #626a73 | #eaeef2 -> #d8dce0 |
| catppuccin_latte | same | #6c6f85 -> #545667 | same |
| nord | same | same | #434c5e -> #485062 |
| solarized_light | #657b83 -> #4c5c62 | #839496 -> #5c6869 | #ddd6c1 -> #d7d1bc |

Blind spot: in catppuccin_latte (1.10:1) and solarized_light (1.21:1)
muted and normal text now look almost the same. The 4.5:1 rule and a
visible muted step cannot both hold on those themes' own colours; a
theme author fixes it by darkening `text`.

## Tests

- PySide6 6.11.2, full suite: 2351 passed, 6 skipped in fixed order and on
  `--randomly-seed=385779718`. One earlier random run had 11 order-dependent
  `test_frame_controls::test_a_hovered_flat_button_fills` failures (pass
  alone and in fixed order), the hover flake group h already lists.
- PySide6 6.5.3 (scratchpad `v653`, QtAds via `ads65shim`), covering files
  (fxstyle*, theme*, sheet, chrome, focus, frame, control, host, menu,
  tool, hover, overlay, splash, tray, fxicons, fxutils, shadow, split,
  radius, floating, fxdocking): all pass except the 4 host-root
  BackgroundRole cases above, `test_fxdocking_optional` (the shim imports
  QtAds at start), and 4 fxdocking teardown errors that also occur without
  this branch's last commits (tests delete a window qtbot registered).
- `ruff check --select F,B,BLE .`: clean. `zensical build`: not run, zensical is not installed in the venv.

## Renders (dark and light, before and after)

Folder: `C:/Users/ValentinBeaumont/AppData/Local/Temp/claude/C--Users-ValentinBeaumont-Documents-GitHub-ls-pipeline/ce4aec2c-f8ce-429e-b78b-baa571edbe90/scratchpad/langsheet/`

- `before/` and `after/`: `{dark,light}_{0..7}_<page>.png` (every gallery page), `{dark,light}_sampler_{button,row,edit}_hover.png` (hover, focus, disabled, checked tool button, list, flat table header, QToolBox, progress pill, tab-widget pane, crowded tab bar, old QDockWidget), `{dark,light}_menu.png`.
- Seen: hovered button is a fill with its own edge beside the focused one; hovered row grey next to the blue selection; flat headers; menu with full-width separators and 8 px box; the Docking page's first pane tab now lines up with the gallery's own first tab.
- Script: `render.py` in the same folder.

## ls-pipeline call sites (at c28f18b4)

- `fxstyle.get_theme_colors()` : 79 calls in 30 files under `python/ls_pipeline/apps/` (graph/canvas.py 14, graph/items.py 13, hub/views/comments.py, widgets/row_colors.py, ...). `get_theme_colors()["x"]` -> `fxstyle.colors().x`; a name in a variable -> `getattr(fxstyle.colors(), name)`.
- `hub/views/comments.py:227` `get_contrast_text_color(color)` -> `fxstyle.readable_ink(color)`.
- `submitter/views/checks.py:59` `get_accent_colors()["primary"]` -> `fxstyle.colors().accent_primary`.
- `widgets/docking.py:79-81` `.replace("@radius", ...)` and `replace_colors(sheet, get_theme_colors())` -> `fxstyle.resolve(sheet)` with `@button_radius` in the sheet.
- `resources/lotchi_colors.yaml`: drop `separator`, `slider_thumb`, `slider_thumb_hover` (dead), and add `shadow` / `shadow_blur` only if Lotchi wants its own.
- Lotchi's `text` / `text_muted` may be derived darker or lighter on its surfaces; nothing to change, but a pixel test there that compares to the yaml value would move.
- `fxutils.add_shadow(widget, blur=..., alpha=...)` no longer takes blur or alpha: none in ls.
