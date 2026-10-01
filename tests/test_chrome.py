"""The base sheet's chrome: branches, scroll bars, arrows, cards, tabs, popups."""

# Built-in
import re

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from qtpy.QtGui import QColor, QHoverEvent
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QLabel,
    QListWidget,
    QMenu,
    QSpinBox,
    QStyle,
    QStyleOptionComboBox,
    QStyleOptionGroupBox,
    QStyleOptionSlider,
    QStyleOptionSpinBox,
    QTableWidget,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle, fxutils

THEMES = pytest.mark.parametrize("theme", fxstyle.get_available_themes())


def _shown(qtbot, theme, widget, size=(320, 240)):
    """Show `widget` alone in a themed window and return the window."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    QVBoxLayout(window).addWidget(widget)
    window.resize(*size)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    # The window holds focus, so no widget wears its focus look.
    window.setFocusPolicy(Qt.StrongFocus)
    window.setFocus()
    QApplication.processEvents()
    return window


def _distance(first, second):
    a, b = QColor(first), QColor(second)
    return max(
        abs(a.red() - b.red()),
        abs(a.green() - b.green()),
        abs(a.blue() - b.blue()),
    )


def _pixels(image, rect):
    return {
        image.pixelColor(x, y).name()
        for x in range(rect.left(), rect.right() + 1)
        for y in range(rect.top(), rect.bottom() + 1)
    }


# (1) Trees: no branch lines, the accordion's chevrons in the icon token.


def _tree():
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setIndentation(20)
    opened = QTreeWidgetItem(tree, ["opened"])
    for name in ("first", "second", "third"):
        QTreeWidgetItem(opened, [name])
    closed = QTreeWidgetItem(tree, ["closed"])
    QTreeWidgetItem(closed, ["hidden"])
    QTreeWidgetItem(tree, ["leaf"])
    opened.setExpanded(True)
    return tree


def _branch(tree, item):
    """Return the branch area left of `item`, in window coordinates."""
    rect = tree.visualItemRect(item)
    rect.setLeft(rect.left() - tree.indentation())
    rect.setRight(rect.left() + tree.indentation() - 1)
    return rect.translated(tree.viewport().mapTo(tree.window(), QPoint()))


@THEMES
def test_a_tree_draws_chevrons_and_no_branch_lines(qtbot, theme):
    tree = _tree()
    window = _shown(qtbot, theme, tree)
    image = window.grab().toImage()
    colors = fxstyle.colors()
    opened, closed, leaf = (tree.topLevelItem(row) for row in range(3))
    for item in (opened, closed):
        inks = _pixels(image, _branch(tree, item))
        assert min(_distance(ink, colors.icon) for ink in inks) <= 24, inks
    # A leaf, a child and the column under an open parent are bare.
    sunken = colors.surface_sunken.lower()
    for item in (leaf, opened.child(0), opened.child(2)):
        assert _pixels(image, _branch(tree, item)) == {sunken}, item.text(0)
    # Open and closed are different marks.
    assert image.copy(_branch(tree, opened)) != image.copy(
        _branch(tree, closed)
    )


# (2) Scroll bars: a thin rounded thumb, no arrows, wider on hover.


def _hover(widget, point):
    widget.setAttribute(Qt.WA_UnderMouse, True)
    QApplication.sendEvent(
        widget,
        QHoverEvent(
            QEvent.HoverMove,
            QPointF(point),
            QPointF(widget.mapToGlobal(point)),
            QPointF(-1, -1),
        ),
    )
    QApplication.processEvents()


def _bar_rect(bar, control):
    option = QStyleOptionSlider()
    bar.initStyleOption(option)
    return bar.style().subControlRect(QStyle.CC_ScrollBar, option, control, bar)


def _thumb_width(bar):
    """Return how many pixels across the bar the thumb paints."""
    image = bar.window().grab().toImage()
    middle = _bar_rect(bar, QStyle.SC_ScrollBarSlider).center().y()
    row = [
        image.pixelColor(bar.mapTo(bar.window(), QPoint(x, middle))).name()
        for x in range(bar.width())
    ]
    thumb = fxstyle.colors().scrollbar_thumb.lower()
    hover = fxstyle.colors().scrollbar_thumb_hover.lower()
    return sum(ink in (thumb, hover) for ink in row)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_scroll_bar_is_a_thin_pill_with_no_arrows(qtbot, theme):
    view = QListWidget()
    view.addItems([f"row {index}" for index in range(60)])
    window = _shown(qtbot, theme, view)
    bar = view.verticalScrollBar()
    assert bar.isVisible()
    assert bar.width() == fxstyle.THIN_SCROLL_WIDTH
    for control in (QStyle.SC_ScrollBarAddLine, QStyle.SC_ScrollBarSubLine):
        assert _bar_rect(bar, control).isEmpty()
    # No track: below the thumb the bar shows the view's own fill.
    image = window.grab().toImage()
    groove = bar.mapTo(window, QPoint(bar.width() // 2, bar.height() * 3 // 4))
    assert image.pixelColor(groove).name() == fxstyle.colors().surface_sunken
    # A rounded thumb paints its corner pixel only in part.
    handle = _bar_rect(bar, QStyle.SC_ScrollBarSlider)
    corner = bar.mapTo(window, QPoint(2, handle.top()))
    middle = bar.mapTo(window, QPoint(bar.width() // 2, handle.center().y()))
    assert image.pixelColor(middle).name() == fxstyle.colors().scrollbar_thumb
    assert image.pixelColor(corner).name() != fxstyle.colors().scrollbar_thumb
    rest = _thumb_width(bar)
    _hover(bar, handle.center())
    hovered = _thumb_width(bar)
    assert 0 < rest < hovered <= bar.width(), (rest, hovered)
    assert bar.width() == fxstyle.THIN_SCROLL_WIDTH


# (3) One arrow everywhere: the chevrons, in the icon token.


def _ink_near(image, rect, ink):
    return min(_distance(pixel, ink) for pixel in _pixels(image, rect))


@THEMES
def test_every_arrow_in_the_sheet_is_a_chevron(theme):
    sheet = fxstyle.build_stylesheet(theme)
    assert "~icon(" not in sheet
    assert not re.search(r"_arrow(_disabled)?.svg", sheet)
    for name in ("expand_more", "expand_less", "chevron_right"):
        assert f"/{name}_" in sheet, name


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_combo_spin_and_header_arrows_wear_the_icon_token(qtbot, theme):
    holder = QWidget()
    column = QVBoxLayout(holder)
    combo = QComboBox()
    combo.addItems(["one", "two"])
    spin = QSpinBox()
    spin.setValue(5)
    table = QTableWidget(3, 2)
    table.setSortingEnabled(True)
    table.sortByColumn(0, Qt.AscendingOrder)
    for widget in (combo, spin, table):
        column.addWidget(widget)
    window = _shown(qtbot, theme, holder, (320, 320))
    image = window.grab().toImage()
    icon = fxstyle.colors().icon

    def mapped(widget, rect):
        return rect.translated(widget.mapTo(window, QPoint()))

    option = QStyleOptionComboBox()
    combo.initStyleOption(option)
    arrow = combo.style().subControlRect(
        QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxArrow, combo
    )
    assert _ink_near(image, mapped(combo, arrow), icon) <= 24
    option = QStyleOptionSpinBox()
    spin.initStyleOption(option)
    for control in (QStyle.SC_SpinBoxUp, QStyle.SC_SpinBoxDown):
        button = spin.style().subControlRect(
            QStyle.CC_SpinBox, option, control, spin
        )
        assert _ink_near(image, mapped(spin, button), icon) <= 24, control
    header = table.horizontalHeader()
    # The sort mark sits at the section's right end, clear of its text.
    right = header.sectionViewportPosition(0) + header.sectionSize(0)
    mark = QRect(right - 20, 0, 20, header.height())
    assert _ink_near(image, mapped(header, mark), icon) <= 40


# (4) A group box's title sits above a whole rounded card.


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("checkable", [False, True], ids=["plain", "checkable"])
def test_a_group_title_sits_above_a_whole_card(qtbot, theme, checkable):
    group = QGroupBox("Render settings")
    group.setCheckable(checkable)
    QVBoxLayout(group).addWidget(QLabel("inside"))
    window = _shown(qtbot, theme, group)
    option = QStyleOptionGroupBox()
    group.initStyleOption(option)

    def rect(control):
        return group.style().subControlRect(
            QStyle.CC_GroupBox, option, control, group
        ).translated(group.mapTo(window, QPoint()))

    title = rect(QStyle.SC_GroupBoxLabel)
    frame = rect(QStyle.SC_GroupBoxFrame)
    assert title.bottom() < frame.top(), (title, frame)
    image = window.grab().toImage()
    border = fxstyle.colors().border.lower()
    # The top edge is whole under the title, and the corners are round.
    top = {
        image.pixelColor(x, frame.top()).name()
        for x in range(frame.left() + 12, frame.right() - 12)
    }
    assert top == {border}, top
    assert image.pixelColor(frame.topLeft()).name() != border
    assert image.pixelColor(
        frame.left(), frame.top() + fxstyle.CARD_RADIUS
    ).name() == border


# (5) No alternating row stripes.


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_rows_have_no_stripes_even_when_asked(qtbot, theme):
    view = QListWidget()
    view.setAlternatingRowColors(True)
    view.addItems(["first", "second", "third"])
    window = _shown(qtbot, theme, view)
    assert not view.alternatingRowColors()
    image = window.grab().toImage()
    inks = set()
    for row in range(3):
        rect = view.visualItemRect(view.item(row))
        point = rect.topRight() + QPoint(-4, rect.height() // 2)
        inks.add(image.pixelColor(view.viewport().mapTo(window, point)).name())
    assert inks == {fxstyle.colors().surface_sunken.lower()}, inks


# (6) A tab's bar is straight, in QTabBar and in QtAds alike.


def _bar_rows(image, rect, ink):
    """Return the rows `ink` covers in each column of `rect`."""
    columns = {}
    for x in range(rect.left(), rect.right() + 1):
        rows = frozenset(
            y
            for y in range(rect.top(), rect.bottom() + 1)
            if image.pixelColor(x, y).name() == ink
        )
        columns[x] = rows
    return columns


def _assert_straight(image, rect, ink):
    columns = _bar_rows(image, rect, ink)
    lit = [rows for rows in columns.values() if rows]
    # The bar spans the tab, 2px thick, its ends on its middle's rows.
    assert len(lit) >= rect.width() - 2, (len(lit), rect.width())
    middle = columns[rect.center().x()]
    assert len(middle) == 2, middle
    assert set(lit) == {middle}, set(lit)
    assert max(middle) == rect.bottom()


@THEMES
def test_the_current_tab_wears_a_straight_bar(qtbot, theme):
    tabs = QTabWidget()
    for name in ("Render", "Comp", "Lighting"):
        tabs.addTab(QLabel(name), name)
    window = _shown(qtbot, theme, tabs)
    bar = tabs.tabBar()
    image = window.grab().toImage()
    accent = fxstyle.colors().accent_primary.lower()
    rect = bar.tabRect(0).translated(bar.mapTo(window, QPoint()))
    _assert_straight(image, rect, accent)
    # The other tabs reserve the bar but draw none.
    other = bar.tabRect(1).translated(bar.mapTo(window, QPoint()))
    assert not any(_bar_rows(image, other, accent).values())
    assert bar.tabRect(0).height() == bar.tabRect(1).height()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_dock_tab_wears_the_same_bar(qtbot, theme):
    pytest.importorskip("PySide6QtAds")
    from fxgui import fxdocking

    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    docks.add_dock("one", "Outliner", QLabel("outliner"), "left")
    docks.add_dock("two", "Assets", QLabel("assets"), "left")
    window = _shown(qtbot, theme, docks, (640, 480))
    for _ in range(3):
        QApplication.processEvents()
    tab = next(
        tab
        for tab in docks.findChildren(QWidget)
        if tab.metaObject().className() == "ads::CDockWidgetTab"
        and tab.property("activeTab")
    )
    image = window.grab().toImage()
    # The tab bar scrolls, so part of a tab can sit out of view.
    rect = tab.visibleRegion().boundingRect()
    rect = rect.translated(tab.mapTo(window, QPoint()))
    _assert_straight(image, rect, fxstyle.colors().accent_primary.lower())


# (7) No state moves an item's text.


def _text_start(image, rect):
    """Return the first column of `rect` whose ink is not the row's fill."""
    middle = rect.center().y()
    fill = image.pixelColor(rect.left() + 2, middle).name()
    for x in range(rect.left() + 2, rect.right()):
        for y in range(rect.top() + 2, rect.bottom() - 1):
            if _distance(image.pixelColor(x, y).name(), fill) > 30:
                return x
    raise AssertionError(f"no text in {rect}")


def _starts(image, rects):
    return [_text_start(image, rect) for rect in rects]


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_combo_popup_row_keeps_its_text_still(qtbot, theme):
    combo = QComboBox()
    combo.addItems(["Same"] * 3)
    combo.setCurrentIndex(1)
    _window = _shown(qtbot, theme, combo)
    combo.showPopup()
    qtbot.waitUntil(lambda: combo.view().isVisible())
    view = combo.view()
    popup = view.window()
    rows = [
        view.visualRect(view.model().index(row, 0)).translated(
            view.viewport().mapTo(popup, QPoint())
        )
        for row in range(3)
    ]
    # Row 1 is current and selected; 0 and 2 rest.
    starts = _starts(popup.grab().toImage(), rows)
    combo.hidePopup()
    assert len(set(starts)) == 1, starts


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_menu_row_keeps_its_text_still(qtbot, theme):
    holder = QWidget()
    window = _shown(qtbot, theme, holder)
    menu = QMenu(window)
    actions = [menu.addAction("Same") for _ in range(3)]
    menu.popup(holder.mapToGlobal(QPoint(10, 10)))
    qtbot.waitExposed(menu)
    menu.setActiveAction(actions[1])
    QApplication.processEvents()
    starts = _starts(
        menu.grab().toImage(),
        [menu.actionGeometry(action) for action in actions],
    )
    menu.close()
    assert len(set(starts)) == 1, starts


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("kind", ["list", "tree"])
def test_a_view_row_keeps_its_text_still(qtbot, theme, kind):
    if kind == "list":
        view = QListWidget()
        view.addItems(["Same"] * 3)
        items = [view.item(row) for row in range(3)]
    else:
        view = QTreeWidget()
        view.setHeaderHidden(True)
        items = [QTreeWidgetItem(view, ["Same"]) for _ in range(3)]
    _window = _shown(qtbot, theme, view)
    items[1].setSelected(True)
    rows = [view.visualItemRect(item) for item in items]
    _hover(view.viewport(), rows[2].center())
    image = view.viewport().grab().toImage()
    # Row 0 rests, 1 is selected, 2 is hovered.
    assert image.pixelColor(rows[2].center()).name() != image.pixelColor(
        rows[0].center()
    ).name()
    starts = _starts(image, rows)
    # Qt 6.11 paints a resting list row 1px further in than a highlighted
    # one, natively; no rule reaches it without hiding BackgroundRole.
    slack = 1 if kind == "list" else 0
    assert max(starts) - min(starts) <= slack, starts


# (8) One popup look: menus, combo lists and the palette, rounded by the
# platform.


def _blend_of(pixel, inks, slack=3):
    """Return whether `pixel` is one of `inks` or an antialiased mix of two."""
    target = QColor(pixel)
    p = (target.red(), target.green(), target.blue())
    colors = [QColor(ink) for ink in inks]
    for a in colors:
        for b in colors:
            first = (a.red(), a.green(), a.blue())
            second = (b.red(), b.green(), b.blue())
            for step in range(33):
                t = step / 32
                mix = [x + (y - x) * t for x, y in zip(first, second)]
                if all(abs(c - m) <= slack for c, m in zip(p, mix)):
                    return True
    return False


def _foreign(image, inks):
    """Return the pixels of `image` that no theme ink accounts for."""
    seen = {}
    for x in range(image.width()):
        for y in range(image.height()):
            name = image.pixelColor(x, y).name()
            if name not in seen:
                seen[name] = _blend_of(name, inks)
    return {name for name, known in seen.items() if not known}


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_combo_popup_is_the_popup_look_edge_to_edge(qtbot, theme):
    combo = QComboBox()
    # No text, so every pixel is fill, edge or the selected row.
    combo.addItems(["", "", ""])
    _window = _shown(qtbot, theme, combo)
    combo.showPopup()
    qtbot.waitUntil(lambda: combo.view().isVisible())
    popup = combo.view().window()
    image = popup.grab().toImage()
    combo.hidePopup()
    colors = fxstyle.colors()
    inks = (colors.surface, colors.border, colors.accent_primary)
    assert not _foreign(image, inks)
    middle = image.height() // 2
    assert image.pixelColor(0, middle).name() == colors.border.lower()
    assert image.pixelColor(2, middle).name() == colors.surface.lower()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_menu_wears_the_same_popup_look(qtbot, theme):
    window = _shown(qtbot, theme, QWidget())
    menu = QMenu(window)
    actions = [menu.addAction("") for _ in range(3)]
    menu.popup(window.mapToGlobal(QPoint(10, 10)))
    qtbot.waitExposed(menu)
    menu.setActiveAction(actions[1])
    QApplication.processEvents()
    image = menu.grab().toImage()
    menu.close()
    colors = fxstyle.colors()
    inks = (colors.surface, colors.border, colors.accent_primary)
    assert not _foreign(image, inks)
    middle = image.height() // 2
    assert image.pixelColor(0, middle).name() == colors.border.lower()
    assert image.pixelColor(2, middle).name() == colors.surface.lower()


def test_every_themed_popup_asks_for_flyout_corners(qtbot, monkeypatch):
    rounded = []
    monkeypatch.setattr(fxutils, "round_window_corners", rounded.append)
    combo = QComboBox()
    combo.addItems(["one", "two"])
    window = _shown(qtbot, "dark", combo)
    combo.showPopup()
    qtbot.waitUntil(lambda: combo.view().isVisible())
    popup = combo.view().window()
    combo.hidePopup()
    menu = QMenu(window)
    menu.addAction("one")
    menu.popup(window.mapToGlobal(QPoint(10, 10)))
    qtbot.waitExposed(menu)
    menu.close()
    assert popup in rounded
    assert menu in rounded
    assert window not in rounded


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_dock_tab_matches_a_tab_bar_tab(qtbot, theme):
    pytest.importorskip("PySide6QtAds")
    from fxgui import fxdocking

    holder = QWidget()
    column = QVBoxLayout(holder)
    tabs = QTabWidget()
    tabs.addTab(QLabel("x"), "Shots")
    tabs.addTab(QLabel("y"), "Log")
    column.addWidget(tabs)
    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    docks.add_dock("shots", "Shots", QLabel("s"), "left")
    docks.add_dock("log", "Log", QLabel("l"), "bottom")
    column.addWidget(docks)
    window = _shown(qtbot, theme, holder, (800, 600))
    for _ in range(3):
        QApplication.processEvents()
    image = window.grab().toImage()
    colors = fxstyle.colors()
    accent = colors.accent_primary.lower()
    text = colors.text

    def measure(widget, rect):
        rect = rect.translated(widget.mapTo(window, QPoint()))
        bar = [
            y - rect.top()
            for y in range(rect.top(), rect.bottom() + 1)
            if image.pixelColor(rect.center().x(), y).name() == accent
        ]
        ink = [
            y - rect.top()
            for y in range(rect.top(), rect.bottom() + 1)
            if y - rect.top() not in bar
            and any(
                _distance(image.pixelColor(x, y).name(), text) <= 40
                for x in range(rect.left(), rect.left() + 40)
            )
        ]
        return rect.height(), bar, (min(ink), max(ink))

    bar = tabs.tabBar()
    tab = next(
        tab
        for tab in docks.findChildren(QWidget)
        if tab.metaObject().className() == "ads::CDockWidgetTab"
        and tab.property("activeTab")
        and tab.isVisible()
    )
    # Same height, the bar on the same rows, the same "Shots" ink rows.
    assert measure(tab, tab.rect()) == measure(bar, bar.tabRect(0))
