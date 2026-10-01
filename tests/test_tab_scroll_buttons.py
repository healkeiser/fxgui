"""A crowded tab bar's scroll buttons cover the tab they sit over."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QLabel,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_no_tab_text_shows_inside_the_scroll_buttons(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    tabs = QTabWidget()
    tabs.setMaximumWidth(260)
    for index in range(8):
        tabs.addTab(QLabel("page"), f"Tab {index}")
    QVBoxLayout(window).addWidget(tabs)
    window.resize(400, 200)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    image = window.grab().toImage()
    buttons = [
        button
        for button in tabs.tabBar().findChildren(QToolButton)
        if button.isVisible()
    ]
    assert len(buttons) == 2
    surface = fxstyle.colors().surface.lower()
    for button in buttons:
        # On the bar, each button looks as it does drawn alone: nothing of
        # the tab under it shows through.
        alone = button.grab().toImage()
        offset = button.mapTo(window, QPoint())
        for x in range(button.width()):
            for y in range(button.height()):
                assert image.pixelColor(offset + QPoint(x, y)) == (
                    alone.pixelColor(x, y)
                ), (button.objectName(), x, y)
        # The gap before each arrow is the strip's own fill.
        gap = {
            alone.pixelColor(x, y).name()
            for x in range(6)
            for y in range(button.height())
        }
        assert gap == {surface}, (button.objectName(), gap)
    # A cut tab reads as cut: its text stops well short of the first arrow.
    left = min(buttons, key=lambda button: button.x())
    start = left.mapTo(window, QPoint())
    rows = range(start.y(), start.y() + left.height())

    def inked(x):
        return any(_distance(image.pixelColor(x, y), surface) > 30 for y in rows)

    arrow = next(x for x in range(start.x(), start.x() + left.width()) if inked(x))
    text = max(x for x in range(0, start.x()) if inked(x))
    assert arrow - text >= 12, (text, arrow)


def _distance(color, ink):
    other = QColor(ink)
    return max(
        abs(color.red() - other.red()),
        abs(color.green() - other.green()),
        abs(color.blue() - other.blue()),
    )
