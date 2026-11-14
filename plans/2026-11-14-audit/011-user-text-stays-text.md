# Plan 011: Text a person typed or a tracker sent is shown as typed, never read as HTML

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_tag_input.py fxgui/fxwidgets/_avatar.py fxgui/fxwidgets/_notification_banner.py fxgui/fxwidgets/_tips.py tests/test_tag_input.py tests/test_avatar.py tests/test_notification_banner_actions.py tests/test_tips.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (plan 015 step 5 and plan 016 step 1 edit the same
  files at other lines; merge order does not matter)
- **Category**: security
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

Qt's `QLabel` and tooltips guess whether a string is HTML ("rich text")
when its format is `Qt.AutoText`: a string that looks like it has a tag is
rendered as HTML. Several fxgui widgets show text that comes from people or
from a production tracker (tag names, person names, banner messages). Such
text can contain `<`, so it renders wrong (`<b>x</b>` turns bold, `a < b`
loses text), and an `<img src=...>` makes Qt try to load that resource.
Pascal passes tracker names into `FXAvatar` and plain messages into
`FXNotificationBanner`, and today reaches into the banner's private
children (by object name) to force plain text, fix the wrapped height and
set action icons.

After this plan: a tag chip and an avatar tooltip always show their text as
typed; a banner can be asked for plain text with a public keyword, sizes
its wrapped message correctly, and an action can carry an icon; a status
tip with no title no longer starts with " - ".

## Current state

Probed at `b283eb13` (offscreen PySide6):

- `FXTagChip("<b>x</b>").label.textFormat()` → `TextFormat.AutoText` (renders bold).
- `Qt.mightBeRichText` is True for `<b>x</b>` and `a <img src='x'>`, False for
  `Tom &amp; Jerry`. So `html.escape(name)` as a tooltip would show the
  literal `&amp;` for a name with `&` — do NOT use `html.escape` for the avatar.
- `apply_tip(QLabel(), "", "body only")` → status tip `' - body only'`.
- A banner with a 6-line plain-text message, width 480: label height 82,
  `heightForWidth` 166 — the message is cut in half. With the default rich
  text the label is 196 for 168 needed (slack under the text).

### 1. Tag chip — `fxgui/fxwidgets/_tag_input.py`, lines 54–55

```python
        self.label = QLabel(text)
        layout.addWidget(self.label)
```

`Qt` is imported at line 7. Tests: `tests/test_tag_input.py` (pattern:
`test_tags_changed_emits_a_copy`, lines 12–19).

### 2. Avatar tooltip — `fxgui/fxwidgets/_avatar.py`, lines 85–89

```python
    def set_name(self, name: str) -> None:
        """Show `name`'s initials and colour, and use it as the tooltip."""
        self._name = name or ""
        self.setToolTip(self._name)
        self.update()
```

Imports today (lines 8–14): `from fxgui import fxicons, fxstyle`; no `apply_tip`.
Other widgets import it as `from fxgui.fxwidgets._tips import apply_tip`
(e.g. `_timeline_slider.py` line 32). `apply_tip(widget, title)` escapes the
title, builds the theme's rich tooltip (`<div><b>Anne Martin</b></div>`),
sets a plain status tip and, unless the caller set one, the accessible name.

The existing test that pins the raw tooltip, `tests/test_avatar.py` lines 96–104:

```python
def test_name_and_tooltip_follow_set_name(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    avatar = FXAvatar("Anne Martin", parent)
    assert avatar.name() == "Anne Martin"
    assert avatar.toolTip() == "Anne Martin"
    avatar.set_name("Bob Stone")
    assert avatar.initials() == "BS"
    assert avatar.toolTip() == "Bob Stone"
```

### 3. Banner — `fxgui/fxwidgets/_notification_banner.py`

Constructor signature, lines 174–189 (all positional-or-keyword today):

```python
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "",
        severity_type: Optional[int] = None,
        timeout: Optional[int] = None,
        actions: Optional[Mapping[str, Callable[[], None]]] = None,
        closable: bool = True,
        width: int = 320,
        logger: Optional[logging.Logger] = None,
        title: Optional[str] = None,
        icon: Optional[str] = None,
        margin: int = 16,
        top: Optional[int] = None,
        spacing: int = fxstyle.PANE_GAP,
    ):
```

Docstring Args (lines 118–135) says `message: The notification message, rich text.`

Message label, lines 246–253:

```python
        self._message_label = QLabel(message)
        self._message_label.setObjectName("fxBannerMessage")
        self._message_label.setTextFormat(Qt.RichText)
        self._message_label.setWordWrap(True)
        self._message_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        main_layout.addWidget(self._message_label)
```

End of `__init__`, lines 278–285:

```python
        self._update_icons()

        for label, callback in (actions or {}).items():
            self.add_action(label, callback)

        self.adjustSize()
        if parent:
            parent.installEventFilter(self)
```

`show()` calls `self.adjustSize()` at line 357, before `super().show()`.

`add_action`, lines 422–459 (signature and the part that matters):

```python
    def add_action(
        self,
        text: str,
        callback: Optional[Callable[[], None]] = None,
    ) -> QPushButton:
        ...
        button = QPushButton(text, self)
        button.setObjectName("fxBannerAction")
        # The first one leads; the rest step back.
        button.setProperty("primary", not self._action_buttons)
        ...
        self._refit()
        return button
```

`_refit`, lines 461–465:

```python
    def _refit(self) -> None:
        """Fit the banner to its content and move the ones stacked under it."""
        self.adjustSize()
        if not self.isHidden() and self.parent():
            self._reposition_notifications(self.parent())
```

`set_message` (lines 478–482) sets the label text then calls `_refit()`.
`fxicons` is imported (line 28); the close button uses
`fxicons.set_icon(self._close_button, "x", color="text_muted")` (line 332).
The banner is a `QFrame` with `StyledPanel`, so its `contentsRect()` excludes
the frame; layout margins are `(16, 12, 16, 12)` (line 214).

Tests: `tests/test_notification_banner_actions.py` — helper `_host(qtbot)`
(lines 24–30, an 800×600 shown QWidget) and
`test_a_longer_message_grows_the_banner_and_moves_the_next_down` (line 109)
are the pattern.

### 4. Status tip — `fxgui/fxwidgets/_tips.py`, line 489 in `apply_tip`

```python
    plain = f"{title} - {body}" if body else title
```

Tests: `tests/test_tips.py` lines 662–680
(`test_apply_tip_sets_markup_and_plain_status`,
`test_apply_tip_status_is_title_only_without_body`).

### Pascal (read-only reference)

`src/ls_pascal/apps/widgets/banner.py` on origin/main, lines ~56–68: finds
`QPushButton` children named `fxBannerAction` to `fxicons.set_icon` them,
finds the `QLabel` named `fxBannerMessage`, sets `PlainText`, then
`setFixedHeight(shown.heightForWidth(room))` with
`room = card.width() - margins.left() - margins.right()`.

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| This plan's tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_tag_input.py tests/test_avatar.py tests/test_tips.py tests/test_notification_banner_actions.py tests/test_notification_banner_defaults.py tests/test_notification_banner_dismiss.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
per test. Never run tests on the real platform (it moves the owner's mouse
pointer). Any ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call, or it overwrites the owner's real settings.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_tag_input.py` — `FXTagChip.__init__`, the label line only.
- `fxgui/fxwidgets/_avatar.py` — `set_name` and one import.
- `fxgui/fxwidgets/_notification_banner.py` — `__init__` (signature, docstring, label format, final fit), `show`, `add_action`, `_refit`.
- `fxgui/fxwidgets/_tips.py` — the `plain = ...` line in `apply_tip`.
- `tests/test_tag_input.py`, `tests/test_avatar.py`, `tests/test_tips.py`,
  `tests/test_notification_banner_actions.py` — new tests; the one avatar assertion change described in Step 2.

**Out of scope** (do NOT touch):

- The banner's default text format: it stays `Qt.RichText` (vendors may send
  markup). Plain text is opt-in.
- `FXStatusDot.set_feedback`'s `setToolTip(tooltip)` — plan 015 step 5 owns that widget.
- `FXStatusBar` message label — it already escapes the message.
- The chip's remove button tip — plan 015 step 5.
- `CHANGELOG.md`; any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch: `fix/user-text-stays-text`.
  (There is no `.gitmodules`, so no submodule step.)
- One commit per step. Style: `[FIX] ...` / `[FEAT] ...`, e.g.
  `[FIX] a tag chip shows its text as typed`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: A tag chip's label is plain text

After `self.label = QLabel(text)` add `self.label.setTextFormat(Qt.PlainText)`.
Add test 1 (Test plan).

**Verify**: `...python.exe -m pytest -q tests/test_tag_input.py` → all pass.

### Step 2: The avatar's tooltip goes through `apply_tip`

Add `from fxgui.fxwidgets._tips import apply_tip` under the `# Internal`
imports, and in `set_name` replace `self.setToolTip(self._name)` with
`apply_tip(self, self._name)`. `apply_tip` escapes the name (so `&` and `<`
read as typed) and makes the name the accessible name too. An empty name gives an empty tooltip.

Update `test_name_and_tooltip_follow_set_name`: replace the two
`avatar.toolTip() == "..."` asserts with `"Anne Martin" in avatar.toolTip()`
and `"Bob Stone" in avatar.toolTip()` (the tooltip is now the theme's rich
tip, `<div><b>Anne Martin</b></div>`). Add test 2.

**Verify**: `...python.exe -m pytest -q tests/test_avatar.py` → all pass.

### Step 3: The status tip has no leading dash

In `apply_tip`, replace line 489 with:

```python
    plain = " - ".join(part for part in (title, body) if part)
```

Add test 3.

**Verify**: `...python.exe -m pytest -q tests/test_tips.py` → all pass.

### Step 4: Banner: a `text_format` keyword and a message fitted by `heightForWidth`

1. Make the new argument keyword-only at the end of the signature:
   `spacing: int = fxstyle.PANE_GAP,` then `*,` then
   `text_format: Qt.TextFormat = Qt.RichText,`. Existing positional calls keep working.
2. Docstring: change `message:` to `The notification message, read in \`text_format\`.`
   and add `text_format: How the message is read: \`Qt.RichText\` (the default) or \`Qt.PlainText\`, which shows \`<\` and newlines as typed. Text from people or a tracker wants plain.`
3. Replace `self._message_label.setTextFormat(Qt.RichText)` with
   `self._message_label.setTextFormat(text_format)`.
4. Fit the label to its wrapped height in `_refit`, before `adjustSize()`:

```python
    def _refit(self) -> None:
        """Fit the banner to its content and move the ones stacked under it."""
        # A wrapped label's size hint is for some other width; ask for this one.
        margins = self.layout().contentsMargins()
        room = self.contentsRect().width() - margins.left() - margins.right()
        label = self._message_label
        label.setFixedHeight(label.heightForWidth(room))
        self.adjustSize()
        if not self.isHidden() and self.parent():
            self._reposition_notifications(self.parent())
```

5. Route the two other fits through `_refit`: in `__init__` replace the
   final `self.adjustSize()` (line 283) with `self._refit()`, and in `show()`
   replace `self.adjustSize()` (line 357) with `self._refit()`. (`_refit`
   repositions only a shown banner, so both calls behave as `adjustSize`
   did, plus the height fix.)

Add tests 4 and 5.

**Verify**: `...python.exe -m pytest -q tests/test_notification_banner_actions.py tests/test_notification_banner_defaults.py tests/test_notification_banner_dismiss.py` → all pass.

### Step 5: An action can carry an icon

Extend `add_action` compatibly: `icon: Optional[str] = None` as a third
parameter after `callback`. After the button is made:

```python
        if icon:
            fxicons.set_icon(button, icon)
```

Document `icon` in its docstring (`An icon name, drawn before the label.`;
add an Args section with `text`, `callback`, `icon`). The constructor's
`actions` mapping is unchanged (label → callback); a caller wanting icons
calls `add_action(label, callback, icon=...)`. Add test 6.

**Verify**: `...python.exe -m pytest -q tests/test_notification_banner_actions.py` → all pass.

### Step 6: Whole suite and lint

**Verify**: whole suite → `3184 passed, 6 skipped` (3178 + 6), 0 failed; lint → `All checks passed!`.

## Test plan

1. `tests/test_tag_input.py` — `test_a_chip_shows_markup_as_typed`:
   `chip = FXTagChip("<b>x</b>")`, `qtbot.addWidget(chip)`; assert
   `chip.label.textFormat() == Qt.PlainText` and `chip.label.text() == "<b>x</b>"`.
   (Import `Qt` from `qtpy.QtCore`.)
2. `tests/test_avatar.py` — `test_a_name_with_markup_is_a_tooltip_as_typed`:
   `FXAvatar('Tom & <img src="x">', parent)`; assert `"<img" not in avatar.toolTip()`,
   `"&lt;img" in avatar.toolTip()` and `avatar.accessibleName() == 'Tom & <img src="x">'`.
3. `tests/test_tips.py` — `test_apply_tip_status_without_a_title_is_the_body`:
   `apply_tip(button, "", "Write the scene")` → `button.statusTip() == "Write the scene"`.
4. `tests/test_notification_banner_actions.py` —
   `test_a_plain_banner_shows_markup_and_newlines_as_typed`:
   `FXNotificationBanner(parent=_host(qtbot), message="a < b\nc", text_format=Qt.PlainText)`;
   assert `banner._message_label.textFormat() == Qt.PlainText` and `banner.message() == "a < b\nc"`.
5. Same file — `test_a_wrapped_message_gets_the_height_it_needs`: for each
   `fmt` in `(Qt.RichText, Qt.PlainText)`, a banner with `width=480`,
   `timeout=0` and a message of 6 lines joined by `"\n"`, each
   `"shot_NNN: publish failed because the cache folder is missing on the server"`;
   `banner.show()`; `qtbot.waitUntil(banner.isVisible)`; then with
   `room = banner.contentsRect().width() - 32` assert
   `banner._message_label.height() == banner._message_label.heightForWidth(room)`.
   Then `banner.set_message(<message> + "\none more line")` and assert the
   same equality again. (Before Step 4, plain text gives 82 for 166.)
6. Same file — `test_an_action_can_carry_an_icon`: `button = banner.add_action("Retry", None, icon="refresh-cw")`;
   assert `not button.icon().isNull()`; `banner.add_action("Later")` has a null icon.

Pattern: `tests/test_notification_banner_actions.py`
(`test_a_longer_message_grows_the_banner_and_moves_the_next_down`).

## Done criteria

- [ ] All six new tests exist and pass; the edited avatar test passes.
- [ ] Whole suite: `3184 passed, 6 skipped`, 0 failed.
- [ ] Lint: `All checks passed!`.
- [ ] `grep -n "setToolTip(self._name)" fxgui/fxwidgets/_avatar.py` → no match.
- [ ] `grep -n 'f"{title} - {body}"' fxgui/fxwidgets/_tips.py` → no match.
- [ ] `git status` shows only in-scope files modified.
- [ ] `plans/2026-11-14-audit/README.md` row 011 updated.

## STOP conditions

Stop and report (do not improvise) if:

- The excerpts above do not match the live code (drift).
- Any existing banner test changes result after Step 4 (stacking, sliding,
  dismiss) — the fit must only change the message label's height.
- Any test outside this plan asserts `FXAvatar.toolTip()` equals the bare name.
- `icon="refresh-cw"` is not an icon fxgui can load (the test's icon is null
  even after Step 5): pick an icon used elsewhere in fxgui (e.g. `"x"`) and
  say so; if no icon loads, stop.
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- Public behaviour changes: a chip with `<` in its text now shows it as typed
  (fix). `FXAvatar.toolTip()` returns the theme's rich tip, not the bare
  name, and the avatar gets an accessible name. A status tip with no title
  is the body alone. Rich banners whose wrapped message had slack under it
  lose that slack (height now exact). New opt-in: `text_format=`,
  `add_action(..., icon=)`.
- Reviewer: the banner's `_refit` is now called from `__init__`, `show`,
  `add_action` and `set_message`; check a banner whose `width` is changed
  after construction (`setFixedWidth`) is refitted by its next `set_message`
  or `show` — that is the supported path.
- Deferred: making plain text the banner default (would change vendors'
  rich messages); `FXStatusDot`'s raw tooltip (plan 015).
- Pascal, once this ships: in `src/ls_pascal/apps/widgets/banner.py`, pass
  `text_format=Qt.TextFormat.PlainText`, drop the `findChild(QLabel, "fxBannerMessage")`
  block, build the card with `actions=None` and call
  `card.add_action(label, run, icon=icon)` for each `(icon, run)` instead of
  the `findChildren(QPushButton, "fxBannerAction")` loop.
