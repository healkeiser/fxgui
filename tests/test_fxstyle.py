"""Tests for `fxgui.fxstyle` theming engine fixes.

Each test reproduces a defect found in the 2026-07 audit:
- `extra` stylesheet content was appended twice by load_stylesheet.
- A missing style file returned the literal string "None".
- Token replacement corrupted longer keys (@border ate @border_light).
"""

# Third-party
import pytest

# Internal
from fxgui import fxstyle

EXTRA_MARKER = "/*FXGUI-EXTRA-MARKER*/"


def test_load_stylesheet_appends_extra_exactly_once(qapp):
    sheet = fxstyle.load_stylesheet(extra=EXTRA_MARKER)
    assert sheet.count(EXTRA_MARKER) == 1


def test_load_stylesheet_missing_file_returns_empty_string(qapp):
    assert fxstyle.load_stylesheet(style_file="does_not_exist.qss") == ""


def test_load_stylesheet_resolves_all_tokens(qapp):
    sheet = fxstyle.load_stylesheet()
    # No placeholder may survive replacement (corrupted tokens would)
    assert "@surface" not in sheet
    assert "@border" not in sheet
    assert "@text" not in sheet


def test_replace_colors_longest_key_first():
    colors = {"border": "#111111", "border_light": "#222222"}
    qss = "a { x: @border; y: @border_light; }"
    out = fxstyle.replace_colors(qss, colors)
    assert "#222222" in out
    assert "#111111_light" not in out
    assert "@" not in out


def test_theme_namespace_is_cached_and_strict(qtbot):
    first = fxstyle.colors()
    second = fxstyle.colors()
    # Cached: paintEvent hot paths must not allocate a namespace per access
    assert first is second

    with pytest.raises(AttributeError, match="Unknown theme color role"):
        _ = first.this_role_does_not_exist


def test_apply_theme_switches_and_invalidates_cache(qtbot):
    fxstyle.apply_theme("light")
    assert fxstyle.get_theme() == "light"
    assert fxstyle.colors().surface == "#f0f0f0"

    fxstyle.apply_theme("dark")
    assert fxstyle.colors().surface == "#302f2f"


def test_standard_icon_map_uses_feedback_fallbacks(qapp):
    """The standard icon map must build from get_feedback_colors() (the
    top-level "feedback" YAML block is deprecated and may be absent)."""
    fxstyle._standard_icon_map = None
    icon_map = fxstyle._get_standard_icon_map()
    assert icon_map  # Built without KeyError
