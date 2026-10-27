"""OKLab mixing, and the theme keys a brand states to match its own fills."""

# Internal
from fxgui import fxstyle


def test_mix_oklab_matches_css_color_mix():
    """As `color-mix(in oklab, #f7f8f8 10%, #101113)` renders in a browser."""
    assert fxstyle.mix_oklab("#101113", "#f7f8f8", 0.10) == "#222325"
    assert fxstyle.mix_oklab("#101113", "#ff4200", 0.10) == "#251817"


def test_mix_oklab_keeps_its_ends():
    assert fxstyle.mix_oklab("#101113", "#ff4200", 0.0) == "#101113"
    assert fxstyle.mix_oklab("#101113", "#ff4200", 1.0) == "#ff4200"


def _states(**theme) -> dict:
    data = {
        "surface": "#101113",
        "surface_sunken": "#0b0c0d",
        "text": "#d6d9dd",
        "text_muted": "#a2a7b0",
    }
    data.update(theme)
    return fxstyle._readable_states(data)


def test_a_stated_state_floor_keeps_a_faint_hover():
    held = _states(state_hover="#151618", state_pressed="#191a1d",
                   state_contrast=1.0)
    assert held["state_hover"] == "#151618"
    assert held["state_pressed"] == "#191a1d"


def test_without_a_floor_a_faint_hover_steps_until_it_reads():
    stepped = _states(state_hover="#151618")
    assert fxstyle.get_contrast_ratio(
        stepped["state_hover"], "#101113") >= fxstyle.STATE_MIN_CONTRAST


def test_strong_text_is_the_text_unless_a_theme_states_it():
    assert _states()["text_strong"] == _states()["text"]
    assert _states(text_strong="#f7f8f8")["text_strong"] == "#f7f8f8"
