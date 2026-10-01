"""Widget fragments speak the control language: hover, popups."""

import re

import pytest

from fxgui import fxstyle
import fxgui.fxwidgets  # noqa: F401  registers every fragment

try:
    import fxgui.fxdocking  # noqa: F401  registers its fragment
except ImportError:  # QtAds is an optional extra.
    pass

_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_ACCENTS = ("@accent_primary", "@accent_secondary")
# A menu's current row is the one hover that wears the accent.
_MENU_LIKE = ("QMenu",)


def _rules():
    for fragment in list(fxstyle._widget_fragments.values()):
        for selectors, body in _RULE.findall(_COMMENT.sub("", fragment)):
            yield [s.strip() for s in selectors.split(",")], body


def _hover_rules():
    for names, body in _rules():
        hovered = [n for n in names if ":hover" in n]
        if hovered and not any(m in n for n in hovered for m in _MENU_LIKE):
            yield names, body


def _body(selector):
    for names, body in _rules():
        if selector in names:
            return body
    raise LookupError(selector)


RULES = list(_hover_rules())


def test_there_are_hover_rules_to_check():
    assert len(RULES) > 5


@pytest.mark.parametrize("names, body", RULES, ids=lambda v: str(v)[:60])
def test_a_hover_rule_names_no_accent(names, body):
    assert not any(token in body for token in _ACCENTS), names


@pytest.mark.parametrize("popup", ["FXCommandPalette", "FXEmojiPicker"])
def test_a_popup_is_a_surface_card_at_the_card_radius(popup):
    body = _body(popup)
    assert "border-radius: @card_radius" in body
    assert "background-color: @surface;" in body
    assert "border: 1px solid @border;" in body


def test_no_fragment_sets_a_third_weight_or_a_point_size():
    """Two weights, the body's and 600; sizes follow the root font."""
    for names, body in _rules():
        assert "font-weight: bold" not in body, names
        assert not re.search(r"font-size:\s*[0-9.]+pt", body), names
        # An emoji is a picture, sized as one; text takes the root font.
        if not all(n.startswith("FXEmojiPicker") for n in names):
            assert "font-size" not in body, names


# The spacing ramp; 32 and 40 are for a window-sized panel, a splash.
_RAMP = {0, 2, 4, 6, 8, 12, 16, 24, 32, 40}
_LITERAL = re.compile(
    r"\.(?:setSpacing|setContentsMargins|addSpacing)\(([0-9, ]+)\)")


def test_a_widget_lays_itself_out_on_the_spacing_ramp():
    from pathlib import Path

    files = Path(fxgui.fxwidgets.__file__).parent.glob("*.py")
    off = []
    for path in files:
        for number, line in enumerate(path.read_text().splitlines(), 1):
            for group in _LITERAL.findall(line):
                values = {int(v) for v in group.split(",")}
                # The accordion's 1 px is a hairline between sections.
                if path.name == "_accordion.py" and values == {1}:
                    continue
                if values - _RAMP:
                    off.append(f"{path.name}:{number} {group}")
    assert off == []
