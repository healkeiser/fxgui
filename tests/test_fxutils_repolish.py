"""Tests for fxutils.repolish and dynamic-property attribute selectors."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QVBoxLayout, QWidget

from fxgui import fxutils


class _StateBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumSize(40, 40)


def test_repolish_applies_dynamic_property_selector(qtbot):
    root = QWidget()
    layout = QVBoxLayout(root)
    box = _StateBox(root)
    layout.addWidget(box)
    qtbot.addWidget(root)
    root.setStyleSheet(
        '_StateBox { background-color: #00ff00; }'
        '_StateBox[level="error"] { background-color: #ff0000; }'
    )
    root.show()
    qtbot.waitExposed(root)

    center = box.rect().center()
    assert box.grab().toImage().pixelColor(center) == QColor("#00ff00")

    box.setProperty("level", "error")
    fxutils.repolish(box)
    qtbot.wait(20)

    assert box.grab().toImage().pixelColor(center) == QColor("#ff0000")
