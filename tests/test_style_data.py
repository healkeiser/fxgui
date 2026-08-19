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


###### Keyboard focus ring


def _channels(hex_color: str) -> list:
    value = hex_color.lstrip("#")
    return [int(value[i : i + 2], 16) for i in (0, 2, 4)]


def _max_channel_delta(color_a: str, color_b: str) -> int:
    return max(
        abs(a - b) for a, b in zip(_channels(color_a), _channels(color_b))
    )


def _focus_block() -> str:
    """The KEYBOARD FOCUS section, which runs to the end of the file.

    Earlier rules point readers at the section by name, so the last mention
    is the section itself rather than a cross-reference to it.
    """
    text = fxstyle.STYLE_FILE.read_text(encoding="utf-8")
    marker = text.rfind("KEYBOARD FOCUS")
    assert marker != -1, "the KEYBOARD FOCUS section is gone"
    return text[marker:]


def test_focus_ring_is_visible_against_every_theme_background():
    """The ring is a non-text UI component, so WCAG 2.1 SC 1.4.11 asks 3:1
    against what sits next to it. Inputs and lists sit on surface_sunken,
    buttons and group boxes on surface, so both have to clear the bar."""
    for name, theme in fxstyle.get_colors()["themes"].items():
        ring = theme["accent_primary"]
        for role in ("surface", "surface_sunken"):
            ratio = _contrast(ring, theme[role])
            assert ratio >= 3.0, f"{name}: ring on {role} is {ratio:.2f}"


def test_focus_ring_is_distinguishable_from_the_unfocused_border():
    """A ring that matches the border it replaces indicates nothing.

    Luminance contrast is the wrong test here: solarized_light pairs a near
    grey border with a saturated blue accent that happens to sit at almost
    the same luminance (1.38:1), yet the two are obviously different colours.
    What the change has to be is a colour change, so this measures channel
    distance instead. The tightest shipped pair is 109 of 255.
    """
    for name, theme in fxstyle.get_colors()["themes"].items():
        delta = _max_channel_delta(theme["accent_primary"], theme["border"])
        assert delta >= 96, f"{name}: ring differs from border by only {delta}"


def test_selected_row_ring_reads_against_the_selection_fill():
    """FXThumbnailDelegate fills a selected row with accent_primary, so the
    ring switches to the token defined to be read on top of it."""
    for name in fxstyle.get_available_themes():
        fxstyle._theme = name
        fxstyle._invalidate_theme_namespace()
        theme = fxstyle._get_theme_namespace()
        ratio = _contrast(theme.text_on_accent_primary, theme.accent_primary)
        assert ratio >= 3.0, f"{name}: selected-row ring is {ratio:.2f}"


def test_focus_rules_are_token_driven():
    """A hardcoded colour in the focus block would be invisible on some of
    the eleven themes, which is the failure this whole section exists to
    prevent."""
    block = _focus_block()
    literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", block)
    assert literals == [], f"hardcoded colours in the focus block: {literals}"
    assert "@accent_primary" in block


def test_focus_rules_never_widen_a_border():
    """A ring that adds border width reflows the layout the moment focus
    arrives, which is worse than no ring at all. Focus rules may recolour a
    border and may restate a 1px one, never resize it."""
    block = _focus_block()
    assert "border-width" not in block
    for declaration in re.findall(r"border:\s*([^;]+);", block):
        assert declaration.startswith("1px"), declaration


def test_checkbox_and_radio_reserve_the_ring_in_both_states():
    """Neither widget has a border of its own, so both states declare one and
    only the colour changes. Without the unfocused half the label jumps a
    pixel when focus lands on it."""
    text = fxstyle.STYLE_FILE.read_text(encoding="utf-8")
    for widget in ("QCheckBox", "QRadioButton"):
        match = re.search(rf"\n{widget}\s*\n?\{{(.*?)\}}", text, re.S)
        assert match is not None, widget
        assert "border: 1px solid transparent" in match.group(1), widget


def test_focus_reset_no_longer_strips_the_ring():
    """Regression: a `border: none` rule covering QCheckBox and QRadioButton
    on focus would remove the ring they now depend on."""
    text = fxstyle.STYLE_FILE.read_text(encoding="utf-8")
    assert "QRadioButton:focus,\nQSlider:focus" not in text
    assert not re.search(
        r"QCheckBox:focus[^{]*\{[^}]*border:\s*none", text, re.S
    )
