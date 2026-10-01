"""A menu bar item keeps one shape: hovered, open, and after the menu closes."""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPointF, Qt
from qtpy.QtGui import QColor, QMouseEvent
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QLabel

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXMainWindow


def _point_at(bar, rect):
    """Move the pointer onto the item, as a real hover does."""
    point = QPointF(rect.center())
    event = QMouseEvent(
        QEvent.MouseMove, point, QPointF(bar.mapToGlobal(rect.center())),
        Qt.NoButton, Qt.NoButton, Qt.NoModifier,
    )
    QApplication.sendEvent(bar, event)
    QApplication.processEvents()


def _shape(bar, rect, ink):
    """Return the bounds of the item's `ink` pixels and whether it rounds."""
    image = bar.grab(rect).toImage()
    ink = QColor(ink).name()
    inside = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).name() == ink
    ]
    if not inside:
        return None
    xs, ys = [x for x, _ in inside], [y for _, y in inside]
    bounds = (min(xs), min(ys), max(xs), max(ys))
    rounded = image.pixelColor(bounds[0], bounds[1]).name() != ink
    return bounds, rounded


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_hover_open_and_closed_items_share_one_rounded_shape(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = FXMainWindow(title="probe")
    window.setCentralWidget(QLabel("body"))
    window.resize(500, 300)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    bar = window.menuBar()
    action = bar.actions()[0]
    rect = bar.actionGeometry(action)
    colors = fxstyle.colors()
    hover_ink, open_ink = colors.state_hover, colors.accent_primary
    assert hover_ink.lower() != open_ink.lower()

    assert _shape(bar, rect, hover_ink) is None, "a resting item is bare"
    assert _shape(bar, rect, open_ink) is None

    _point_at(bar, rect)
    hover = _shape(bar, rect, hover_ink)
    assert _shape(bar, rect, open_ink) is None, "hover is not the accent"

    QTest.mouseClick(bar, Qt.LeftButton, Qt.NoModifier, rect.center())
    QTest.qWait(30)
    opened = _shape(bar, rect, open_ink)

    # The owner's case: the menu closes with the pointer still on the item.
    action.menu().close()
    QTest.qWait(30)
    _point_at(bar, rect)
    closed = _shape(bar, rect, hover_ink)

    assert hover is not None and opened is not None and closed is not None
    assert hover[0] == opened[0] == closed[0], (hover, opened, closed)
    assert hover[1] and opened[1] and closed[1], "the corners are rounded"
