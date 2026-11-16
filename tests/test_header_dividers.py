"""A header is flat: one rule under it, no divider between sections."""

# Third-party
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget

# Internal
from fxgui import fxstyle


def test_only_the_first_column_s_rule_runs_through_the_header(
    qtbot, app_root
):
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
        beside = shot.pixelColor(edge(section) - 2, middle).name()
        # The first column's rule runs on through the header, as through
        # its rows; no other section stands a divider.
        assert (at != beside) == (section == 0)
        assert shot.pixelColor(edge(section), header.height() - 1).name() == (
            border)
