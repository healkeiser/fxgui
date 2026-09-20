"""A painted version picker: pixels, a menu, and a row that offers nothing."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QImage
from qtpy.QtWidgets import (
    QMenu,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
)

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


def _option_for(tree, index):
    """The style option the view would hand the delegate for `index`."""

    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    option.font = tree.font()
    tree.itemDelegate().initStyleOption(option, index)
    return option


def test_the_hint_makes_room_for_the_pill(qtbot):
    """A cell sized to its contents must not clip the control it paints."""

    picked, delegate, _ = _tree(qtbot, choices=["v001", "v002", "v003"])
    plain, _, _ = _tree(qtbot, choices=[])
    index = picked.model().index(0, 1)
    plain_index = plain.model().index(0, 1)
    assert delegate.sizeHint(
        _option_for(picked, index), index
    ).width() > delegate.sizeHint(
        _option_for(plain, plain_index), plain_index
    ).width()


def test_choosing_a_version_announces_it(qtbot, monkeypatch):
    """The delegate reports the choice; it never writes it to the model."""

    tree, delegate, item = _tree(qtbot, choices=["v001", "v002", "v003"])
    index = tree.model().index(0, 1)

    ran = []

    def choose(self, *args, **kwargs):
        ran.append(True)
        return next(
            action for action in self.actions() if action.text() == "v001"
        )

    monkeypatch.setattr(QMenu, "exec_", choose, raising=False)
    monkeypatch.setattr(QMenu, "exec", choose, raising=False)

    seen = []
    delegate.picked.connect(lambda idx, value: seen.append((idx.row(), value)))
    rect = delegate._picker_rect(_option_for(tree, index), index)
    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=rect.center())

    assert ran, "the patched exec method actually ran"
    assert seen == [(0, "v001")]
    assert item.text(1) == "v003"


def test_a_click_outside_the_pill_announces_nothing(qtbot):
    tree, delegate, _ = _tree(qtbot, choices=["v001", "v002", "v003"])
    seen = []
    delegate.picked.connect(lambda idx, value: seen.append(value))
    qtbot.mouseClick(
        tree.viewport(),
        Qt.LeftButton,
        pos=tree.visualRect(tree.model().index(0, 0)).center(),
    )
    assert seen == []
