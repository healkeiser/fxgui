# Plan 023: fxgui offers the empty-state prompt, the scroll cut shadow, text inks and a tab-order helper Pascal built

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. The lead maintains `plans/2026-11-14-audit/README.md`.
>
> **Drift check (run first)**: `git diff --stat b283eb13..HEAD -- fxgui/fxstyle.py fxgui/fxutils.py fxgui/fxwidgets/__init__.py fxgui/fxwidgets/_labels.py fxgui/examples.py docs/how-to/widgets.md docs/how-to/styling.md`
> Other plans of this audit may have landed in `fxstyle.py`, `fxutils.py`, `examples.py` and the docs
> pages; that is expected. Only the excerpts below must still match. A mismatch in them is a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (additions only; no existing behaviour changes)
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Pascal, fxgui's main consumer, built four small generic pieces on top of fxgui. None of them
knows anything about Pascal's domain:

- an empty-state prompt (8 users);
- a shadow drawn where a scroll area cuts its content off (3 users);
- `ink(widget, token)`, which writes a widget's text in one theme colour through a stylesheet
  property (about 60 call sites);
- `set_tab_order(widgets)`, which chains a tab order through focus proxies (3 users).

The owner asked that any widget from Pascal that deserves to be in fxgui moves there. These four
follow fxgui's theming contract already (pull model: looks in QSS, colours read at paint). Moving them
means every fxgui consumer gets them, and Pascal can delete its copies. Pascal's own change is out of
scope here.

Pieces deliberately NOT moved: Pascal's media player (`apps/widgets/player.py`) and node graph
(`apps/widgets/graph/`) import Pascal's domain (channels, frame rates, preferences, the pipeline API);
they would need a redesign, not a move.

## Current state

Pascal's code, to port (read-only reference checkout `C:\Users\ValentinBeaumont\Documents\GitHub\ls-pascal`;
read with `git -C C:\Users\ValentinBeaumont\Documents\GitHub\ls-pascal show origin/main:<path>`, its local
main is stale). Copy the logic, then adapt names, docstrings and imports to fxgui's conventions.

`src/ls_pascal/apps/widgets/empty_state.py` (68 lines):

```python
ICON_PIXELS = 40

class EmptyState(QWidget):
    """An icon, the action to take, and what it brings.

    Args:
        action: What the user does next, e.g. "Pick a task".
        detail: What doing it brings; empty for no second line.
    """

    def __init__(self, icon: str, action: str, detail: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon = FXIconLabel(size=ICON_PIXELS)
        self.action = QLabel()
        font = self.action.font()
        font.setBold(True)
        self.action.setFont(font)
        ink(self.action, "text")
        self.detail = QLabel()
        ink(self.detail, "text_muted")
        stack = column(GAP, parent=self)          # a QVBoxLayout with spacing GAP
        stack.setContentsMargins(GAP, GAP, GAP, GAP)
        stack.addStretch(1)
        stack.addWidget(self.icon)
        for label in (self.action, self.detail):
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stack.addWidget(label)
        stack.addStretch(1)
        self.set_prompt(icon, action, detail)

    def set_prompt(self, icon: str, action: str, detail: str = "") -> None:
        """Say something else: another icon, action and detail."""
        # A shut pane (the Publisher's, before a task) still reads its ask.
        fxicons.set_icon(self.icon, icon, color="text_muted", inks={"disabled": "text_muted"})
        self.action.setText(action)
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))

    def prompt(self) -> tuple[str, str]:
        """Return the action and the detail shown."""
        return self.action.text(), self.detail.text()
```

`src/ls_pascal/apps/widgets/cut_shadow.py` (62 lines): a `QWidget` child of a `QScrollArea`,
`WA_TransparentForMouseEvents`, 10 px tall, placed over the bottom of the viewport geometry; it
follows `verticalScrollBar().rangeChanged/valueChanged` and the viewport's Resize event (an event
filter, because "the area's own resize arrives before it lays out its viewport"); it hides when
`bar.value() >= bar.maximum()`; its `paintEvent` fills a vertical gradient from the theme's `shadow`
colour with alpha 0 to the same colour with alpha doubled (capped at 255) — "the theme's alpha suits a
blurred halo; a flat fade needs twice it" — then a 1 px line in `colors.border` at the bottom. It
connects `fxstyle.theme_changed` to `self.update` (allowed by fxgui's contract only for real side
effects; here the paint already reads `fxstyle.colors()` each time, so drop that connection: a theme
switch repaints the widget anyway — verify with the test in step 2).

`src/ls_pascal/apps/widgets/text.py`, the `ink` part:

```python
INK_PROPERTY = "lsInk"
_LEVELS = ("debug", "info", "success", "warning", "error")
INKS = ("text", "text_muted", "text_disabled", "accent_primary",
        *(f"feedback_{level}_foreground" for level in _LEVELS))

fxstyle.register_widget_style("".join(
    f'QWidget[{INK_PROPERTY}="{token}"] {{ color: @{token}; }}\n'
    f'QLabel[{INK_PROPERTY}="{token}"] {{ background-color: transparent; }}\n'
    for token in INKS))

def ink(widget: QWidget, token: str | None) -> None:
    """Write `widget`'s text in the theme colour `token`; `None` stops it.

    Raises:
        ValueError: If `token` is not one of `INKS`.
    """
    if token is not None and token not in INKS:
        raise ValueError(f"no ink {token!r}: one of {INKS}")
    widget.setProperty(INK_PROPERTY, token or "")
    fxutils.repolish(widget)
```

(The module docstring says: "A label goes transparent too, since a label with a rule of its own
otherwise takes the sheet's `surface` fill.")

`src/ls_pascal/apps/widgets/focus.py`:

```python
def set_tab_order(widgets: Sequence[QWidget]) -> None:
    """Chain `widgets` into exactly this tab order; `Shift+Tab` reverses it."""
    # Each one's proxy: `setTabOrder` moves nothing given a NoFocus bar.
    stops = [_proxied(widget) for widget in widgets]
    for earlier, later in zip(stops, stops[1:], strict=False):
        QWidget.setTabOrder(earlier, later)

def _proxied(widget: QWidget) -> QWidget:
    """Return what takes focus for `widget`, following its focus proxies."""
    proxy = rehome(widget.focusProxy())
    while proxy is not None:
        widget, proxy = proxy, rehome(proxy.focusProxy())
    return widget
```

(`zip(..., strict=False)` needs Python 3.10; fxgui supports 3.9: use plain `zip`.)

fxgui, where things go and the pattern to match:

- `fxgui/fxstyle.py` has the `mark_as_*` family (`mark_as_title` ~769, `mark_as_frame` ~802,
  `mark_as_thin_scroll` ~830, `mark_as_nav` ~848): a dynamic property plus `fxutils.repolish`, with
  rules in `qss/style.qss` or registered. `ink` belongs there as `fxstyle.ink(widget, token)`; read
  `mark_as_frame` and copy its shape, docstring style and `__all__` registration (find `__all__` near
  line ~150).
- `fxgui/fxutils.py` has `repolish` (~226) and `rehome` (~539). `set_tab_order` goes in `fxutils`,
  added to its `__all__`.
- Widgets: a new private module `fxgui/fxwidgets/_empty_state.py` holding `FXEmptyState` and
  `FXScrollShadow`, exported from `fxgui/fxwidgets/__init__.py` (imports ~line 74-87, `__all__` ~89+,
  kept sorted as it is). `FXIconLabel` is in `fxgui/fxwidgets/_labels.py` (~148).
- Spacing: use `fxstyle.PANE_GAP` or the gap constant the neighbouring widgets use (grep `PANE_GAP`
  in `fxgui/fxwidgets/_tag_input.py`); do not invent a number.
- Gallery: `fxgui/examples.py` has `_page(*sections)` (~86) and `_section("<ClassName>", widget, ...)`
  calls (e.g. `_section("FXIconLabel", _row(*icons))` ~364). `tests/test_gallery.py` fails unless every
  public widget has a section titled with its class name.
- Docs: `docs/how-to/widgets.md` has a table of widgets/helpers and sections; `docs/how-to/styling.md`
  documents `mark_as_*`. Add each new name where its siblings are documented.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| One test file | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_empty_state.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | no failures (3178 passed at planning time, plus new tests and those of plans landed since) |
| Lint | copy the ruff command from `.github/workflows/tests.yml` exactly | exit 0 |

Run every command from the worktree root (the shared venv's editable install points at another
checkout; the current directory makes yours win). Never run tests on the real Qt platform.

## Scope

**In scope**: `fxgui/fxwidgets/_empty_state.py` (create), `fxgui/fxwidgets/__init__.py`,
`fxgui/fxstyle.py` (only the new `ink` and its rules/`__all__`), `fxgui/fxutils.py` (only
`set_tab_order` and `__all__`), `fxgui/examples.py`, `docs/how-to/widgets.md`,
`docs/how-to/styling.md`, `tests/test_empty_state.py` (create), `tests/test_ink.py` (create),
`tests/test_tab_order.py` (create).

**Out of scope**: anything in ls-pascal; `stepped()`, `and_list()` and Pascal's `layout.py` helpers
(not moved); any change to existing widgets.

## Git workflow

Branch as given by the operator; commits `[FEAT] fxstyle.ink: ...`, `[FEAT] fxutils.set_tab_order: ...`,
`[FEAT] FXEmptyState and FXScrollShadow: ...`, each ending with the operator's Co-Authored-By line.
Do not push.

## Steps

### Step 1: `fxstyle.ink(widget, token)`

Add `INK_PROPERTY = "fxInk"` and `INKS` = `("text", "text_muted", "text_strong", "text_disabled",
"accent_primary", *feedback_<level>_foreground for debug, info, success, warning, error)`. Register
the rules exactly as Pascal does (one `color` rule per token on `QWidget[fxInk="<token>"]`, and
`background-color: transparent` for `QLabel[fxInk="<token>"]`), with `fxstyle.register_widget_style`
at module level (check that fxstyle may call its own `register_widget_style` at import; if the
function needs state built later, put the rules in `qss/style.qss` instead, generated by hand for
those 10 tokens). `ink(widget, None)` clears the property. An unknown token raises `ValueError`
naming the allowed ones. Add `ink` to `__all__`.

**Verify**: `tests/test_ink.py` — a label inked `text_muted` in a themed root (pattern: the
`themed_window` / `register_themed_root` usage in `tests/test_tips.py`) draws its glyphs in
`colors().text_muted` after `apply_theme("dark")` and again after `apply_theme("light")` (read the
label's palette `WindowText` after `ensurePolished()`, or a pixel; pick the one existing tests use);
`ink(label, None)` returns to the default ink; a bad token raises `ValueError`; an inked label has no
own fill (its background pixel equals the parent's). → all pass.

### Step 2: `FXEmptyState` and `FXScrollShadow`

Create `fxgui/fxwidgets/_empty_state.py`: module docstring, `__author__`/`__email__` metadata as other
modules have (copy from `_labels.py`), `FXEmptyState(icon, action, detail="", parent=None)` with
`set_prompt(icon, action, detail="")` and `prompt() -> Tuple[str, str]`, using `fxstyle.ink` and
`FXIconLabel`; and `FXScrollShadow(area: QScrollArea)` as described in "Current state", without the
`theme_changed` connection. Public attributes `icon`, `action`, `detail` stay public (Pascal reads
them). Export both from `fxgui/fxwidgets/__init__.py`.

**Verify**: `tests/test_empty_state.py`:
- the prompt shows icon, bold action, muted detail; an empty detail hides its label; `set_prompt`
  replaces all three; `prompt()` returns the pair;
- a disabled empty state still draws the icon in `text_muted` (the `inks={"disabled": ...}` reason);
- `FXScrollShadow`: on an area whose content is taller than the viewport it is visible and sits on
  the viewport's bottom 10 px; scrolled to the end it hides; with content shorter than the viewport it
  hides; after resizing the area it follows the viewport; its bottom row pixel is `colors().border`
  and, after `apply_theme("light")`, the light theme's border (proves no signal is needed);
→ all pass.

### Step 3: `fxutils.set_tab_order(widgets)`

Port it with plain `zip`, `rehome` as Pascal uses it, a Google docstring with an example, `__all__`.

**Verify**: `tests/test_tab_order.py` — three line edits in a shown window chained C, A, B: focus on C
then `focusNextChild()` lands on A, then B; a widget whose focus proxy is a child edit chains through
the proxy. Use `QWidget.nextInFocusChain()` checks if focus moves are unreliable offscreen. → pass.

### Step 4: gallery and docs

Add sections titled `FXEmptyState` and `FXScrollShadow` to `fxgui/examples.py` in the page where
`FXIconLabel` lives (an empty state with icon "inbox" or another icon that exists in the default
library — check with `fxicons.get_icon` in a probe; a short scroll area with many labels and a
shadow). Document `FXEmptyState`, `FXScrollShadow`, `fxstyle.ink` and `fxutils.set_tab_order` next to
their siblings in the two docs pages.

**Verify**: `python -m pytest -q tests/test_gallery.py tests/test_fxwidgets_exports.py tests/test_docstring_examples.py` → all pass;
`grep -n "FXEmptyState\|FXScrollShadow" docs/how-to/widgets.md` → at least one hit each;
`grep -n "ink(" docs/how-to/styling.md` → at least one hit.

### Step 5: whole suite and lint

**Verify**: whole-suite command → no failures; lint command → exit 0.

## Test plan

New files `tests/test_empty_state.py`, `tests/test_ink.py`, `tests/test_tab_order.py`, with the cases
listed in steps 1-3. Pattern: `tests/test_tips.py` for themed roots and pixel/ink reading,
`tests/test_keyboard_widgets.py` for focus.

## Done criteria

- [ ] `from fxgui.fxwidgets import FXEmptyState, FXScrollShadow` works; `fxstyle.ink` and
      `fxutils.set_tab_order` are in their modules' `__all__`
- [ ] the three new test files pass; the whole suite has no failures; lint exits 0
- [ ] `tests/test_gallery.py` passes with the two new sections
- [ ] `git status` shows only in-scope files changed

## STOP conditions

- `register_widget_style` cannot be called from inside `fxstyle.py` at import and putting the rules in
  `qss/style.qss` would change an existing rule.
- A Pascal excerpt above does not match `origin/main` of ls-pascal (it moved on): port the current one
  only if its public shape (constructor arguments, `set_prompt`, `prompt`, attributes) is unchanged;
  otherwise stop.
- The gallery test needs anything beyond a titled section.

## Maintenance notes

- `INKS` is a closed list on purpose: each token is one QSS rule. A new ink token is one line there.
- `FXScrollShadow` reads the theme's `shadow` and `border` at paint; never cache them.
- Pascal: once this ships, Pascal can replace `apps/widgets/empty_state.py`, `cut_shadow.py`,
  `text.ink` and `focus.set_tab_order` with `FXEmptyState`, `FXScrollShadow`, `fxstyle.ink` (note the
  property is `fxInk`, not `lsInk`: any Pascal rule that selects `[lsInk=...]` must follow) and
  `fxutils.set_tab_order`.
