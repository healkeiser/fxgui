"""A delegate row's card is its only fill: its corners show the view's well."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem

# Internal
from fxgui.fxwidgets import FXThumbnailDelegate

from _helpers import hover, themed_window

# Any well but the sheet's own `surface_sunken`, as a docked pane's is.
_WELL = "#2b5d34"


def _corners(image, view, item):
    rect = view.visualItemRect(item)
    viewport = view.viewport()
    return {
        QColor(image.pixel(viewport.mapTo(view.window(), point))).name()
        for point in (rect.topLeft(), rect.topRight(),
                      rect.bottomLeft(), rect.bottomRight())
    }


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("card", [True, False])
@pytest.mark.parametrize("state", ["rest", "hover", "selected"])
def test_nothing_square_shows_outside_a_rows_rounded_corners(
        qtbot, theme, card, state):
    view = QTreeWidget()
    view.setObjectName("well")
    view.setHeaderHidden(True)
    view.setRootIsDecorated(False)
    view.setItemDelegate(FXThumbnailDelegate())
    rows = [QTreeWidgetItem(view, [f"Row{index}"]) for index in range(3)]
    if card:
        for row in rows:
            row.setData(0, Qt.BackgroundRole, "surface")
    view.setStyleSheet(f"#well {{ background-color: {_WELL}; }}")
    window = themed_window(qtbot, theme, view)
    item = rows[1]
    if state == "selected":
        item.setSelected(True)
    elif state == "hover":
        hover(qtbot, view.viewport(),
              view.visualItemRect(item).center())
    image = window.grab().toImage()
    assert _corners(image, view, item) == {_WELL}
