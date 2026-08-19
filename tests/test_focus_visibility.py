"""Keyboard focus has to be visible, and it has to cost no space.

Regression: the theme carried fifteen `:focus` rules and none of them drew
anything on a real widget. Measured on the dark theme, tabbing onto a line
edit, a combo box, a spin box, a tree, a list, a table, a push button, a tool
button or a slider changed either nothing at all or nothing beyond a text
caret and an arrow icon, so a person navigating by keyboard could not see
where they were. `QPushButton:focus` recoloured the border to the same token
the unfocused rule already used.

Two properties are pinned here, and the second matters as much as the first:

- the indicator is visible, measured as pixels of the theme's accent gained
  when focus arrives, and
- the indicator costs nothing, measured as the widget's geometry and size
  hint being identical focused and unfocused. A ring that widens a border
  reflows the layout under the person's cursor.

The item view row is separate. A stylesheet cannot reach it (a
`::item:focus` rule matches no pixels) so FXThumbnailDelegate draws it, and
those tests scan the row's edges directly.

Set the ``FXGUI_SCREENSHOT_DIR`` environment variable to also dump the grabs
as PNGs for human inspection.
"""

# Built-in
import os

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate


def _save(image, name: str) -> None:
    directory = os.environ.get("FXGUI_SCREENSHOT_DIR")
    if directory:
        os.makedirs(directory, exist_ok=True)
        image.save(os.path.join(directory, name))


@pytest.fixture
def themed(qapp):
    """Apply the dark theme's stylesheet for the duration of one test."""

    previous = qapp.styleSheet()
    fxstyle._theme = "dark"
    fxstyle._invalidate_theme_namespace()
    qapp.setStyleSheet(fxstyle.load_stylesheet(theme="dark"))
    # A caret is not a focus indicator, and a blinking one makes a grab
    # depend on when it was taken
    flash = qapp.cursorFlashTime()
    qapp.setCursorFlashTime(0)
    yield qapp
    qapp.setCursorFlashTime(flash)
    qapp.setStyleSheet(previous)


def _count(image, color: QColor) -> int:
    """How many pixels of the image are exactly this colour."""

    target = color.rgb() & 0x00FFFFFF
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if (image.pixel(x, y) & 0x00FFFFFF) == target
    )


def _hosted(qtbot, widget):
    """Put a widget in a shown window behind a button that holds focus first.

    A widget cannot be measured unfocused unless something else in the same
    window has the focus, so the window comes with a sink button.
    """

    window = QWidget()
    layout = QVBoxLayout(window)
    sink = QPushButton("sink")
    layout.addWidget(sink)
    layout.addWidget(widget)
    window.resize(280, 260)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    # Focus only moves inside an active window, and activation is delivered
    # through the event loop rather than by the call itself
    window.activateWindow()
    QApplication.processEvents()
    _focus(sink)
    assert sink.hasFocus(), "the window never became active"
    return window, sink


def _focus(widget, reason=Qt.TabFocusReason) -> None:
    """Give a widget focus the way the Tab key would, and let it arrive."""

    widget.setFocus(reason)
    QApplication.processEvents()


def _drop_text_selection(widget) -> None:
    """Clear the select-all that focus performs on a text entry widget.

    A spin box highlights its contents when focus arrives, and the highlight
    is drawn in accent_primary. Left in place it would pass a ring test on a
    theme that draws no ring at all, so it is cleared before measuring.
    """

    line_edit = widget
    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        line_edit = widget.lineEdit()
    if isinstance(line_edit, QLineEdit):
        line_edit.deselect()
        QApplication.processEvents()


def _combo():
    widget = QComboBox()
    widget.addItems(["one", "two"])
    return widget


def _tree():
    widget = QTreeWidget()
    widget.setHeaderLabels(["A", "B"])
    for row in range(4):
        QTreeWidgetItem(widget, [f"row {row}", "x"])
    widget.setCurrentItem(widget.topLevelItem(1))
    return widget


def _list():
    widget = QListWidget()
    widget.addItems([f"item {row}" for row in range(4)])
    widget.setCurrentRow(1)
    return widget


def _table():
    widget = QTableWidget(4, 2)
    for row in range(4):
        for column in range(2):
            widget.setItem(row, column, QTableWidgetItem(f"{row},{column}"))
    widget.setCurrentCell(1, 0)
    return widget


def _tabs():
    widget = QTabWidget()
    for name in ("First", "Second", "Third"):
        widget.addTab(QWidget(), name)
    return widget


def _group():
    widget = QGroupBox("Group")
    # A plain group box is NoFocus, so only a checkable one can show a ring
    widget.setCheckable(True)
    QVBoxLayout(widget).addWidget(QPushButton("inner"))
    return widget


# Every focusable class the theme styles. QScrollBar and a plain QGroupBox
# are absent because Qt gives both NoFocus, so neither can ever be tabbed to
FOCUSABLE = [
    ("line_edit", QLineEdit),
    ("plain_text_edit", QPlainTextEdit),
    ("text_edit", QTextEdit),
    ("combo_box", _combo),
    ("spin_box", QSpinBox),
    ("double_spin_box", QDoubleSpinBox),
    ("push_button", lambda: QPushButton("Button")),
    ("tool_button", QToolButton),
    ("check_box", lambda: QCheckBox("Check me")),
    ("radio_button", lambda: QRadioButton("Radio")),
    ("slider", lambda: QSlider(Qt.Horizontal)),
    ("tree", _tree),
    ("list", _list),
    ("table", _table),
    ("tabs", _tabs),
    ("group_box", _group),
]


def _focus_target(widget):
    """What actually receives focus for this widget.

    A QTabWidget hands focus to its tab bar, which is where the ring is drawn.
    """

    if isinstance(widget, QTabWidget):
        return widget.tabBar()
    return widget


@pytest.mark.parametrize(
    "name,factory", FOCUSABLE, ids=[name for name, _ in FOCUSABLE]
)
def test_focus_gains_accent_pixels(qtbot, themed, name, factory):
    """Tabbing onto the widget has to change what is on screen."""

    accent = QColor(fxstyle.get_theme_colors()["accent_primary"])
    widget = factory()
    # The window owns the widget, so it has to outlive the measurement
    window, _ = _hosted(qtbot, widget)

    before = widget.grab().toImage()
    unfocused = _count(before, accent)

    _focus(_focus_target(widget))
    assert _focus_target(widget).hasFocus()
    _drop_text_selection(widget)
    after = widget.grab().toImage()
    focused = _count(after, accent)

    _save(before, f"focus_{name}_unfocused.png")
    _save(after, f"focus_{name}_focused.png")

    assert focused > unfocused, (
        f"{name}: focus added no accent pixels "
        f"({unfocused} -> {focused}), the indicator is invisible"
    )


@pytest.mark.parametrize(
    "name,factory", FOCUSABLE, ids=[name for name, _ in FOCUSABLE]
)
def test_focus_moves_nothing(qtbot, themed, name, factory):
    """The border box has to be identical focused and unfocused.

    A ring that adds width reflows every widget beside it the moment focus
    lands, so the geometry and the size hint are both pinned.
    """

    widget = factory()
    window, _ = _hosted(qtbot, widget)

    geometry = widget.geometry()
    hint = widget.sizeHint()

    _focus(_focus_target(widget))

    assert widget.geometry() == geometry, f"{name}: the widget moved"
    assert widget.sizeHint() == hint, f"{name}: the size hint changed"


###### FXThumbnailDelegate's current row


def _delegate_tree(qtbot, selected: bool):
    """A two-column tree whose row 1 is current, with the delegate installed.

    The selection is set before the caller grabs anything, so focus is the
    only thing that changes between the two grabs.
    """

    tree = QTreeWidget()
    tree.setHeaderLabels(["Shot", "Status"])
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    for row in range(4):
        item = QTreeWidgetItem(tree, [f"sh{row:03d}0", "ok"])
        item.setData(
            0, FXThumbnailDelegate.DESCRIPTION_ROLE, f"Description {row}"
        )
    FXThumbnailDelegate.apply_transparent_selection(tree)

    window, sink = _hosted(qtbot, tree)
    # Returned to the caller so the window that owns the tree stays alive
    tree._fxgui_test_window = window
    # Both columns need real width: the ring is scanned on each side of the
    # boundary between them
    window.resize(460, 320)
    QApplication.processEvents()
    tree.header().setStretchLastSection(True)
    tree.setColumnWidth(0, 220)
    tree.setCurrentItem(tree.topLevelItem(1))
    if not selected:
        tree.clearSelection()
    _focus(sink)
    return tree, tree.model().index(1, 0)


def _near(image, x: int, y: int, color: QColor, tolerance: int = 40) -> bool:
    """Whether a pixel is this colour, allowing for an antialiased stroke."""

    found = QColor(image.pixel(x, y))
    return (
        abs(found.red() - color.red()) <= tolerance
        and abs(found.green() - color.green()) <= tolerance
        and abs(found.blue() - color.blue()) <= tolerance
    )


def test_delegate_outlines_the_current_row(qtbot, themed):
    """The row the keyboard is on has to be visible without being selected.

    This is the case the stylesheet cannot serve and the one that decides
    whether a tree can be navigated by keyboard at all.
    """

    accent = QColor(fxstyle.get_theme_colors()["accent_primary"])
    tree, index = _delegate_tree(qtbot, selected=False)

    before = tree.viewport().grab().toImage()
    _focus(tree)
    after = tree.viewport().grab().toImage()

    _save(before, "focus_delegate_row_unfocused.png")
    _save(after, "focus_delegate_row_unselected.png")

    row = tree.visualRect(index)
    assert _count(after, accent) > _count(before, accent)
    # The ring sits on the row's own top edge, not somewhere in the viewport
    assert any(
        _near(after, x, row.top(), accent)
        for x in range(row.left() + 8, row.right() - 8)
    )


def test_delegate_ring_reads_on_a_selected_row(qtbot, themed):
    """A selected row is already filled with accent_primary, so an accent ring
    on top of it would be invisible. The ring switches to the token that
    exists to be read against that fill."""

    theme = fxstyle.get_theme_colors()
    on_accent = QColor(theme["text_on_accent_primary"])
    tree, index = _delegate_tree(qtbot, selected=True)

    before = tree.viewport().grab().toImage()
    _focus(tree)
    after = tree.viewport().grab().toImage()
    _save(after, "focus_delegate_row_selected.png")

    row = tree.visualRect(index)
    edge = [
        x
        for x in range(row.left() + 8, row.right() - 8)
        if _near(after, x, row.top(), on_accent)
    ]
    assert edge, "no ring on the selected row's top edge"
    # And it was not there before focus arrived
    assert not [
        x
        for x in range(row.left() + 8, row.right() - 8)
        if _near(before, x, row.top(), on_accent)
    ]


def test_delegate_ring_spans_the_whole_row(qtbot, themed):
    """The ring belongs to the row, but a delegate paints one cell at a time.

    Each cell draws its own segment, so the two failures to rule out are a
    ring that stops at the column boundary and a stroked rectangle per cell,
    which would draw a line down that boundary.
    """

    accent = QColor(fxstyle.get_theme_colors()["accent_primary"])
    tree, index = _delegate_tree(qtbot, selected=False)
    _focus(tree)
    image = tree.viewport().grab().toImage()

    row = tree.visualRect(index)
    boundary = tree.columnViewportPosition(1)
    assert row.left() < boundary < tree.viewport().width(), "no second column"

    on_edge = [
        x
        for x in range(2, tree.viewport().width() - 2)
        if _near(image, x, row.top(), accent)
    ]
    assert [x for x in on_edge if x < boundary], "no ring on the first column"
    assert [x for x in on_edge if x > boundary], "no ring on the last column"
    # Straight through the boundary rather than stopping either side of it
    assert all(_near(image, x, row.top(), accent) for x in range(
        boundary - 2, boundary + 3
    )), "the ring breaks at the column boundary"

    interior = range(row.top() + 6, row.bottom() - 5)
    stray = [
        y
        for y in interior
        if any(_near(image, boundary + dx, y, accent) for dx in (-1, 0, 1))
    ]
    assert not stray, f"a vertical line runs down the column boundary: {stray}"


def test_delegate_draws_no_ring_without_focus(qtbot, themed):
    """The ring means the keyboard is here, so a view nobody is on must not
    draw one even though it still has a current row."""

    accent = QColor(fxstyle.get_theme_colors()["accent_primary"])
    tree, index = _delegate_tree(qtbot, selected=False)
    image = tree.viewport().grab().toImage()

    row = tree.visualRect(index)
    assert not [
        x
        for x in range(row.left() + 8, row.right() - 8)
        if _near(image, x, row.top(), accent)
    ]


def test_delegate_row_keeps_its_height_when_focused(qtbot, themed):
    """The ring is stroked inside the row rect, so it costs no space."""

    from qtpy.QtWidgets import QStyleOptionViewItem

    tree, index = _delegate_tree(qtbot, selected=False)
    delegate = tree.itemDelegate()

    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    unfocused_hint = delegate.sizeHint(option, index)
    unfocused_rect = tree.visualRect(index)

    _focus(tree)

    option.rect = tree.visualRect(index)
    assert delegate.sizeHint(option, index) == unfocused_hint
    assert tree.visualRect(index) == unfocused_rect


def test_focus_row_is_read_from_the_view_not_the_cell(qtbot, themed):
    """`State_HasFocus` is only ever set on the current cell.

    Measured: in a three-column tree with the row selected, column 0 carries
    the flag and columns 1 and 2 do not. A ring drawn from that flag alone
    would stop at the first column boundary, so the delegate asks the view
    which row is current instead.
    """

    from qtpy.QtWidgets import QStyle, QStyleOptionViewItem

    tree, index = _delegate_tree(qtbot, selected=True)
    delegate = tree.itemDelegate()
    _focus(tree)

    option = QStyleOptionViewItem()
    option.widget = tree

    for column in range(tree.columnCount()):
        cell = tree.model().index(1, column)
        assert delegate._is_focus_row(option, cell), f"column {column}"

    # Not a claim about the delegate, a claim about Qt: only one cell of the
    # row carries the flag the naive implementation would have used
    flagged = []

    class _Spy(type(delegate)):
        def paint(self, painter, opt, idx):
            if opt.state & QStyle.State_HasFocus:
                flagged.append((idx.row(), idx.column()))
            super().paint(painter, opt, idx)

    tree.setItemDelegate(_Spy(tree))
    tree.viewport().grab()
    assert flagged == [(1, 0)], flagged

    # Other rows are not the focus row
    assert not delegate._is_focus_row(option, tree.model().index(0, 0))


def test_focus_row_is_empty_when_the_view_is_not_focused(qtbot, themed):
    """The row check has to gate on the view holding focus, not just on a
    current index existing."""

    from qtpy.QtWidgets import QStyleOptionViewItem

    tree, index = _delegate_tree(qtbot, selected=True)
    delegate = tree.itemDelegate()

    option = QStyleOptionViewItem()
    option.widget = tree

    assert not tree.hasFocus()
    assert not delegate._is_focus_row(option, index)

    _focus(tree)
    assert delegate._is_focus_row(option, index)


def test_ring_paints_on_every_shipped_theme(qtbot, qapp):
    """A theme where the indicator does not appear is a failure, not a
    caveat, so every shipped theme is rendered rather than only reasoned
    about. The contrast side of this lives in test_style_data.py; what is
    measured here is that the pixels arrive at all.

    Only the row's top edge is scanned: eleven full-image sweeps would cost
    more than the coverage is worth.
    """

    previous = qapp.styleSheet()
    themes = fxstyle.get_available_themes()
    assert len(themes) == 11, f"theme count changed: {themes}"

    try:
        for theme_name in themes:
            fxstyle._theme = theme_name
            fxstyle._invalidate_theme_namespace()
            qapp.setStyleSheet(fxstyle.load_stylesheet(theme=theme_name))
            accent = QColor(fxstyle.get_theme_colors()["accent_primary"])

            tree, index = _delegate_tree(qtbot, selected=False)
            row = tree.visualRect(index)
            span = range(row.left() + 8, row.right() - 8)

            before = tree.viewport().grab().toImage()
            assert not [
                x for x in span if _near(before, x, row.top(), accent)
            ], f"{theme_name}: a ring is drawn without focus"

            _focus(tree)
            after = tree.viewport().grab().toImage()
            assert [
                x for x in span if _near(after, x, row.top(), accent)
            ], f"{theme_name}: the focused row draws no ring"
    finally:
        qapp.setStyleSheet(previous)
        fxstyle._theme = None
        fxstyle._invalidate_theme_namespace()
