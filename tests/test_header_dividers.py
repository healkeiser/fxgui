"""A header draws a divider between sections, where a column resizes."""

# Third-party
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget

# Internal
from fxgui import fxstyle


def test_a_divider_stands_between_sections_and_not_after_the_last(
        qtbot, app_root):
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Version", "Artist"])
    tree.header().setStretchLastSection(False)
    app_root.layout().addWidget(tree)
    app_root.resize(500, 200)
    app_root.show()
    qtbot.waitExposed(app_root)
    header = tree.header()
    shot = header.grab().toImage()
    border = QColor(str(fxstyle.colors().border)).name()
    middle = header.height() // 2

    def edge(section):
        return header.sectionViewportPosition(section) + header.sectionSize(
            section) - 1

    assert shot.pixelColor(edge(0), middle).name() == border
    assert shot.pixelColor(edge(1), middle).name() == border
    assert shot.pixelColor(edge(2), middle).name() != border
