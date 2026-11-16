"""A mark set or taken off after the first show looks as if set before it."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

# Internal
from fxgui import fxstyle

from _helpers import themed_window


def _corner(qtbot, theme, at_show, after):
    """Return a tree's top-left corner pixels, flush `at_show`, then `after`."""
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    for row in range(8):
        QTreeWidgetItem(tree, [f"sh{row:03d}0"])
    fxstyle.mark_flush(tree, at_show)
    window = themed_window(qtbot, theme, tree)
    if after is not None:
        fxstyle.mark_flush(tree, after)
    QApplication.processEvents()
    image = window.grab().toImage()
    origin = tree.mapTo(window, QPoint(0, 0))
    return [
        image.pixelColor(origin.x() + step, origin.y() + step).name()
        for step in range(4)
    ]


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("flush", [True, False])
def test_a_view_marked_after_its_show_has_the_corners_of_one_marked_before(
    qtbot, theme, flush
):
    # A flush view's corner is square: no arc, no ground cut out of it. A
    # framed one's is round, however it lost its flush mark.
    assert _corner(qtbot, theme, not flush, flush) == _corner(
        qtbot, theme, flush, None)
