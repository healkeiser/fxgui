"""The theme an application falls back to when nothing is saved.

"dark" out of the box. An application shipping a theme of its own in a
custom color file needs to say otherwise: without that, its own first
run reads exactly like a person having chosen "dark", so it cannot both
honour a saved choice and default to its own brand.
"""

# Internal
from fxgui import fxconfig, fxstyle


def test_the_default_is_dark_until_somebody_says_otherwise(qapp):
    assert fxstyle.get_default_theme() == "dark"
    assert fxstyle.load_saved_theme() == "dark"


def test_an_unsaved_file_answers_the_configured_default(qapp):
    fxstyle.set_default_theme("dracula")

    assert fxstyle.get_default_theme() == "dracula"
    assert fxstyle.load_saved_theme() == "dracula"


def test_a_saved_theme_still_wins_over_the_default(qapp):
    """The whole point of the default is that it is only a fallback: a
    person who picked a theme keeps it across restarts."""
    fxstyle.set_default_theme("dracula")
    fxconfig.set_value("theme/current", "nord")

    assert fxstyle.load_saved_theme() == "nord"


def test_a_default_the_color_file_does_not_offer_falls_back_to_dark(qapp):
    """Not validated when it is set, because the color file it has to
    name may be set afterwards -- so the check happens here, where a name
    that would reach `apply_theme` and raise is answered with "dark"
    instead."""
    fxstyle.set_default_theme("no_such_theme")

    assert fxstyle.load_saved_theme() == "dark"
