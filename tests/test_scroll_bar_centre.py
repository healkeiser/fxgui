"""A scroll bar's thumb sits centred between the rows and the frame."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QImage
from qtpy.QtWidgets import (
    QListWidget,
    QStyle,
    QStyleOptionSlider,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle

from _helpers import themed_window

# The sheet's 1 px edge around every item view.
_EDGE = 1


def _render(window, ratio):
    image = QImage(window.size() * ratio, QImage.Format_ARGB32)
    image.setDevicePixelRatio(ratio)
    image.fill(0)
    window.render(image)
    return image


def _thumb_middle(bar):
    option = QStyleOptionSlider()
    bar.initStyleOption(option)
    return bar.style().subControlRect(
        QStyle.CC_ScrollBar, option, QStyle.SC_ScrollBarSlider, bar).center()


def _gaps(image, ratio, start, stop, at, across):
    """Return the ground pixels before and after the thumb on one line.

    The line runs from `start` to `stop` (logical, exclusive) at `at`;
    `across` reads it along x, else along y.
    """
    def ink(step):
        x, y = (step, round(at * ratio)) if across else (round(at * ratio), step)
        return image.pixelColor(x, y).name()

    line = [ink(step) for step in range(round(start * ratio),
                                         round(stop * ratio))]
    ground = fxstyle.colors().surface_sunken.lower()
    first = next(i for i, colour in enumerate(line) if colour != ground)
    last = max(i for i, colour in enumerate(line) if colour != ground)
    return first, len(line) - 1 - last


def _view(kind):
    if kind == "list":
        view = QListWidget()
        view.addItems([f"row {index} " * 20 for index in range(60)])
    else:
        view = QTreeWidget()
        view.setHeaderLabels(["Name"])
        view.setHeaderHidden(kind == "tree")
        view.header().setStretchLastSection(False)
        view.setColumnWidth(0, 800)
        for index in range(60):
            view.addTopLevelItem(QTreeWidgetItem([f"row {index}"]))
    return view


@pytest.mark.parametrize("ratio", [1.0, 1.5])
@pytest.mark.parametrize("kind", ["list", "tree", "headed tree"])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_thumb_is_centred_across_its_bar(qtbot, theme, kind, ratio):
    view = _view(kind)
    window = themed_window(qtbot, theme, view, size=(300, 300))
    image = _render(window, ratio)
    origin = view.mapTo(window, QPoint())
    viewport = view.viewport().geometry().translated(origin)
    for bar in (view.verticalScrollBar(), view.horizontalScrollBar()):
        assert bar.isVisible()
        middle = bar.mapTo(window, _thumb_middle(bar))
        if bar.orientation() == Qt.Vertical:
            gaps = _gaps(image, ratio, viewport.right() + 1,
                         origin.x() + view.width() - _EDGE, middle.y(), True)
        else:
            gaps = _gaps(image, ratio, viewport.bottom() + 1,
                         origin.y() + view.height() - _EDGE, middle.x(), False)
        assert gaps[0] == gaps[1], (bar.orientation(), gaps)
