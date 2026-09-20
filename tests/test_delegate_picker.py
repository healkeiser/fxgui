"""A painted version picker: pixels, a menu, and a row that offers nothing."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem

from fxgui.fxwidgets import FXThumbnailDelegate


def _tree(qtbot, *, choices):
    """A one-row, two-column tree whose second column may hold a picker."""

    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Version"])
    tree.setRootIsDecorated(False)
    tree.header().setStretchLastSection(False)
    tree.setColumnWidth(0, 240)
    tree.setColumnWidth(1, 90)
    tree.resize(360, 120)
    delegate = FXThumbnailDelegate()
    delegate.show_thumbnail = False
    delegate.picker_column = 1
    tree.setItemDelegate(delegate)
    item = QTreeWidgetItem(tree, ["Beauty", "v003"])
    item.setData(1, FXThumbnailDelegate.PICKER_TEXT_ROLE, "v003")
    item.setData(1, FXThumbnailDelegate.PICKER_CHOICES_ROLE, choices)
    qtbot.addWidget(tree)
    tree.show()
    qtbot.waitExposed(tree)
    return tree, delegate, item


def _painted(tree, rect) -> set:
    """The distinct colours the viewport shows inside `rect`."""

    image: QImage = tree.viewport().grab().toImage()
    return {
        image.pixel(x, y)
        for x in range(rect.left(), rect.right() + 1)
        for y in range(rect.top(), rect.bottom() + 1)
    }


def test_a_row_with_several_versions_paints_a_pill(qtbot):
    """The pill region carries more than a plain cell paints there."""

    picked, _, _ = _tree(qtbot, choices=["v001", "v002", "v003"])
    plain, _, _ = _tree(qtbot, choices=[])
    rect = picked.visualRect(picked.model().index(0, 1))
    assert len(_painted(picked, rect)) > len(_painted(plain, rect))


def test_a_row_with_one_version_paints_no_pill(qtbot):
    """One choice is not a choice, so the cell stays plain text."""

    single, _, _ = _tree(qtbot, choices=["v003"])
    plain, _, _ = _tree(qtbot, choices=[])
    rect = single.visualRect(single.model().index(0, 1))
    assert _painted(single, rect) == _painted(plain, rect)


def test_a_row_with_no_choices_paints_no_pill(qtbot):
    """The 1.x defect written as a test: no choices, no control."""

    none, _, _ = _tree(qtbot, choices=[])
    rect = none.visualRect(none.model().index(0, 1))
    image = none.viewport().grab().toImage()
    assert image.pixel(rect.right() - 2, rect.center().y()) == image.pixel(
        rect.right() - 2, rect.top() + 1
    )
