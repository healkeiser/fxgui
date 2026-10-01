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

# Imported here, not in a test: the suite keeps only the sheet fragments
# registered before a test starts.
try:
    from fxgui import fxdocking
except ImportError:
    fxdocking = None

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


# (6) A tab is muted text; the current one an edged pill, in QTabBar and
# QtAds alike.


def _pill(image, rect):
    """Return the current tab's edge rows, its width and its text's rows.

    The edge is the @control_edge ring; rows count from the tab's top.
    """
    colors = fxstyle.colors()
    edge = colors.control_edge.lower()
    fill = colors.state_hover
    middle = rect.center().y()
    columns = [
        x for x in range(rect.left(), rect.right() + 1)
        if image.pixelColor(x, middle).name() == edge
    ]
    centre = (min(columns) + max(columns)) // 2
    rows = [
        y for y in range(rect.top(), rect.bottom() + 1)
        if image.pixelColor(centre, y).name() == edge
    ]
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
def test_the_current_tab_is_an_edged_pill(qtbot, theme):
    tabs = QTabWidget()
    for name in ("Render", "Comp", "Lighting"):
        tabs.addTab(QLabel(name), name)
    window = _shown(qtbot, theme, tabs)
    bar = tabs.tabBar()
    image = window.grab().toImage()
    colors = fxstyle.colors()
    current = bar.tabRect(0).translated(bar.mapTo(window, QPoint()))
    rows, width, _ink = _pill(image, current)
    # A ring: one row at the top and one at the bottom, rounded corners.
    assert len(rows) == 2, rows
    corner = QPoint(current.center().x() - width // 2, current.top() + rows[0])
    assert image.pixelColor(corner).name() != colors.control_edge.lower()
    inside = QPoint(corner.x() + 3, current.center().y())
    assert image.pixelColor(inside).name() == colors.state_hover.lower()
    # The other tabs are bare text on the strip, in the muted tab ink.
    # Above the pane's top edge, which the bar overlaps by a pixel.
    other = bar.tabRect(1).translated(bar.mapTo(window, QPoint()))
    inks = _pixels(image, other.adjusted(0, 0, 0, -2))
    assert colors.control_edge.lower() not in inks
    assert colors.state_hover.lower() not in inks
    assert min(_distance(ink, colors.text_muted) for ink in inks) <= 24
    assert bar.tabRect(0).height() == bar.tabRect(1).height()


@THEMES
def test_inactive_tab_text_reads_at_4_5_to_1(theme):
    fxstyle.apply_theme(theme)
    colors = fxstyle.colors()
    assert fxstyle.get_contrast_ratio(colors.text_muted, colors.surface) >= 4.5
    # The pill's edge is what marks the current tab at 3:1.
    assert fxstyle.get_contrast_ratio(colors.control_edge, colors.surface) >= 3


def test_selecting_a_tab_moves_nothing(qtbot):
    tabs = QTabWidget()
    for name in ("Render", "Comp", "Lighting"):
        tabs.addTab(QLabel(name), name)
    _window = _shown(qtbot, "dark", tabs)
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
    window = _shown(qtbot, theme, tabs, (420, 120))
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


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_completer_list_wears_the_popup_look(qtbot, theme):
    from qtpy.QtWidgets import QCompleter, QLineEdit

    line = QLineEdit()
    window = _shown(qtbot, theme, line)
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
    if fxdocking is None:
        pytest.skip("needs the docking extra")

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
    window = _shown(qtbot, theme, holder, (1400, 600))
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
    # Same height, the pill's edge and the "Assets" text on the same rows.
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


def test_a_tab_is_its_text_plus_the_padding_in_every_state(qtbot):
    if fxdocking is None:
        pytest.skip("needs the docking extra")
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
    _window = _shown(qtbot, "dark", holder, (1000, 500))
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
    assert rest == [_TAB_FRAME] * 6, rest
    _hover(bar, bar.tabRect(1).center())
    _hover(dock_tabs[0], dock_tabs[0].rect().center())
    assert widths() == rest
    tabs.setCurrentIndex(2)
    docks.show_dock(names[0])
    QApplication.processEvents()
    assert widths() == rest


def test_no_dock_tab_in_the_gallery_is_elided(qtbot):
    if fxdocking is None:
        pytest.skip("needs the docking extra")
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
    """Return how far right of `start` the first @control_edge pixel is."""
    edge = fxstyle.colors().control_edge.lower()
    return next(
        x - start for x in range(start, stop)
        if image.pixelColor(x, y).name() == edge
    )


def test_a_dock_tab_starts_as_far_in_as_a_tab_bar_tab(qtbot):
    """Measured from the strip's own start: a pane's starts inside its edge."""
    if fxdocking is None:
        pytest.skip("needs the docking extra")
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
    left = bar.mapTo(window, QPoint()).x()
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
    border = 1
    for tab in tabs:
        area = tab.dockAreaWidget()
        start = area.mapTo(window, QPoint()).x() + border
        rect = tab.rect().translated(tab.mapTo(window, QPoint()))
        assert _first_edge(image, rect.center().y(), start, rect.right()) == (
            ours), tab.dockWidget().windowTitle()
    window.close()
    window.deleteLater()
    QApplication.processEvents()
