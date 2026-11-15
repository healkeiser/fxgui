# Plan 004: Panels, dialogs, notices, chips, switches, progress and elevation take ls-ui's layout

> **Executor instructions**: read this plan fully, then the repo's `CLAUDE.md`. Follow the steps in
> order; run each verification. On a STOP condition, stop and report. The lead maintains
> `plans/2026-11-15-look/README.md`.
>
> **Drift check**: plan 001 has landed on your base. Re-locate every excerpt below in the live code;
> STOP only if what you must change is gone or different in substance. Plans 002 and 003 run in
> parallel and also edit `style.qss`: touch only the blocks this plan names.

## Status
- Priority: P2 · Effort: M · Risk: MED · Depends on: 001 · Category: look · Planned at: `7a4eff64`, 2026-11-15

## Why this matters
The rest of what a pipeline window shows: docked panes, dialogs, notices, chips, the switch, progress
bars and floating cards' shadows. The reference look gives these specific paddings, sizes and
elevations; fxgui's are close in kind but differ in value.

## Current state (line numbers from `7a4eff64`)
- `fxgui/fxdocking.py`: frame behind panes, each area a card radius 12 with a 1 px pane edge (near
  58-63); gap 4 everywhere: container margins 4 (near 785), splitter handle 4 (near 788), pane content
  margins 4, 0, 4, 4 (near 504-505).
- `style.qss` near 1552-1572: QSplitter handle 8 px invisible, hover a 2 px accent line in the middle.
  Framed window gaps use `PANE_GAP` (now 6 after plan 001) and `@frame` (qss near 1589-1661).
- `fxgui/fxwidgets/_confirm_delete.py`: plain QDialog with default layout margins.
- `fxgui/fxwidgets/_dialogs.py` (FXFloatingDialog): container card radius 12 (near 36-41); a title band
  with a sunken fill and top corners 11 (near 42-46); gutter 12 (near 30); title margins 12, 8, 12, 8
  (near 100-101); body margins 12 (near 109-110); buttons margins 12, 8, 12, 12 (near 114).
- `fxgui/fxwidgets/_notification_banner.py`: fixed width 320 (near 185, 209); margins 16, 12, 16, 12
  (near 219-223); icon 18 in a 20 box (near 224-225); title rank "section" (near 235); action buttons
  padding 6/16 (near 66-72).
- `fxgui/fxwidgets/_progress_card.py`: margins 16, 12, 16, 12; icons 18 in 20.
- `fxgui/fxwidgets/_empty_state.py`: icon 40; action bold (plan 001 made it 500) body text; detail
  muted body text; spacing 4 (`fxstyle.PANE_GAP`), margins 4.
- `fxgui/fxwidgets/_tag_input.py` FXTagChip: radius `@small_radius` (6), padding 2/4, layout margins
  8, 2, 4, 2; remove button 16 × 16.
- `fxgui/fxwidgets/_toggle_switch.py`: track 36 × 18 (near 162-170), thumb = track − 2·2 = 14.
- `style.qss` near 1-27: `QProgressBar` 4 px pill, radius 2.
- `fxgui/fxutils.py` `add_shadow(widget, offset=(0, 0))` (near 163-196) reads the theme's `shadow`
  colour and `shadow_blur` (`style.yaml` 20, a non-colour value kept per theme today).

## Targets
| What | Today | Target | Reference |
|---|---|---|---|
| Dock and framed-window gap between panes and around them | 4 (6 after 001 where it uses PANE_GAP) | **8** (a named constant, e.g. `FRAME_GAP = 8`, used by fxdocking's margins/handle and the framed window) | ls-ui raised page: 8 px margin |
| Pane content margins | 4, 0, 4, 4 | keep 8 px gap outside; inside **0** extra (the pane's own widgets bring their padding) — if this squeezes content visibly, keep 4 and say so | |
| Splitter hover line | 2 px | **1 px** (colour unchanged) | ls-ui panel edge: 1 px line on hover, 8 px grab |
| FXConfirmDeleteDialog margins / spacing | style default / 6 | **20, 16, 20, 16** / 12; buttons right-aligned 8 apart (the button box already orders them) | ls-ui dialog: 20 px sides, 16 top/bottom, body 12 |
| FXFloatingDialog | title band with its own fill, 12 px gutters | **no band fill** (title sits on the card), margins 20, 16, 20, 16, title rank "section" (15/500 after 001), body spacing 12 | ls-ui dialogs: no lines or bands between header, body, footer |
| Notification banner | width 320, margins 16/12, icon 18, title 15/600 | width **384**, margins **12**, spacing 8, icon **16**, title **13 px weight 500** (body font, medium), action buttons padding 6/10 | ls-ui toast: 384 wide, padding 12, gap 8, icon 16, 13 px title medium |
| Progress card | margins 16/12, icon 18 | margins **12**, icon **16** | same card language |
| Empty state | spacing 4, action body bold, detail body | spacing **16**, icon 40 (keep), action **16 px weight 500**, detail **14 px** muted, text max width **384** | ls-ui empty md: gap 16, title 16 medium, description 14, max width 384 |
| FXTagChip | radius 6, padding 2/4, height ~22 | radius **9**, height **28**, text 12 px, 6 px gap, padding so the text and the remove button centre | ls-ui chip: 28 px, 9 px radius, 12 px text |
| Toggle switch | track 36 × 18, thumb 14 | track **36 × 20**, thumb **16**, 2 px inset (keep) | ls-ui switch md: 36 × 20, 16 px thumb |
| QProgressBar | 4 px, radius 2 | **6 px**, radius 3 | ls-ui meter 6 px pill |
| Floating cards' shadow | offset (0, 0), blur 20 | default offset **(0, 6)**, blur **16** (set `shadow_blur: 16` in every bundled theme's data in `style.yaml`, the only non-colour line touched there) | ls-ui shadow-lg ≈ 0 8 15, one layer (QGraphicsDropShadowEffect has one layer and no spread) |

Keep: colours, the scrim, the pane edge colour, radii 12 for cards, every widget's public API.

## Commands
Same as plan 001.

## Scope
In: `fxgui/fxdocking.py` (gaps), the splitter and framed-window blocks of `style.qss`, `_confirm_delete.py`,
`_dialogs.py`, `_notification_banner.py`, `_progress_card.py`, `_empty_state.py`, `_tag_input.py`,
`_toggle_switch.py`, the QProgressBar block, `fxutils.add_shadow`'s default offset, `shadow_blur` in
`style.yaml`, and the tests that pin these. Out: colour values; rows (002); buttons/menus/tabs/tooltips (003); motion (005).

## Steps
1. Probe the before values of every row in Targets. 2. Docking and framed gaps; splitter line.
3. Dialogs. 4. Banner and progress card. 5. Empty state. 6. Chip. 7. Switch. 8. Progress bar.
9. Shadow. After each: the matching tests, updated on purpose where they pin an old number.
10. Whole suite and lint; after pictures (`page_docking`, `page_windows`, `family_dialog_confirm`,
`family_dialog_floating`, `page_display`, `page_inputs`, `family_switch`) into `...\scratchpad\look\after-004\`.

## Done criteria
- [ ] Probe shows every target; whole suite no failures; lint clean; changed expectations listed
- [ ] `git diff -- fxgui/style.yaml` shows only `shadow_blur` lines

## STOP conditions
- 8 px dock gaps break a QtAds layout test that cannot be updated without changing behaviour.
- The banner's 384 width overflows its default parent in a test.

## Maintenance notes
`style.yaml` changes (`shadow_blur`): a brand colour file that copies fxgui's should re-copy or set it.
Pascal's own EmptyState copy keeps its old look until Pascal moves to `FXEmptyState`.
