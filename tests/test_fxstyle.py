"""Tests for `fxgui.fxstyle` theming engine fixes.

Token replacement must not corrupt longer keys (@border eating
@border_light), and the namespace must be cached.
"""

# Third-party
import pytest

# Internal
from fxgui import fxstyle

def test_token_replacement_takes_the_longest_key_first():
    tokens = {"@border": "#111111", "@border_light": "#222222"}
    out = fxstyle._substitute("a { x: @border; y: @border_light; }", tokens)
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
    """The standard icon map builds from each theme's own feedback block."""
    fxstyle._standard_icon_map = None
    icon_map = fxstyle._get_standard_icon_map()
    assert icon_map  # Built without KeyError
