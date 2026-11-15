# Plan 002: Rows, trees, tables and headers take ls-ui's layout

> **Executor instructions**: read this plan fully, then the repo's `CLAUDE.md`. Follow the steps in
> order; run each verification. On a STOP condition, stop and report. The lead maintains
> `plans/2026-11-15-look/README.md`.
>
> **Drift check**: plan 001 (core metrics) has landed on your base; it changed `fxstyle.py`,
> `style.qss` and tests. Re-locate every excerpt below in the live code; STOP only if what you must
> change is gone or different in substance.

## Status
- Priority: P1 (what a pipeline user looks at all day) · Effort: M · Risk: MED (delegate geometry is
  pinned by many tests) · Depends on: 001 · Category: look · Planned at: `7a4eff64`, 2026-11-15

## Why this matters
Trees and lists are most of what a pipeline window shows. The reference look (ls-ui's tables and
lists) gives a header 36 px tall in 12 px medium text with 12 px cell padding, a 1 px hairline under
every row, square full-bleed hover and selected fills, a 2 px keyboard focus outline inside the row,
14 px fold chevrons, and a 22 px indent per tree level. fxgui is close (rows 28/36/52 already match;
tables and the thumbnail delegate already draw row rules) but differs in the header, the cell
padding, plain trees without rules, rounded list rows, a 1 px focus ring and 16 px chevrons.

## Current state (read these places; line numbers are from `7a4eff64`, they moved with plan 001)
- `fxgui/qss/style.qss` near 1450-1495: `QHeaderView::section { padding: 8px 4px; font-size: @font_size_small; color: @text_muted; border-bottom: 1px solid @border; ... }`.
- `fxgui/qss/style.qss` near 1102-1128: `QListView::item` fixed 28 px; hover/selected list rows radius 9
  (only lists round). Near 1117-1121: `QTreeView::item { padding: 0 }`, height `@row_height`.
- `fxgui/qss/style.qss` near 1072-1085: tree branch chevrons, no lines; `fxstyle.py` near 287-291 pads a
  chevron to a 16 px box per indentation.
- `fxgui/fxstyle.py` near 2090 and 2157-2169: `FXProxyStyle` draws a 1 px rule under each table cell at
  60 % of the edge colour (`QTableView` only).
- `fxgui/fxwidgets/_delegates.py` (FXThumbnailDelegate): row icon 16 px at a 6 px margin (near 563-564,
  1946-1953); text right margin 10 (near 568); 1 px rule under each row (near 1383-1414); the keyboard
  focus ring is 1 px accent inside the row, square (near 1541-1570).
- Nav lists (`fxstyle.mark_as_nav`, qss near 1183-1206): 28 px chips, radius 9, margin 1 px 4 px.

## Targets
| What | Today | Target | Reference |
|---|---|---|---|
| Header section height | ~32 (8 + text + 8) | **36** min height | ls-ui `h-9` header [measured 36] |
| Header padding | 8 / 4 | **0 / 12** (text 12 px in from the column edge) | ls-ui list header `px-3` |
| Header text | 12 px muted | 12 px muted, **weight 500** | ls-ui 12 px medium |
| Cell horizontal padding (tables, trees, lists; item views generally) | 0-4 | **12** each side (in `::item` padding or the proxy's text rect) | ls-ui cells `px-3` |
| FXThumbnailDelegate leading margin / text right margin | 6 / 10 | **12 / 12** (icon at 12 px; overlays and pills keep their own insets relative to it) | same |
| Row rule | tables and the delegate only | also **plain QTreeView and QListView** that are not popups, nav lists or combo lists: 1 px, the same 60 % edge colour role the table rule uses | ls-ui every row has a 1 px bottom hairline |
| List row hover/selected shape | radius 9 | **square, full bleed** | ls-ui rows: no radius, no inset |
| Nav list chip | radius 9, margin 1/4 | radius **6**, margin **1 px top/bottom** (side inset kept) | ls-ui sidebar link highlight 6 px, inset 1 px |
| Keyboard focus in a row (delegate and the proxy's item focus) | 1 px accent ring | **2 px** accent outline inside the row, square, keyboard only (as today) | ls-ui clickable rows: 2 px inside |
| Tree fold chevron | 16 px in a 16 px box | **14 px** glyph, centred in the indentation box | ls-ui TreeChevron 14 px |
| Tree indentation per level | Qt default 20 | **22** | ls-ui 22 px a level |
| Row heights 28/36/52, plain list 28 | — | **keep** (they already match the reference) | Carmen row sizes 28/36/52 |

Keep: the delegate's status pill look (the owner wants pills unchanged), its thumbnail geometry
relative to the row height, measure-equals-paint invariants, hover fade, selection colours.

## Commands
Same as plan 001 (tests from the worktree root, `-n 8` for the whole suite, ruff
`--select F,B,BLE`, the picture script
`C:\Users\VALENT~1\AppData\Local\Temp\claude\cbe1f96ba19709d6\9f9de763-ae27-411a-8c49-3493164a641f\scratchpad\look\render_families.py <out> --themes dark light`).

## Scope
In: `fxgui/qss/style.qss` (header, item views, nav, branch), `fxgui/fxstyle.py` (FXProxyStyle row rule,
chevron box, indentation, header metrics), `fxgui/fxwidgets/_delegates.py` (margins, focus outline),
and the tests that pin these. Out: colours; row heights; the status pill's look; menus/combos/popups
(plan 003); motion (plan 005).

## Steps
1. Probe: print header height, a tree's indentation, the delegate's icon x and focus width.
   **Verify**: the before values.
2. Header: height, padding, weight. **Verify**: probe 36; header text 12 px from the column edge.
3. Cells and the delegate margins (12). **Verify**: `tests/test_delegate_layout.py` and
   `tests/test_full_width_rows.py` fail only where they pin 6/10, then update them with the reason.
4. Row rules on plain trees and lists (not popups, nav, combo lists, completers). **Verify**: a pixel
   test: a 3-row QTreeWidget shows a rule under rows 1 and 2; a combo popup and a nav list show none.
5. Square list rows; nav chip 6 px radius, 1 px inset. **Verify**: pixel tests.
6. Focus 2 px; chevron 14 px; indentation 22. **Verify**: tests; the keyboard-focus ring still shows
   only after a key, never after a click.
7. Whole suite and lint; after pictures (`page_lists_and_trees`, `family_tree_selection`, dark, light)
   into `...\scratchpad\look\after-002\`.

## Done criteria
- [ ] Probe shows every target; whole suite no failures; lint clean
- [ ] Every changed expectation listed (test, old, new) in the commit body
- [ ] No colour changed; the status pill pixels unchanged (an existing pill test still passes untouched)

## STOP conditions
- The delegate's measure and paint disagree after the margin change.
- A row rule would draw inside a popup, a completer or a combo list.
- The 2 px focus outline hides the row's text at the small row size (28 px).

## Maintenance notes
Pascal draws its own rows through FXThumbnailDelegate and plain trees; they follow. Pascal's tests
that measure a row's text x (if any) will move by 6 px.
