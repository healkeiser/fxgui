"""Tests for `fxgui.fxstyle` theming engine fixes.

Each test reproduces a defect found in the 2026-07 audit:
- `extra` stylesheet content was appended twice by load_stylesheet.
- A missing style file returned the literal string "None".
- Token replacement corrupted longer keys (@border ate @border_light).
- The declarative `theme_style` API crashed on nested theme sections
  (the per-theme "feedback" dict) and corrupted long tokens.
"""

# Third-party
import pytest
from qtpy.QtWidgets import QWidget

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


def test_theme_style_declarative_api(qtbot):
    """The documented `theme_style` class attribute must work: nested theme
    sections must not raise TypeError and long tokens must not be corrupted
    by their prefixes."""

    class TokenWidget(fxstyle.FXThemeAware, QWidget):
        theme_style = """
            TokenWidget {
                background: @surface_alt;
                border: 1px solid @border_light;
                color: @text_muted;
            }
        """

    widget = TokenWidget()
    qtbot.addWidget(widget)

    # Triggers __apply_theme_style_attribute (old code: TypeError on the
    # theme's nested "feedback" dict, and "#3a3939_light"-style corruption)
    fxstyle.theme_manager.notify_theme_changed(fxstyle.get_theme())

    sheet = widget.styleSheet()
    colors = fxstyle.get_theme_colors()
    assert colors["surface_alt"] in sheet
    assert colors["border_light"] in sheet
    assert colors["text_muted"] in sheet
    assert "@" not in sheet


def test_theme_namespace_is_cached_and_strict(qtbot):
    class Probe(fxstyle.FXThemeAware, QWidget):
        pass

    widget = Probe()
    qtbot.addWidget(widget)

    first = widget.theme
    second = widget.theme
    # Cached: paintEvent hot paths must not allocate a namespace per access
    assert first is second

    with pytest.raises(AttributeError, match="Unknown theme color role"):
        _ = first.this_role_does_not_exist


def test_apply_theme_switches_and_invalidates_cache(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)

    class Probe(fxstyle.FXThemeAware, QWidget):
        pass

    probe = Probe()
    qtbot.addWidget(probe)

    fxstyle.apply_theme(widget, "light")
    assert fxstyle.get_theme() == "light"
    assert probe.theme.surface == "#f0f0f0"

    fxstyle.apply_theme(widget, "dark")
    assert probe.theme.surface == "#302f2f"


def test_standard_icon_map_uses_feedback_fallbacks(qapp):
    """The standard icon map must build from get_feedback_colors() (the
    top-level "feedback" YAML block is deprecated and may be absent)."""
    fxstyle.invalidate_standard_icon_map()
    icon_map = fxstyle._get_standard_icon_map()
    assert icon_map  # Built without KeyError
