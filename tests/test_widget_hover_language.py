"""No widget fragment paints a hover in the accent, which marks focus."""

import re

import pytest

from fxgui import fxstyle
import fxgui.fxdocking  # noqa: F401  registers its fragment
import fxgui.fxwidgets  # noqa: F401  registers every fragment

_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_ACCENTS = ("@accent_primary", "@accent_secondary")
# A menu's current row is the one hover that wears the accent.
_MENU_LIKE = ("QMenu",)


def _hover_rules():
    for fragment in list(fxstyle._widget_fragments.values()):
        for selectors, body in _RULE.findall(fragment):
            names = [s.strip() for s in selectors.split(",")]
            hovered = [n for n in names if ":hover" in n]
            if hovered and not any(m in n for n in hovered for m in _MENU_LIKE):
                yield names, body


RULES = list(_hover_rules())


def test_there_are_hover_rules_to_check():
    assert len(RULES) > 5


@pytest.mark.parametrize("names, body", RULES, ids=lambda v: str(v)[:60])
def test_a_hover_rule_names_no_accent(names, body):
    assert not any(token in body for token in _ACCENTS), names

