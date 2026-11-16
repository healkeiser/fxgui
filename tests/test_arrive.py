"""`fxstyle.arrive`: new content fades in as it rises, the old leaves.

Rows, panes and blocks used to just appear.
"""

# Third-party
import pytest
from qtpy.QtCore import QRect
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QApplication, QTreeWidgetItem, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFilteredTree, FXSkeleton

OLD = QColor("#ff0000")
NEW = QColor("#0000ff")


class Block(QWidget):
    """Paints one colour in a band from y = 10 down, x = 10 across."""

    colour = OLD

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(QRect(10, 10, self.width() - 20, 30), self.colour)
        painter.end()


@pytest.fixture
def block(qtbot, app_root):
    widget = Block()
    app_root.layout().addWidget(widget)
    app_root.resize(200, 120)
    app_root.show()
    qtbot.waitExposed(app_root)
    return widget


def _cover(widget):
    covers = widget.findChildren(fxstyle._ArrivalCover)
    return covers[0] if covers else None


def _at(qtbot, cover, shown):
    """Hold the cover at `shown` of its way, its own run stopped."""
    qtbot.waitUntil(lambda: cover._new is not None)
    for run in cover.findChildren(fxstyle.QVariantAnimation):
        run.stop()
    cover._step(shown)


def _blue(colour):
    """Whether the new content shows here, part faded over the ground."""
    return colour.blue() - colour.red() > 50


def _first_row(image, colour, x=50):
    return next(
        (y for y in range(image.height())
         if image.pixelColor(x, y) == colour), None)


def test_nothing_moves_under_reduced_motion(block):
    with fxstyle.arrive(block):
        block.colour = NEW

    assert _cover(block) is None


def test_the_old_leaves_and_the_new_rises_into_place(qtbot, motion, block):
    with fxstyle.arrive(block):
        block.colour = NEW
    cover = _cover(block)
    assert cover is not None

    _at(qtbot, cover, 0.0)
    start = block.grab().toImage()
    assert start.pixelColor(50, 25) == OLD

    _at(qtbot, cover, 0.15)
    rising = block.grab().toImage()
    _at(qtbot, cover, 1.0)
    landed = block.grab().toImage()

    assert landed.pixelColor(50, 25) == NEW
    # Mid-way the old is gone (it leaves in MOTION_INSTANT) and the new
    # stands lower than where it lands.
    assert _first_row(rising, OLD) is None
    assert _first_row(landed, NEW) == 10
    top = next(
        y for y in range(rising.height())
        if _blue(rising.pixelColor(50, y)))
    assert top > 10


def test_a_side_panel_slides_in_from_the_right(qtbot, motion, block):
    block.colour = NEW
    fxstyle.arrive(block, side=True)
    cover = _cover(block)

    _at(qtbot, cover, 0.1)
    image = block.grab().toImage()
    left = next(
        x for x in range(image.width())
        if _blue(image.pixelColor(x, 25)))

    assert left > 10 + 4


def test_the_cover_goes_once_arrived(qtbot, motion, block):
    fxstyle.arrive(block)

    qtbot.waitUntil(lambda: _cover(block) is None, timeout=2000)


def test_a_skeleton_leaving_lets_the_rows_arrive(qtbot, motion, app_root):
    panel = FXFilteredTree()
    QTreeWidgetItem(panel.tree, ["one"])
    app_root.layout().addWidget(panel)
    app_root.resize(300, 300)
    app_root.show()
    qtbot.waitExposed(app_root)
    FXSkeleton.cover(panel.tree)
    QApplication.processEvents()

    FXSkeleton.uncover(panel.tree)

    assert _cover(panel.tree.viewport()) is not None


def test_a_refill_arrives_filtered(qtbot, motion, app_root):
    panel = FXFilteredTree()
    app_root.layout().addWidget(panel)
    app_root.resize(300, 300)
    app_root.show()
    qtbot.waitExposed(app_root)
    panel.filter_bar.setText("tw")
    QApplication.processEvents()

    with panel.refill():
        panel.tree.clear()
        for name in ("one", "two"):
            QTreeWidgetItem(panel.tree, [name])

    shown = [
        panel.tree.topLevelItem(row).text(0)
        for row in range(panel.tree.topLevelItemCount())
        if not panel.tree.topLevelItem(row).isHidden()
    ]
    assert shown == ["two"]
    assert _cover(panel.tree.viewport()) is not None
