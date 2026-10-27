"""A header is flat: one rule under it, no divider between sections."""

# Third-party
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget

# Internal
from fxgui import fxstyle


def test_no_divider_stands_between_sections(qtbot, app_root):
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

    for section in range(3):
        at = shot.pixelColor(edge(section), middle).name()
        assert at != border
        assert at == shot.pixelColor(edge(section) - 2, middle).name()
        assert shot.pixelColor(edge(section), header.height() - 1).name() == (
            border)
