# Theming Pull-Model Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the pull-model theming core from `specs/2026-07-30-theming-pull-model-design.md`: one cascading theme sheet applied at registered roots, a unified token pass, the new public API (`colors()`, `apply_theme(name)`, `theme_changed`, `register_widget_style`, `repolish`), and full backward-compatibility shims.

**Architecture:** Qt repolishes and repaints all descendants when an ancestor's stylesheet changes, so widgets stop being individually notified: the theme sheet is set on registered roots (`FXApplication` standalone, individual windows in DCCs) and everything below updates via the cascade. This plan covers spec phases 0 (spike) and 1 (core + shims). Phase 2 (migrating the 30 built-in widgets off `FXThemeAware`) and phase 3 (docs) get a follow-up plan informed by the spike results — until then, built-in widgets keep running on the untouched `FXThemeAware` mixin, which remains fully functional.

**Tech Stack:** Python, qtpy (PySide6 test target; PySide2/PyQt5/PyQt6 compatible), pytest + pytest-qt (headless offscreen, see `tests/conftest.py`), PyYAML.

## Global Constraints

- **No breakage:** the pre-rework test suite must pass unmodified (deprecation warnings are acceptable; pytest config does not escalate warnings to errors).
- **Do NOT add `DeprecationWarning` to `FXThemeAware` in this plan.** Built-in widgets still use it; the warning lands at the end of the phase-2 plan, after they migrate.
- All Qt imports via `qtpy`, never a binding directly.
- Google-style docstrings with Args/Returns; comprehensive type annotations; new public names exported via `__all__`.
- Commit message convention: `[FEAT] ...`, `[FIX] ...`, `[TEST] ...`, `[DOC] ...` (repo standard, see CLAUDE.md).
- Work on branch `feat/theming-pull-model`, branched from `main`. Never commit to `main`.
- Run tests with: `python -m pytest tests/ -v` (offscreen platform is forced by `tests/conftest.py`).

---

### Task 1: Branch and baseline

**Files:** none modified.

**Interfaces:**
- Produces: branch `feat/theming-pull-model`; a recorded green baseline of the existing suite.

- [ ] **Step 1: Create the branch**

```bash
git checkout -b feat/theming-pull-model main
```

- [ ] **Step 2: Run the full suite and record the baseline**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS. If anything fails before we touch code, STOP and report — the compat criterion is meaningless without a green baseline.

---

### Task 2: Spike — prove the Qt mechanics (GATE)

The whole design rests on three Qt behaviors plus one performance number. This task proves them on the installed binding and records the results. The tests stay in the suite permanently as guards.

**Files:**
- Create: `tests/test_style_cascade.py`

**Interfaces:**
- Produces: a recorded GATE decision for Task 5 (`_FORCE_UPDATE_WALK` True or False).

- [ ] **Step 1: Write the spike tests**

```python
"""Spike/guard tests: the Qt mechanics the pull-model theming relies on.

1. An ancestor setStyleSheet delivers QEvent.StyleChange to descendants.
2. A custom-painted descendant repaints after an ancestor restyle.
3. A QSS class selector matches a Python subclass name, and a plain
   QWidget subclass paints a QSS background when WA_StyledBackground
   is set.
4. Repolishing a deep tree is fast enough for switch-time use.
"""

import time

from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget


class _PaintTracker(QWidget):
    """Custom-painted child that counts paints and StyleChange events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paint_count = 0
        self.style_change_count = 0
        self.setMinimumSize(40, 40)

    def paintEvent(self, event):
        self.paint_count += 1
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ff0000"))
        painter.end()

    def changeEvent(self, event):
        if event.type() == QEvent.StyleChange:
            self.style_change_count += 1
        super().changeEvent(event)


class _StyledBox(QWidget):
    """Plain QWidget subclass targeted by a QSS class selector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Required for QSS backgrounds from an ANCESTOR sheet: a plain
        # QWidget subclass ignores them otherwise. setStyleSheet directly
        # on a widget enables this implicitly, ancestor sheets do not.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumSize(40, 40)


def _build_tree(depth_widget_cls):
    """Root > container > tracked child, so the cascade crosses a level."""
    root = QWidget()
    layout = QVBoxLayout(root)
    container = QWidget(root)
    layout.addWidget(container)
    inner = QVBoxLayout(container)
    child = depth_widget_cls(container)
    inner.addWidget(child)
    return root, child


def test_ancestor_restyle_delivers_stylechange(qtbot):
    root, child = _build_tree(_PaintTracker)
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)

    child.style_change_count = 0
    root.setStyleSheet("QWidget { background-color: #0000ff; }")
    qtbot.wait(50)

    assert child.style_change_count >= 1


def test_ancestor_restyle_repaints_custom_painted_child(qtbot):
    root, child = _build_tree(_PaintTracker)
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)
    qtbot.wait(50)

    before = child.paint_count
    root.setStyleSheet("QWidget { background-color: #00ff00; }")
    qtbot.wait(100)

    assert child.paint_count > before


def test_qss_class_selector_matches_python_subclass(qtbot):
    root, child = _build_tree(_StyledBox)
    qtbot.addWidget(root)
    root.setStyleSheet("_StyledBox { background-color: #ff00ff; }")
    root.show()
    qtbot.waitExposed(root)

    image = child.grab().toImage()
    assert image.pixelColor(child.rect().center()) == QColor("#ff00ff")


def test_qss_class_selector_matches_qt_subclass(qtbot):
    """Same check for a QLabel subclass (no WA_StyledBackground needed)."""

    class _FancyLabel(QLabel):
        pass

    root = QWidget()
    layout = QVBoxLayout(root)
    label = _FancyLabel("x")
    label.setMinimumSize(40, 40)
    layout.addWidget(label)
    qtbot.addWidget(root)
    root.setStyleSheet("_FancyLabel { background-color: #00ffff; }")
    root.show()
    qtbot.waitExposed(root)

    image = label.grab().toImage()
    assert image.pixelColor(label.rect().center()) == QColor("#00ffff")


def test_repolish_cost_on_deep_tree(qtbot):
    """Measure switch-time repolish on ~300 widgets. Generous bound: the
    point is a recorded number, not a race."""
    root = QWidget()
    layout = QVBoxLayout(root)
    parent = root
    for _ in range(10):  # 10 levels deep
        box = QWidget(parent)
        (parent.layout() or QVBoxLayout(parent)).addWidget(box)
        QVBoxLayout(box)
        for _ in range(30):  # 30 labels per level
            box.layout().addWidget(QLabel("x", box))
        parent = box
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)

    start = time.perf_counter()
    root.setStyleSheet("QLabel { color: #123456; }")
    qtbot.wait(10)
    elapsed = time.perf_counter() - start

    print(f"\nrepolish of ~300-widget tree took {elapsed * 1000:.1f} ms")
    assert elapsed < 2.0
```

- [ ] **Step 2: Run the spike**

Run: `python -m pytest tests/test_style_cascade.py -v -s`
Expected: all 5 PASS, with the repolish timing printed.

- [ ] **Step 3: Record the GATE decision**

- If `test_ancestor_restyle_repaints_custom_painted_child` PASSES: Task 5 sets `_FORCE_UPDATE_WALK = False`. Note "repaint cascade confirmed" in the commit message.
- If it FAILS (and only that one): Task 5 sets `_FORCE_UPDATE_WALK = True` (the fallback `update()` walk). Delete this one test, keep the other four, and note "repaint cascade NOT guaranteed on <binding>, fallback walk enabled" in the commit message.
- If `test_ancestor_restyle_delivers_stylechange` or either class-selector test FAILS: **STOP. The design assumption is broken. Report to the user before writing any implementation code.**

- [ ] **Step 4: Commit**

```bash
git add tests/test_style_cascade.py
git commit -m "[TEST] Spike: Qt cascade mechanics for pull-model theming"
```

---

### Task 3: Unified token pass (`_token_map` / `_resolve_tokens`)

One implementation replaces the three that exist today (`load_stylesheet`'s hand map, `replace_colors`, the mixin's `__apply_theme_style_attribute`). The old entry points keep working; they are rewired in later tasks.

**Files:**
- Modify: `fxgui/fxstyle.py` (add private helpers after `get_contrast_text_color`, around line 811)
- Test: `tests/test_fxstyle_tokens.py` (create)

**Interfaces:**
- Consumes: existing `get_colors()`, `get_contrast_text_color()`, `_parent_directory`.
- Produces: `_token_map(theme_name: str) -> Dict[str, str]` and `_resolve_tokens(qss: str, theme_name: str) -> str`, both private to `fxstyle`. Tasks 4 and 9 call `_resolve_tokens`.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the unified token pass in fxstyle."""

from fxgui import fxstyle


def test_token_map_contains_flat_theme_keys(qapp):
    tokens = fxstyle._token_map("dark")
    assert tokens["@surface"].startswith("#")
    assert tokens["@text"].startswith("#")


def test_token_map_flattens_feedback_colors(qapp):
    tokens = fxstyle._token_map("dark")
    assert "@feedback_error_foreground" in tokens
    assert "@feedback_error_background" in tokens
    assert tokens["@feedback_error_foreground"].startswith("#")


def test_token_map_computes_on_accent_colors(qapp):
    tokens = fxstyle._token_map("dark")
    assert tokens["@text_on_accent_primary"] in ("#FFFFFF", "#000000") or (
        tokens["@text_on_accent_primary"].startswith("#")
    )
    assert "@icon_on_accent_primary" in tokens


def test_token_map_merges_unknown_theme_over_dark(qapp):
    # Unknown themes fall back to dark values key-by-key.
    assert fxstyle._token_map("no_such_theme") == fxstyle._token_map("dark")


def test_resolve_tokens_longest_key_first(qapp):
    qss = "a: @border; b: @border_light;"
    resolved = fxstyle._resolve_tokens(qss, "dark")
    assert "@" not in resolved
    assert "_light" not in resolved  # @border must not corrupt @border_light


def test_resolve_tokens_icons_path(qapp):
    resolved = fxstyle._resolve_tokens("url(~icons/x.svg)", "dark")
    assert "~icons" not in resolved
    assert "stylesheet_dark" in resolved or "stylesheet_light" in resolved
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fxstyle_tokens.py -v`
Expected: FAIL with `AttributeError: module 'fxgui.fxstyle' has no attribute '_token_map'`

- [ ] **Step 3: Implement in `fxgui/fxstyle.py`**

Add `Dict` to the `typing` import at the top of the file, then add after `get_contrast_text_color`:

```python
def _token_map(theme_name: str) -> Dict[str, str]:
    """Build the ``@token`` -> value map for a theme.

    Single source of truth for stylesheet token resolution. Includes:
    flat theme color roles, flattened feedback colors
    (``@feedback_<level>_<part>``), computed on-accent colors, and the
    ``~icons`` folder path.

    Args:
        theme_name: Theme to resolve. Unknown names fall back to "dark"
            key-by-key (the dark theme acts as the defaults baseline).

    Returns:
        Mapping of placeholder (including the ``@``/``~`` prefix) to value.
    """
    colors_dict = get_colors()
    themes = colors_dict.get("themes", {})
    base = themes.get("dark", {})
    theme_data = {**base, **themes.get(theme_name, {})}

    tokens: Dict[str, str] = {
        f"@{key}": value
        for key, value in theme_data.items()
        if isinstance(value, str)
    }

    # Feedback colors flatten to @feedback_<level>_<part>. Theme-level
    # block wins over the deprecated top-level one.
    feedback = theme_data.get("feedback") or colors_dict.get("feedback") or {}
    for level, pair in feedback.items():
        if isinstance(pair, dict):
            for part, value in pair.items():
                tokens[f"@feedback_{level}_{part}"] = value

    # On-accent colors: theme value if defined, computed otherwise.
    accent_primary = theme_data.get("accent_primary", "#2196F3")
    accent_secondary = theme_data.get("accent_secondary", "#1976D2")
    tokens.setdefault("@accent_primary", accent_primary)
    tokens.setdefault("@accent_secondary", accent_secondary)
    text_on_primary = theme_data.get(
        "text_on_accent_primary", get_contrast_text_color(accent_primary)
    )
    text_on_secondary = theme_data.get(
        "text_on_accent_secondary", get_contrast_text_color(accent_secondary)
    )
    tokens["@text_on_accent_primary"] = text_on_primary
    tokens["@text_on_accent_secondary"] = text_on_secondary
    tokens["@icon_on_accent_primary"] = theme_data.get(
        "icon_on_accent_primary", text_on_primary
    )
    tokens["@icon_on_accent_secondary"] = theme_data.get(
        "icon_on_accent_secondary", text_on_secondary
    )

    # Icon folder path used by url(~icons/...) in QSS, chosen by the
    # target theme's surface lightness (not the globally current theme).
    surface = QColor(theme_data.get("surface", "#000000"))
    icon_folder = (
        "stylesheet_light" if surface.lightness() > 128 else "stylesheet_dark"
    )
    tokens["~icons"] = str(_parent_directory / "icons" / icon_folder).replace(
        os.sep, "/"
    )
    return tokens


def _resolve_tokens(qss: str, theme_name: str) -> str:
    """Replace all ``@token``/``~icons`` placeholders in a stylesheet.

    Args:
        qss: Stylesheet text containing placeholders.
        theme_name: Theme whose values to substitute.

    Returns:
        The stylesheet with placeholders replaced, longest keys first so
        ``@border`` cannot corrupt ``@border_light``.
    """
    tokens = _token_map(theme_name)
    for key in sorted(tokens, key=len, reverse=True):
        qss = qss.replace(key, tokens[key])
    return qss
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_fxstyle_tokens.py tests/test_fxstyle.py -v`
Expected: all PASS (including the pre-existing fxstyle tests).

- [ ] **Step 5: Commit**

```bash
git add fxgui/fxstyle.py tests/test_fxstyle_tokens.py
git commit -m "[FEAT] fxstyle: unified token map/resolution pass"
```

---

### Task 4: Sheet builder and widget-style fragments

**Files:**
- Modify: `fxgui/fxstyle.py`
- Test: `tests/test_fxstyle_builder.py` (create)

**Interfaces:**
- Consumes: `_resolve_tokens(qss, theme_name)` from Task 3; existing `STYLE_FILE`, `get_theme()`.
- Produces: `build_stylesheet(theme: Optional[str] = None) -> str`, `register_widget_style(qss: str) -> None`, `_font_stylesheet() -> str`, module global `_widget_fragments: "OrderedDict[str, str]"`, and a stub `_reapply_to_roots() -> None` (real body in Task 5). Tasks 5, 6, 9 use these.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the theme sheet builder and fragment registry."""

from fxgui import fxstyle


def test_build_stylesheet_resolves_all_tokens(qapp):
    sheet = fxstyle.build_stylesheet("dark")
    assert sheet  # non-empty
    assert "@" not in sheet
    assert "~icons" not in sheet


def test_build_stylesheet_defaults_to_current_theme(qapp):
    assert fxstyle.build_stylesheet() == fxstyle.build_stylesheet(
        fxstyle.get_theme()
    )


def test_register_widget_style_appends_fragment(qapp):
    fxstyle.register_widget_style(
        "FXPlanTestWidget { background: @surface; }"
    )
    sheet = fxstyle.build_stylesheet("dark")
    assert "FXPlanTestWidget" in sheet
    assert "@surface" not in sheet


def test_register_widget_style_dedupes_identical_fragments(qapp):
    fragment = "FXPlanDedupe { color: @text; }"
    fxstyle.register_widget_style(fragment)
    fxstyle.register_widget_style(fragment)
    assert fxstyle.build_stylesheet("dark").count("FXPlanDedupe") == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fxstyle_builder.py -v`
Expected: FAIL with `AttributeError` on `build_stylesheet`.

- [ ] **Step 3: Implement in `fxgui/fxstyle.py`**

Add `import hashlib` and `from collections import OrderedDict` to the built-in imports. Add near the other globals (`_theme_namespace` block, around line 444):

```python
_widget_fragments: "OrderedDict[str, str]" = OrderedDict()
```

Extract the font block from `load_stylesheet` into a helper (place before `load_stylesheet`), and add the builder and registry functions:

```python
def _font_stylesheet() -> str:
    """Return the platform font-family stylesheet block."""
    if sys.platform == "win32":
        default_font = "Segoe UI"
    else:
        default_font = QFontDatabase.systemFont(
            QFontDatabase.GeneralFont
        ).family()
    return f'* {{\n    font-family: "{default_font}";\n}}\n'


def build_stylesheet(theme: Optional[str] = None) -> str:
    """Build the complete theme stylesheet.

    Concatenates the platform font block, the base ``style.qss``, and all
    fragments registered via :func:`register_widget_style`, then resolves
    every ``@token`` in a single pass. Pure: no global state is modified.

    Args:
        theme: Theme name. Defaults to the current theme.

    Returns:
        The ready-to-apply stylesheet string.
    """
    if theme is None:
        theme = get_theme()
    parts = [_font_stylesheet()]
    if os.path.exists(STYLE_FILE):
        with open(STYLE_FILE, "r", encoding="utf-8") as in_file:
            parts.append(in_file.read())
    parts.extend(_widget_fragments.values())
    return _resolve_tokens("\n".join(parts), theme)


def register_widget_style(qss: str) -> None:
    """Register a widget's QSS fragment with the theme stylesheet.

    Call once at module import time. The fragment may use ``@tokens``
    (e.g. ``@surface``, ``@border``); use your widget's class name as
    selector to scope the rules. Identical fragments are registered once.

    If themed roots already exist, the rebuilt sheet is re-applied to
    them immediately, so late registration is safe.

    Args:
        qss: Stylesheet fragment with optional ``@token`` placeholders.

    Examples:
        >>> fxstyle.register_widget_style('''
        ...     MyWidget { background: @surface; border: 1px solid @border; }
        ... ''')
    """
    key = hashlib.sha1(qss.encode("utf-8")).hexdigest()
    if key in _widget_fragments:
        return
    _widget_fragments[key] = qss
    _reapply_to_roots()


def _reapply_to_roots() -> None:
    """Re-apply the current theme sheet to all registered roots.

    Stub: real body lands with the root registry.
    """
```

Add `"build_stylesheet"` and `"register_widget_style"` to `__all__` (in the "Stylesheet functions" group).

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_fxstyle_builder.py tests/test_fxstyle.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add fxgui/fxstyle.py tests/test_fxstyle_builder.py
git commit -m "[FEAT] fxstyle: theme sheet builder and widget-style fragment registry"
```

---

### Task 5: Themed-root registry

**Files:**
- Modify: `fxgui/fxstyle.py`
- Modify: `tests/conftest.py` (state isolation for the new globals)
- Test: `tests/test_fxstyle_roots.py` (create)

**Interfaces:**
- Consumes: `build_stylesheet()` from Task 4; `fxgui._compat.is_valid`; `fxicons.sync_colors_with_theme`.
- Produces: `register_themed_root(root) -> None`, module global `_themed_roots: weakref.WeakSet`, real `_reapply_to_roots()` body, module constant `_FORCE_UPDATE_WALK: bool`. Task 6 calls `_reapply_to_roots`; Tasks 10-11 call `register_themed_root`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the themed-root registry."""

from qtpy.QtWidgets import QWidget

from fxgui import fxstyle


def test_register_themed_root_applies_sheet_immediately(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    assert root.styleSheet() == ""
    fxstyle.register_themed_root(root)
    assert root.styleSheet() != ""
    assert "@" not in root.styleSheet()


def test_reapply_updates_all_roots(qtbot):
    root_a, root_b = QWidget(), QWidget()
    qtbot.addWidget(root_a)
    qtbot.addWidget(root_b)
    fxstyle.register_themed_root(root_a)
    fxstyle.register_themed_root(root_b)

    fragment = "FXPlanRootsProbe { color: @text; }"
    fxstyle.register_widget_style(fragment)

    assert "FXPlanRootsProbe" in root_a.styleSheet()
    assert "FXPlanRootsProbe" in root_b.styleSheet()


def test_dead_roots_drop_out(qtbot):
    root = QWidget()
    fxstyle.register_themed_root(root)
    count_before = len(fxstyle._themed_roots)
    del root
    import gc

    gc.collect()
    assert len(fxstyle._themed_roots) < count_before
    # Must not raise on dead entries either:
    fxstyle._reapply_to_roots()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fxstyle_roots.py -v`
Expected: FAIL with `AttributeError` on `register_themed_root`.

- [ ] **Step 3: Implement in `fxgui/fxstyle.py`**

Add `import weakref` to the built-in imports. Add next to `_widget_fragments`:

```python
_themed_roots: "weakref.WeakSet" = weakref.WeakSet()

# GATE from the spike (tests/test_style_cascade.py): False when Qt's
# cascade reliably repaints custom-painted descendants after an ancestor
# restyle; True enables an explicit update() walk as fallback.
_FORCE_UPDATE_WALK = False
```

**Set `_FORCE_UPDATE_WALK` according to the Task 2 GATE decision.**

Replace the `_reapply_to_roots` stub and add the public function:

```python
def register_themed_root(root) -> None:
    """Register a widget (or QApplication) as a themed root.

    The current theme stylesheet is applied to it immediately and
    re-applied on every subsequent :func:`apply_theme` call. Qt cascades
    the sheet to all descendants, so children need no registration.

    Standalone apps: ``FXApplication`` registers itself; nothing to do.
    DCC-embedded windows: ``FXMainWindow`` registers itself when the
    running QApplication is foreign, so the host app is never restyled.

    Roots are held weakly; destroyed widgets drop out automatically.

    Args:
        root: Any object with ``setStyleSheet`` (QWidget or QApplication).
    """
    _ensure_theme_loaded()
    fxicons.sync_colors_with_theme()
    _themed_roots.add(root)
    root.setStyleSheet(build_stylesheet())


def _reapply_to_roots() -> None:
    """Re-apply the current theme sheet to all live registered roots."""
    if not _themed_roots:
        return
    sheet = build_stylesheet()
    for root in list(_themed_roots):
        if not _compat.is_valid(root):
            continue
        root.setStyleSheet(sheet)
        if _FORCE_UPDATE_WALK and hasattr(root, "findChildren"):
            for child in root.findChildren(QWidget):
                child.update()
```

Add `"register_themed_root"` to `__all__`.

- [ ] **Step 4: Extend test-state isolation in `tests/conftest.py`**

In the `_isolate_fxgui_state` fixture, after the existing resets (`fxstyle._standard_icon_map = None`), add:

```python
    fxstyle._widget_fragments.clear()
    fxstyle._themed_roots = type(fxstyle._themed_roots)()
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_fxstyle_roots.py tests/test_fxstyle_builder.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add fxgui/fxstyle.py tests/conftest.py tests/test_fxstyle_roots.py
git commit -m "[FEAT] fxstyle: themed-root registry with weak references"
```

---

### Task 6: `apply_theme` rework with dual-signature shim

**Files:**
- Modify: `fxgui/fxstyle.py` (replace the existing `apply_theme`, currently around line 899)
- Test: `tests/test_fxstyle_apply.py` (create)

**Interfaces:**
- Consumes: `_reapply_to_roots()`, `_themed_roots` (Task 5); existing `get_available_themes()`, `save_theme()`, `_invalidate_theme_namespace()`, `invalidate_standard_icon_map()`, `theme_manager`, `fxicons.sync_colors_with_theme()`.
- Produces: `apply_theme(*args, widget=None, theme=None) -> str` supporting the new call `apply_theme("dark")` and the old calls `apply_theme(w, "dark")` / `apply_theme(w, theme="dark")` / `apply_theme(widget=w, theme="dark")` (old forms warn and register the widget as a root).

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for apply_theme: new signature, old-signature shim, mixin compat."""

import warnings

import pytest
from qtpy.QtWidgets import QWidget

from fxgui import fxstyle


def test_new_signature_switches_theme(qtbot):
    fxstyle.apply_theme("light")
    assert fxstyle.get_theme() == "light"
    fxstyle.apply_theme("dark")
    assert fxstyle.get_theme() == "dark"


def test_new_signature_updates_registered_roots(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    fxstyle.apply_theme("light")
    light_sheet = root.styleSheet()
    fxstyle.apply_theme("dark")
    assert root.styleSheet() != light_sheet


def test_unknown_theme_raises(qtbot):
    with pytest.raises(ValueError):
        fxstyle.apply_theme("no_such_theme")


def test_old_signature_warns_and_registers_root(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    with pytest.warns(DeprecationWarning):
        fxstyle.apply_theme(widget, "light")
    assert fxstyle.get_theme() == "light"
    assert widget.styleSheet() != ""
    # The widget is now a root: further switches keep it updated.
    sheet = widget.styleSheet()
    fxstyle.apply_theme("dark")
    assert widget.styleSheet() != sheet


def test_old_keyword_signature_works(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    with pytest.warns(DeprecationWarning):
        fxstyle.apply_theme(widget, theme="dark")
    assert fxstyle.get_theme() == "dark"


def test_theme_changed_signal_still_fires(qtbot):
    received = []
    fxstyle.theme_manager.theme_changed.connect(received.append)
    try:
        fxstyle.apply_theme("light")
    finally:
        fxstyle.theme_manager.theme_changed.disconnect(received.append)
    assert received == ["light"]


def test_fxthemeaware_mixin_still_notified(qtbot):
    calls = []

    class Probe(fxstyle.FXThemeAware, QWidget):
        def _on_theme_changed(self, _theme_name=None):
            calls.append(fxstyle.get_theme())

    probe = Probe()
    qtbot.addWidget(probe)
    fxstyle.apply_theme("light")
    assert "light" in calls
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fxstyle_apply.py -v`
Expected: `test_new_signature_switches_theme` and others FAIL — current `apply_theme` requires `(widget, theme)`, so `apply_theme("light")` raises `TypeError` (or treats the string as widget).

- [ ] **Step 3: Replace `apply_theme` in `fxgui/fxstyle.py`**

Add `import warnings` to the built-in imports. Replace the whole existing `apply_theme` function with:

```python
def apply_theme(*args, widget: Optional[QWidget] = None, theme: Optional[str] = None) -> str:
    """Apply a theme everywhere.

    Canonical form::

        fxstyle.apply_theme("dracula")

    Updates the persistent theme state, rebuilds the theme stylesheet,
    re-applies it to every registered root (see
    :func:`register_themed_root`), refreshes icon colors, and emits
    ``theme_changed``.

    .. deprecated::
        The old form ``apply_theme(widget, theme)`` still works: it
        registers ``widget`` as a themed root and proceeds. Prefer
        ``apply_theme(theme)``.

    Args:
        theme: The theme name to apply (e.g., "dark", "light").
        widget: Deprecated. A widget to register as a themed root.

    Returns:
        The theme that was applied.

    Raises:
        ValueError: If the theme does not exist.
        TypeError: If no theme name was provided.
    """
    global _theme

    # Untangle the two calling conventions.
    if args:
        if isinstance(args[0], str):
            if len(args) > 1 or theme is not None:
                raise TypeError("apply_theme() takes a single theme name")
            theme = args[0]
        else:
            if widget is not None:
                raise TypeError("apply_theme() got widget twice")
            widget = args[0]
            if len(args) == 2:
                if theme is not None:
                    raise TypeError("apply_theme() got theme twice")
                theme = args[1]
            elif len(args) > 2:
                raise TypeError("apply_theme() takes at most 2 arguments")
    if theme is None:
        raise TypeError("apply_theme() missing required 'theme'")

    available_themes = get_available_themes()
    if theme not in available_themes:
        raise ValueError(
            f"Theme '{theme}' not found. Available themes: {available_themes}"
        )

    if widget is not None:
        warnings.warn(
            "apply_theme(widget, theme) is deprecated; call "
            "apply_theme(theme) once. For DCC-embedded windows, use "
            "register_themed_root(widget) at construction instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        _themed_roots.add(widget)

    _theme = theme
    _invalidate_theme_namespace()
    save_theme(theme)
    fxicons.sync_colors_with_theme()
    invalidate_standard_icon_map()
    _reapply_to_roots()
    theme_manager.notify_theme_changed(theme)

    return theme
```

- [ ] **Step 4: Run to verify pass, including the pre-existing suite**

Run: `python -m pytest tests/test_fxstyle_apply.py tests/test_fxstyle.py -v`
Expected: all PASS. `tests/test_fxstyle.py::test_apply_theme_switches_and_invalidates_cache` uses the old signature and must pass (it will emit a DeprecationWarning, which is fine).

- [ ] **Step 5: Commit**

```bash
git add fxgui/fxstyle.py tests/test_fxstyle_apply.py
git commit -m "[FEAT] fxstyle: apply_theme(name) with old-signature compat shim"
```

---

### Task 7: `colors()` and module-level `theme_changed`

**Files:**
- Modify: `fxgui/fxstyle.py`
- Test: `tests/test_fxstyle_colors_api.py` (create)

**Interfaces:**
- Consumes: `_get_theme_namespace()`, `_ensure_theme_loaded()`, `theme_manager` (all existing).
- Produces: `colors() -> FXThemeColors` and module attribute `theme_changed` (the singleton's bound signal). This is the canonical read API the docs and phase-2 migration will use.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the canonical color-read API."""

from qtpy.QtWidgets import QWidget

from fxgui import fxstyle


def test_colors_returns_namespace(qtbot):
    fxstyle.apply_theme("dark")
    colors = fxstyle.colors()
    assert colors.surface.startswith("#")
    assert colors.text.startswith("#")


def test_colors_tracks_theme_switches(qtbot):
    fxstyle.apply_theme("dark")
    dark_surface = fxstyle.colors().surface
    fxstyle.apply_theme("light")
    assert fxstyle.colors().surface != dark_surface


def test_module_level_theme_changed_signal(qtbot):
    received = []
    fxstyle.theme_changed.connect(received.append)
    try:
        fxstyle.apply_theme("light")
    finally:
        fxstyle.theme_changed.disconnect(received.append)
    assert received == ["light"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fxstyle_colors_api.py -v`
Expected: FAIL with `AttributeError: module 'fxgui.fxstyle' has no attribute 'colors'`.

- [ ] **Step 3: Implement in `fxgui/fxstyle.py`**

Directly below the `theme_manager = FXThemeManager()` line, add:

```python
# Canonical module-level alias: connect side-effect widgets to
# fxstyle.theme_changed without going through the manager object.
theme_changed = theme_manager.theme_changed
```

Next to `get_theme()`, add:

```python
def colors() -> "FXThemeColors":
    """Get the current theme colors as a namespace (canonical read API).

    Cheap enough for ``paintEvent`` hot paths: the namespace is cached
    per theme and rebuilt only on theme switches. Treat it as read-only.

    Returns:
        FXThemeColors with one attribute per color role.

    Examples:
        >>> def paintEvent(self, event):
        ...     painter = QPainter(self)
        ...     painter.fillRect(self.rect(), QColor(fxstyle.colors().surface))
    """
    _ensure_theme_loaded()
    return _get_theme_namespace()
```

Add `"colors"` and `"theme_changed"` to `__all__`.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_fxstyle_colors_api.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add fxgui/fxstyle.py tests/test_fxstyle_colors_api.py
git commit -m "[FEAT] fxstyle: colors() namespace and module-level theme_changed"
```

---

### Task 8: `fxutils.repolish`

**Files:**
- Modify: `fxgui/fxutils.py` (add function; add `"repolish"` to its `__all__`)
- Test: `tests/test_fxutils_repolish.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `fxutils.repolish(widget: QWidget) -> None`. Phase-2 widgets call it after changing a dynamic property.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for fxutils.repolish and dynamic-property attribute selectors."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QVBoxLayout, QWidget

from fxgui import fxutils


class _StateBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumSize(40, 40)


def test_repolish_applies_dynamic_property_selector(qtbot):
    root = QWidget()
    layout = QVBoxLayout(root)
    box = _StateBox(root)
    layout.addWidget(box)
    qtbot.addWidget(root)
    root.setStyleSheet(
        '_StateBox { background-color: #00ff00; }'
        '_StateBox[level="error"] { background-color: #ff0000; }'
    )
    root.show()
    qtbot.waitExposed(root)

    center = box.rect().center()
    assert box.grab().toImage().pixelColor(center) == QColor("#00ff00")

    box.setProperty("level", "error")
    fxutils.repolish(box)
    qtbot.wait(20)

    assert box.grab().toImage().pixelColor(center) == QColor("#ff0000")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fxutils_repolish.py -v`
Expected: FAIL with `AttributeError: module 'fxgui.fxutils' has no attribute 'repolish'`.

- [ ] **Step 3: Implement in `fxgui/fxutils.py`**

```python
def repolish(widget: "QWidget") -> None:
    """Force re-evaluation of the stylesheet rules for a widget.

    Call after changing a Qt dynamic property that a stylesheet
    attribute selector depends on, e.g.
    ``MyBanner[level="error"] { ... }``.

    Args:
        widget: The widget to unpolish/polish and repaint.

    Examples:
        >>> banner.setProperty("level", "error")
        >>> fxutils.repolish(banner)
    """
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
```

Match the module's existing import style for `QWidget` (check the top of `fxgui/fxutils.py` and reuse its qtpy import block).

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_fxutils_repolish.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fxgui/fxutils.py tests/test_fxutils_repolish.py
git commit -m "[FEAT] fxutils: repolish() helper for dynamic-property styling"
```

---

### Task 9: Rewire `load_stylesheet` over the unified token pass

`load_stylesheet` keeps its exact signature, side effects, and behavior (it is the documented DCC entry point and is used by `FXApplication` until Task 10), but its hand-maintained replacement map is replaced by `_resolve_tokens`.

**Files:**
- Modify: `fxgui/fxstyle.py` (replace the body of `load_stylesheet`, currently around line 1194)
- Test: existing `tests/test_fxstyle.py` (no new file)

**Interfaces:**
- Consumes: `_resolve_tokens`, `_font_stylesheet` (Tasks 3-4).
- Produces: `load_stylesheet(style_file=STYLE_FILE, extra=None, theme=None) -> str` — unchanged contract: missing file returns `""`; sets `_theme`; invalidates the namespace; syncs icon colors; prepends the font block; appends `extra` once. Note: `load_stylesheet` does NOT include registered fragments; that is `build_stylesheet`'s job.

- [ ] **Step 1: Replace the body of `load_stylesheet`**

```python
def load_stylesheet(
    style_file: str = STYLE_FILE,
    extra: Optional[str] = None,
    theme: str = None,
) -> str:
    """Load the stylesheet and replace placeholders with actual values.

    Note:
        Kept for backward compatibility and manual DCC styling. New code
        should rely on :func:`register_themed_root` /
        :func:`apply_theme`, which use :func:`build_stylesheet`
        (including registered widget fragments; this function does not).

    Args:
        style_file: The path to the QSS file. Defaults to `STYLE_FILE`.
        extra: Extra stylesheet content to append. Defaults to None.
        theme: The theme to use (e.g., "dark", "light", "dracula").
            If None, uses the saved theme from persistent storage.

    Returns:
        The stylesheet with all placeholders replaced.
    """
    global _theme

    if not os.path.exists(style_file):
        # An empty string is a valid "no-op" stylesheet.
        return ""

    if theme is None:
        theme = load_saved_theme()

    # Keep the historical side effects: global theme state stays in sync
    # and icon colors follow (important for startup with a saved theme).
    _theme = theme
    _invalidate_theme_namespace()
    fxicons.sync_colors_with_theme()

    with open(style_file, "r", encoding="utf-8") as in_file:
        stylesheet = in_file.read()

    stylesheet = _font_stylesheet() + _resolve_tokens(stylesheet, theme)
    if extra:
        stylesheet += extra

    return stylesheet
```

Delete nothing else: `replace_colors` stays public and untouched (it operates on caller-provided dicts, a different contract).

- [ ] **Step 2: Run the pre-existing fxstyle tests**

Run: `python -m pytest tests/test_fxstyle.py tests/test_style_data.py tests/test_visual.py -v`
Expected: all PASS — in particular `test_load_stylesheet_resolves_all_tokens`, `test_load_stylesheet_appends_extra_exactly_once`, and `test_load_stylesheet_missing_file_returns_empty_string`.

- [ ] **Step 3: Run the full suite**

Run: `python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add fxgui/fxstyle.py
git commit -m "[FEAT] fxstyle: load_stylesheet rewired over the unified token pass"
```

---

### Task 10: `FXApplication` becomes a themed root

**Files:**
- Modify: `fxgui/fxwidgets/_application.py:44-62`
- Test: existing `tests/test_application.py`, plus one new test appended to it

**Interfaces:**
- Consumes: `register_themed_root` (Task 5).
- Produces: `FXApplication` registers itself; its stylesheet now updates via `_reapply_to_roots` instead of a private signal connection. The `_on_theme_changed` method is removed (private, no longer connected).

- [ ] **Step 1: Write the failing test (append to `tests/test_application.py`)**

```python
def test_fxapplication_is_themed_root(qtbot):
    """FXApplication's stylesheet follows apply_theme(name) with no
    per-app signal connection."""
    from qtpy.QtWidgets import QApplication

    from fxgui import fxstyle

    app = QApplication.instance()
    fxstyle._themed_roots.add(app)  # simulate FXApplication registration
    fxstyle.apply_theme("light")
    light_sheet = app.styleSheet()
    fxstyle.apply_theme("dark")
    assert app.styleSheet() != light_sheet
    app.setStyleSheet("")  # clean up for other tests
```

Note: tests run under pytest-qt's plain `QApplication`, not `FXApplication` (singleton constraints), so this test exercises the root mechanism the same way `FXApplication.__init__` will.

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_application.py -v`
Expected: the new test FAILS only if Tasks 5-6 are incomplete; if it already passes, continue (the mechanism is proven, the wiring change below is still required).

- [ ] **Step 3: Rewire `FXApplication.__init__`**

In `fxgui/fxwidgets/_application.py`, replace lines 50-55:

```python
            # Load stylesheet with saved theme from persistent storage
            # load_stylesheet() automatically uses the saved theme
            self.setStyleSheet(fxstyle.load_stylesheet())

            # Connect to theme changes to update application stylesheet
            fxstyle.theme_manager.theme_changed.connect(self._on_theme_changed)
```

with:

```python
            # Register as themed root: the saved theme's stylesheet is
            # applied now and re-applied automatically on apply_theme().
            fxstyle.register_themed_root(self)
```

Delete the now-unconnected `_on_theme_changed` method (lines 60-62). Before deleting, grep `tests/test_application.py` for `_on_theme_changed`: if any existing test references it, keep the method as a thin wrapper (`def _on_theme_changed(self, theme_name): fxstyle._reapply_to_roots()`) instead of deleting, and note it for phase-2 removal.

- [ ] **Step 4: Run the application and style tests**

Run: `python -m pytest tests/test_application.py tests/test_fxstyle.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add fxgui/fxwidgets/_application.py tests/test_application.py
git commit -m "[FEAT] FXApplication: register as themed root instead of per-app signal"
```

---

### Task 11: `FXMainWindow` becomes a themed root; internal call sites use the new signature

**Files:**
- Modify: `fxgui/fxwidgets/_main_window.py:137-139` (init styling) and `:715-728` (`_set_theme`)
- Test: existing `tests/test_main_window.py`, plus one new test appended to it

**Interfaces:**
- Consumes: `register_themed_root`, `apply_theme(name)` (Tasks 5-6).
- Produces: `FXMainWindow(set_stylesheet=True)` windows live-update on theme switches (fixes the current multi-window staleness, where only the window that triggered the switch got restyled).

- [ ] **Step 1: Write the failing test (append to `tests/test_main_window.py`)**

```python
def test_main_window_live_updates_on_theme_switch(qtbot):
    """set_stylesheet=True windows are themed roots: every window
    follows apply_theme, not just the one that triggered it."""
    from fxgui import fxstyle
    from fxgui.fxwidgets import FXMainWindow

    window_a = FXMainWindow()
    window_b = FXMainWindow()
    qtbot.addWidget(window_a)
    qtbot.addWidget(window_b)

    fxstyle.apply_theme("light")
    sheet_a, sheet_b = window_a.styleSheet(), window_b.styleSheet()
    fxstyle.apply_theme("dark")

    assert window_a.styleSheet() != sheet_a
    assert window_b.styleSheet() != sheet_b
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_main_window.py::test_main_window_live_updates_on_theme_switch -v`
Expected: FAIL — today each window gets a static init-time sheet that never updates unless it triggered the switch itself.

- [ ] **Step 3: Rewire `FXMainWindow`**

In `fxgui/fxwidgets/_main_window.py`, replace lines 137-139:

```python
        # Styling - load_stylesheet() automatically uses the saved theme
        if self._set_stylesheet:
            self.setStyleSheet(fxstyle.load_stylesheet())
```

with:

```python
        # Styling: register as a themed root. The saved theme's sheet is
        # applied now and re-applied on every apply_theme(), whether the
        # app is an FXApplication (standalone) or foreign (DCC host).
        if self._set_stylesheet:
            fxstyle.register_themed_root(self)
```

In `_set_theme` (line 728), replace:

```python
        fxstyle.apply_theme(self, theme=theme)
```

with:

```python
        fxstyle.apply_theme(theme)
```

(The window is already registered as a root; passing `self` would only trigger the deprecation shim.)

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_main_window.py tests/test_widgets_keyboard.py -v`
Expected: all PASS, including the new live-update test.

- [ ] **Step 5: Commit**

```bash
git add fxgui/fxwidgets/_main_window.py tests/test_main_window.py
git commit -m "[FEAT] FXMainWindow: themed root registration, live multi-window switching"
```

---

### Task 12: End-to-end verification and closeout

**Files:**
- Test: `tests/test_visual.py` (append one test)

**Interfaces:**
- Consumes: everything above.
- Produces: a rendered-pixels proof that a theme switch restyles a plain child widget through the cascade with zero per-widget code.

- [ ] **Step 1: Write the end-to-end visual test (append to `tests/test_visual.py`)**

```python
def test_theme_switch_restyles_children_through_cascade(qtbot):
    """Pull model end-to-end: a plain QLineEdit under a themed root
    renders differently in dark vs light with no per-widget theming
    code at all."""
    from qtpy.QtWidgets import QLineEdit, QVBoxLayout, QWidget

    from fxgui import fxstyle

    root = QWidget()
    layout = QVBoxLayout(root)
    line = QLineEdit()
    line.setMinimumSize(120, 28)
    layout.addWidget(line)
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    root.show()
    qtbot.waitExposed(root)

    center = line.rect().center()
    fxstyle.apply_theme("dark")
    qtbot.wait(20)
    dark_pixel = line.grab().toImage().pixelColor(center)
    fxstyle.apply_theme("light")
    qtbot.wait(20)
    light_pixel = line.grab().toImage().pixelColor(center)

    assert dark_pixel != light_pixel
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/test_visual.py -v`
Expected: all PASS.

- [ ] **Step 3: Run the complete suite one last time**

Run: `python -m pytest tests/ -v`
Expected: everything PASSES — pre-existing tests unmodified (Global Constraint), all new tests green.

- [ ] **Step 4: Manual smoke check (report to user, do not skip silently)**

Run: `python -m fxgui.examples` (needs a display; if executing headless, ask the user to run it). Toggle themes from the window's theme menu and confirm live restyling. This is the human gate before the phase-2 migration plan.

- [ ] **Step 5: Commit**

```bash
git add tests/test_visual.py
git commit -m "[TEST] End-to-end cascade restyle proof for pull-model theming"
```

---

## Out of scope for this plan (phase-2 plan, written after this one lands)

- Migrating the 30+ built-in widgets off `FXThemeAware` (per-widget QSS extraction into `style.qss`, paint-time reads, dynamic-property states, the four `theme_changed` subscribers).
- `FXFloatingDialog` root registration (only meaningful once its styling moves into the cascade).
- Adding the `DeprecationWarning` to `FXThemeAware` (must come after built-ins migrate, or every fxgui app warns).
- Docs rewrite around the one-sentence contract.
- Theme-aware `QIconEngine` (explicitly deferred by the spec).
