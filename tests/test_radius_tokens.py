"""Corners come from two tokens: a control's radius and a card's."""

# Built-in
import re

# Internal
from fxgui import fxstyle, fxwidgets  # noqa: F401  (registers every rule)

# A pill (a groove, a scroll thumb) rounds at half its thickness, and a
# part inside a 1 px border at one less: those stay in pixels.
_SIZES = {"2", "4", "8"}


def _literal_radii(qss: str) -> list:
    qss = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    # A slider's groove and handle, a scroll bar's thumb and a progress bar
    # are pills.
    qss = re.sub(r"(QSlider|QScrollBar)::[^{]*\{[^}]*\}", "", qss)
    qss = re.sub(r"QProgressBar[^{]*\{[^}]*\}", "", qss)
    return [m for m in re.findall(r"radius:\s*(\d+)px", qss) if m in _SIZES]


def test_the_base_sheet_names_no_control_or_card_radius_in_pixels():
    assert _literal_radii(fxstyle.STYLE_FILE.read_text(encoding="utf-8")) == []


def test_no_widget_rule_names_one_in_pixels():
    for qss in fxstyle._widget_fragments.values():
        assert _literal_radii(qss) == [], qss[:80]


def test_the_tokens_are_the_constants():
    sheet = fxstyle.resolve("a{border-radius:@button_radius;} b{x:@card_radius;}")
    assert f"{fxstyle.BUTTON_RADIUS}px" in sheet
    assert f"{fxstyle.CARD_RADIUS}px" in sheet
