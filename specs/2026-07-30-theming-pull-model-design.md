# Theming rework: pull model (cascading sheet + paint-time reads)

- **Date:** 2026-07-30
- **Status:** Approved (design), pending implementation plan
- **Scope:** `fxstyle`, `fxutils`, `fxgui/qss/style.qss`, all `fxwidgets` modules
- **Hard requirement:** no breakage of the currently public API during the
  deprecation cycle. Existing downstream code must keep working unchanged,
  with at most `DeprecationWarning`s. The entire existing test suite must
  stay green throughout.

## Problem

Making a custom widget theme-aware currently requires: inheriting
`FXThemeAware` first in the MRO, choosing between three coexisting
mechanisms (`theme_style`, `_on_theme_changed`, deprecated
`_apply_theme_styles`), and picking among half a dozen color-access paths.
The machinery behind it (per-widget signal connections, deferred
`QTimer.singleShot(0)` first apply, C++-validity checks, cache invalidation
in three places, an icon-widget registry) exists because the design is a
**push model**: colors are baked into per-widget stylesheet strings and
pixmaps at apply time, so every widget must be individually notified to
rebake when the theme switches.

Evidence the model overshoots: none of the 30+ built-in widgets uses the
"recommended" `theme_style` attribute; `FXToggleSwitch` uses the whole
mixin only to get an `update()` call; `FXSearchBar._on_theme_changed`
rebuilds QSS whose only dynamic part is token substitution.

## Goals

1. The custom-widget contract fits in one sentence and needs no mixin.
2. Live theme switching works with zero per-widget signal connections for
   the common cases.
3. One token-resolution implementation instead of three.
4. fxgui's own widgets are dogfooded on the exact contract the docs teach.
5. Full backward compatibility for one release cycle via shims.

## Non-goals (explicitly deferred)

- Theme-aware `QIconEngine` (fxicons registry and cache choreography stay
  as-is this round).
- Removing the compatibility shims (next major version).
- QPalette-based theming (rejected: ~10 usable roles vs ~25 semantic roles,
  and QSS overrides palette in hard-to-reason ways).

## Design

### Pull model

Qt already repolishes and repaints every descendant when a stylesheet is
set on `QApplication` or an ancestor widget, sending each a
`QEvent.StyleChange`. Painting is on demand. Therefore: nothing gets
notified; things read current theme state when Qt asks them to render.

### Theme state

Unchanged in substance: current theme name plus persistence via
`fxconfig`, colors loaded from `style.yaml`. `FXThemeColors` (attribute
namespace over the color dict) stays, cached per theme.

### One sheet, one token pass

The theme stylesheet is built in a single place from:

1. `style.qss`, which absorbs the static QSS currently rebuilt in Python
   by widget `_on_theme_changed` methods, keyed by class selectors
   (QSS class selectors match `QMetaObject::className()`, which is the
   Python class name for PySide/PyQt subclasses).
2. Fragments registered by external widget authors via
   `fxstyle.register_widget_style(qss)`, appended after the base sheet.

Tokens (`@surface`, `@border_light`, computed `@text_on_accent_primary`,
flattened feedback colors such as `@feedback_error_foreground`, the
`~icons` path) are resolved in one generic pass, longest key first. This
replaces the three implementations that exist today: `load_stylesheet`'s
hand-maintained map, `replace_colors`, and the mixin's
`__apply_theme_style_attribute`.

### Themed roots

A module-level `WeakSet` of root widgets that receive the sheet:

- **Standalone:** `FXApplication` registers itself as the sole root; the
  sheet cascades to every window.
- **DCC-embedded (Houdini, Maya, Nuke):** `FXMainWindow` and
  `FXFloatingDialog` detect that `QApplication.instance()` is foreign and
  register themselves individually. The host application is never
  restyled, same guarantee as today.

Dead windows drop out of the `WeakSet`; nothing to disconnect.
Registering a root applies the current sheet to it immediately, so startup
with a saved theme behaves exactly as today.

### Switching

`fxstyle.apply_theme(name)` does: validate, update state, invalidate the
color-namespace cache, persist to `fxconfig`, sync icon colors
(`fxicons.sync_colors_with_theme()`, unchanged this round), rebuild the
sheet, `setStyleSheet` on each registered root, emit `theme_changed`.
Qt's cascade repolishes and repaints all descendants.

### Public API

| Name | Role |
| --- | --- |
| `fxstyle.colors()` | Canonical color read: cached namespace, `colors().surface`, safe in `paintEvent` hot paths |
| `fxstyle.apply_theme(name)` | Switch the theme everywhere |
| `fxstyle.theme_changed` | Signal, only for side-effect subscribers |
| `fxstyle.register_widget_style(qss)` | External widget authors, once at module import; `@tokens` allowed; deduped by hash; triggers live re-apply if roots are already themed |
| `fxutils.repolish(widget)` | Re-evaluate QSS after a dynamic property change |

### The custom-widget contract

> Put your rules in QSS with `@tokens` using your class name as selector
> (via `register_widget_style`, or directly in `style.qss` for built-ins),
> or read `fxstyle.colors()` inside `paintEvent`. Only if a theme switch
> has side effects beyond looks (cached pixmaps, re-highlighting) do you
> connect to `fxstyle.theme_changed`.

No mixin, no MRO rule, no override, no timer.

### State-dependent styling

Qt dynamic properties plus attribute selectors:
`FXNotificationBanner[level="error"] { ... }`,
`FXDropZone[dragOver="true"] { ... }`. The widget sets the property and
calls `fxutils.repolish(self)`.

## Migration of built-in widgets

Provisional categorization; confirming each widget is a plan-phase task.

1. **QSS-only (~18-20):** `_on_theme_changed` bodies become static rules
   in `style.qss`; the Python styling code is deleted. Inner elements get
   stable objectNames by convention (`fx_search_container`) so ID
   selectors can target them. Examples: `FXSearchBar`, `_inputs` widgets,
   `FXProgressCard`, `FXBreadcrumb`, `FXFilePathWidget`, `FXTagChip`,
   dialogs, fuzzy-search widgets.
2. **State-dependent QSS:** `FXNotificationBanner`, `FXDropZone`,
   `FXValidatedLineEdit` move to dynamic properties + repolish.
3. **Paint-time readers (~6):** `FXToggleSwitch`, `FXRangeSlider`,
   `FXRatingWidget`, `FXLoadingSpinner`, delegates: drop the mixin, read
   `fxstyle.colors()` at paint time. Widgets that cache theme colors as
   instance attributes (`FXTimelineSlider`) switch to paint-time reads;
   `colors()` is a cached namespace, so a per-paint read is one attribute
   lookup and the private cache should be removable.
4. **Side-effect subscribers (~4):** `FXPygmentsHighlighter` (re-highlight),
   `FXSplashScreen` (re-render pixmap), `FXMainWindow` (banner icon,
   theme-action check states) connect to `theme_changed` in `__init__`.

After migration, fxgui's own widgets carry no theming code except the four
subscribers.

## Compatibility shims (one release cycle)

- **`FXThemeAware` stays importable and functional:** connects
  `theme_changed` to `_on_theme_changed`, keeps the `.theme` property
  (forwarding to `colors()`), keeps `theme_style` working, keeps the
  `QTimer.singleShot(0)` initial apply inside the shim only. Emits one
  `DeprecationWarning` per class. Existing subclasses behave identically.
- **`apply_theme(widget, theme)` old signature:** detected by argument
  type; warns; registers `widget` as a themed root; proceeds.
- **`load_stylesheet()` stays public** (documented DCC entry point), as a
  thin wrapper over the new sheet builder.
- **Color getters stay working:** `get_theme_colors`, `get_accent_colors`,
  `get_feedback_colors`, `get_icon_color`, `get_theme`,
  `get_available_themes`. Docs point to `colors()` as canonical.
- **`theme_manager` stays public** (it is in `__all__`);
  `fxstyle.theme_changed` is the same signal instance exposed at module
  level. `_apply_theme_styles` and `_safe_apply_theme_styles` keep working
  inside the `FXThemeAware` shim, warnings unchanged. Nothing public is
  removed this cycle.

Acceptance criterion for the whole compat layer: the pre-rework test suite
passes unmodified against the reworked library (deprecation warnings
excepted).

## Validation

### Step 0: spike (gate, fail fast)

One pytest-qt test file proving, on the installed bindings:

1. An ancestor `setStyleSheet` delivers `QEvent.StyleChange` to
   descendants.
2. A custom-painted descendant repaints afterwards (tracked via a
   `paintEvent` counter after event processing).
3. A QSS class selector matches a Python subclass name.
4. Repolish time on a deep/wide tree is acceptable (measured, not felt).

If (2) is unreliable on PySide2, `apply_theme` gains one top-down
`update()` walk over registered roots. Documented fallback; the
zero-per-widget-code property is preserved.

### Tests

- Unit: sheet builder token resolution (longest-first, feedback
  flattening), root registry weak behavior, `register_widget_style` dedup
  and live re-apply, old-signature `apply_theme` shim.
- Visual regression: `test_visual.py` gains before/after `widget.grab()`
  assertions for one widget per migration category, so a theme switch
  that silently stops recoloring fails CI.
- Regression: full existing suite green under shims, with expected
  deprecation warnings asserted.
- Manual: `examples.py` showcase cycled through all themes after each
  migration batch; DCC smoke test in a live Houdini session for the
  embedded-root path.

## Rollout

1. **Spike** (step 0 above). Decision gate.
2. **Core:** sheet builder, root registry, `apply_theme(name)`,
   `colors()`, `register_widget_style`, `repolish`, shims. Existing suite
   green before any widget changes.
3. **Widget migration in category batches**, one commit per batch, tests +
   showcase pass after each: QSS-only, then dynamic-property, then
   paint-time, then subscribers.
4. **Docs:** theming guide rewritten around the one-sentence contract;
   CHANGELOG documents deprecations and the mechanical migration recipe.

## Risks

| Risk | Mitigation |
| --- | --- |
| PySide2 does not repaint custom-painted descendants on ancestor restyle | Spike proves it; fallback `update()` walk in `apply_theme` |
| QSS specificity conflicts once all widget styles share one sheet | Class-selector convention, fragments appended after base sheet, visual regression tests |
| Repolish cost in large embedded UIs (Houdini) | Only fxgui roots are restyled, never the host; spike measures on a deep tree |
| External subclasses relying on mixin internals | Shim keeps `FXThemeAware` behavior byte-compatible for one cycle; changelog recipe |
| Widgets outside any themed root (parentless dialogs in DCCs) | They register themselves as roots (`FXFloatingDialog` does this already by design) |

## Resolved decisions

- Compatibility: break with shims, one release cycle (user decision).
- Icon engine: out of scope this round (user decision).
- Spec location: `specs/` at repo root, deliberately outside the mkdocs
  `docs_dir` so internal design docs are not published to GitHub Pages.
