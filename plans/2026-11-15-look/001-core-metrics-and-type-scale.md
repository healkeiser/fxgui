# Plan 001: Core metrics and type scale take ls-ui's values

> **Executor instructions**: read this plan fully, then the repo's `CLAUDE.md`. Follow the steps in
> order; run each verification. On a STOP condition, stop and report. The lead maintains
> `plans/2026-11-15-look/README.md`; do not edit it.
>
> **Drift check (run first)**: `git diff --stat 7a4eff64..HEAD -- fxgui/fxstyle.py fxgui/qss/style.qss`
> must be empty; otherwise compare the excerpts below with the live code and STOP on a mismatch.

## Status
- Priority: P1 (every other look plan builds on it) · Effort: M · Risk: MED (many pixel tests move)
- Depends on: none · Category: look · Planned at: `7a4eff64`, 2026-11-15

## Why this matters
fxgui's controls are 27 px tall at the 13 px body font; the reference look (ls-ui) draws its default
controls 32 px tall (6 px padding, a 1.5 line box, a 1 px edge inside the box). fxgui's one gap is
4 px where ls-ui's inline gap is 6 px. Indicators (checkbox, radio) are 18 px where ls-ui's are 16 px.
fxgui's headings use 600/700 weights where ls-ui never goes past 500 (medium). Every other look plan
assumes these core values.

## Current state (read these places)
- `fxgui/fxstyle.py:269` `PANE_GAP = 4` — the one gap: `FXProxyStyle.pixelMetric` returns it for
  `PM_LayoutHorizontalSpacing`/`PM_LayoutVerticalSpacing` (near line 2203), token `@pane_gap`.
- `fxgui/fxstyle.py:307` `INDICATOR_SIZE = 18`; tokens `@indicator_size`, `@indicator_inner` (16),
  `@indicator_round` (9) near line 1597-1603.
- `fxgui/fxstyle.py:357-358` `_FIELD_BOX = 10`, `_BUTTON_BOX = 14`; `control_height(widget)` near
  line 1078: `line = widget.fontMetrics().size(Qt.TextShowMnemonic, "Ag").height(); return line + _BUTTON_BOX`.
  The token builder near line 1440-1460 computes `@text_line`, `@field_inner` (= height − 10),
  `@row_line`, `@spin_padding` from the same line.
- `fxgui/fxstyle.py` `_DEFAULT_RANKS` near line 420: `"section": {"size": 15, "weight": 600}`,
  `"card": {"size": 16, "weight": 700}`.
- `fxgui/qss/style.qss`: QPushButton padding 6/10 (near 588-600); QLineEdit padding 4/8 (near 348-359);
  QComboBox padding 4/6 (near 645-658); QAbstractSpinBox `@spin_padding` (near 815-840).
- Weights above 500 in fxgui (each becomes 500, "medium"): QToolBar bold (qss near 561), QToolBox
  open tab 600 (qss near 1521), `_breadcrumb.py` current segment 600 (near 152-155),
  `_notification_banner.py` action 600 (near 71), `_empty_state.py` action bold (near 55-57),
  menu badge bold (fxstyle near 2247-2252), delegate title DemiBold (`_delegates.py` near 795-799) and
  child-count badge 600 (near 911-920). The tooltip title `<b>` belongs to plan 003, not here.

## Targets (the reference values)
| What | Today | Target | Reference |
|---|---|---|---|
| Control height at the 13 px body font | 27 | **32** = a line box of round(1.5 × font px) = 20, plus 6 px padding top and bottom less the 1 px edge (5 + 1 each side) | ls-ui md button and md input 32 px; 13 px controls 31.5 → 32 |
| Control height rule | measured line + 14 | `max(measured line, round(1.5 × font pixel size)) + 12`, so a bigger font still grows | |
| Button padding (sides) | 10 | 10 (keep); vertical padding solved from the rule above | ls-ui 6/10 |
| Field padding | 4 / 8 | vertical solved to reach the control height; sides **10** | ls-ui input 6/10 |
| Combo padding | 4 / 6 | vertical solved; left **10**; right keeps room for its 16 px chevron, chevron 10 px from the right edge | ls-ui select md |
| Default layout gap (`PANE_GAP`) | 4 | **6** | ls-ui toolbar/control gap `gap-1.5` |
| Indicator box (checkbox, radio) | 18 (16 inner) | **16** (14 inner), radius 6 (radio round 8), check glyph 12-14 px | ls-ui checkbox md 16 px, 6 px radius |
| Title rank "section" | 15 / 600 | **15 / 500** | ls-ui dialog title 15 px medium |
| Title rank "card" | 16 / 700 | **18 / 500** | ls-ui side panel title 18 px medium |
| Weights 600/700/bold listed above | 600/700 | **500** | ls-ui uses 400 and 500 only |
| Push button text weight | regular | **500** | ls-ui buttons medium |

Notes:
- Keep the structure: control height stays computed from the widget's font (not a fixed 32), the
  `@field_inner`/`@spin_padding` solvers stay, `_FocusVisibility` and "focus moves nothing" stay.
- QSS cannot set `line-height`; the line box is a height, the text centres in it.
- The splash title, the floating dialog and the notification banner use the "card"/"section" ranks:
  they follow automatically.

## Commands
| Purpose | Command (from the worktree root) | Expected |
|---|---|---|
| Tests, one file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/<file>.py` | pass |
| Whole suite | same with `-q -n 8` | no failures |
| Lint | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m ruff check --select F,B,BLE .` | `All checks passed!` |
| Pictures | `...python.exe C:\Users\VALENT~1\AppData\Local\Temp\claude\cbe1f96ba19709d6\9f9de763-ae27-411a-8c49-3493164a641f\scratchpad\look\render_families.py <out> --themes dark light` | PNGs written |

Run only from the worktree root (the shared venv's editable install points at another checkout).
Tests run offscreen (conftest); never on the real platform. Any script scopes QSettings first.

## Scope
In: `fxgui/fxstyle.py` (the constants, `control_height`, the token builder, `_DEFAULT_RANKS`, the proxy
style's metrics), `fxgui/qss/style.qss` (button/field/combo/spin/indicator paddings and weights),
the weight lines listed above in `_breadcrumb.py`, `_notification_banner.py`, `_empty_state.py`,
`_delegates.py`, and the tests that pin these values. Out: colours, `style.yaml` colour values, motion
(plan 005), row/menu/tab/tooltip/panel layouts (plans 002-004).

## Steps
1. Write a probe that prints, for themes dark and light, the control height of a QPushButton, a
   QLineEdit, a QComboBox, a QSpinBox, an FXSplitButton and an FXJoinedGroup child, the default layout
   spacing, and an indicator's size. **Verify**: the "before" numbers (27-ish, 4, 18) print.
2. Change `control_height`, the token builder and the paddings so every control family reaches the
   target. **Verify**: the probe prints 32 for every control at 13 px, and a 16 px font gives more.
3. `PANE_GAP` 6; indicators 16; ranks; the weights. **Verify**: probe; `grep -n "font-weight: 600\|font-weight: 700\|bold" fxgui/qss/style.qss` shows no heading/body weight above 500 except where a test explains why.
4. Run the whole suite; update every test that pinned an old number, keeping each test's intent; keep
   every relation test ("focus moves nothing", "one gap", "measure equals paint") passing unchanged.
   **Verify**: whole suite no failures; lint clean.
5. Render after pictures for dark and light into
   `C:\Users\VALENT~1\AppData\Local\Temp\claude\cbe1f96ba19709d6\9f9de763-ae27-411a-8c49-3493164a641f\scratchpad\look\after-001\`
   and look at `page_buttons`, `page_inputs`, `family_button_states`: nothing clipped, text centred.

## Done criteria
- [ ] Probe: every control 32 px at the 13 px body font in dark and light; gap 6; indicator 16
- [ ] Whole suite no failures; lint clean; each changed expectation listed in the commit body
- [ ] No colour value changed (`git diff -- fxgui/style.yaml` shows no colour line)

## STOP conditions
- A control cannot reach 32 without changing a public signature.
- A relation test (focus moves nothing, measure equals paint) would have to be deleted to pass.
- Text clips in any rendered control.

## Maintenance notes
Consumers that hard-code 27/28 px next to fxgui controls will look off by a few pixels: Pascal sizes
some of its own widgets from `fxstyle.control_height`, which follows; anything hard-coded must follow too.
