# The control language in widget code

Branch `lang-widgets`, from `audit-fixes` at `d59b1ce7`. Spec:
plans/2026-10-01-vscode-language.md, with the owner ruling (a selected row
keeps the accent in every view, so change 5 is dropped).

## What changed

| Widget | Before | After | Test that pins it |
|--------|--------|-------|-------------------|
| `FXThumbnailDelegate` rows | hover filled `@accent_secondary`, text `@text_on_accent_secondary`, icon in Active mode | hover `@state_hover`, the row's own text ink, icon in Normal mode; selected stays `@accent_primary`, focused view or not | `test_item_views.py`: `test_a_hovered_row_is_the_neutral_hover_fill_not_an_accent`, `test_a_hovered_row_keeps_its_text_ink`, `test_a_selected_row_keeps_the_accent_in_a_view_without_focus` |
| `FXItemDelegate` | switched an icon to Active on hover | deleted: a hover no longer changes an icon, so it did nothing `QStyledItemDelegate` does not | gallery test (section renamed `QListWidget`); `FXDropZone` drops its use |
| `FXBreadcrumb` segment | `@accent_primary` tint at 80/255 | `@text` tint at 36/255, a neutral tint | `test_breadcrumb_hover.py::test_the_tint_is_a_neutral_theme_ink_rather_than_a_hex` |
| `FXToggleSwitch` off, hovered | edge `@accent_primary`, the same as focus | track `@state_hover`, edge unchanged; focus alone recolours the edge | `test_toggle_switch.py::test_a_hovered_switch_is_not_dressed_as_focused` |
| `FXRatingWidget` hover preview | stars in `@accent_secondary` | stars in `@text`; the set value stays `@accent_primary` | `test_paint_widgets_theme.py::test_a_rating_s_hover_preview_is_drawn_in_text_not_an_accent` |
| `FXNotificationBanner` actions | primary hover `@accent_secondary`; others hover `@surface_alt`; no focus rule | primary uses `@primary_button` / `_hover` / `_pressed` and a `@text` focus edge, as `FXPrimaryButton`; others and the close button hover `@state_hover`, focus edge `@accent_primary` | `test_widget_language.py::test_a_hover_rule_names_no_accent` |
| `FXEmojiPicker` | hover and focus one rule (accent edge); frame `@surface_sunken` at `@button_radius` | hover fills `@state_hover` with a transparent edge (beats the base `QToolButton:hover` edge); focus alone draws the accent edge; frame `@surface` at `@card_radius` | `test_emoji_picker.py::test_a_hovered_cell_is_filled_but_not_edged_like_focus`, `test_widget_language.py::test_a_popup_is_a_surface_card_at_the_card_radius` |
| `FXCommandPalette` frame | `@button_radius` | `@card_radius`, the popup tier | same popup test; `test_command_palette.py::test_the_palette_wears_a_popup_frame` checks the 8 px corner |
| `FXStatusBar` busy line | an `@accent_secondary` to `@accent_primary` gradient | one flat `@accent_primary` run, as a progress chunk | `test_status_bar_busy.py::test_the_busy_line_is_one_flat_accent_like_a_progress_chunk` |
| QtAds title-bar buttons (`fxdocking.py`) | Active icon ink `@icon_on_accent_secondary` | Active ink `@icon`, since the hover fill is neutral | `test_fxdocking.py::test_a_hovered_pane_button_keeps_its_icon_ink` |
| `FXCollapsibleWidget` header | an open header filled `@state_hover` for good, so it read as hovered; title always 600 | a section header: hover fills `@state_hover` at `@button_radius`, the open one has a 600 title (closed: body weight) and the `expand_more` chevron | `test_collapsible_header.py::test_a_header_is_a_section_header_hover_fills_open_weighs` |
| Type in widget code | `bold` (700) in four places, the badge 3 px under the body, the description 1 pt under, `9pt` in `FXCodeBlock`, `14px` in `FXLoadingOverlay` | two weights, the body's and 600; metadata (description) 1 px under the body, a badge 2 px under at 600 (11 and 10 px at the 12 px body); no hand-set text size | `test_item_views.py::test_the_delegate_s_type_is_the_body_weight_and_600_only`, `test_widget_language.py::test_no_fragment_sets_a_third_weight_or_a_point_size` |
| Spacing in widget code | 5, 10, 20, 50 px | 6, 8, 16, 40 px: every literal spacing or margin is on the ramp 0, 2, 4, 6, 8, 12, 16, 24, 32, 40 (32 and 40 for a window-sized panel, the splash) | `test_widget_language.py::test_a_widget_lays_itself_out_on_the_spacing_ramp` |
| Gallery | | a plain `QProgressBar` beside `FXProgressCard`, so the base sheet's bar shows | `test_gallery.py` |

`test_widget_language.py` also scans every registered widget fragment: no
`:hover` rule outside a `QMenu` names `@accent_primary` or
`@accent_secondary`. It passes on this branch.

Already in the language, unchanged: `FXStatusItem` (hover `@state_hover`),
`FXRangeSlider` (hover thickens the edge, focus turns it `@text`, as
`QSlider`), `FXIconButton`, `FXJoinedGroup`, `FXDropZone`, the keycaps of
`apply_tip`.

## Not done, and why

- `FXProgressCard` keeps its own `QProgressBar` rules (6 px, `@surface_sunken`
  track). Spec 5.9 moves the bar to a flat 4 px pill in the base sheet, which
  is lang-sheet's file. Once that lands, delete the card's two
  `QProgressBar` rules and `setFixedHeight(6)` in `_progress_card.py`, so
  the card takes the one bar look. I asked lang-sheet for the final rule
  and had no answer when this report was written.
- The meta (11 px) and badge (10 px / 600) ranks are local to the delegate
  (`_delegates._smaller`). If lang-sheet ships named roles or spacing
  constants in `fxstyle`, the delegate, the ramp test and the layouts should
  read them instead. I asked; no answer yet.
- `FXStatusBar`'s resting accent line along the top (an `@accent_primary`
  to `@accent_secondary` gradient on an unframed bar) is decoration, not a
  progress bar or a hover, and the spec does not name it. Left as is; say if
  it should go flat too.
- The `FXNotificationBanner` hover could not be seen in an offscreen grab
  (the banner's fade effect), before or after. The rule is pinned by the
  scan test only.

## For lang-sheet (their files)

1. Completer popups (`FXMentionEdit`'s name list, any `QCompleter`):
   `fxstyle._dress_popup` themes them, but no rule makes them a popup. They
   should be `@border` at `@card_radius`, rows as a combo list (the pointer
   moves the current row, so hover = selected = `@accent_primary`).
2. `docs/how-to/theming.md`: "Cards in item views" still says a hovered
   row is `@accent_secondary` with `@text_on_accent_secondary`; it is now
   `@state_hover` with the row's own ink. The sliders and switches table:
   `FXToggleSwitch` off, hover is now fill `@state_hover`, edge unchanged.
   "Popups, cards and shadows": the popup frame is `@card_radius`.
3. `tests/test_toolbutton_hover.py` pins a hovered `QToolButton` on
   `@accent_secondary` (spec 5.2).

## For the lead (no owner)

`fxicons._DEFAULT_INKS["active"]` is `icon_on_accent_secondary`, and
`fxicons._icon_for_widget` gives the normal ink to push buttons only. Once a
hovered `QToolButton` is `@state_hover` (spec 5.2), every tool button icon
set through `fxicons.set_icon` hovers in the on-accent ink on a grey fill.
A menu row is the reverse: it hovers on `@accent_primary`, but its icon's
Active ink is the secondary one. Proposed: `_icon_for_widget` gives every
`QAbstractButton` its normal ink for Active, and the Active default becomes
`icon_on_accent_primary`. Sent to the lead; not done here.

## ls-pipeline call sites

None. `FXItemDelegate` is used nowhere in ls-pipeline's source (only in its
installed copy of fxgui under `.venv`).

## Renders

Offscreen, `QT_QPA_FONTDIR=C:/Windows/Fonts`, dark and light, before
(`d59b1ce7`) and after. Script: `lang_widgets/render.py`. Root:
`C:/Users/ValentinBeaumont/AppData/Local/Temp/claude/C--Users-ValentinBeaumont-Documents-GitHub-ls-pipeline/ce4aec2c-f8ce-429e-b78b-baa571edbe90/scratchpad/lang_widgets/`

- `before/` and `after/`, each with `<theme>_<n>_<tab>.png` (every gallery
  tab's whole page), `<theme>_states.png` (forced states: delegate rows at
  rest, hovered, selected, selected and hovered; a hovered breadcrumb
  segment; a hovered off switch; a rating preview; the busy line; a hovered
  emoji cell; a banner with actions; the command palette) and
  `<theme>_splash.png`.

What they show: hovered rows, segments, switch and emoji cell are grey, not
blue; the hovered emoji cell no longer carries the focus edge; the rating
preview is the text ink; the busy line is flat. Gallery pages differ only
in the type weight and spacing, by design. The base sheet's own hovers
(push and tool buttons, plain lists) are lang-sheet's and still show the
old look on this branch.

## Test runs

- Covering files while working, main venv (PySide6 6.11).
- Full suite once at the end (main venv): 1 failed, 2336 passed, 6
  skipped in 209 s. The failure is
  `test_status_items.py::test_a_clickable_item_lights_under_the_mouse`, a
  `waitUntil` timing out at 1 s. `FXStatusItem` is unchanged on this
  branch, and the file passes three runs out of three on its own: a hover
  timing test under load, the kind group h already lists.
- `ruff check --select F,B,BLE .` (the CI gate): passes.
- Covering files on PySide6 6.5.3 (`scratchpad/v653`, `PYTHONPATH` on the
  worktree): 564 passed, 1 skipped (`test_fxdocking.py`: no QtAds in that
  venv). One earlier run of the same set failed
  `test_log_widget_api.py::test_append_many_writes_every_line_in_order_after_what_is_queued`
  with a "C++ object already deleted" in `fxstyle._mark`; it passed in two
  isolated runs and the rerun of the set. Order-dependent and not touched
  here; one for group h.
