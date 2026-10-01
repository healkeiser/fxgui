"""A widget dropped by its caller is freed: no slot on a child keeps it."""

# Built-in
import gc
import weakref

# Third-party
import pytest

# Internal
from fxgui import fxwidgets


def _breadcrumb():
    crumb = fxwidgets.FXBreadcrumb()
    crumb.set_path(["a", "b", "c"])
    return crumb


def _banner():
    return fxwidgets.FXNotificationBanner(actions={"Retry": lambda: None})


@pytest.mark.parametrize(
    "build",
    [
        fxwidgets.FXMainWindow,
        _breadcrumb,
        fxwidgets.FXEmojiPicker,
        fxwidgets.FXFuzzySearchTree,
        fxwidgets.FXFilteredTree,
        _banner,
    ],
    ids=[
        "main_window", "breadcrumb", "emoji_picker", "fuzzy", "filtered",
        "banner",
    ],
)
def test_a_dropped_widget_is_freed(qapp, build):
    ref = weakref.ref(build())
    gc.collect()
    assert ref() is None
