# Plan 009: The thumbnail delegate draws a neutral tag, keeps a label's case, and keeps pale marks readable

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_delegates.py fxgui/fxwidgets/_roles.py tests/test_delegate_status_label.py fxgui/examples.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (plan 014 also edits `fxgui/fxwidgets/_delegates.py`,
  in a different function, `_read_thumbnail`; whichever lands second rebases)
- **Category**: direction
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`FXThumbnailDelegate` paints tree rows. At a row's right edge it can show a
**status label**: a small coloured mark (a dot, or an icon) followed by
muted words, like "● WIP". It was built for statuses, and three things make
it awkward for anything else:

1. It shows only when a colour is given. A tag with no status meaning
   (Pascal's "Library") must borrow a colour, and Pascal borrows
   `accent_secondary`, which looks like its "WIP" status colour.
2. Its words are always UPPERCASED, so "Library" or "v012" cannot keep
   their case.
3. A pale colour from a production tracker (Kitsu's near-white "todo")
   vanishes on a light row. Pascal works around it with its own `is_pale()`.

After this plan: a label with text and **no colour role at all** draws as a
neutral tag (thin outline, muted words, no coloured mark); a new
`STATUS_LABEL_UPPERCASE_ROLE` set to `False` keeps the case; and the mark's
colour is stepped at paint time until it reads on the row's ground.

## Current state

Files:

- `fxgui/fxwidgets/_roles.py` — every item-data role fxgui claims, in one
  `range` (lines 6–24). The comment says a new role goes before `SORT`.
- `fxgui/fxwidgets/_delegates.py` — `FXThumbnailDelegate`. Relevant parts
  below.
- `tests/test_delegate_layout.py` — the pattern: `_tree_with_item` (line
  33), `_option_for` (line 115), `_indicator_rects` (line 173),
  `_indicator_hits` (line 212); colours `PILL_COLOR = QColor("#ff00ff")`,
  `DOT_COLOR = QColor("#00ff00")` (lines 22–23).
- `tests/test_icon_fallback_and_roles.py:120-129` — asserts
  `FIRST_FREE_ROLE == max(every *_ROLE on the class, SORT_ROLE) + 1`; a role
  added to `_roles.py` must also get a class attribute ending in `_ROLE`.
- `fxgui/examples.py:436-468` — `_thumbnail_tree()`, the gallery's
  `FXThumbnailDelegate` section.

`fxgui/fxwidgets/_roles.py:6-24`:

```python
# One range, so no two roles can share a number and FIRST_FREE is always
# the first one past them. A role added here goes before SORT.
(
    THUMBNAIL_VISIBLE,
    ...
    PICKER_UNAVAILABLE,
    STATUS_LABEL_ICON,
    SORT,
    FIRST_FREE,
) = range(int(Qt.UserRole) + 1, int(Qt.UserRole) + 16)
```

`fxgui/fxwidgets/_delegates.py:440-449`:

```python
class _Indicators(NamedTuple):
    """What a row's status pill and dot take, and the colours they wear."""

    label_width: int
    dot_width: int
    footprint: int
    label_color: QColor
    dot_color: QColor
    label_text: str
    label_icon: str = ""
```

`fxgui/fxwidgets/_delegates.py:507-510` (class attributes):

```python
    STATUS_LABEL_COLOR_ROLE = _roles.STATUS_LABEL_COLOR
    STATUS_LABEL_TEXT_ROLE = _roles.STATUS_LABEL_TEXT
    # An icon name drawn in the label's colour in place of its dot.
    STATUS_LABEL_ICON_ROLE = _roles.STATUS_LABEL_ICON
```

Constants (`_delegates.py:550-559`): `_INDICATOR_BAND_HEIGHT = 14`,
`_INDICATOR_RIGHT_MARGIN = 6`, `_LABEL_PADDING = 4`, `_LABEL_MARK = 8`,
`_LABEL_ICON = 14`, `_LABEL_GAP = 5`.

`fxgui/fxwidgets/_delegates.py:905-974` (measure; the only caller of
`_status_label_width` is here, line 942):

```python
    def _status_label_width(
        self, label_text: str, option: QStyleOptionViewItem, icon: str = ""
    ) -> int:
        """Return the width of the status mark and its words."""
        return (
            self._mark_size(icon)
            + self._LABEL_GAP
            + QFontMetrics(self._label_font(option)).horizontalAdvance(
                label_text.upper()
            )
        )

    def _indicator_metrics(self, index, option, fit=False) -> _Indicators:
        ...
        label_color = fxstyle.qcolor(index.data(self.STATUS_LABEL_COLOR_ROLE))
        label_text = index.data(self.STATUS_LABEL_TEXT_ROLE)
        label_icon = str(index.data(self.STATUS_LABEL_ICON_ROLE) or "")
        dot_color = fxstyle.qcolor(index.data(self.STATUS_DOT_COLOR_ROLE))

        show_label = bool(
            self.show_status_label
            and index.data(self.STATUS_LABEL_VISIBLE_ROLE) is not False
            and label_text
            and label_color.isValid()
        )
        label_width = (
            self._status_label_width(str(label_text), option, label_icon)
            if show_label
            else 0
        )
        ...
        # Painting only: a measured width must never depend on the width.
        if fit and label_width and self._title_squeezed(
            index, option, label_width, dot_width
        ):
            # The title wins: the label keeps its coloured mark alone.
            label_width, label_text = self._mark_size(label_icon), ""
        ...
        return _Indicators(label_width, dot_width, footprint, label_color,
                           dot_color, str(label_text or ""), label_icon)
```

`fxgui/fxwidgets/_delegates.py:1143-1190` (`_draw_status_label`, paint):
draws the mark (`_mark(icon, color.name())` for an icon, else a filled
ellipse of `color`), then the words in `fxstyle.colors().text_muted` with
`painter.drawText(words, Qt.AlignVCenter | Qt.AlignLeft, text.upper())`.

`fxgui/fxwidgets/_delegates.py:1436-1466` (`_draw_status_indicators`) calls
`self._indicator_metrics(index, option, fit=True)` and passes
`marks.label_color`, `marks.label_text`, `marks.label_icon` on.

The outlined pill to copy, `_draw_picker` (`_delegates.py:1881-1886`):

```python
        theme = fxstyle.colors()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(theme.border_light), 1))
        painter.setBrush(QBrush(QColor(theme.surface)))
        painter.drawRoundedRect(
            QRectF(rect), fxstyle.SMALL_RADIUS, fxstyle.SMALL_RADIUS)
```

The row's ground at paint (`_draw_row_fill`, `_delegates.py:1265-1272`): the
`selection` token when `option.state & QStyle.State_Selected`, else the
band from `self._custom_background(index)` (line 1231, a `QColor` or
`None`), else `option.palette.color(QPalette.Base)`.

`fxstyle.readable_ink(background, preferred=None, floor=4.5) -> str`
(`fxgui/fxstyle.py:902`): returns `preferred` if it reads on `background`
at `floor`:1, else the first colour stepped from it toward black or white
that does. `fxstyle.CONTROL_CONTRAST = 3.0` (`fxstyle.py:284`). It is
cached on colour names, so calling it in paint is cheap.

Facts measured during planning: an unthemed `QTreeWidget` in the test
setup has a white `Base`; `#ff00ff` (the tests' `PILL_COLOR`) reads at
3.14:1 on white, so it is **not** stepped and existing pixel tests keep
their colour; Kitsu-like `#f5f5f5` would be stepped. `accent_secondary` is
below 3:1 on `surface` in the dark, catppuccin_latte and solarized_light
themes (Pascal's library pill).

Conventions: Google-style docstrings, type annotations, Qt only through
`qtpy`, read `fxstyle.colors()` at paint time (never cache colours),
comments explain why in one line.

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| New tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_delegate_status_label.py` | all pass |
| Delegate tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_delegate_layout.py tests/test_delegate_fixes.py tests/test_status_icon.py tests/test_icon_fallback_and_roles.py tests/test_item_views.py tests/test_row_size.py tests/test_delegate_owned_rows.py` | all pass |
| Gallery | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_gallery.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen`, starts each test on
the dark theme and isolates settings. Never run tests on the real platform.
Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call. Set `FXGUI_SCREENSHOT_DIR` to a scratch folder
outside the repo if you want the tests' `_save` images; never commit them.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_roles.py`
- `fxgui/fxwidgets/_delegates.py` — `_Indicators`, the role attributes and
  class docstring, `_status_label_width`, `_indicator_metrics`,
  `_draw_status_label`, `_draw_status_indicators`, one new method
  `_mark_ink`.
- `tests/test_delegate_status_label.py` (create)
- `fxgui/examples.py` — `_thumbnail_tree()` only.

**Out of scope** (do NOT touch):

- The status **dot** (`_draw_status_dot`): no neutral dot, no stepping.
  Pascal leaves the dot unset; extend later if wanted.
- A colour role that is *set* but unusable (`"not a color"`, `""`, `42`):
  it still hides the label. `test_unusable_color_roles_hide_without_raising`
  (`tests/test_delegate_layout.py:1090`) pins that; keep it passing.
- `_draw_picker`, `_read_thumbnail` (plan 014), `CHANGELOG.md`, Pascal.
- `docs/moving-from-12.md:233`, which wrongly lists
  `STATUS_LABEL_ICON_ROLE` as gone: report it, do not fix it here.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch:
  `feat/neutral-label-pill`. (No `.gitmodules`: no submodule step.)
- Commit style, e.g. `[FEAT] FXThumbnailDelegate: a neutral tag, kept case, readable marks`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: Add the uppercase role

1. `fxgui/fxwidgets/_roles.py`: add `STATUS_LABEL_UPPERCASE,` after
   `STATUS_LABEL_ICON,` (before `SORT`), and change the range end from
   `+ 16` to `+ 17`.
2. `fxgui/fxwidgets/_delegates.py`, after `STATUS_LABEL_ICON_ROLE`:

```python
    # False keeps the label's words as given ("Library", "v012").
    STATUS_LABEL_UPPERCASE_ROLE = _roles.STATUS_LABEL_UPPERCASE
```

3. In the class docstring `Note:` role list, add
   `STATUS_LABEL_ICON_ROLE` (`str`, an icon name) next to the text role if
   missing, and `STATUS_LABEL_UPPERCASE_ROLE` (`bool`, default True) to the
   `bool` line.

`SORT` and `FIRST_FREE` move up by one. That is fine: consumers derive
their roles from `FIRST_FREE_ROLE` at run time.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_icon_fallback_and_roles.py tests/test_item_views.py`
→ all pass.

### Step 2: Measure a neutral label and a kept case

1. `_Indicators`: append `label_upper: bool = True` after `label_icon`
   (a default, so every positional construction still works; tests slice
   `[:3]`).
2. `_status_label_width(self, label_text, option, icon="", upper=True, neutral=False)`:
   - `words = label_text.upper() if upper else label_text`;
   - `advance = QFontMetrics(self._label_font(option)).horizontalAdvance(words)`;
   - coloured (not `neutral`): return `self._mark_size(icon) + self._LABEL_GAP + advance` (unchanged);
   - `neutral`: return `2 * self._LABEL_PADDING + advance`, plus
     `self._LABEL_ICON + self._LABEL_GAP` when `icon` is set.
   Update its docstring (Args for `upper`, `neutral`).
3. `_indicator_metrics`:
   - `colour_data = index.data(self.STATUS_LABEL_COLOR_ROLE)`;
     `label_color = fxstyle.qcolor(colour_data)`;
   - `neutral = colour_data is None` (no colour role at all; an unusable
     value is not neutral);
   - `upper = index.data(self.STATUS_LABEL_UPPERCASE_ROLE) is not False`;
   - `show_label` keeps every condition but replaces
     `and label_color.isValid()` with
     `and (label_color.isValid() or neutral)`;
   - pass `upper=upper, neutral=neutral` to `_status_label_width`;
   - the squeeze branch: for a neutral label, hide it
     (`label_width, label_text = 0, ""`), since it has no coloured mark to
     keep; a coloured one keeps its mark alone as today. Comment: one line
     saying why;
   - return `_Indicators(..., label_icon, upper)`.
   Update the docstring sentence "it has a usable colour (and text, for
   the pill)" to say a label with text and no colour role is a neutral tag.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_delegate_layout.py tests/test_status_icon.py tests/test_row_size.py`
→ all pass (in particular `test_unusable_color_roles_hide_without_raising`
and `test_the_label_keeps_only_its_mark_when_the_title_would_be_cut`).

### Step 3: Paint the neutral tag, the case, and a readable mark

1. Add a method next to `_draw_status_label`:

```python
    def _mark_ink(
        self, option: QStyleOptionViewItem, index: QModelIndex, color: QColor
    ) -> QColor:
        """Return `color` stepped until it reads on the row's ground.

        A tracker's near-white "todo" vanishes on a light row otherwise.
        """
        band = self._custom_background(index)
        if option.state & QStyle.State_Selected:
            ground = QColor(fxstyle.colors().selection)
        elif band is not None:
            ground = band
        else:
            ground = option.palette.color(QPalette.Base)
        return QColor(
            fxstyle.readable_ink(ground, color, fxstyle.CONTROL_CONTRAST))
```

2. `_draw_status_indicators`: when `marks.label_color.isValid()`, pass
   `self._mark_ink(option, index, marks.label_color)` instead of
   `marks.label_color`; pass `upper=marks.label_upper` as a new keyword.
3. `_draw_status_label(..., icon="", upper=True)`:
   - `words_text = text.upper() if upper else text`; draw `words_text`
     where it drew `text.upper()`;
   - when `not color.isValid()` (neutral), draw instead of the mark:
     a rounded rectangle `QRectF(label_x + 0.5, top + 0.5, label_width - 1, self._INDICATOR_BAND_HEIGHT - 1)`
     with pen `QPen(QColor(fxstyle.colors().border_light), 1)`,
     `Qt.NoBrush`, radius `fxstyle.SMALL_RADIUS` (the half-pixel inset
     keeps the 1 px line inside the measured width); then, from
     `x = label_x + self._LABEL_PADDING`, the icon if any via
     `_mark(icon, "text_muted")` in a `_LABEL_ICON` square centred in the
     band (then `x += self._LABEL_ICON + self._LABEL_GAP`), then the words
     in `text_muted` in `QRect(x, top, label_x + label_width - self._LABEL_PADDING - x, self._INDICATOR_BAND_HEIGHT)`;
     return. Keep the `if label_x < left_limit: return` guard first.
   - The coloured path is otherwise unchanged.

**Verify**: the "Delegate tests" command from the table → all pass.

### Step 4: Tests

Create `tests/test_delegate_status_label.py` (cases in "Test plan").

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_delegate_status_label.py`
→ 6 passed.

### Step 5: Gallery

In `fxgui/examples.py` `_thumbnail_tree()`, on each episode row (`top`,
after its `Qt.BackgroundRole` line) add a neutral, case-kept tag:

```python
        # No colour: a neutral tag, in its own case.
        top.setData(0, delegate.STATUS_LABEL_TEXT_ROLE, "Library")
        top.setData(0, delegate.STATUS_LABEL_UPPERCASE_ROLE, False)
```

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_gallery.py`
→ all pass.

### Step 6: Whole suite and lint

**Verify**: whole suite → `3184 passed, 6 skipped` (3178 + 6), 0 failed;
ruff → `All checks passed!`

## Test plan

New file `tests/test_delegate_status_label.py`. Copy the small helpers you
need from `tests/test_delegate_layout.py` (`_tree_with_item` shape,
`_option_for`) rather than importing from another test module. Build an
item with `STATUS_LABEL_TEXT_ROLE` set and `STATUS_LABEL_COLOR_ROLE` left
unset for "neutral" cases; no status dot.

1. `test_a_label_with_no_colour_role_is_a_neutral_tag` —
   `m = delegate._indicator_metrics(index, option)`: `m.label_width ==
   2 * delegate._LABEL_PADDING + QFontMetrics(delegate._label_font(option)).horizontalAdvance("READY")`,
   `not m.label_color.isValid()`, and
   `m.footprint == delegate._INDICATOR_RIGHT_MARGIN + m.label_width + 1`.
2. `test_the_neutral_tag_is_an_outline_with_no_coloured_mark` — grab
   `tree.viewport().grab().toImage()`; in the label rect (from
   `delegate._indicator_left(option.rect, m.label_width, 0)`, band top from
   `delegate._band_top`), the left edge column holds at least one pixel
   within 24 per channel of `fxstyle.colors().border_light`; and no pixel in
   the rect has HSL saturation above 60 (no coloured mark). Build the row
   with `thumbnail=False` so no picture shares the image.
3. `test_the_uppercase_role_false_keeps_the_case` — text `"v012"` with a
   colour `PILL_COLOR` and `STATUS_LABEL_UPPERCASE_ROLE = False`:
   `m.label_width == delegate._LABEL_MARK + delegate._LABEL_GAP + advance("v012")`
   and `m.label_upper is False`; with the role unset, `advance("V012")`.
4. `test_a_pale_mark_is_stepped_to_read_on_the_row` — call
   `delegate._mark_ink(option, index, QColor("#f5f5f5"))` with an option
   whose palette Base is white (an unthemed tree): the result's contrast
   with `#ffffff` is ≥ `fxstyle.CONTROL_CONTRAST`; and
   `_mark_ink(..., QColor("#ff00ff"))` returns `#ff00ff` unchanged (already
   reads). Set `Qt.BackgroundRole` to `"#000000"` on the item: a
   `#101010` mark is stepped lighter (contrast with black ≥ 3).
5. `test_a_squeezed_neutral_tag_hides_and_frees_its_room` — a long title
   (copy `LONG_TITLE` from `test_delegate_layout.py`), neutral label:
   `_indicator_metrics(index, option, fit=True)` gives `label_width == 0`
   and `footprint == 0`; without `fit`, `label_width > 0` (measure never
   depends on the width).
6. `test_an_unusable_colour_still_hides_the_label` — colour role `"not a color"`
   with text: `label_width == 0` (the neutral path needs the role unset).

## Done criteria

- [ ] `pytest -q tests/test_delegate_status_label.py` → 6 passed.
- [ ] The delegate test command in the table passes unchanged tests.
- [ ] Whole suite `3184 passed, 6 skipped`, 0 failed; ruff passes.
- [ ] `grep -n "STATUS_LABEL_UPPERCASE" fxgui/fxwidgets/_roles.py fxgui/fxwidgets/_delegates.py`
      → one hit in `_roles.py`, at least two in `_delegates.py`.
- [ ] `git status` shows only the in-scope files (no screenshots).
- [ ] `plans/2026-11-14-audit/README.md` status row updated.

## STOP conditions

- `_indicator_metrics`, `_draw_status_label` or `_roles.py` differ from the
  excerpts (drift), or plan 014 already rebased this file in a way that
  moves these functions — re-read and continue only if the excerpts still
  match.
- Any existing pixel test in `tests/test_delegate_layout.py` fails because
  its `#ff00ff` mark was stepped: the measured ground is no longer white or
  the floor changed; report the ground colour, do not loosen the test.
- An existing test sets label text without a colour role and expects
  nothing drawn: that is a documented contract; stop and report its name.
- `test_icon_fallback_and_roles.py` fails after Step 1 (the role table and
  the class attributes disagree).

## Maintenance notes

- Public behaviour changes: (a) a label with text and no colour role now
  draws a neutral outlined tag where it drew nothing; (b) a coloured mark
  that reads below 3:1 on its row is stepped toward black or white (defect
  fix); (c) new `STATUS_LABEL_UPPERCASE_ROLE`; `SORT_ROLE` and
  `FIRST_FREE_ROLE` move up by one, so a consumer that hard-coded their
  numbers must derive them from `FIRST_FREE_ROLE`.
- Reviewer: check measure and paint agree for the neutral tag (padding on
  both sides, the half-pixel outline inset), and that `_mark_ink` reads the
  same ground `_draw_row_fill` paints (selection, band, Base).
- Hover is ignored for the ground: a hovered row is a mix close to its
  ground, so the stepped mark still reads.
- Deferred: the status dot could take the same `_mark_ink`.
- Pascal: `src/ls_pascal/apps/views/tree.py` can delete `is_pale()` and its
  `text_muted` fallback (~lines 50–56 and ~197–201 on origin/main), and the
  "Library" pill can drop its `accent_secondary` colour role (~lines
  160–176) and set `STATUS_LABEL_UPPERCASE_ROLE` to `False`. Separately,
  Pascal's `apps/widgets/record_table.py:75` hard-codes
  `UserRole + 11`, which is fxgui's `PICKER_CHOICES_ROLE`; it should derive
  from `FIRST_FREE_ROLE` (only matters if that table ever uses the delegate).
