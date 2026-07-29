"""Tests for style.yaml data quality and QSS accessibility fixes."""

# Built-in
import re

# Internal
from fxgui import fxstyle


def _contrast(color_a: str, color_b: str) -> float:
    lum_a = fxstyle.get_luminance(color_a)
    lum_b = fxstyle.get_luminance(color_b)
    high, low = max(lum_a, lum_b), min(lum_a, lum_b)
    return (high + 0.05) / (low + 0.05)


def test_dark_text_muted_is_distinct_and_readable():
    """Regression: dark text_muted (#b1b1b1) was visually identical to text
    (#bbbbbb), so muted hierarchy did not exist in the default theme."""
    dark = fxstyle.get_colors()["themes"]["dark"]

    assert dark["text_muted"].lower() != dark["text"].lower()
    # Perceptibly different from primary text (channel delta), yet readable
    delta = abs(
        int(dark["text"][1:3], 16) - int(dark["text_muted"][1:3], 16)
    )
    assert delta >= 24
    assert _contrast(dark["text_muted"], dark["surface"]) >= 4.5


def test_all_themes_text_on_surface_contrast():
    """fxgui's own themes (dark/light) meet WCAG AA (4.5:1). Branded themes
    reproduce upstream palettes faithfully (Solarized is famously ~4.1:1),
    so they only get a readability floor."""
    themes = fxstyle.get_colors()["themes"]
    for name, theme in themes.items():
        ratio = _contrast(theme["text"], theme["surface"])
        minimum = 4.5 if name in ("dark", "light") else 4.0
        assert ratio >= minimum, f"{name}: {ratio:.2f} < {minimum}"


def test_dcc_colors_redshift_typo_fixed_with_alias():
    dcc = fxstyle.get_colors()["dcc"]
    assert "redshift" in dcc
    # Deprecated alias kept for backward compatibility
    assert dcc.get("redshit") == dcc["redshift"]


def test_qss_qwidget_block_keeps_focus_outline():
    """Regression: the global QWidget rule contained `outline: 0`, killing
    the keyboard focus indicator for every widget in the application."""
    text = fxstyle.STYLE_FILE.read_text(encoding="utf-8")
    match = re.search(r"\nQWidget\s*\{(.*?)\}", text, re.S)
    assert match is not None
    qwidget_block = match.group(1)
    assert "outline: 0" not in qwidget_block
    assert "outline: 1px solid" in qwidget_block
