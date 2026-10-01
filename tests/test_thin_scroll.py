"""A thin scroll area sits on its card: no fill, a narrow quiet bar."""

import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fxgui import fxstyle

_CARD = "#7a3b8f"


@pytest.fixture
def card(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    frame = QFrame(root)
    frame.setObjectName("card")
    frame.setStyleSheet(f"QFrame#card {{ background: {_CARD}; }}")
    QVBoxLayout(root).addWidget(frame)
    QVBoxLayout(frame)
    root.resize(200, 160)
    return root, frame


def _area(frame, rows=40):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    held = QWidget()
    column = QVBoxLayout(held)
    for index in range(rows):
        column.addWidget(QLabel(f"row {index}"))
    area.setWidget(held)
    frame.layout().addWidget(area)
    return area


def test_the_bar_is_thin_and_the_area_shows_the_card(qtbot, card):
    root, frame = card
    area = _area(frame)
    fxstyle.mark_as_thin_scroll(area)
    root.show()
    qtbot.waitExposed(root)
    QApplication.processEvents()
    bar = area.verticalScrollBar()
    assert bar.isVisible()
    assert bar.width() == fxstyle.THIN_SCROLL_WIDTH
    image = root.grab().toImage()
    inside = area.viewport().mapTo(root, QPoint(4, 4))
    assert image.pixelColor(inside).name() == _CARD
    groove = bar.mapTo(root, QPoint(bar.width() // 2, bar.height() - 2))
    assert image.pixelColor(groove).name() == _CARD


def test_marking_after_the_show_takes_effect(qtbot, card):
    root, frame = card
    area = _area(frame)
    root.show()
    qtbot.waitExposed(root)
    fxstyle.mark_as_thin_scroll(area)
    QApplication.processEvents()
    assert area.verticalScrollBar().width() == fxstyle.THIN_SCROLL_WIDTH


def test_unmarking_brings_the_theme_bar_back(qtbot, card):
    root, frame = card
    area = _area(frame)
    fxstyle.mark_as_thin_scroll(area)
    root.show()
    qtbot.waitExposed(root)
    fxstyle.mark_as_thin_scroll(area, False)
    QApplication.processEvents()
    assert area.verticalScrollBar().width() > fxstyle.THIN_SCROLL_WIDTH
