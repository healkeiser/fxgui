"""The web look's details that fxgui takes from the studio's tracker."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QHBoxLayout,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import (
    FXKeycap,
    FXMeterBar,
    FXMeterShare,
    FXTagChip,
    FXThumbnailDelegate,
)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_toned_and_dimmed_read_and_rank_between_text_and_muted(theme):
    tokens = fxstyle._token_map(theme)
    surface = tokens["@surface"]
    ratio = fxstyle.get_contrast_ratio
    text, toned = tokens["@text"], tokens["@text_toned"]
    muted, dimmed = tokens["@text_muted"], tokens["@text_dimmed"]
    for ink in (toned, dimmed):
        assert ratio(ink, surface) >= fxstyle.TEXT_CONTRAST, (theme, ink)
    # Text, toned, muted, dimmed: each no louder than the one before.
    assert ratio(text, surface) >= ratio(toned, surface) >= ratio(muted, surface)
    assert ratio(muted, surface) >= ratio(dimmed, surface)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_meter_s_fill_reads_at_3_to_1_on_its_track(theme):
    tokens = fxstyle._token_map(theme)
    assert fxstyle.get_contrast_ratio(
        tokens["@accent_primary"], tokens["@meter_track"]) >= 2.99


def test_a_dark_card_is_raised_a_light_one_is_the_pane():
    dark, light = fxstyle._token_map("dark"), fxstyle._token_map("light")
    assert dark["@card"] != dark["@surface"]
    assert light["@card"] == light["@surface"]


# The windows a test shows, held until the test ends.
_HELD = []


@pytest.fixture(autouse=True)
def _release():
    yield
    _HELD.clear()


def _shown(qtbot, *widgets):
    window = QWidget()
    _HELD.append(window)
    fxstyle.register_themed_root(window)
    row = QHBoxLayout(window)
    for widget in widgets:
        row.addWidget(widget)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_a_compact_button_is_24_px_with_small_text(qtbot):
    button = QPushButton("Reply")
    fxstyle.mark_compact(button)
    _shown(qtbot, button)
    assert button.height() == fxstyle.COMPACT_HEIGHT
    assert button.font().pixelSize() == fxstyle.FONT_SIZE - 1


def test_a_keycap_is_20_px_tall_and_a_lone_key_square(qtbot):
    cap = FXKeycap("K")
    _shown(qtbot, cap)
    label = cap.findChild(QLabel)
    assert (label.width(), label.height()) == (20, 20)


def test_a_dense_tree_is_one_row_size_under(qtbot):
    fxstyle.apply_row_size("normal", save=False)
    dense, plain = QTreeWidget(), QTreeWidget()
    for tree in (dense, plain):
        QTreeWidgetItem(tree, ["shot"])
    fxstyle.mark_dense(dense)
    _shown(qtbot, dense, plain)
    height = lambda tree: tree.visualItemRect(tree.topLevelItem(0)).height()  # noqa: E731
    assert (height(dense), height(plain)) == (28, 36)
    assert fxstyle.row_height(dense) == 28 and fxstyle.row_height() == 36


def test_a_flush_view_draws_no_frame(qtbot):
    tree = QTreeWidget()
    fxstyle.mark_flush(tree)
    _shown(qtbot, tree)
    assert tree.frameWidth() == 0


def test_column_lines_rule_the_first_column_always_the_rest_on_demand(qtbot):
    tree = QTreeWidget()
    tree.setColumnCount(3)
    _shown(qtbot, tree)
    try:
        fxstyle.apply_column_lines(False, save=False)
        assert [fxstyle._column_ruled(tree, c) for c in range(3)] == [
            True, False, False]
        fxstyle.apply_column_lines(True, save=False)
        assert [fxstyle._column_ruled(tree, c) for c in range(3)] == [
            True, True, False]
    finally:
        fxstyle.apply_column_lines(False, save=False)


def test_a_select_s_value_reads_in_the_strong_ink(qtbot):
    combo = QComboBox()
    combo.addItems(["HHHHHH"])
    _shown(qtbot, combo)
    image = combo.grab().toImage()
    brightest = max(
        QColor(image.pixel(x, y)).lightness()
        for y in range(image.height()) for x in range(8, 60))
    assert brightest == QColor(fxstyle.colors().text_strong).lightness()


def test_a_chip_is_neutral_with_an_optional_dot(qtbot):
    plain = FXTagChip("comp", removable=False)
    dotted = FXTagChip("WIP", color="feedback_warning_foreground")
    _shown(qtbot, plain, dotted)
    assert plain.dot is None and dotted.dot is not None
    assert dotted.dot.size().width() == 8


def test_a_meter_splits_its_shares_and_stops_full():
    bar = FXMeterBar([FXMeterShare(5), FXMeterShare(3, faint=True)], maximum=16)
    assert bar.fractions() == [5 / 16, 3 / 16]
    assert FXMeterBar([30], maximum=20).fractions() == [1.0]
    assert FXMeterBar(compact=True).height() == 4


def _thumbnail_tree(qtbot):
    tree = QTreeWidget()
    tree.setColumnCount(2)
    delegate = FXThumbnailDelegate(tree)
    tree.setItemDelegate(delegate)
    item = QTreeWidgetItem(tree, ["sh0010", "1001"])
    _shown(qtbot, tree)
    return tree, delegate, item


def test_a_row_s_own_weight_beats_the_emphasis(qtbot):
    tree, delegate, item = _thumbnail_tree(qtbot)
    index = tree.model().index(0, 0)
    option = QStyleOptionViewItem()
    option.font = tree.font()
    emphasis = fxstyle.drawn_weight(fxstyle.EMPHASIS_WEIGHT)
    assert delegate._title_font(option, index).weight() == emphasis
    light = QFont(tree.font())
    light.setWeight(QFont.Weight(fxstyle.drawn_weight(fxstyle.BODY_WEIGHT)))
    item.setFont(0, light)
    assert delegate._title_font(option, index).weight() == (
        fxstyle.drawn_weight(fxstyle.BODY_WEIGHT))


def test_align_column_aligns_the_cells_and_the_header(qtbot):
    tree, delegate, _item = _thumbnail_tree(qtbot)
    delegate.align_column(tree, 1, Qt.AlignRight, tabular=True)
    header = tree.model().headerData(1, Qt.Horizontal, Qt.TextAlignmentRole)
    assert int(header) & int(Qt.AlignHorizontal_Mask) == int(Qt.AlignRight)
    assert 1 in delegate._tabular_columns


def test_a_focus_ring_shows_for_the_keyboard_only(qtbot):
    field, button = QLineEdit(), QPushButton("Cancel")
    window = _shown(qtbot, field, button)
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    fxstyle.focus_visible(field)
    field.setFocus()
    QTest.keyClick(window, Qt.Key_Tab)
    ring = fxstyle._FocusRing._shown
    assert ring is not None and ring._target is button
    grow = fxstyle.FOCUS_RING_WIDTH
    assert ring.geometry() == button.geometry().adjusted(-grow, -grow, grow, grow)
    QTest.mouseClick(field, Qt.LeftButton)
    assert fxstyle._FocusRing._shown is None


@pytest.mark.parametrize("dense_first", [True, False])
def test_a_summary_row_on_a_dense_view_is_a_dense_row(qtbot, dense_first):
    from fxgui.fxwidgets import FXSummaryRow

    fxstyle.apply_row_size("normal", save=False)
    tree = QTreeWidget()
    QTreeWidgetItem(tree, ["shot"])
    if dense_first:
        fxstyle.mark_dense(tree)
    summary = FXSummaryRow(tree)
    if not dense_first:
        fxstyle.mark_dense(tree)
    _shown(qtbot, tree)
    qtbot.waitUntil(lambda: summary.height() == 28)
    assert tree.viewportMargins().bottom() == 28


def test_a_section_wears_its_own_ink(qtbot):
    from qtpy.QtWidgets import QTableWidget

    table = QTableWidget(1, 2)
    table.setHorizontalHeaderLabels(["HHHH", "HHHH"])
    header = table.horizontalHeader()
    fxstyle.ink_section(header, 1, "accent_primary")
    _shown(qtbot, table)
    image = header.grab().toImage()

    def inks(section):
        left = header.sectionViewportPosition(section)
        return {
            QColor(image.pixel(x, y)).name()
            for y in range(image.height())
            for x in range(left + 4, left + 60)
        }

    assert fxstyle.colors().accent_primary.lower() in inks(1)
    assert fxstyle.colors().accent_primary.lower() not in inks(0)
    with pytest.raises(ValueError):
        fxstyle.ink_section(header, 0, "nope")


def test_an_elided_label_at_its_size_hint_shows_its_whole_text(qtbot):
    from fxgui.fxwidgets import FXElidedLabel

    label = FXElidedLabel("Valentin Beaumont · May 11")
    _shown(qtbot, label)
    label.resize(label.sizeHint())
    assert label.elided_text() == label.text()
    label.resize(label.sizeHint().width() - 20, label.height())
    assert label.elided_text() != label.text()


def _ask(qtbot, **options):
    from fxgui.fxwidgets import FXConfirmDialog

    dialog = FXConfirmDialog(title="Close sh0010?", **options)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.activateWindow()
    qtbot.waitUntil(dialog.isActiveWindow)
    return dialog


def test_a_plain_confirm_takes_its_verb_on_enter(qtbot):
    dialog = _ask(qtbot, verb="Save", alternative="Discard",
                  alternative_tone="danger")
    assert dialog.verb_button.property("fxRole") == "primary"
    assert dialog.alternative_button.property("fxRole") == "danger"
    # The verb at the right end, the alternative at the left.
    assert dialog.alternative_button.x() < dialog.cancel_button.x() < (
        dialog.verb_button.x())
    QTest.keyClick(dialog.focusWidget(), Qt.Key_Return)
    assert dialog.result() == dialog.VERB and dialog.choice() == "verb"


def test_a_third_choice_closes_with_its_own_answer(qtbot):
    dialog = _ask(qtbot, verb="Save", alternative="Discard")
    dialog.alternative_button.click()
    assert dialog.result() == dialog.ALTERNATIVE
    assert dialog.choice() == "alternative"


def test_a_danger_confirm_takes_cancel_on_enter_and_escape(qtbot):
    dialog = _ask(qtbot, verb="Replace", tone="danger")
    QTest.keyClick(dialog.focusWidget(), Qt.Key_Return)
    assert dialog.choice() == "cancel"
    other = _ask(qtbot, verb="Replace")
    QTest.keyClick(other, Qt.Key_Escape)
    assert other.choice() == "cancel"


def test_a_confirm_refuses_an_unknown_tone_or_default():
    from fxgui.fxwidgets import FXConfirmDialog

    for options in ({"tone": "loud"}, {"default": "maybe"},
                    {"default": "alternative"}):
        with pytest.raises(ValueError):
            FXConfirmDialog(title="?", **options)


@pytest.mark.parametrize("tabular", [True, False])
def test_a_column_sized_to_its_contents_draws_its_text_whole(qtbot, tabular):
    tree = QTreeWidget()
    tree.setColumnCount(2)
    tree.setHeaderLabels(["Shot", "Frames"])
    delegate = FXThumbnailDelegate(tree)
    tree.setItemDelegate(delegate)
    for text in ("1001-1002", "88888"):
        QTreeWidgetItem(tree, ["sh0010", text])
    delegate.align_column(tree, 1, Qt.AlignRight, tabular=tabular)
    _shown(qtbot, tree)
    tree.header().setStretchLastSection(False)
    tree.resizeColumnToContents(1)
    index = tree.model().index(0, 1)
    option = QStyleOptionViewItem()
    option.font = tree.font()
    option.rect = tree.visualRect(index)
    needed = delegate._text_cell_width(option, index)
    assert tree.columnWidth(1) >= needed


def test_a_confirm_card_moves_by_its_title_and_stays_owned(qtbot):
    from qtpy.QtCore import QPoint

    from fxgui.fxwidgets import FXConfirmDeleteDialog

    parent = QWidget()
    parent.resize(800, 600)
    qtbot.addWidget(parent)
    parent.show()
    dialog = FXConfirmDeleteDialog(parent, title="Delete SH010?")
    dialog.show()
    qtbot.waitExposed(dialog)
    # Owned by its parent's window: on Windows it stays above that window.
    assert dialog.windowHandle().transientParent() is parent.windowHandle()
    title = dialog.title_label
    start = dialog.pos()
    QTest.mousePress(title, Qt.LeftButton, pos=QPoint(10, 5))
    QTest.mouseMove(title, QPoint(70, 45))
    QTest.mouseRelease(title, Qt.LeftButton, pos=QPoint(70, 45))
    assert dialog.pos() != start
    dialog.close()


def test_a_breadcrumb_segment_shows_an_ampersand_as_text(qtbot):
    from qtpy.QtGui import QFontMetrics, QKeySequence
    from qtpy.QtWidgets import QPushButton

    from fxgui.fxwidgets import FXBreadcrumb

    crumb = FXBreadcrumb()
    _shown(qtbot, crumb)
    crumb.set_path(["Projects", "R&D"])
    segment = [
        button for button in crumb.findChildren(QPushButton)
        if button.objectName() == "fxBreadcrumbSegment"
    ][-1]
    # Escaped for Qt: no mnemonic, so no Alt+D and room for the "&".
    assert segment.text() == "R&&D"
    assert QKeySequence.mnemonic(segment.text()).isEmpty()
    metrics = QFontMetrics(segment.font())
    assert segment.sizeHint().width() >= metrics.horizontalAdvance("R&D")


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("checkable", [False, True])
def test_column_0_sized_to_its_contents_draws_its_title_whole(
    qtbot, app_root, theme, checkable
):
    """Each title alone in its column: its width rounds its own way."""
    fxstyle.apply_theme(theme, save=False)
    app_root.resize(700, 300)
    app_root.show()
    titles = ["Shadow", "A much longer item name", "Lighting pass 2",
              "beauty_v004", "Rim light", "Character seq010", "Episode edit",
              "Matte painting", "Fog volume", "Ambient occlusion"]
    for title in titles:
        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setItemDelegate(FXThumbnailDelegate(tree))
        parent = QTreeWidgetItem(tree, ["G"])
        item = QTreeWidgetItem(parent, [title])
        if checkable:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
        tree.expandAll()
        app_root.layout().addWidget(tree)
        qtbot.waitExposed(tree)
        header = tree.header()
        header.setStretchLastSection(False)
        tree.resizeColumnToContents(0)
        width = header.sectionSize(0)
        row = tree.visualItemRect(item)

        def cell(tree=tree, row=row, width=width):
            image = tree.viewport().grab().toImage()
            # Short of the column rule at the cell's right edge.
            return image.copy(0, row.top(), width - 3, row.height())

        fitted = cell()
        tree.setColumnWidth(0, width + 80)
        assert cell() == fitted, title
        # Hidden, not unparented: freed mid-show, its header crashes Qt 6.5.
        tree.hide()


def test_an_empty_state_cuts_a_long_word_in_its_middle(qtbot):
    from fxgui.fxwidgets import FXEmptyState

    word = "sh0010_comp_lighting_v004_final"
    empty = FXEmptyState("inbox", word, "Its files show here")
    window = _shown(qtbot, empty)
    window.resize(220, 300)
    QApplication = __import__("qtpy.QtWidgets", fromlist=["QApplication"]).QApplication
    for _ in range(3):
        QApplication.processEvents()
    shown = empty.action.text()
    metrics = empty.action.fontMetrics()
    assert "…" in shown
    assert metrics.horizontalAdvance(shown) <= empty.action.contentsRect().width()
    assert empty.action.toolTip() == word
    # Room again: the whole word, no tip.
    window.resize(900, 300)
    for _ in range(3):
        QApplication.processEvents()
    assert empty.action.text() == word and empty.action.toolTip() == ""


def test_the_first_column_rule_runs_through_header_and_summary(qtbot):
    from fxgui.fxwidgets import FXSummaryRow

    tree = QTreeWidget()
    tree.setColumnCount(3)
    tree.setHeaderLabels(["Name", "Frames", "Size"])
    for n in range(3):
        QTreeWidgetItem(tree, [f"sh00{n}0", "1001", "2"])
    summary = FXSummaryRow(tree)
    summary.set_texts(["3 shots", "3003", "6"])
    _shown(qtbot, tree)
    header = tree.header()
    x = header.sectionViewportPosition(0) + header.sectionSize(0) - 1
    ink = QColor(fxstyle.colors().border)
    ink.setAlphaF(fxstyle._TABLE_RULE_ALPHA)

    def ruled(widget, y):
        image = widget.grab().toImage()
        here = QColor(image.pixel(x, y))
        beside = QColor(image.pixel(x - 4, y))
        return here != beside

    assert ruled(header, header.height() // 2)
    assert ruled(summary, summary.height() // 2)
    # Not after the last column.
    last = header.sectionViewportPosition(2) + header.sectionSize(2) - 1
    image = header.grab().toImage()
    assert QColor(image.pixel(last, header.height() // 2)) == QColor(
        image.pixel(last - 4, header.height() // 2))


def test_an_editable_combo_s_field_holds_its_descenders(qtbot):
    """Its text's ink is as tall as the same words in a label: nothing cut."""
    text = "jgpq_yyy"
    combo = QComboBox()
    combo.setEditable(True)
    combo.setEditText(text)
    label = QLabel(text)
    _shown(qtbot, combo, label)
    field = combo.lineEdit()
    field.setCursorPosition(0)
    field.deselect()
    label.setFont(field.font())
    QApplication.processEvents()

    def ink_rows(widget):
        image = widget.grab().toImage()
        ground = QColor(image.pixel(1, image.height() // 2))
        rows = [
            y for y in range(image.height())
            if any(
                abs(QColor(image.pixel(x, y)).lightness() - ground.lightness())
                > 60
                for x in range(4, min(image.width(), 80))
            )
        ]
        return rows[-1] - rows[0] + 1 if rows else 0

    tight = field.fontMetrics().tightBoundingRect(text).height()
    assert ink_rows(field) >= tight - 1


def test_always_on_top_shows_its_check():
    from fxgui.fxwidgets import FXMainWindow

    window = FXMainWindow(title="Top")
    action = window.window_on_top_action
    assert action.isCheckable() and action.icon().isNull()
    window.deleteLater()


def test_a_disabled_split_button_on_a_frame_keeps_its_edge(qtbot):
    from fxgui.fxwidgets import FXSplitButton

    row = QWidget()
    fxstyle.mark_as_frame(row)
    split = FXSplitButton()
    split.setText("Publish")
    QHBoxLayout(row).addWidget(split)
    split.setEnabled(False)
    _shown(qtbot, row)
    image = split.grab().toImage()
    middle = split.height() // 2
    assert QColor(image.pixel(0, middle)).name() == fxstyle.colors().border.lower()


def test_a_disabled_nav_row_reads_disabled(qtbot):
    from qtpy.QtWidgets import QListWidget

    pages = QListWidget()
    pages.addItems(["Shots", "Assets"])
    pages.item(1).setFlags(Qt.NoItemFlags)
    fxstyle.mark_as_nav(pages)
    _shown(qtbot, pages)
    image = pages.viewport().grab().toImage()
    rect = pages.visualItemRect(pages.item(1))
    inks = {
        QColor(image.pixel(x, y)).name()
        for x in range(rect.left(), rect.right())
        for y in range(rect.top(), rect.bottom())
    }
    assert fxstyle.colors().text_disabled.lower() in inks
    assert fxstyle.colors().text_muted.lower() not in inks


def test_a_wrapping_list_row_grows_past_28_px(qtbot):
    from qtpy.QtWidgets import QListWidget

    listed = QListWidget()
    listed.setWordWrap(True)
    listed.addItem("A long change note " * 8)
    window = _shown(qtbot, listed)
    window.resize(220, 300)
    QApplication.processEvents()
    listed.doItemsLayout()
    QApplication.processEvents()
    assert listed.visualItemRect(listed.item(0)).height() > 28


def test_a_log_s_hanging_indent_is_capped(qtbot):
    from fxgui.fxwidgets import FXOutputLogWidget

    log = FXOutputLogWidget(hang_indent=r"^\S+\s+\S+\s+\S+\s+")
    _shown(qtbot, log)
    header = "12:00:01 INFO ls_pascal.adapters.kitsu.client_and_more:355 "
    log.append_log(header + "the message " * 20)
    log.flush()
    block = log.output_area.document().firstBlock()
    space = log.output_area.fontMetrics().horizontalAdvance(" ")
    assert block.blockFormat().leftMargin() <= space * log.HANG_COLUMNS + 1


def test_the_emoji_button_is_a_control_s_height(qtbot):
    from fxgui.fxwidgets import FXEmojiButton, FXIconButton

    emoji, icon = FXEmojiButton(), FXIconButton("smile")
    _shown(qtbot, emoji, icon)
    assert emoji.size() == icon.size()


def _input(qtbot, **options):
    from fxgui.fxwidgets import FXInputDialog

    dialog = FXInputDialog(title="Rename sh0010", **options)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.activateWindow()
    qtbot.waitUntil(dialog.isActiveWindow)
    return dialog


def test_an_input_card_takes_its_value_on_enter(qtbot):
    dialog = _input(qtbot, value="sh0010", verb="Rename")
    assert dialog.focusWidget() is dialog.field
    dialog.field.setText("sh0020")
    QTest.keyClick(dialog.field, Qt.Key_Return)
    assert dialog.choice() == "verb" and dialog.value() == "sh0020"


def test_a_required_input_shuts_its_verb_while_empty(qtbot):
    dialog = _input(qtbot, value="", required=True)
    assert not dialog.verb_button.isEnabled()
    dialog.field.setText("x")
    assert dialog.verb_button.isEnabled()


def test_a_text_input_breaks_lines_on_enter_and_takes_on_ctrl_enter(qtbot):
    dialog = _input(qtbot, kind="text", value="")
    QTest.keyClicks(dialog.field, "one")
    QTest.keyClick(dialog.field, Qt.Key_Return)
    QTest.keyClicks(dialog.field, "two")
    assert dialog.isVisible() and dialog.value() == "one\ntwo"
    QTest.keyClick(dialog.field, Qt.Key_Return, Qt.ControlModifier)
    assert dialog.choice() == "verb"


def test_a_choice_input_reads_its_pick_and_refuses_no_choices():
    from fxgui.fxwidgets import FXInputDialog

    dialog = FXInputDialog(title="?", kind="choice", choices=["a", "b"],
                           value="b")
    assert dialog.value() == "b"
    for options in ({"kind": "pick"}, {"kind": "choice"}):
        with pytest.raises(ValueError):
            FXInputDialog(title="?", **options)


def test_a_grid_skeleton_draws_a_name_column_and_its_narrow_columns(qtbot):
    from fxgui.fxwidgets import FXSkeleton

    sheet = QWidget()
    window = _shown(qtbot, sheet)
    window.resize(700, 200)
    skeleton = FXSkeleton.cover(sheet, "grid", columns=7)
    skeleton._animation.stop()
    QApplication.processEvents()
    image = skeleton.grab().toImage()
    ground = QColor(image.pixel(2, 2))
    y = fxstyle.row_height() // 2
    runs, inside = 0, False
    for x in range(image.width()):
        bar = QColor(image.pixel(x, y)) != ground
        if bar and not inside:
            runs += 1
        inside = bar
    assert skeleton.kind == "grid"
    assert runs == 1 + 7, runs


@pytest.mark.parametrize("rows", [True, False])
def test_a_table_selecting_rows_lights_the_row_under_the_pointer(qtbot, rows):
    from qtpy.QtWidgets import QAbstractItemView, QTableWidget

    from _helpers import hover, pixel, themed_window

    table = QTableWidget(3, 3)
    if rows:
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window = themed_window(qtbot, "dark", table, size=(400, 240))
    viewport = table.viewport()
    cell = lambda row, column: table.visualRect(  # noqa: E731
        table.model().index(row, column)).center()
    hover(qtbot, viewport, cell(1, 0))
    hovered = fxstyle.colors().state_hover

    assert (pixel(window, viewport, cell(1, 2)) == hovered) is rows
    assert pixel(window, viewport, cell(0, 2)) != hovered
