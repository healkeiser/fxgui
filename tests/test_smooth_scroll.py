"""Every fxgui list, tree and table scrolls by the pixel, both ways."""

# Third-party
import pytest
from qtpy.QtWidgets import QAbstractItemView, QHeaderView

# Internal
from fxgui.fxwidgets import FXDropZone, FXFuzzySearchList, FXFuzzySearchTree

PIXEL = QAbstractItemView.ScrollMode.ScrollPerPixel


@pytest.mark.parametrize(
    "build", [FXFuzzySearchList, FXFuzzySearchTree, FXDropZone]
)
def test_item_views_scroll_by_the_pixel(qtbot, build):
    widget = build()
    qtbot.addWidget(widget)

    views = [
        view
        for view in widget.findChildren(QAbstractItemView)
        if not isinstance(view, QHeaderView)
    ]

    assert views
    for view in views:
        assert view.verticalScrollMode() == PIXEL, type(view).__name__
        assert view.horizontalScrollMode() == PIXEL, type(view).__name__
