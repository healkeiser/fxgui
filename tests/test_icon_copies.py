"""Each call hands out its own icon or pixmap, never the cached object."""

import pytest

from fxgui import fxicons

shiboken = pytest.importorskip("qtpy.shiboken")


def test_each_icon_is_the_callers_own(qapp):
    assert fxicons.get_icon("house") is not fxicons.get_icon("house")


def test_a_caller_deleting_its_icon_leaves_the_next_one_whole(qapp):
    # QtAds' binding deletes an icon registered with its icon provider.
    shiboken.delete(fxicons.get_icon("x"))
    again = fxicons.get_icon("x")
    assert shiboken.isValid(again)
    assert not again.pixmap(16, 16).isNull()


def test_a_caller_changing_its_pixmap_leaves_the_next_one_alone(qapp):
    first = fxicons.get_pixmap("house", 16, 16, dpr=1.0)
    first.setDevicePixelRatio(7.0)
    first.fill()
    again = fxicons.get_pixmap("house", 16, 16, dpr=1.0)
    assert again.devicePixelRatio() == 1.0
    assert again.toImage() != first.toImage()
