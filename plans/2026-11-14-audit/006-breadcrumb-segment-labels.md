# Plan 006: A breadcrumb can show words of its own over its raw path parts

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_breadcrumb.py tests/test_breadcrumb_labels.py fxgui/examples.py docs/how-to/widgets.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`FXBreadcrumb` shows a path as clickable segments. The text on each button
is the raw path part. Apps often want a different word on screen than the
value they navigate by: an internal key part such as `sq010` shown as
"Sequence 010", while signals, `path()` and the path editor keep `sq010`.
Today the only way is to override the private method `_add_segment`, as
Pascal (the main consumer) does. Pascal's override recomputes every label
once per segment, and any change to `_add_segment` breaks it silently.
This plan adds a public, documented way to label segments: a method to
override, `segment_labels(path)`, and a matching constructor argument.

## Current state

Files:

- `fxgui/fxwidgets/_breadcrumb.py` — the widget. `FXBreadcrumb` starts at
  line 194; `__init__` at 246–341; `_rebuild_breadcrumb` at 547–563;
  `_add_segment` at 565–592.
- `tests/test_breadcrumb_history.py` — the pattern for the new tests
  (`_crumb` and `_buttons` helpers at lines 16–32).
- `fxgui/examples.py` — the gallery; the breadcrumb is built at lines
  233–234 and placed with `_section("FXBreadcrumb", breadcrumb)` at line 261.
  `_section(title, *items)` (line 56) takes several widgets.
- `docs/how-to/widgets.md` — "## Breadcrumbs" section, lines 157–197.

`fxgui/fxwidgets/_breadcrumb.py:246-254` (signature today; no `*`):

```python
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        separator: str = "/",
        home_icon: str = "house",
        show_navigation: bool = False,
        path_separator: str = "/",
        home_path: Optional[List[str]] = None,
        tab_stops: bool = True,
    ):
```

`fxgui/fxwidgets/_breadcrumb.py:547-592`:

```python
    def _rebuild_breadcrumb(self) -> None:
        """Rebuild the segments for the current path."""
        while self._layout.count() > 1:  # Keep stretch
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._path:
            return

        for i, segment in enumerate(self._path):
            if i > 0:
                self._add_separator()

            is_last = i == len(self._path) - 1
            is_home = i == 0
            self._add_segment(segment, i, is_home, is_last)

    def _add_segment(
        self, text: str, index: int, is_home: bool, is_last: bool
    ) -> None:
        """Add a segment button; the last one is where the path already is."""
        button = _Segment(self, current=is_last)
        ...
        if is_home and self._home_icon:
            fxicons.set_icon(button, self._home_icon)
            button.setToolTip(text)
        else:
            button.setText(text)
        ...
```

`_add_segment` uses `text` only for the button text or the home tooltip;
navigation uses `index`, and `navigate_to`, `set_path`, `path()`,
`enter_edit_mode` (line 417, joins `self._path`) and every signal work on
`self._path`, the raw parts. So labels passed as `text` change only what is
drawn.

Pascal's workaround (read-only reference,
`git -C C:\Users\ValentinBeaumont\Documents\GitHub\ls-pascal show origin/main:src/ls_pascal/apps/views/breadcrumb.py`,
lines 39–48):

```python
    def _add_segment(
        self, text: str, index: int, is_home: bool, is_last: bool
    ) -> None:
        """Draw segment `index` in its words; the path keeps the key's parts."""
        try:
            key = StudioKey(tuple(self.path()))
            words = key_words(key, has_episodes=self._has_episodes)
        except (ValueError, NotFoundError):
            words = self.path()
        super()._add_segment(words[index], index, is_home, is_last)
```

No existing test covers `_add_segment`.

Conventions: Google-style docstrings (Args/Returns), type annotations, Qt
only through `qtpy`, public names in `__all__` (the class is already
exported; a method needs nothing), comments explain why in one line.

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| New tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_breadcrumb_labels.py` | all pass |
| Breadcrumb tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_breadcrumb_history.py tests/test_breadcrumb_colors.py tests/test_breadcrumb_hover.py` | all pass |
| Gallery test | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_gallery.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_breadcrumb.py`
- `tests/test_breadcrumb_labels.py` (create)
- `fxgui/examples.py` — the breadcrumb lines in the inputs page only.
- `docs/how-to/widgets.md` — the "Breadcrumbs" section only.

**Out of scope** (do NOT touch):

- The signature of `_add_segment(text, index, is_home, is_last)`: Pascal
  still overrides it until it moves to the new API. Keep it, and keep it
  called once per segment with the label as `text`.
- Labels in the path editor, `path()`, `home_path()` or any signal: these
  stay raw parts by design.
- `CHANGELOG.md`, any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch:
  `feat/breadcrumb-segment-labels`. (No `.gitmodules`: no submodule step.)
- Commit style, e.g. `[FEAT] FXBreadcrumb: segment_labels shows words over the raw path`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: Add the constructor argument and the method

In `fxgui/fxwidgets/_breadcrumb.py`:

1. Add `Callable` to the `from typing import ...` line.
2. Append a keyword-only parameter at the end of `__init__`:
   `*, segment_labels: Optional[Callable[[List[str]], List[str]]] = None`
   (put `*,` after `tab_stops: bool = True,`). Store it:
   `self._segment_labels = segment_labels`. Every existing positional call
   keeps working.
3. Document it in the class docstring `Args:` after `tab_stops`:
   "segment_labels: Turns the path's parts into the words shown on the
   segments, one per part. The path, its editor and the signals keep the
   parts. Defaults to showing the parts."
4. Add a public method after `path()`:

```python
    def segment_labels(self, path: List[str]) -> List[str]:
        """Return the words shown on the segments of `path`, one per part.

        Override it, or pass `segment_labels` to the constructor, to show
        words of your own; the path, its editor and the signals keep the
        parts.

        Args:
            path: The path's parts.

        Returns:
            One label per part. The default is the parts themselves.
        """
        if self._segment_labels is not None:
            return list(self._segment_labels(list(path)))
        return list(path)
```

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -c "import inspect; from fxgui.fxwidgets import FXBreadcrumb as B; print(inspect.signature(B.__init__).parameters['segment_labels'].kind)"`
→ `KEYWORD_ONLY`.

### Step 2: Feed the labels to the segments, once per rebuild

In `_rebuild_breadcrumb`, after the `if not self._path: return` guard:

```python
        labels = self.segment_labels(self._path)
        # A wrong count would shift words onto the wrong segments.
        if len(labels) != len(self._path):
            labels = list(self._path)
```

and in the loop call `self._add_segment(labels[i], i, is_home, is_last)`
instead of passing `segment`. Exceptions raised by `segment_labels` (or the
callable) propagate: the caller owns its own fallback, as Pascal's
`try/except` does today. Do not catch them.

Update the `Examples:` block of the class docstring with one line:
`>>> FXBreadcrumb(segment_labels=lambda parts: [p.upper() for p in parts])`.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_breadcrumb_history.py tests/test_breadcrumb_colors.py tests/test_breadcrumb_hover.py`
→ all pass (no behaviour change without labels).

### Step 3: Write the tests

Create `tests/test_breadcrumb_labels.py` (cases in "Test plan").

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_breadcrumb_labels.py`
→ 7 passed.

### Step 4: Gallery

In `fxgui/examples.py`, after line 234 (`breadcrumb.set_path(...)`), build
a second breadcrumb that shows words:

```python
    labelled = fxwidgets.FXBreadcrumb(
        home_icon="",
        segment_labels=lambda parts: [
            {"seq010": "Sequence 010", "sh0010": "Shot 0010"}.get(p, p)
            for p in parts
        ],
    )
    labelled.set_path(["Projects", "pipeline", "seq010", "sh0010"])
```

and change line 261 to `_section("FXBreadcrumb", breadcrumb, labelled)`.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_gallery.py`
→ all pass.

### Step 5: Docs

In `docs/how-to/widgets.md`, at the end of the "## Breadcrumbs" section
(after the paragraph ending "the strip disappears.", before
"## Your Own Item-Data Roles"), add a short subsection: a breadcrumb can
show words of its own; pass `segment_labels=` (a function from the parts
to one word per part) or override `segment_labels(self, path)` in a
subclass. `path()`, the editor and every signal keep the parts. A list of
the wrong length shows the parts. Include one code block, e.g.:

```python
crumb = FXBreadcrumb(
    home_icon="",
    segment_labels=lambda parts: [p.replace("sq", "Sequence ") for p in parts],
)
crumb.set_path(["pilot", "sq010"])  # shows "pilot / Sequence 010"
```

**Verify**: `grep -n "segment_labels" docs/how-to/widgets.md` → at least 2
matches. You add no links, so the strict docs build cannot break; zensical
is not installed in the venv at planning time and you must not install it.
Say in your report that the docs build was not run.

### Step 6: Whole suite and lint

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8`
→ `3185 passed, 6 skipped` (3178 + 7), 0 failed.
the Lint command from the table → `All checks passed!`

## Test plan

New file `tests/test_breadcrumb_labels.py`. Copy the `_crumb` / `_buttons`
helper shape from `tests/test_breadcrumb_history.py:16-32` (build, `qtbot.addWidget`,
resize 500×32, `set_path`, show, `waitExposed`), passing constructor kwargs
through. Use `PATH = ["Projects", "MyShow", "Assets", "Hero"]` and a label
function `UPPER = lambda parts: [p.upper() for p in parts]`. Build with
`home_icon=""` so the first segment shows text.

1. `test_the_segments_show_the_labels` — `[b.text() for b in _buttons(crumb)]`
   equals `["PROJECTS", "MYSHOW", "ASSETS", "HERO"]`.
2. `test_the_path_keeps_the_raw_parts` — `crumb.path() == PATH`.
3. `test_a_segment_click_says_the_raw_parts` — collect
   `segment_clicked`; `QTest.mouseClick(_buttons(crumb)[2], Qt.LeftButton)`
   (index 2, not 0: the first segment is the home button) → the signal got
   `(2, PATH[:3])`.
4. `test_the_editor_shows_the_raw_path` — `crumb.enter_edit_mode()`;
   `crumb._line_edit.text() == "Projects/MyShow/Assets/Hero"`; then
   `crumb.exit_edit_mode()`.
5. `test_labels_of_the_wrong_length_fall_back_to_the_parts` —
   `segment_labels=lambda parts: ["only one"]` → button texts equal `PATH`.
6. `test_a_subclass_names_its_own_labels` — a subclass overriding
   `segment_labels(self, path)` to return `[f"<{p}>" for p in path]` →
   texts are `["<Projects>", ...]`; count calls in the override and assert
   one call per `set_path` (the old Pascal way called per segment).
7. `test_the_home_icon_tooltip_is_the_label` — default `home_icon` ("house")
   with `UPPER` → `_buttons(crumb)[0].toolTip() == "PROJECTS"` and its
   `text() == ""`.

## Done criteria

- [ ] `pytest -q tests/test_breadcrumb_labels.py` → 7 passed.
- [ ] Whole suite `3185 passed, 6 skipped`, 0 failed.
- [ ] The Lint command from the table passes.
- [ ] `grep -n "def _add_segment" fxgui/fxwidgets/_breadcrumb.py` shows the
      unchanged signature `(self, text: str, index: int, is_home: bool, is_last: bool)`.
- [ ] `git status` shows only the four in-scope files.
- [ ] `plans/2026-11-14-audit/README.md` status row updated.

## STOP conditions

- `_rebuild_breadcrumb` or `_add_segment` no longer look like the excerpts
  (drift).
- Any of the existing breadcrumb tests fails after Step 2.
- Something other than `_add_segment` reads a segment button's `text()` to
  navigate (check with `grep -n "\.text()" fxgui/fxwidgets/_breadcrumb.py`;
  today only `_Segment.paintEvent` reads it, to draw). If navigation or the
  editor reads button text, labels would leak into the path: stop.
- `tests/test_gallery.py` demands something new for the second breadcrumb.

## Maintenance notes

- Public behaviour: new method `FXBreadcrumb.segment_labels(path)` and new
  keyword-only argument `segment_labels=`. Without them, nothing changes.
- The wrong-length fallback is silent on purpose (a crumb must always
  draw); exceptions propagate so a real bug is not hidden.
- Reviewer: check labels never reach `self._path`, the editor or a signal.
- `_add_segment` stays private and keeps its signature; once Pascal has
  moved, it may be simplified.
- Pascal: `src/ls_pascal/apps/views/breadcrumb.py` can delete its
  `_add_segment` override and override `segment_labels(self, path)` instead,
  keeping its `try/except (ValueError, NotFoundError)` fallback to `path`.
