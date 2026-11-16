"""A tool button's icon stands centred whatever its size's parity."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, QSize
from qtpy.QtGui import QColor, QIcon, QPixmap
from qtpy.QtWidgets import QToolButton

# Internal
from fxgui import fxwidgets

from _helpers import shown

INK = "#ff00ff"


def _icon(side: int) -> QIcon:
    pixmap = QPixmap(side, side)
    pixmap.fill(QColor(INK))
    return QIcon(pixmap)


def _gaps(window, button):
    """Return the icon's gaps to the button's left, right, top and bottom."""
    image = window.grab().toImage()
    origin = button.mapTo(window, QPoint(0, 0))
    ink = [
        (x, y)
        for x in range(button.width())
        for y in range(button.height())
        if image.pixelColor(origin.x() + x, origin.y() + y).name() == INK
    ]
    xs, ys = [x for x, _ in ink], [y for _, y in ink]
    return (min(xs), button.width() - 1 - max(xs),
            min(ys), button.height() - 1 - max(ys))


@pytest.mark.parametrize("side", [15, 16, 17, 18])
def test_an_odd_icon_stands_as_far_in_as_an_even_one(qtbot, app_root, side):
    """An odd icon stood 7 px in on the left and top, 5 px on the right and
    bottom: the sheet's padding rounds an even icon's half down only."""
    button = QToolButton()
    button.setIcon(_icon(side))
    button.setIconSize(QSize(side, side))
    app_root.layout().addWidget(button)
    shown(qtbot, app_root, (200, 80))

    assert _gaps(app_root, button) == (6, 6, 6, 6)


def test_a_command_row_centres_its_default_17_px_icons(qtbot, app_root):
    row = fxwidgets.FXCommandRow()
    row.addAction(_icon(row.iconSize().width()), "Add")
    app_root.layout().addWidget(row)
    shown(qtbot, app_root, (200, 80))
    button = next(b for b in row.findChildren(QToolButton) if b.defaultAction())

    assert row.iconSize().width() == 17
    left, right, top, bottom = _gaps(app_root, button)
    assert left == right and top == bottom
