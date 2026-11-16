"""fxutils' menu and tree helpers: popups, submenus, filter, state, widths."""

# Built-in
import gc

# Third-party
from qtpy.QtCore import QModelIndex, QPoint, Qt
from qtpy.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem, QWidget

# Internal
from fxgui import fxutils
from fxgui.fxwidgets import FXThumbnailDelegate


def test_popup_menu_shows_the_menu_and_frees_it_once_closed(qtbot):
    owner = QWidget()
    qtbot.addWidget(owner)
    menu = QMenu(owner)
    menu.addAction("one")
    gone = []
    menu.destroyed.connect(lambda: gone.append(True))
    fxutils.popup_menu(menu, QPoint(10, 10))
    qtbot.waitUntil(menu.isVisible)
    menu.close()
    qtbot.waitUntil(lambda: bool(gone))


def test_add_submenu_outlives_its_python_wrapper(qtbot):
    owner = QWidget()
    qtbot.addWidget(owner)
    menu = QMenu(owner)
    sub = fxutils.add_submenu(menu, "More")
    sub.addAction("deep")
    del sub
    gc.collect()
    action = menu.actions()[0]
    assert action.text() == "More"
    assert [a.text() for a in action.menu().actions()] == ["deep"]



def test_add_submenu_goes_before_the_action_it_is_given(qtbot):
    owner = QWidget()
    qtbot.addWidget(owner)
    menu = QMenu(owner)
    first = menu.addAction("first")
    menu.addAction("last")

    fxutils.add_submenu(menu, "More", before=first)

    assert [a.text() for a in menu.actions()] == ["More", "first", "last"]

def _tree(qtbot, columns=1):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setColumnCount(columns)
    return tree


def _row(parent, *texts):
    return QTreeWidgetItem(parent, list(texts))


def test_a_match_on_a_branch_keeps_its_whole_subtree(qtbot):
    tree = _tree(qtbot)
    passes = _row(tree, "Beauty Passes")
    child = _row(passes, "img_0012")
    grandchild = _row(child, "layer")
    other = _row(tree, "Other")
    fxutils.filter_tree(tree, "beauty")
    assert not passes.isHidden()
    assert not child.isHidden()
    assert not grandchild.isHidden()
    assert other.isHidden()


def test_a_deep_match_keeps_its_ancestors_and_hides_its_cousins(qtbot):
    tree = _tree(qtbot)
    shots = _row(tree, "shots")
    seq = _row(shots, "sq010")
    hit = _row(seq, "sh0040")
    cousin = _row(seq, "sh0050")
    fxutils.filter_tree(tree, "0040")
    assert not shots.isHidden() and not seq.isHidden() and not hit.isHidden()
    assert cousin.isHidden()


def test_any_column_matches_and_empty_text_shows_every_row(qtbot):
    tree = _tree(qtbot, columns=2)
    row = _row(tree, "name", "In progress")
    other = _row(tree, "else", "Done")
    fxutils.filter_tree(tree, "progress")
    assert not row.isHidden() and other.isHidden()
    fxutils.filter_tree(tree, "  ")
    assert not row.isHidden() and not other.isHidden()


def test_mark_decides_what_a_verdict_does(qtbot):
    tree = _tree(qtbot)
    keep = _row(tree, "keep")
    drop = _row(tree, "drop")
    verdicts = {}
    fxutils.filter_tree(
        tree, "keep", mark=lambda item, ok: verdicts.__setitem__(item.text(0), ok)
    )
    assert verdicts == {"keep": True, "drop": False}
    assert not drop.isHidden(), "a custom mark replaces hiding"
    assert not keep.isHidden()


def test_children_of_yields_every_child(qtbot):
    tree = _tree(qtbot)
    top = _row(tree, "top")
    kids = [_row(top, str(i)) for i in range(3)]
    assert list(fxutils.children_of(top)) == kids


def _fill(tree):
    tree.clear()
    shots = _row(tree, "shots", "")
    for version in ("v001", "v002"):
        _row(shots, "comp", version)
    for index in range(40):
        _row(tree, f"row{index}", "")
    return shots


def test_tree_state_survives_a_rebuild(qtbot):
    tree = _tree(qtbot, columns=2)
    tree.resize(200, 120)
    tree.show()
    qtbot.waitExposed(tree)
    shots = _fill(tree)
    shots.setExpanded(True)
    tree.setCurrentItem(shots.child(1))
    tree.doItemsLayout()
    tree.verticalScrollBar().setValue(5)
    state = fxutils.TreeState.of(tree)

    shots = _fill(tree)
    assert not shots.isExpanded()
    state.restore(tree)
    assert shots.isExpanded()
    assert tree.currentItem() is shots.child(1), "the v002 row, not v001"
    assert tree.selectedItems() == [shots.child(1)]
    assert tree.verticalScrollBar().value() == 5


def test_restoring_skips_rows_that_are_gone(qtbot):
    tree = _tree(qtbot, columns=2)
    shots = _fill(tree)
    shots.setExpanded(True)
    tree.setCurrentItem(shots.child(0))
    state = fxutils.TreeState.of(tree)
    tree.clear()
    _row(tree, "else", "")
    state.restore(tree)
    assert tree.currentItem() is None
    assert tree.selectedItems() == []


def test_an_empty_state_scrolls_to_the_top(qtbot):
    tree = _tree(qtbot, columns=2)
    tree.resize(200, 120)
    tree.show()
    qtbot.waitExposed(tree)
    _fill(tree)
    tree.doItemsLayout()
    tree.verticalScrollBar().setValue(8)
    fxutils.TreeState().restore(tree)
    assert tree.verticalScrollBar().value() == 0


def test_fit_columns_measures_collapsed_rows_and_never_narrows(qtbot):
    tree = _tree(qtbot, columns=2)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    top = _row(tree, "top", "x")
    _row(top, "a much longer name hidden under a collapsed row", "y")
    header = tree.header()
    header.resizeSection(0, 60)
    fxutils.fit_columns(tree)
    wide = header.sectionSize(0)
    tree.resizeColumnToContents(0)
    assert wide > header.sectionSize(0), "Qt's own fit misses the child"
    header.resizeSection(0, 2000)
    fxutils.fit_columns(tree)
    assert header.sectionSize(0) == 2000


def test_fit_columns_counts_the_views_icon_size(qtbot):
    from qtpy.QtCore import QSize

    from fxgui import fxicons

    tree = _tree(qtbot, columns=2)
    tree.setIconSize(QSize(48, 48))
    item = _row(tree, "beauty", "x")
    item.setIcon(0, fxicons.get_icon("check"))
    header = tree.header()
    header.resizeSection(0, 10)
    fxutils.fit_columns(tree)
    fitted = header.sectionSize(0)
    tree.resizeColumnToContents(0)
    assert fitted >= header.sectionSize(0)


def _counted_tree(qtbot, monkeypatch, groups=20, children=9):
    """A 6-column tree on FXThumbnailDelegate; count its measures."""
    from qtpy.QtWidgets import QAbstractItemView

    tree = _tree(qtbot, columns=6)
    delegate = FXThumbnailDelegate(tree)
    tree.setItemDelegate(delegate)
    tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    counts = {"sizeHint": 0, "_row_height": 0}
    for name in counts:
        real = getattr(FXThumbnailDelegate, name)

        def spy(self, *args, _real=real, _name=name):
            counts[_name] += 1
            return _real(self, *args)

        monkeypatch.setattr(FXThumbnailDelegate, name, spy)
    for group in range(groups):
        top = QTreeWidgetItem(tree, [f"group {group}", "a", "b", "c", "d", "e"])
        for child in range(children):
            QTreeWidgetItem(top, [
                f"v{child:03d}", f"2026-11-{group + 1:02d}", f"user{group % 3}",
                f"{group * child} MB", "ok", f"{child}" * (child + 1)])
    return tree, delegate, counts


def test_fit_columns_measures_widths_only(qtbot, monkeypatch):
    tree, delegate, counts = _counted_tree(qtbot, monkeypatch)

    fxutils.fit_columns(tree)

    # No row's height measured: a full sizeHint per cell made a pick slow.
    assert counts == {"sizeHint": 0, "_row_height": 0}


def test_a_width_hint_is_the_size_hints_width(qtbot, monkeypatch):
    from qtpy.QtGui import QFont
    from qtpy.QtWidgets import QStyleOptionViewItem

    from fxgui import fxicons

    tree, delegate, _counts = _counted_tree(qtbot, monkeypatch, groups=2)
    delegate.align_column(tree, 3, tabular=True)
    item = tree.topLevelItem(0)
    item.setIcon(2, fxicons.get_icon("folder"))
    bold = QFont()
    bold.setBold(True)
    item.setFont(1, bold)
    item.setCheckState(4, Qt.Checked)
    option = QStyleOptionViewItem()
    tree.initViewItemOption(option)
    model = tree.model()
    parents = [QModelIndex()]
    while parents:
        parent = parents.pop()
        for row in range(model.rowCount(parent)):
            for column in range(6):
                index = model.index(row, column, parent)
                # Twice: the second answer comes from the measure kept.
                for _ in range(2):
                    assert delegate.width_hint(option, index) == (
                        delegate.sizeHint(option, index).width())
            parents.append(model.index(row, 0, parent))


def test_restoring_lays_the_rows_out_once(qtbot, monkeypatch):
    tree, _delegate, counts = _counted_tree(qtbot, monkeypatch)
    tree.resize(400, 200)
    tree.show()
    qtbot.waitExposed(tree)
    tree.topLevelItem(3).setExpanded(True)
    tree.setCurrentItem(tree.topLevelItem(3).child(2))
    tree.doItemsLayout()
    tree.verticalScrollBar().setValue(40)
    state = fxutils.TreeState.of(tree)
    # Refilled, as a pane's fill does.
    tree.clear()
    for group in range(20):
        top = QTreeWidgetItem(tree, [f"group {group}", "a", "b", "c", "d", "e"])
        for child in range(9):
            QTreeWidgetItem(top, [
                f"v{child:03d}", f"2026-11-{group + 1:02d}",
                f"user{group % 3}", f"{group * child} MB", "ok",
                f"{child}" * (child + 1)])
    for name in counts:
        counts[name] = 0

    state.restore(tree)

    shown = 20 + 9  # the rows a layout measures: one group open
    # One layout, and the odd row Qt measures for its default height; a
    # forced second layout measured every row again.
    assert counts["sizeHint"] <= (shown + 3) * 6
    assert tree.currentItem() is tree.topLevelItem(3).child(2)
    assert tree.verticalScrollBar().value() == 40


def test_a_font_differing_only_in_hinting_is_measured_in_its_own(qtbot):
    from qtpy.QtGui import QFont
    from qtpy.QtWidgets import QStyleOptionViewItem

    tree = _tree(qtbot, columns=2)
    delegate = FXThumbnailDelegate(tree)
    hinted = QFont("Inter")
    hinted.setPixelSize(13)
    hinted.setHintingPreference(QFont.PreferFullHinting)
    unhinted = QFont(hinted)
    unhinted.setHintingPreference(QFont.PreferNoHinting)
    assert hinted.key() == unhinted.key()

    for font in (hinted, unhinted):
        option = QStyleOptionViewItem()
        option.font = font
        title = delegate._title_font(option)
        # A font cached by key() alone came back with the other's hinting.
        assert title.hintingPreference() == font.hintingPreference()
