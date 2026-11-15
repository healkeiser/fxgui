# The look plans of 2026-11-15: fxgui takes ls-ui's non-colour look

Written at commit `7a4eff64` (fxgui 14.5.0). The owner's ruling, verbatim: "The colors and
everything should stay in pascal for the Lotchi theme, but for the rest (animation, spacing,
borders, etc.) ls-ui looks pretty good on the web, and a unification is great to have."

So: **colours do not move** (every bundled theme keeps its own colours; a brand's colours stay in
its own colour file). **Everything that is not a colour becomes fxgui's one look**, for every theme,
taken from ls-ui (the web look of the studio's tracker): sizes, paddings, radii, borders, focus shape,
type scale and weights, icon sizes, elevation, scroll bars, the layout of each widget family, and
motion where Qt has an honest equivalent. No per-theme keys for these; a theme key only for what a
brand owns (a font family, a colour). No studio name, logo or asset in fxgui.

Rules for every plan:
- Pixel and size tests that pin the old look are updated on purpose; each plan lists every changed
  expectation (test, old value, new value) in its commit message body.
- Behaviour never changes inside a look change (no new or removed interaction).
- Accessibility never worse: text contrast floors, keyboard focus always visible, keyboard reach.
- Where a web effect has no honest Qt equivalent, skip it and say so; never fake it.

| Plan | Title | Depends on | Status |
|------|-------|------------|--------|
| 001 | Core metrics and type scale: control height 32, gap 6, indicators 16, weights 500, title ranks; Inter and JetBrains Mono shipped as the default faces | none | DONE (released 15.0.0) |
| 002 | Rows, trees, tables and headers | 001 | DONE (released 15.0.0) |
| 003 | Buttons, fields, tabs, menus and tooltips | 001 | DONE (released 15.0.0) |
| 004 | Panels, dialogs, notices, chips, switches, progress and elevation | 001 | DONE (released 15.0.0) |
| 005 | Motion: ls-ui's durations and curves | 001 | DONE (released 15.0.0) |

Skipped on purpose (no honest Qt equivalent, or a feature rather than a look): frosted-glass popups
(no access to pixels behind a window), scale-in of popups and dialogs, the app shrinking behind a
dialog, press-to-shrink buttons and hover fades on QSS widgets (QSS has no transitions; every
button would need custom painting), gliding highlights in menus and tab bars (QMenu and QTabBar paint
per item), row FLIP animation and chevron rotation in item views, a painted 3 px focus halo outside
controls (QSS cannot draw outside a widget; fxgui's keyboard focus stays a recoloured edge, which is
also what ls-ui does to an outlined control's ring), keycap chips inside QMenu shortcuts, skeleton
loaders and the top progress line (new widgets, not a look change).

## Decisions taken while executing

- Fonts (owner, 2026-11-15): fxgui ships Inter and JetBrains Mono, taken byte for byte from the brand's grid-fitted files (ttfautohint, strong stem width), as the default body/title and mono faces with `hinting: vertical`. Measured: `none` ignores the grid-fitting; `vertical` is the crispest and makes Inter 400 as dark as unhinted 500, so body stays 400 and 500 is the step above. Recipe and numbers: `fxgui/fonts/README.md`.
- No font or weight rule on every instance of a common class (it overrides `setFont`): the push-button weight rule plan 001 first added was removed.
- Tabs keep the shared 6 px gap (ls-ui: 4 px): eight tests pin the relation that tab gaps, the first tab's inset and a pane's content inset are one gap; kept on purpose.
- A tree's row rule runs on under its indentation (the sheet rules `::branch`); the neutral status tag is a 20 px badge with 6 px sides.
- Reduced motion (`FXGUI_REDUCED_MOTION=1`) now skips every fxgui animation, not only the fades; the validated field's red flash stays (it is information, not motion).
