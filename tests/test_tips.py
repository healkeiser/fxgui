"""Tests for the native rich-tooltip helpers in `fxwidgets._tips`."""

# Built-in
import re

# Third-party
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QListWidgetItem, QPushButton

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import _tips


def _strip_markup(html: str) -> str:
    """Return the text a user actually reads, with all tags removed."""
    return re.sub(r"<[^>]+>", "", html)


# ' HTML shape


def test_title_only(qtbot):
    html = _tips.tip("Back")

    assert "<b>Back</b>" in html
    assert "<table" in html
    # No body row and no keycap when only a title was given.
    assert "margin-top" not in html
    assert "font-family:monospace" not in html


def test_title_and_body(qtbot):
    html = _tips.tip("Back", "Navigate to previous location")

    assert "<b>Back</b>" in html
    assert "Navigate to previous location" in html
    # The body sits in its own block below the title.
    assert "margin-top" in html
    assert "font-family:monospace" not in html


def test_title_and_shortcut(qtbot):
    html = _tips.tip("Save", shortcut="Ctrl+S")

    assert "<b>Save</b>" in html
    assert "font-family:monospace" in html
    # Title and keycap share one line, the cap pushed right by a cell.
    assert 'align="right"' in html
    assert "margin-top" not in html


def test_title_body_and_shortcut(qtbot):
    html = _tips.tip("Save", "Write the scene to disk", "Ctrl+S")

    assert "<b>Save</b>" in html
    assert "Write the scene to disk" in html
    assert 'align="right"' in html
    assert "margin-top" in html


def test_width_is_capped(qtbot):
    """Qt ignores `max-width`; the cap must ride on a table width attribute
    or a long sentence stretches the tooltip across the monitor."""
    html = _tips.tip("Publish", "x" * 400)

    assert f'width="{_tips.TIP_WIDTH}"' in html


# ' Escaping


def test_caller_strings_are_escaped(qtbot):
    html = _tips.tip("Fire & <Ice>", "path/to/A&B <shot>", "Ctrl+S")

    # The raw characters must not reach the markup...
    assert "<Ice>" not in html
    assert "<shot>" not in html
    # ...but the words survive as text.
    assert "Fire &amp; &lt;Ice&gt;" in html
    assert "path/to/A&amp;B &lt;shot&gt;" in html


def test_escaping_survives_as_text(qtbot):
    """What the user reads is the string they were given."""
    from html import unescape

    title = "Fire & <Ice>"
    html = _tips.tip(title)

    assert unescape(_strip_markup(html)).strip() == title


# ' Empty in, empty out


def test_all_blank_yields_empty_string(qtbot):
    assert _tips.tip("") == ""
    assert _tips.tip("", "", "") == ""


def test_keycap_empty_yields_empty_string(qtbot):
    assert _tips.keycap("") == ""


def test_body_only_still_renders(qtbot):
    html = _tips.tip("", "Nothing is selected")

    assert "Nothing is selected" in html
    assert "<b>" not in html


# ' Shortcut rendering


def test_keycap_uses_native_text(qtbot):
    """A Mac must show the platform glyphs rather than the literal "Ctrl",
    which is what QKeySequence's NativeText format is for."""
    native = QKeySequence("Ctrl+Shift+E").toString(QKeySequence.NativeText)
    html = _tips.keycap("Ctrl+Shift+E")

    assert native in _strip_markup(html).replace("&nbsp;", "")


def test_keycap_falls_back_to_raw_string(qtbot):
    """Qt yields nothing for a sequence it cannot parse; the raw string is
    still more useful to the reader than an empty cap."""
    assert QKeySequence("not a shortcut").toString() == ""
    assert "not a shortcut" in _strip_markup(_tips.keycap("not a shortcut"))


# ' Theme awareness


def test_colors_come_from_the_active_theme(qtbot):
    fxstyle.apply_theme("dark")
    dark = _tips.tip("Save", "Write the scene to disk", "Ctrl+S")

    fxstyle.apply_theme("light")
    light = _tips.tip("Save", "Write the scene to disk", "Ctrl+S")

    assert dark != light
    for token in ("text", "text_muted", "state_hover"):
        fxstyle.apply_theme("dark")
        dark_value = fxstyle.get_theme_colors()[token]
        fxstyle.apply_theme("light")
        light_value = fxstyle.get_theme_colors()[token]

        assert dark_value in dark
        assert light_value in light
        assert dark_value not in light


def test_tokens_used_exist_in_every_theme(qtbot):
    """A missing token would raise a KeyError on hover, in a studio theme
    nobody tested."""
    for name in fxstyle.get_available_themes():
        fxstyle.apply_theme(name)
        colors = fxstyle.get_theme_colors()
        for token in ("text", "text_muted", "state_hover"):
            assert token in colors, f"{name} is missing {token}"


# ' apply_tip


def test_apply_tip_sets_markup_and_plain_status(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)

    _tips.apply_tip(button, "Save", "Write the scene to disk", "Ctrl+S")

    assert "<b>Save</b>" in button.toolTip()
    status = button.statusTip()
    assert "<" not in status and ">" not in status
    assert "Save" in status and "Write the scene to disk" in status


def test_apply_tip_status_is_title_only_without_body(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)

    _tips.apply_tip(button, "Back")

    assert button.statusTip() == "Back"


def test_apply_tip_tolerates_missing_status_tip(qtbot):
    """Not every tooltip target carries a status tip; the guard must hold."""

    class ToolTipOnly:
        def __init__(self):
            self.tooltip = ""

        def setToolTip(self, text):
            self.tooltip = text

    target = ToolTipOnly()
    assert not hasattr(target, "setStatusTip")

    _tips.apply_tip(target, "Shot 0010", "Ready to render")

    assert "<b>Shot 0010</b>" in target.tooltip


def test_apply_tip_works_on_view_items(qtbot):
    """Item classes are annotated the same way as widgets."""
    item = QListWidgetItem("Shot 0010")

    _tips.apply_tip(item, "Shot 0010", "Ready to render")

    assert "<b>Shot 0010</b>" in item.toolTip()
    assert item.statusTip() == "Shot 0010 - Ready to render"
