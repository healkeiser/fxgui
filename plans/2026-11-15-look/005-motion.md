# Plan 005: Motion takes ls-ui's durations and curves

> **Executor instructions**: read this plan fully, then the repo's `CLAUDE.md`. Follow the steps in
> order; run each verification. On a STOP condition, stop and report. The lead maintains
> `plans/2026-11-15-look/README.md`.
>
> **Drift check**: plan 001 has landed on your base. Re-locate every excerpt below; STOP only if what
> you must change is gone or different in substance. Plans 002-004 run in parallel; they touch sizes,
> not animations. Plan 004 edits `_toggle_switch.py`, `_notification_banner.py` geometry: touch only
> their animation lines.

## Status
- Priority: P2 · Effort: S-M · Risk: LOW · Depends on: 001 · Category: look · Planned at: `7a4eff64`, 2026-11-15

## Why this matters
The reference look has five durations (instant 100, fast 150, base 200, slow 300, spring 400 ms) and
one main curve, "out" = cubic-bezier(0.2, 0, 0, 1); anything that travels uses a critically damped
spring (stiffness 520, damping 40 per unit mass, damping ratio ≈ 0.877, settled in 400 ms). fxgui uses
OutCubic everywhere with its own durations. Qt can express all three honestly: a bezier
`QEasingCurve`, and the spring as a custom easing function.

## Current state (line numbers from `7a4eff64`)
`fxgui/fxstyle.py` near 372-383: `POPUP_FADE_MS = 150`, `WINDOW_FADE_MS = 250`, `POPUP_DROP = 6`,
`PANEL_FADE_MS = 220`, `PANEL_RISE = 8`, `PANEL_OPEN_MS = 260`; `_fade_in` (near 3063-3072),
`_drop_in` (near 3050-3060), `_Reveal` (near 2563-2647); `FXGUI_REDUCED_MOTION` (near 387-392).
Widget animations (all OutCubic unless noted): `_toggle_switch.py` 150 ms InOutCubic (near 63-65);
`_collapsible.py` 150 ms (near 83); `_accordion.py` passes 150 (near 48); `_notification_banner.py`
250 ms slide in/out/restack (near 266-268, 383, 399, 425); `_seating.py` `ENTRANCE_MS = 160`,
`ENTRANCE_SLIDE = 12` (near 38-53); `fxdocking.py` pane open uses `PANEL_OPEN_MS` (near 213-270);
`_delegates.py` row hover leave fade 0.15 s quadratic (near 598, 638, 1416-1443).

## Targets
| What | Today | Target | Reference |
|---|---|---|---|
| Motion constants | scattered | new public constants in `fxstyle`: `MOTION_INSTANT = 100`, `MOTION_FAST = 150`, `MOTION_BASE = 200`, `MOTION_SLOW = 300`, `MOTION_SPRING = 400`; `ease_out()` returning `QEasingCurve(BezierSpline)` with `addCubicBezierSegment(QPointF(0.2, 0), QPointF(0, 1), QPointF(1, 1))`; `ease_spring()` returning a curve that follows the spring (custom type from the closed form x(t) = 1 − e^(−ζωt)(cos ω_d t + ζω/ω_d sin ω_d t), ω = √520, ζ = 40 / (2√520), t scaled to 0.4 s, clamped to 1 at the end) | ls-ui tokens.css / motionCore.js |
| Popup and tooltip fade | 150 ms OutCubic | **100 ms, ease_out** (`POPUP_FADE_MS = 100`) | ls-ui menus/tooltips open 100 ms |
| Popup drop | 6 px | **0** (no drop: the reference scales in, which a top-level window cannot do honestly; fade alone) — keep `POPUP_DROP` as the public constant set to 0 | |
| Window fade on show | 250 ms | **200 ms** (base), ease_out | ls-ui dialog open 200 ms |
| Page/pane reveal | 220 ms, rise 8 | **300 ms** (slow), rise **4**, ease_out | ls-ui page arriving: 300 ms, 4 px |
| Pane opening (splitter grows) | 260 ms OutCubic | **400 ms, ease_spring** | ls-ui panel slide on the spring |
| Toggle switch thumb | 150 ms InOutCubic | **200 ms, ease_out** | ls-ui switch 200 ms out |
| Collapsible / accordion | 150 ms | **200 ms, ease_out** | ls-ui fold 200 ms |
| Banner slide in / out | 250 ms | **in 200 ms ease_out, out 150 ms ease_out**; restack **400 ms ease_spring** | ls-ui toast enter 200, leave 150-200, restack spring |
| Seating entrance | 160 ms, 12 px | **200 ms, ease_out, 4 px** | ls-ui content enters from 4 px over 200 ms |
| Row hover leave fade | 150 ms quadratic | **150 ms, ease_out** | ls-ui hover out 150 ms |
| Reduced motion | `FXGUI_REDUCED_MOTION=1` | unchanged contract: every animation above skipped; spinners keep turning | |

Keep: what animates and when (no new or removed animation), the busy line and spinner speeds, the
validated line edit's shake.

## Commands
Same as plan 001. Motion tests: `tests/test_motion.py` and the widgets' own tests.

## Scope
In: the motion constants and helpers in `fxstyle.py`, `_fade_in`/`_drop_in`/`_Reveal`, and the
animation lines in `_toggle_switch.py`, `_collapsible.py`, `_accordion.py`, `_notification_banner.py`,
`_seating.py`, `fxdocking.py`, `_delegates.py`; docs (`docs/how-to/theming.md` or a motion section);
tests. Out: sizes, colours, anything else.

## Steps
1. Add the constants and the two curves with tests: `ease_out().valueForProgress(0.5)` equals the
   bezier's value (compare with a numeric bezier solve), `ease_spring()` is 0 at 0, ≥ 0.99 at 1, under
   1.01 everywhere (under 1 % overshoot), monotonic within tolerance.
2. Switch every listed animation to the targets.
3. Update tests that pin durations; reduced-motion tests still pass.
4. Whole suite and lint. Export the constants in `fxstyle.__all__`; document them.

## Done criteria
- [ ] `grep -n "OutCubic\|InOutCubic" fxgui` shows no remaining use in the listed animations
- [ ] Whole suite no failures; lint clean; changed expectations listed

## STOP conditions
- A custom easing function crashes or is unsupported on PySide6 6.5.3: keep a 16-step keyframe
  approximation (`QVariantAnimation.setKeyValueAt`) for the spring instead and say so.
