"""A painted version picker: pixels, a menu, and a row that offers nothing."""

from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QFont, QImage
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


def _raw_option_for(tree, index):
    """The option the view really hands `editorEvent` and `sizeHint`.

    Qt fills in the rect and the view's own font and stops there; it never
    runs the delegate's `initStyleOption`, so no per-row `FontRole` reaches
    this one.
    """

    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    option.font = tree.font()
    return option


def _option_for(tree, index):
    """The option `paint` works from: initialised, so `FontRole` applies."""

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


def _opened_menu(qtbot, monkeypatch, *, choices, unavailable):
    """Each shown action's text and enabled state, read while the menu lives."""

    tree, delegate, item = _tree(qtbot, choices=choices)
    item.setData(1, FXThumbnailDelegate.PICKER_UNAVAILABLE_ROLE, unavailable)
    index = tree.model().index(0, 1)
    shown = []

    def capture(self, *args, **kwargs):
        shown.extend((a.text(), a.isEnabled()) for a in self.actions())
        return None

    monkeypatch.setattr(QMenu, "exec_", capture, raising=False)
    monkeypatch.setattr(QMenu, "exec", capture, raising=False)
    rect = delegate._picker_rect(_option_for(tree, index), index)
    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=rect.center())
    return shown


def test_an_unavailable_choice_is_shown_greyed_with_its_reason(
    qtbot, monkeypatch
):
    shown = _opened_menu(
        qtbot,
        monkeypatch,
        choices=["v001", "v002", "v003"],
        unavailable={"v001": "no files on disk"},
    )
    assert shown == [
        ("v001\tno files on disk", False),
        ("v002", True),
        ("v003", True),
    ]


def test_a_row_whose_other_choices_are_unavailable_still_paints_a_pill(
    qtbot,
):
    """Two choices with one unavailable is still a menu worth opening: it
    says why the other version cannot be picked."""

    tree, delegate, item = _tree(qtbot, choices=["v001", "v003"])
    item.setData(
        1,
        FXThumbnailDelegate.PICKER_UNAVAILABLE_ROLE,
        {"v001": "no files on disk"},
    )
    index = tree.model().index(0, 1)
    assert delegate._picker_rect(_option_for(tree, index), index) is not None


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


def test_the_drawn_pill_and_the_clickable_one_are_the_same_pill(qtbot):
    """A row with its own font drew one pill and hit-tested another.

    `paint` is handed an option run through `initStyleOption`, which is what
    applies a row's `FontRole`. `sizeHint` and `editorEvent` are handed the
    view's raw option, which is not. Measured against two fonts the same pill
    lands in two places, and the gap is dead pixels that look clickable.
    """

    tree, delegate, item = _tree(qtbot, choices=["v001", "v002", "v003"])
    big = QFont()
    big.setPointSize(18)
    big.setBold(True)
    item.setData(1, Qt.ItemDataRole.FontRole, big)
    index = tree.model().index(0, 1)

    # editorEvent fills the raw option in before it hit-tests.
    assert delegate._picker_rect(
        delegate._init(_raw_option_for(tree, index), index), index
    ) == delegate._picker_rect(_option_for(tree, index), index)


def test_a_click_on_a_big_font_pill_opens_it(qtbot, monkeypatch):
    """The same defect stated as the artist meets it: a click that misses."""

    tree, delegate, item = _tree(qtbot, choices=["v001", "v002", "v003"])
    big = QFont()
    big.setPointSize(18)
    big.setBold(True)
    item.setData(1, Qt.ItemDataRole.FontRole, big)
    index = tree.model().index(0, 1)

    ran = []

    def choose(self, *args, **kwargs):
        ran.append(True)
        return next(a for a in self.actions() if a.text() == "v001")

    monkeypatch.setattr(QMenu, "exec_", choose, raising=False)
    monkeypatch.setattr(QMenu, "exec", choose, raising=False)

    seen = []
    delegate.picked.connect(lambda idx, value: seen.append(value))

    # Just inside the left edge of the pill the row actually paints.
    drawn = delegate._picker_rect(_option_for(tree, index), index)
    qtbot.mouseClick(
        tree.viewport(),
        Qt.LeftButton,
        pos=QPoint(drawn.left() + 2, drawn.center().y()),
    )

    assert ran, "the patched exec method actually ran"
    assert seen == ["v001"]


def _ink_right_edge(tree, rect, background) -> int:
    """The rightmost column inside `rect` painting something over the row."""

    image: QImage = tree.viewport().grab().toImage()
    for x in range(rect.right(), rect.left() - 1, -1):
        if any(
            image.pixel(x, y) != background
            for y in range(rect.top() + 2, rect.bottom() - 1)
        ):
            return x
    return -1


def test_a_row_with_nothing_to_offer_lines_up_with_the_pills(qtbot):
    """A column that mixes pills and plain values keeps the values in line.

    The pill is anchored to the cell's right edge, so a left-aligned plain
    value on a row with only one version stepped back to the left and broke
    the column. The tolerance is one glyph's worth of side bearing: the
    measurement is painted ink and the target is a layout edge.
    """

    plain, delegate, _ = _tree(qtbot, choices=["v001"])
    index = plain.model().index(0, 1)
    cell = plain.visualRect(index)
    shot: QImage = plain.viewport().grab().toImage()

    edge = _ink_right_edge(plain, cell, shot.pixel(cell.left() + 2, cell.top() + 1))
    expected = cell.right() - delegate._picker_text_inset()
    assert edge != -1, "the plain value painted nothing"
    assert abs(edge - expected) <= 8, (edge, expected)
