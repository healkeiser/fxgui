"""Two guesses a consumer should not have to make.

`get_icon` raised `FileNotFoundError` for a name no library carries, so
every consumer mapping open-ended studio data onto a curated set wrapped
the call in a `try/except` -- and a curated set not carrying a name is
ordinary rather than exceptional.

`FXThumbnailDelegate` claimed `UserRole + 1` through `UserRole + 12` and
said so only in prose, so a view stamping roles of its own on the same
items had to guess a safe margin past that range. Two studio
repositories each guessed one by hand, and one of them guessed `+10`
first: a real collision with `CHILD_COUNT_VISIBLE_ROLE`, which showed up
as a child count on rows that had no children.
"""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon

# Internal
from fxgui import fxicons
from fxgui.fxwidgets import FXThumbnailDelegate


# A brand fxgui's curated "dcc" library does carry, and one no library
# does. The second is the case every consumer of an open-ended name hits.
CURATED = "houdini"
UNCURATED = "a_dcc_nobody_has_curated"


def test_an_uncurated_name_still_raises_without_a_fallback(qtbot, qapp):
    """The default is unchanged: a caller who named no stand-in wanted to
    hear about it."""
    with pytest.raises(FileNotFoundError):
        fxicons.get_icon(UNCURATED, library="dcc")


def test_a_fallback_name_answers_for_an_uncurated_one(qtbot, qapp):
    icon = fxicons.get_icon(UNCURATED, library="dcc", fallback="apps")

    assert not icon.isNull()


def test_the_fallback_is_looked_up_in_the_default_library(qtbot, qapp):
    """Which is the point, and the one surprising thing about it: the
    library that just failed to carry the name is the least likely place
    for the stand-in, and the general-purpose set is where it lives.

    "apps" is a material icon and is in no "dcc" library at all, so a
    fallback resolved in `library` would raise here.
    """
    with pytest.raises(FileNotFoundError):
        fxicons.get_icon("apps", library="dcc")

    assert not fxicons.get_icon(
        UNCURATED, library="dcc", fallback="apps"
    ).isNull()


def test_a_curated_name_is_unaffected_by_a_fallback(qtbot, qapp):
    """A fallback is a fallback, not a substitution."""
    with_fallback = fxicons.get_icon(
        CURATED, library="dcc", fallback="apps"
    )
    without = fxicons.get_icon(CURATED, library="dcc")

    assert not with_fallback.isNull()
    assert with_fallback.availableSizes() == without.availableSizes()


def test_a_qicon_fallback_is_answered_with_as_it_is(qtbot, qapp):
    """`QIcon()` asks for a blank rather than a picture of something
    else, which is what a consumer wants when there is no honest
    stand-in for the thing the name meant."""
    blank = fxicons.get_icon(UNCURATED, library="dcc", fallback=QIcon())

    assert blank.isNull()


def test_a_fallback_that_is_not_there_either_is_not_swallowed(qtbot, qapp):
    """A second silent stand-in would hide a mistake in the code rather
    than in the data."""
    with pytest.raises(FileNotFoundError):
        fxicons.get_icon(
            UNCURATED, library="dcc", fallback="also_not_a_real_icon"
        )


def test_the_fallback_keeps_the_size_and_colour_asked_for(qtbot, qapp):
    """A stand-in that came out at another size would be visible as a
    layout jump on exactly the rows that fell back."""
    icon = fxicons.get_icon(
        UNCURATED, library="dcc", width=32, height=32, fallback="apps"
    )

    assert icon.availableSizes(), "it rendered something"
    assert max(size.width() for size in icon.availableSizes()) >= 32


def test_the_delegates_role_ceiling_is_published(qtbot, qapp):
    assert FXThumbnailDelegate.FIRST_FREE_ROLE == Qt.UserRole + 13


def test_the_ceiling_is_clear_of_every_role_the_delegate_claims(
    qtbot, qapp
):
    """The property that has to hold as roles are added: the ceiling is
    above all of them, so a consumer deriving from it never collides."""
    claimed = [
        value
        for name, value in vars(FXThumbnailDelegate).items()
        if name.endswith("_ROLE") and name != "FIRST_FREE_ROLE"
    ]

    assert claimed, "the delegate does claim roles"
    assert FXThumbnailDelegate.FIRST_FREE_ROLE > max(claimed)


def test_the_ceiling_wastes_nothing(qtbot, qapp):
    """Immediately above the last claimed role rather than a round number
    past it, so the constant IS the ceiling and not another margin."""
    claimed = [
        value
        for name, value in vars(FXThumbnailDelegate).items()
        if name.endswith("_ROLE") and name != "FIRST_FREE_ROLE"
    ]

    assert FXThumbnailDelegate.FIRST_FREE_ROLE == max(claimed) + 1


def test_the_role_that_collided_is_inside_the_claimed_range(qtbot, qapp):
    """The measured collision: a consumer picked `UserRole + 10` as its
    own and met `CHILD_COUNT_VISIBLE_ROLE`."""
    assert FXThumbnailDelegate.CHILD_COUNT_VISIBLE_ROLE == Qt.UserRole + 10
    assert (
        FXThumbnailDelegate.CHILD_COUNT_VISIBLE_ROLE
        < FXThumbnailDelegate.FIRST_FREE_ROLE
    )
