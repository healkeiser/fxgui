"""A header's resizable column edge lights in the accent under the pointer."""

# Third-party
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem

# Internal
from fxgui import fxstyle

from _helpers import near, themed_window


def _tree(qtbot):
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Version", "Artist"])
    QTreeWidgetItem(tree, ["shot", "v001", "someone"])
    tree.header().setSectionResizeMode(QHeaderView.Interactive)
    tree.setColumnWidth(0, 120)
    window = themed_window(qtbot, "dark", tree)
    header = tree.header()
    marks = [
        child for child in header.viewport().children()
        if type(child).__name__ == "_ResizeMark"
    ]
    assert marks, "the header shows with no resize mark"
    return window, header, marks[0]


def test_an_edge_lights_under_the_pointer_and_clears_off_it(qtbot):
    _window, header, mark = _tree(qtbot)
    edge = header.sectionViewportPosition(0) + header.sectionSize(0)
    middle = header.height() // 2
    QTest.mouseMove(header.viewport(), QPoint(edge - 1, middle))
    qtbot.waitUntil(lambda: mark._x == edge, timeout=1000)
    image = mark.grab().toImage()
    accent = QColor(fxstyle.colors().accent_primary)
    assert near(image.pixelColor(edge, middle), accent, 40)
    QTest.mouseMove(header.viewport(), QPoint(edge // 2, middle))
    qtbot.waitUntil(lambda: mark._x is None, timeout=1000)


def test_a_fixed_column_edge_stays_dark(qtbot):
    _window, header, mark = _tree(qtbot)
    header.setSectionResizeMode(0, QHeaderView.Fixed)
    edge = header.sectionViewportPosition(0) + header.sectionSize(0)
    QTest.mouseMove(header.viewport(), QPoint(edge - 1, header.height() // 2))
    qtbot.wait(50)
    assert mark._x is None
