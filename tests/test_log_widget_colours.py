"""ANSI colours in the log pane resolve to the running theme's colours."""

# Third-party
import pytest
from qtpy.QtGui import QTextFormat

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXOutputLogWidget


def _fragments(pane):
    """(text, format) for every fragment of the pane's first line."""
    block = pane.output_area.document().firstBlock()
    found = []
    it = block.begin()
    while not it.atEnd():
        fragment = it.fragment()
        found.append((fragment.text(), fragment.charFormat()))
        it += 1
    return found


def _pane(qtbot, text):
    pane = FXOutputLogWidget()
    qtbot.addWidget(pane)
    pane.append_log(text)
    qtbot.waitUntil(lambda: bool(pane.output_area.toPlainText().strip()))
    return pane


def _expected(role):
    foreground = fxstyle.qcolor(f"feedback_{role}_foreground").name()
    return fxstyle.readable_ink(fxstyle.colors().surface_sunken, foreground)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_level_word_takes_the_theme_warning_colour(qtbot, qapp, theme):
    fxstyle.apply_theme(theme)
    pane = _pane(qtbot, "\x1b[33mWARNING\x1b[0m rest")
    (word, word_fmt), (rest, rest_fmt) = _fragments(pane)
    assert (word, rest) == ("WARNING", " rest")
    ink = word_fmt.foreground().color().name()
    assert ink == _hex(_expected("warning"))
    assert fxstyle.get_contrast_ratio(ink, fxstyle.colors().surface_sunken) >= 4.5
    assert not rest_fmt.hasProperty(QTextFormat.ForegroundBrush)


def test_red_maps_to_the_error_colour(qtbot, qapp):
    fxstyle.apply_theme("dark")
    pane = _pane(qtbot, "\x1b[31mERROR\x1b[0m")
    (_, fmt), = _fragments(pane)
    assert fmt.foreground().color().name() == _hex(_expected("error"))


def test_a_theme_switch_recolours_a_line_already_shown(qtbot, qapp):
    fxstyle.apply_theme("dark")
    pane = _pane(qtbot, "\x1b[33mWARNING\x1b[0m rest")
    fxstyle.apply_theme("light")
    (_, fmt), _ = _fragments(pane)
    assert fmt.foreground().color().name() == _hex(_expected("warning"))


def _hex(value):
    from qtpy.QtGui import QColor

    return QColor(value).name()
