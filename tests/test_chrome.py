"""The base sheet's chrome: branches, scroll bars, arrows, cards, tabs, popups."""

# Built-in
import re

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect, Qt
from qtpy.QtGui import QColor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QLabel,
    QListWidget,
    QMenu,
    QSpinBox,
    QStyle,
    QStyleFactory,
    QStyleOptionComboBox,
    QStyleOptionGroupBox,
    QStyleOptionSlider,
    QStyleOptionSpinBox,
    QTableWidget,
    QTabBar,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle, fxutils

from _helpers import hover, themed_window

# Imported here, not in a test: the suite keeps only the sheet fragments
# registered before a test starts.
try:
    from fxgui import fxdocking
except ImportError:
    fxdocking = None

THEMES = pytest.mark.parametrize("theme", fxstyle.get_available_themes())


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
    window = themed_window(qtbot, theme, tree)
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
    window = themed_window(qtbot, theme, view)
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
    hover(qtbot, bar, handle.center())
    hovered = _thumb_width(bar)
    assert 0 < rest < hovered <= bar.width(), (rest, hovered)
    assert bar.width() == fxstyle.THIN_SCROLL_WIDTH


# (3) One arrow everywhere: the chevrons, in the icon token.


def _ink_near(image, rect, ink):
    return min(_distance(pixel, ink) for pixel in _pixels(image, rect))


@THEMES
def test_every_arrow_in_the_sheet_is_a_chevron(theme):
    sheet = fxstyle._build_stylesheet(theme)
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
    window = themed_window(qtbot, theme, holder, size=(320, 320))
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
    window = themed_window(qtbot, theme, group)
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
    window = themed_window(qtbot, theme, view)
    assert not view.alternatingRowColors()
    image = window.grab().toImage()
    inks = set()
    for row in range(3):
        rect = view.visualItemRect(view.item(row))
        point = rect.topRight() + QPoint(-4, rect.height() // 2)
        inks.add(image.pixelColor(view.viewport().mapTo(window, point)).name())
    assert inks == {fxstyle.colors().surface_sunken.lower()}, inks


# (6) A tab is muted text; the current one a filled pill with no edge, in
# QTabBar and QtAds alike.


def _pill(image, rect):
    """Return the current tab's top and bottom rows, width and text rows.

    The pill is its @state_pressed fill; rows count from the tab's top.
    """
    colors = fxstyle.colors()
    fill = colors.state_pressed
    middle = rect.center().y()
    columns = [
        x for x in range(rect.left(), rect.right() + 1)
        if image.pixelColor(x, middle).name() == fill.lower()
    ]
    # Left of the text, where the fill runs from the top row to the bottom.
    side = min(columns) + 3
    filled = [
        y for y in range(rect.top(), rect.bottom() + 1)
        if image.pixelColor(side, y).name() == fill.lower()
    ]
    rows = [min(filled), max(filled)]
    ink = [
        y - rect.top()
        for x in range(min(columns) + 1, max(columns))
        for y in range(min(rows) + 1, max(rows))
        if _distance(image.pixelColor(x, y).name(), fill) > 60
    ]
    return (
        [y - rect.top() for y in rows],
        max(columns) - min(columns),
        (min(ink), max(ink)),
    )


@THEMES
def test_the_current_tab_is_a_filled_pill_with_no_edge(qtbot, theme):
    tabs = QTabWidget()
    for name in ("Render", "Comp", "Lighting"):
        tabs.addTab(QLabel(name), name)
    window = themed_window(qtbot, theme, tabs)
    bar = tabs.tabBar()
    image = window.grab().toImage()
    colors = fxstyle.colors()
    current = bar.tabRect(0).translated(bar.mapTo(window, QPoint()))
    rows, width, _ink = _pill(image, current)
    # Rounded corners, and nothing drawn around the fill.
    corner = QPoint(current.center().x() - width // 2, current.top() + rows[0])
    assert image.pixelColor(corner).name() != colors.state_pressed.lower()
    assert colors.control_edge.lower() not in _pixels(image, current)
    inside = QPoint(corner.x() + 3, current.center().y())
    assert image.pixelColor(inside).name() == colors.state_pressed.lower()
    # The other tabs are bare text on the strip, in the muted tab ink.
    # Above the pane's top edge, which the bar overlaps by a pixel.
    other = bar.tabRect(1).translated(bar.mapTo(window, QPoint()))
    inks = _pixels(image, other.adjusted(0, 0, 0, -2))
    assert colors.state_pressed.lower() not in inks
    assert colors.state_hover.lower() not in inks
    assert min(_distance(ink, colors.text_muted) for ink in inks) <= 24
    assert bar.tabRect(0).height() == bar.tabRect(1).height()


@THEMES
def test_inactive_tab_text_reads_at_4_5_to_1(theme):
    fxstyle.apply_theme(theme)
    colors = fxstyle.colors()
    assert fxstyle.get_contrast_ratio(colors.text_muted, colors.surface) >= 4.5
    # The current tab's fill stands off a hovered tab's; its text reads.
    assert fxstyle.get_contrast_ratio(
        colors.state_pressed, colors.state_hover) >= fxstyle.STATE_MIN_CONTRAST
    assert fxstyle.get_contrast_ratio(colors.text, colors.state_pressed) >= 4.5


def test_selecting_a_tab_moves_nothing(qtbot):
    tabs = QTabWidget()
    for name in ("Render", "Comp", "Lighting"):
        tabs.addTab(QLabel(name), name)
    _window = themed_window(qtbot, "dark", tabs)
    bar = tabs.tabBar()
    before = [bar.tabRect(index) for index in range(3)]
    tabs.setCurrentIndex(1)
    QApplication.processEvents()
    assert [bar.tabRect(index) for index in range(3)] == before


@THEMES
def test_no_tab_text_shows_inside_the_scroll_buttons(qtbot, theme):
    tabs = QTabWidget()
    for index in range(14):
        tabs.addTab(QLabel(str(index)), f"Crowded tab {index}")
    # A widget's own rule outranks the theme's, so tab text is one ink.
    tabs.tabBar().setStyleSheet("QTabBar::tab { color: #ff00ff; }")
    window = themed_window(qtbot, theme, tabs, size=(420, 120))
    bar = tabs.tabBar()
    buttons = [
        button for button in bar.findChildren(QWidget)
        if button.metaObject().className() == "QToolButton"
        and button.isVisible()
    ]
    assert len(buttons) == 2
    image = window.grab().toImage()
    area = buttons[0].geometry().united(buttons[1].geometry())
    strip = area.translated(bar.mapTo(window, QPoint()))
    inks = _pixels(image, strip)
    assert min(_distance(ink, "#ff00ff") for ink in inks) > 120
    # The buttons stand off the tabs by a gap in the strip's own colour.
    gap = QRect(strip.left(), strip.top(), 4, strip.height())
    assert _pixels(image, gap) == {fxstyle.colors().surface.lower()}


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
    _window = themed_window(qtbot, theme, combo)
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
    window = themed_window(qtbot, theme, holder)
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
    _window = themed_window(qtbot, theme, view)
    items[1].setSelected(True)
    rows = [view.visualItemRect(item) for item in items]
    hover(qtbot, view.viewport(), rows[2].center())
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
    _window = themed_window(qtbot, theme, combo)
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
    window = themed_window(qtbot, theme, QWidget())
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


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_completer_list_wears_the_popup_look(qtbot, theme):
    from qtpy.QtWidgets import QCompleter, QLineEdit

    line = QLineEdit()
    window = themed_window(qtbot, theme, line)
    completer = QCompleter(["", "", ""], line)
    line.setCompleter(completer)
    line.setFocus()
    completer.complete()
    popup = completer.popup()
    qtbot.waitUntil(popup.isVisible)
    popup.setCurrentIndex(completer.completionModel().index(1, 0))
    QApplication.processEvents()
    image = popup.grab().toImage()
    popup.hide()
    colors = fxstyle.colors()
    middle = image.height() // 2
    assert image.pixelColor(0, middle).name() == colors.border.lower()
    assert image.pixelColor(2, middle).name() == colors.surface.lower()
    # The current row is the accent, as a combo box's is.
    assert colors.accent_primary.lower() in _pixels(image, image.rect())
    # Marked for the card look, which an application's sheet carries too.
    assert popup.property(fxstyle.POPUP_PROPERTY) is True
    assert window


def test_every_themed_popup_asks_for_flyout_corners(qtbot, monkeypatch):
    rounded = []
    monkeypatch.setattr(fxutils, "round_window_corners", rounded.append)
    combo = QComboBox()
    combo.addItems(["one", "two"])
    window = themed_window(qtbot, "dark", combo)
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
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")

    holder = QWidget()
    column = QVBoxLayout(holder)
    tabs = QTabWidget()
    tabs.addTab(QLabel("x"), "Assets")
    tabs.addTab(QLabel("y"), "Log")
    column.addWidget(tabs)
    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    docks.add_dock("shots", "Shots", QLabel("s"), "left")
    docks.add_dock("assets", "Assets", QLabel("a"), "left")
    column.addWidget(docks)
    # Wide enough that both dock tabs fit, so neither scrolls out of view.
    window = themed_window(qtbot, theme, holder, size=(1400, 600))
    for _ in range(3):
        QApplication.processEvents()
    image = window.grab().toImage()
    bar = tabs.tabBar()
    tab = next(
        tab
        for tab in docks.findChildren(QWidget)
        if tab.metaObject().className() == "ads::CDockWidgetTab"
        and tab.property("activeTab")
        and tab.isVisible()
    )
    # Same height, the pill and the "Assets" text on the same rows.
    ours = tab.rect().translated(tab.mapTo(window, QPoint()))
    theirs = bar.tabRect(0).translated(bar.mapTo(window, QPoint()))
    assert ours.height() == theirs.height()
    edge, _width, ink = _pill(image, ours)
    assert (edge, ink) == _pill(image, theirs)[::2]
    # No title is cut short.
    assert all(
        label.text() == label.property("text") or "..." not in label.text()
        for label in tab.findChildren(QLabel)
    )


# A tab is its text plus the padding (10px, a 1px edge and a 2px margin on
# each side), in every state, and never elided.
_TAB_FRAME = 2 * (10 + 1 + 2)


def _text_width(widget, text):
    return widget.fontMetrics().size(Qt.TextShowMnemonic, text).width()


def _room_for_tabs(docks, name, width=400):
    """Widen the left pane area: no tab sits behind its title bar buttons."""
    manager = docks.manager()
    area = manager.findDockWidget(name).dockAreaWidget()
    manager.setSplitterSizes(area, [width, 200])
    QApplication.processEvents()


def test_a_tab_is_its_text_plus_the_padding_in_every_state(qtbot):
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    names = ("A", "Render", "Lighting and shading")
    holder = QWidget()
    column = QVBoxLayout(holder)
    tabs = QTabWidget()
    for name in names:
        tabs.addTab(QLabel(name), name)
    column.addWidget(tabs)
    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    for name in names:
        docks.add_dock(name, name, QLabel(name), "left")
    column.addWidget(docks)
    _window = themed_window(qtbot, "dark", holder, size=(1000, 500))
    _room_for_tabs(docks, names[0], 600)
    bar = tabs.tabBar()
    dock_tabs = [
        docks.manager().findDockWidget(name).tabWidget() for name in names
    ]

    def widths():
        ours = [
            bar.tabRect(index).width() - _text_width(bar, bar.tabText(index))
            for index in range(bar.count())
        ]
        theirs = [
            tab.width() - _text_width(tab, tab.findChild(QLabel).text())
            for tab in dock_tabs
        ]
        return ours + theirs

    assert bar.elideMode() == Qt.ElideNone
    rest = widths()
    # The first QTabBar tab adds the 2 px lead its :first margin carries.
    assert rest == [_TAB_FRAME + 2] + [_TAB_FRAME] * 5, rest
    hover(qtbot, bar, bar.tabRect(1).center())
    assert widths() == rest
    hover(qtbot, dock_tabs[0], dock_tabs[0].rect().center())
    assert widths() == rest
    tabs.setCurrentIndex(2)
    docks.show_dock(names[0])
    QApplication.processEvents()
    assert widths() == rest


def test_no_dock_tab_in_the_gallery_is_elided(qtbot):
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    from fxgui import examples

    fxstyle.apply_theme("dark")
    window = examples.build()
    pages = window.centralWidget()
    pages.setCurrentIndex(pages.count() - 1)
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    tabs = [
        widget for widget in window.findChildren(QWidget)
        if widget.metaObject().className() == "ads::CDockWidgetTab"
        and widget.isVisible()
    ]
    assert tabs
    for tab in tabs:
        label = tab.findChild(QLabel)
        title = tab.dockWidget().windowTitle()
        assert label.text() == title, (label.text(), title)
        assert tab.width() - _text_width(tab, title) == _TAB_FRAME
    window.close()
    window.deleteLater()
    QApplication.processEvents()


def _first_edge(image, y, start, stop):
    """Return how far right of `start` the current pill's fill starts."""
    edge = fxstyle.colors().state_pressed.lower()
    return next(
        x - start for x in range(start, stop)
        if image.pixelColor(x, y).name() == edge
    )


def test_a_dock_tab_starts_as_far_in_as_a_tab_bar_tab(qtbot):
    """Measured from each pane's outer edge."""
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    from fxgui import examples

    fxstyle.apply_theme("dark")
    window = examples.build()
    pages = window.centralWidget()
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    bar = pages.tabBar()
    image = window.grab().toImage()
    first = bar.tabRect(0).translated(bar.mapTo(window, QPoint()))
    left = pages.mapTo(window, QPoint()).x()
    ours = _first_edge(image, first.center().y(), left, first.right())

    pages.setCurrentIndex(pages.count() - 1)
    QApplication.processEvents()
    image = window.grab().toImage()
    tabs = [
        widget for widget in window.findChildren(QWidget)
        if widget.metaObject().className() == "ads::CDockWidgetTab"
        and widget.isVisible()
    ]
    assert tabs
    for tab in tabs:
        area = tab.dockAreaWidget()
        start = area.mapTo(window, QPoint()).x()
        rect = tab.rect().translated(tab.mapTo(window, QPoint()))
        assert _first_edge(image, rect.center().y(), start, rect.right()) == (
            ours), tab.dockWidget().windowTitle()
    window.close()
    window.deleteLater()
    QApplication.processEvents()


def _hovered_tab(image, rect):
    """Return the pill's inside, its corner and the inks of a tab's `rect`."""
    pill = rect.adjusted(2, 3, -2, -3)
    inside = image.pixelColor(pill.left() + 3, pill.center().y()).name()
    corner = image.pixelColor(pill.topLeft()).name()
    return inside, corner, _pixels(image, pill.adjusted(1, 1, -1, -1))


@THEMES
def test_a_hovered_tab_shows_the_pill_and_keeps_its_text(qtbot, theme):
    tabs = QTabWidget()
    for name in ("Render", "Comp", "Lighting"):
        tabs.addTab(QLabel(name), name)
    window = themed_window(qtbot, theme, tabs)
    bar = tabs.tabBar()
    colors = fxstyle.colors()
    other = bar.tabRect(1).translated(bar.mapTo(window, QPoint()))
    rest = _pixels(window.grab().toImage(), other.adjusted(0, 0, 0, -2))
    before = bar.tabRect(1)
    hover(qtbot, bar, bar.tabRect(1).center())
    image = window.grab().toImage()
    inside, corner, inks = _hovered_tab(image, other)
    # The pill's fill, rounded, a visible step off the strip, with no edge.
    assert inside == colors.state_hover.lower()
    assert corner != colors.state_hover.lower()
    assert fxstyle.get_contrast_ratio(
        colors.state_hover, colors.surface) >= fxstyle.STATE_MIN_CONTRAST
    assert colors.control_edge.lower() not in inks
    # The text keeps its rest ink: the muted text, not the normal one.
    assert colors.text_muted.lower() in rest
    assert colors.text_muted.lower() in inks
    if colors.text.lower() != colors.text_muted.lower():
        assert colors.text.lower() not in inks
    assert bar.tabRect(1) == before


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_hovered_current_tab_keeps_its_own_fill(qtbot, theme):
    tabs = QTabWidget()
    for name in ("Render", "Comp"):
        tabs.addTab(QLabel(name), name)
    window = themed_window(qtbot, theme, tabs)
    bar = tabs.tabBar()
    current = bar.tabRect(0).translated(bar.mapTo(window, QPoint()))
    hover(qtbot, bar, bar.tabRect(0).center())

    inside, _corner, _inks = _hovered_tab(window.grab().toImage(), current)

    assert inside == fxstyle.colors().state_pressed.lower()


def _pill_leads(image, rect, fill):
    """Return the gaps from a filled pill's sides to its first and last ink."""
    middle = rect.center().y()
    columns = [
        x for x in range(rect.left(), rect.right() + 1)
        if image.pixelColor(x, middle).name() == fill.lower()
    ]
    left, right = min(columns), max(columns)
    ink = [
        x for x in range(left, right + 1)
        for y in range(rect.top(), rect.bottom() + 1)
        if _distance(image.pixelColor(x, y).name(), fill) > 60
    ]
    return min(ink) - left, right - max(ink)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_close_button_stands_as_far_in_as_the_text(qtbot, theme):
    tabs = QTabWidget()
    tabs.setTabsClosable(True)
    for name in ("Untitled", "Other"):
        tabs.addTab(QLabel(name), name)
    window = themed_window(qtbot, theme, tabs)
    bar = tabs.tabBar()
    colors = fxstyle.colors()
    rest = [bar.tabButton(1, QTabBar.RightSide).geometry()]
    current = bar.tabRect(0).translated(bar.mapTo(window, QPoint()))
    lead, trail = _pill_leads(
        window.grab().toImage(), current, colors.state_pressed)
    assert abs(trail - lead) <= 1, (lead, trail)
    hover(qtbot, bar, bar.tabRect(1).topLeft() + QPoint(12, 12))
    other = bar.tabRect(1).translated(bar.mapTo(window, QPoint()))
    lead, trail = _pill_leads(
        window.grab().toImage(), other, colors.state_hover)
    assert abs(trail - lead) <= 1, (lead, trail)
    # Nothing moves between rest, hover and selected.
    rest.append(bar.tabButton(1, QTabBar.RightSide).geometry())
    tabs.setCurrentIndex(1)
    QApplication.processEvents()
    rest.append(bar.tabButton(1, QTabBar.RightSide).geometry())
    assert rest[0] == rest[1] == rest[2]


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_hovered_dock_tab_shows_the_pill_and_keeps_its_text(qtbot, theme):
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    docks.add_dock("one", "Render", QLabel("one"), "left")
    docks.add_dock("two", "Comp", QLabel("two"), "left")
    window = themed_window(qtbot, theme, docks, size=(600, 400))
    _room_for_tabs(docks, "one")
    manager = docks.manager()
    manager.findDockWidget("one").toggleView(True)
    manager.findDockWidget("one").setAsCurrentTab()
    QApplication.processEvents()
    tab = manager.findDockWidget("two").tabWidget()
    colors = fxstyle.colors()
    rect = tab.rect().translated(tab.mapTo(window, QPoint()))
    hover(qtbot, tab, tab.rect().center())
    image = window.grab().toImage()
    inside, corner, inks = _hovered_tab(image, rect)
    assert inside == colors.state_hover.lower()
    assert corner != colors.state_hover.lower()
    assert colors.control_edge.lower() not in inks
    assert colors.text_muted.lower() in inks
    assert colors.text.lower() not in inks


def _pill_run(line):
    """Return the first and last index of the current pill in `line`.

    The pill is the run of non-strip pixels around its first fill pixel: its
    antialiased rim belongs to it.
    """
    colors = fxstyle.colors()
    fill, strip = colors.state_pressed.lower(), colors.surface.lower()
    first = last = line.index(fill)
    while first > 0 and line[first - 1] != strip:
        first -= 1
    while line[last + 1] != strip:
        last += 1
    return first, last


def _vertical_gaps(image, x, top, bottom):
    """Return the strip rows above and below the current pill at column `x`.

    Above runs from `top` to the pill; below, from the pill to the first row
    that is neither the strip nor the pill: the pane's or content's edge.
    """
    strip = fxstyle.colors().surface.lower()
    rows = [image.pixelColor(x, y).name() for y in range(top, bottom)]
    first, last = _pill_run(rows)
    below = 0
    while rows[last + 1 + below] == strip:
        below += 1
    return first, below


def _gap_between(image, y, start, stop):
    """Return the strip columns between the current pill and the hovered one."""
    strip = fxstyle.colors().surface.lower()
    cols = [image.pixelColor(x, y).name() for x in range(start, stop)]
    _first, right = _pill_run(cols)
    nxt = next(i for i in range(right + 1, len(cols)) if cols[i] != strip)
    return nxt - right - 1


def test_the_gaps_around_and_between_tab_pills_are_one_size(qtbot):
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    from fxgui import examples

    fxstyle.apply_theme("dark")
    window = examples.build()
    pages = window.centralWidget()
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    bar = pages.tabBar()
    hover(qtbot, bar, bar.tabRect(1).center())
    image = window.grab().toImage()
    origin = bar.mapTo(window, QPoint())
    first = bar.tabRect(0).translated(origin)
    # Inside the card's 1 px border, as the dock pane's below.
    top = pages.mapTo(window, QPoint()).y() + 1
    above, last = _pill_run([image.pixelColor(first.center().x(), y).name()
                             for y in range(top, first.bottom() + 2)])
    # No edge under the strip: the page itself is what the gap reaches.
    page = pages.currentWidget().mapTo(window, QPoint()).y()
    below = page - (top + last) - 1
    between = _gap_between(
        image, first.center().y(), first.left(), bar.tabRect(1).right())
    gaps = {"above": above, "below": below, "between": between}
    height = bar.tabRect(0).height()

    pages.setCurrentIndex(pages.count() - 1)
    QApplication.processEvents()
    image = window.grab().toImage()
    tab = next(
        widget for widget in window.findChildren(QWidget)
        if widget.metaObject().className() == "ads::CDockWidgetTab"
        and widget.isVisible()
    )
    area = tab.dockAreaWidget()
    rect = tab.rect().translated(tab.mapTo(window, QPoint()))
    # Inside the pane's 1 px border.
    top = area.mapTo(window, QPoint()).y() + 1
    dock_above, dock_below = _vertical_gaps(
        image, rect.center().x(), top, rect.bottom() + 8)
    window.close()
    window.deleteLater()
    QApplication.processEvents()

    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    docks.add_dock("one", "Render", QLabel("one"), "left")
    docks.add_dock("two", "Comp", QLabel("two"), "left")
    holder = themed_window(qtbot, "dark", docks, size=(600, 400))
    _room_for_tabs(docks, "one")
    manager = docks.manager()
    manager.findDockWidget("one").setAsCurrentTab()
    QApplication.processEvents()
    one = manager.findDockWidget("one").tabWidget()
    two = manager.findDockWidget("two").tabWidget()
    hover(qtbot, two, two.rect().center())
    image = holder.grab().toImage()
    left = one.rect().translated(one.mapTo(holder, QPoint()))
    right = two.rect().translated(two.mapTo(holder, QPoint()))
    dock_between = _gap_between(
        image, left.center().y(), left.left(), right.right())

    gaps.update(dock_above=dock_above, dock_below=dock_below,
                dock_between=dock_between)
    assert len(set(gaps.values())) == 1, gaps
    assert one.height() == height


def _start_and_top_gaps(image, pill, left, top):
    """Return the strip columns before and rows above the current `pill`.

    `left` and `top` are the strip's first column and row, inside any edge.
    """
    row = [image.pixelColor(x, pill.center().y()).name()
           for x in range(left, pill.right() + 1)]
    column = [image.pixelColor(pill.center().x(), y).name()
              for y in range(top, pill.bottom() + 1)]
    return _pill_run(row)[0], _pill_run(column)[0]


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_first_tab_pill_starts_as_far_in_as_it_sits_down(qtbot, theme):
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    tabs = QTabWidget()
    tabs.addTab(QLabel("x"), "Render")
    tabs.addTab(QLabel("y"), "Comp")
    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    docks.add_dock("one", "Task", QLabel("one"), "left")
    window = themed_window(qtbot, theme, tabs, docks, size=(600, 500))
    QApplication.processEvents()
    image = window.grab().toImage()
    bar = tabs.tabBar()
    origin = bar.mapTo(window, QPoint())
    # Inside the pane's 1 px edge, which the bar starts past.
    bar_gaps = _start_and_top_gaps(
        image, bar.tabRect(0).translated(origin),
        tabs.mapTo(window, QPoint()).x() + 1, origin.y())
    tab = docks.manager().findDockWidget("one").tabWidget()
    area = tab.dockAreaWidget().mapTo(window, QPoint())
    dock_gaps = _start_and_top_gaps(
        image, tab.rect().translated(tab.mapTo(window, QPoint())),
        area.x() + 1, area.y() + 1)
    assert bar_gaps[0] == bar_gaps[1], bar_gaps
    assert dock_gaps == bar_gaps, (dock_gaps, bar_gaps)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_panes_content_sits_one_tab_gap_in_from_its_edges(qtbot, theme):
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    body = QLabel("body")
    docks.add_dock("one", "Task", body, "left")
    window = themed_window(qtbot, theme, docks, size=(600, 400))
    QApplication.processEvents()
    image = window.grab().toImage()
    tab = docks.manager().findDockWidget("one").tabWidget()
    area_widget = tab.dockAreaWidget()
    area = area_widget.mapTo(window, QPoint())
    pill = tab.rect().translated(tab.mapTo(window, QPoint()))
    gap, _top = _start_and_top_gaps(image, pill, area.x() + 1, area.y() + 1)
    assert gap == fxstyle.PANE_GAP
    content = body.geometry().translated(body.parentWidget().mapTo(
        window, QPoint()))
    # Inside the pane's 1 px edge, and below the pill's own gap.
    inner = area_widget.rect().adjusted(1, 1, -1, -1).translated(area)
    assert content.left() - inner.left() == gap
    assert inner.right() - content.right() == gap
    assert inner.bottom() - content.bottom() == gap
    column = [image.pixelColor(pill.center().x(), y).name()
              for y in range(pill.top(), content.top())]
    assert len(column) - 1 - _pill_run(column)[1] == gap


def test_a_hovered_title_bar_button_is_a_tab_pill_tall(qtbot):
    if fxdocking is None:
        pytest.skip("needs PySide6-QtAds")
    docks = fxdocking.FXDockArea()
    docks.set_central(QLabel("central"))
    docks.add_dock("one", "Render", QLabel("one"), "left")
    docks.add_dock("two", "Comp", QLabel("two"), "left")
    window = themed_window(qtbot, "dark", docks, size=(600, 400))
    _room_for_tabs(docks, "one")
    button = next(
        widget for widget in window.findChildren(QWidget)
        if widget.objectName() == "detachGroupButton" and widget.isVisible()
    )
    tab = docks.manager().findDockWidget("two").tabWidget()
    hover(qtbot, button)
    image = window.grab().toImage()
    strip = fxstyle.colors().surface.lower()

    def rows(widget, x):
        origin = widget.mapTo(window, QPoint())
        found = [
            y for y in range(origin.y(), origin.y() + widget.height())
            if image.pixelColor(origin.x() + x, y).name() != strip
        ]
        return min(found), max(found)

    # The current tab's pill, edge included, a column inside its side edge.
    assert rows(button, button.width() // 2) == rows(tab, tab.width() // 2)


def _completer(qtbot, theme, items=("Alpha", "Beta", "Gamma", "Delta")):
    from qtpy.QtWidgets import QCompleter, QLineEdit

    line = QLineEdit()
    window = themed_window(qtbot, theme, line)
    completer = QCompleter(list(items), line)
    line.setCompleter(completer)
    line.setFocus()
    completer.complete()
    popup = completer.popup()
    qtbot.waitUntil(popup.isVisible)
    return window, completer, popup


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_completer_shows_four_rows_without_scrolling(qtbot, theme):
    _window, _completer_, popup = _completer(qtbot, theme)
    assert popup.verticalScrollBar().maximum() == 0
    popup.hide()


def test_a_completer_in_a_themed_app_shows_four_rows_too(qtbot, app_root):
    from qtpy.QtWidgets import QCompleter, QLineEdit

    line = QLineEdit()
    app_root.layout().addWidget(line)
    app_root.show()
    qtbot.waitExposed(app_root)
    completer = QCompleter(["Alpha", "Beta", "Gamma", "Delta"], line)
    line.setCompleter(completer)
    line.setFocus()
    completer.complete()
    popup = completer.popup()
    qtbot.waitUntil(popup.isVisible)
    assert popup.verticalScrollBar().maximum() == 0
    popup.hide()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_hovered_completer_row_is_the_accent_as_a_menu_row(qtbot, theme):
    _window, completer, popup = _completer(qtbot, theme)
    model = completer.completionModel()
    row = popup.visualRect(model.index(2, 0))
    # Not the hover helper: it would move the popup off its line edit.
    QTest.mouseMove(popup, QPoint(-5, -5))
    qtbot.wait(20)
    QTest.mouseMove(popup.viewport(), row.center())
    qtbot.waitUntil(popup.viewport().underMouse)
    image = popup.viewport().grab().toImage()
    popup.hide()
    # Past the text: a glyph may reach any column near the row's start.
    assert image.pixelColor(row.right() - 4, row.center().y()).name() == (
        fxstyle.colors().accent_primary.lower())


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_combo_and_completer_rows_are_menu_rows_tall(qtbot, theme):
    """A menu row is 24 px at the 12 px body font, its text plus 8 px."""
    _window, completer, popup = _completer(qtbot, theme)
    model = completer.completionModel()
    completer_rows = {
        popup.visualRect(model.index(row, 0)).height() for row in range(4)}
    popup.hide()
    combo = QComboBox()
    combo.addItems(["Alpha", "Beta", "Gamma", "Delta"])
    window = themed_window(qtbot, theme, combo)
    combo.showPopup()
    qtbot.waitUntil(lambda: combo.view().isVisible())
    view = combo.view()
    combo_rows = {
        view.visualRect(view.model().index(row, 0)).height()
        for row in range(4)}
    combo.hidePopup()
    menu = QMenu(window)
    actions = [menu.addAction(name) for name in ("Alpha", "Beta")]
    menu.popup(window.mapToGlobal(QPoint(10, 10)))
    qtbot.waitExposed(menu)
    menu_rows = {menu.actionGeometry(action).height() for action in actions}
    menu.close()
    assert completer_rows == combo_rows == menu_rows
    assert len(menu_rows) == 1


@pytest.mark.parametrize("base", QStyleFactory.keys())
def test_a_combo_row_stands_no_taller_than_a_menu_row_may(qtbot, qapp, base):
    """Windows 11 asks 34 px for a combo row; the sheet caps every style."""
    name = qapp.style().name()
    fxstyle.set_style(qapp, base)
    try:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(["main", "alt"])
        window = themed_window(qtbot, "dark", combo)  # noqa: F841
        combo.showPopup()
        qtbot.waitUntil(lambda: combo.view().isVisible())
        view = combo.view()
        row = view.visualRect(view.model().index(0, 0)).height()
        combo.hidePopup()
    finally:
        fxstyle.set_style(qapp, name or "Fusion")

    assert row <= 24


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_combo_popup_has_the_menu_corners(qtbot, theme):
    combo = QComboBox()
    combo.addItems(["", "", ""])
    window = themed_window(qtbot, theme, combo)
    combo.showPopup()
    qtbot.waitUntil(lambda: combo.view().isVisible())
    combo_image = combo.view().window().grab().toImage()
    combo.hidePopup()
    menu = QMenu(window)
    for _ in range(3):
        menu.addAction("")
    menu.popup(window.mapToGlobal(QPoint(10, 10)))
    qtbot.waitExposed(menu)
    menu_image = menu.grab().toImage()
    menu.close()
    colors = fxstyle.colors()
    for image in (combo_image, menu_image):
        # The edge bends away from the corner, as the card radius draws it.
        assert {image.pixelColor(x, x).name() for x in range(2)} == {
            colors.surface.lower()}
        assert image.pixelColor(0, image.height() // 2).name() == (
            colors.border.lower())


def test_a_tooltip_wears_the_menu_look_and_corners(qtbot, app_root, monkeypatch):
    from qtpy.QtWidgets import QToolTip

    rounded = []
    monkeypatch.setattr(fxutils, "round_window_corners", rounded.append)
    app_root.show()
    qtbot.waitExposed(app_root)
    QToolTip.showText(app_root.mapToGlobal(QPoint(20, 20)), "Tip", app_root)
    tip = next(
        widget for widget in QApplication.topLevelWidgets()
        if widget.windowType() == Qt.ToolTip and widget.isVisible())
    image = tip.grab().toImage()
    QToolTip.hideText()
    colors = fxstyle.colors()
    middle = image.height() // 2
    assert image.pixelColor(0, middle).name() == colors.border.lower()
    assert image.pixelColor(2, middle).name() == colors.surface.lower()
    assert image.pixelColor(0, 0).name() != colors.border.lower()
    assert tip in rounded
