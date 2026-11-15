# Plan 003: Buttons, fields, tabs, menus and tooltips take ls-ui's layout

> **Executor instructions**: read this plan fully, then the repo's `CLAUDE.md`. Follow the steps in
> order; run each verification. On a STOP condition, stop and report. The lead maintains
> `plans/2026-11-15-look/README.md`.
>
> **Drift check**: plan 001 (control height 32, gap 6, indicators 16, weights 500) has landed on your
> base. Re-locate every excerpt below in the live code; STOP only if what you must change is gone or
> different in substance. Plans 002 and 004 run in parallel and also edit `style.qss`: touch only the
> rule blocks this plan names.

## Status
- Priority: P1 · Effort: M · Risk: MED · Depends on: 001 · Category: look · Planned at: `7a4eff64`, 2026-11-15

## Why this matters
After plan 001 the controls have the reference height; this plan gives the families a Pascal user
touches most the reference's inner layout: tool buttons as 28 px ghost squares, tabs with 4/8 padding
in 12 px medium text, menus with 32 px items and 6/8 padding, tooltips in 12 px text with a quicker
re-show.

## Current state (line numbers from `7a4eff64`; they moved with plan 001)
- `fxgui/qss/style.qss` near 1291-1298: `QToolButton { margin: 2px; padding: 2px; border: 1px solid transparent; border-radius: @button_radius }` ("a 22 px box around a 16 px icon").
- `style.qss` near 882-937: `QTabBar::tab { margin: 4px 2px; padding: 3px 10px; ... }`, first tab
  margin-left 4 px; selected = a filled pill; `fxstyle.py` `TAB_PADDING = 10` (near 272), `@tab_padding`,
  `_CLOSE_INSET` (near 275). `tests/test_chrome.py` near 650 pins tab width = text + 2·(10+1+2).
- `style.qss` near 231-311: `QMenu { padding: 4px; border-radius: @card_radius }`,
  `QMenu::item { padding: 8px 24px; border-radius: @button_radius }`, icon margins left 12 / right 13,
  separator `margin: 4px 0`, check indicator 18 px shifted 12, submenu arrow 16 + 5 margin.
  Menu badge (fxstyle near 2239-2306): `_MENU_ITEM_PADDING = 24`.
- `style.qss` near 30-37: `QToolTip { padding: 4px 10px; border-radius: @small_radius; }` (no font size).
- `fxgui/fxwidgets/_tips.py`: title `<b>`; `_CODE_COLUMNS = 64` with a comment "about the 440 px a
  tooltip takes at most"; `_LINE_GAP 3`, `_BLOCK_GAP 8`, `_FACT_GAP 14`, code 11 px.
- Combo popup rows (qss near 1153-1176): padding 8 px top/bottom, ≤ 32 px rows.

## Targets
| What | Today | Target | Reference |
|---|---|---|---|
| QToolButton (plain, icon) box | 22 px (margin 2, padding 2) | **28 × 28**: margin 0, padding 5, 1 px reserved edge, 16 px icon; spacing between tool buttons comes from layouts (gap 6 after plan 001) and `QToolBar { spacing: 6px }` | ls-ui toolbar/panel icon buttons: ghost sm 28 × 28 |
| Tab padding | 3 / 10 | **4 / 8** (`TAB_PADDING` 8) | ls-ui tab trigger `px-2 py-1` |
| Tab text | body 13 | **12 px, weight 500** | ls-ui tabs 12 px medium |
| Tab gap / inset | margin 4 v, 2 h | keep 4 px top/bottom inset and **4 px between tabs** (margin 0 2px stays = 4) | ls-ui 4 px gap, chip inset 4 px |
| Tab radius | 9 | 9 (keep) | ls-ui 9 |
| Menu item padding | 8 / 24 | **6 / 8** plus the icon column Qt reserves (icon 16, 8 px gap to the text) | ls-ui menu item `py-1.5 px-2`, gap 8 |
| Menu item height | ~32 | **32** at 13 px | ls-ui 31.5 → 32 |
| Menu item highlight | radius 9, flush | radius 9, **1 px inset top and bottom** (`margin: 1px 0`) | ls-ui `before:inset-px` |
| Menu separator | 1 px, margin 4 px 0 | 1 px, **margin 4 px, spanning the popup's 4 px inset** (negative side margins if Qt allows, else keep) | ls-ui `-mx-1 my-1 h-px` |
| Menu badge item padding | 24 | follows the new item padding | |
| Combo popup rows | padding 8 v | **6 / 8**, 32 px rows | ls-ui select list = menu items |
| Tooltip text | 13 | **12 px** (`QToolTip { font-size: @font_size_small }`) | ls-ui tooltip 12 px |
| Tooltip title in `tip()` | `<b>` (bold) | **weight 500** (a span with `font-weight:500`) | ls-ui weights ≤ 500 |
| Tooltip code rows | 64 columns (≈440 px) | **48 columns** (≈320 px at the 11 px mono) | ls-ui tooltip max width 320 px |
| Tooltip re-show window | Qt 2000 ms (`SH_ToolTip_FallAsleepDelay`) | **300 ms** via `FXProxyStyle.styleHint` | ls-ui: instant while moving between targets within 300 ms. This is a timing of the tooltip, not a new interaction; say so in the commit |
| Tooltip open delay | Qt 700 ms | keep (ls-ui is 700 ms) | |

Keep: FXIconButton round (its own design), FXPrimaryButton/flat/overlay fills, the focus look,
keycaps (11 px, radius 6), `tip()`'s public signature and every caller string escaped.

## Commands
Same as plan 001 (worktree root; `-n 8`; ruff `--select F,B,BLE`; pictures with
`...\scratchpad\look\render_families.py <out> --themes dark light`).

## Scope
In: the QToolButton, QToolBar spacing, QTabBar, QMenu, combo popup row and QToolTip blocks of
`style.qss`; `TAB_PADDING`, `_CLOSE_INSET`, the menu-badge padding and `styleHint` in `fxstyle.py`;
`_tips.py` (title weight, `_CODE_COLUMNS` and its comment); the tests that pin them. Out: colours;
header/rows (plan 002); dialogs/panels/chips/switch (plan 004); motion (plan 005).

## Steps
1. Probe: tool button size, a tab's padding and font, a menu item's height, the tooltip font, the
   fall-asleep delay. **Verify**: before values.
2. Tool buttons and toolbar spacing. **Verify**: 28 × 28; gallery `page_buttons` nothing clipped.
3. Tabs (padding, 12 px 500, `TAB_PADDING`, close inset). **Verify**: update `tests/test_chrome.py`'s width rule to text + 2·(8+1+2) with the reason.
4. Menus and combo popup rows. **Verify**: a menu item 32 px; separator 1 px with 4 px margin.
5. Tooltips (`style.qss`, `_tips.py`, `styleHint`). **Verify**: `tests/test_tips.py` updated where it pins 64 columns or `<b>`; a test that `QApplication.style().styleHint(QStyle.SH_ToolTip_FallAsleepDelay)` is 300 under a themed root.
6. Whole suite and lint; after pictures (`page_buttons`, `family_menu`, `family_combo_popup`,
   `family_tooltip_plain`, `family_tooltip_facts`, `page_containers` tabs) into `...\scratchpad\look\after-003\`.

## Done criteria
- [ ] Probe shows every target; whole suite no failures; lint clean; changed expectations listed
- [ ] No colour changed; `tip("Save", "Write the scene to disk", "Ctrl+S")` still renders title, body and keycaps

## STOP conditions
- A 28 px tool button clips an icon or a text label (tool buttons with text use the same padding;
  they must still fit their text).
- Negative separator margins break menu painting: keep `margin: 4px 0` and say so.

## Maintenance notes
Pascal's toolbars of QToolButtons become 28 px squares 6 px apart; any Pascal layout that relied on
the old 2 px margin as its spacing should set spacing 6.
