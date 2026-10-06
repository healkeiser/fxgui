"""The command palette filters as you type, runs on Enter, and gets out of the way."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QLabel, QMainWindow

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXCommand, FXCommandPalette


rank = FXCommandPalette.rank


def _window(qtbot):
    window = QMainWindow()
    fxstyle.register_themed_root(window)
    qtbot.addWidget(window)
    window.resize(900, 600)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    return window


def _palette(qtbot, commands):
    window = _window(qtbot)
    palette = FXCommandPalette(window, lambda: commands)
    palette.open_commands()
    qtbot.waitUntil(palette.isVisible)
    return window, palette


def _labels(palette):
    rows = palette.rows
    return [rows.topLevelItem(i).text(0) for i in range(rows.topLevelItemCount())]


def _type(palette, text):
    QTest.keyClicks(palette.field, text)
    QTest.qWait(20)


def _commands(ran):
    return [
        FXCommand("Collapse all", lambda: ran.append("fold"), "Ctrl+-",
                  "View", tip="Close every branch"),
        FXCommand("Expand loaded", lambda: ran.append("open"), section="View"),
        FXCommand("Keyboard shortcuts", lambda: ran.append("keys"),
                  section="Help"),
    ]


def test_matching_takes_every_word_in_order():
    assert rank("ep seq sh", "ep010 seq010 sh0010 layout") is not None
    assert rank("SH0010 LAY", "ep010 seq010 sh0010 layout") is not None
    assert rank("sh seq", "ep010 seq010 sh0010 layout") is None
    assert rank("anim", "ep010 seq010 sh0010 layout") is None


def test_word_starts_rank_before_inner_matches():
    start = rank("lay", "ep010 layout")
    inner = rank("lay", "display")
    assert start is not None and inner is not None
    assert start < inner


def test_typing_filters_and_enter_runs_the_first(qtbot):
    ran = []
    _window_, palette = _palette(qtbot, _commands(ran))

    _type(palette, "collapse all")
    assert _labels(palette) == ["Collapse all"]
    QTest.keyClick(palette.field, Qt.Key_Return)

    assert ran == ["fold"]
    assert not palette.isVisible()


def test_arrow_keys_move_the_choice(qtbot):
    _window_, palette = _palette(qtbot, _commands([]))
    _type(palette, "e")
    first = palette.rows.currentItem().text(0)

    QTest.keyClick(palette.field, Qt.Key_Down)
    assert palette.rows.currentItem().text(0) != first
    QTest.keyClick(palette.field, Qt.Key_Up)
    assert palette.rows.currentItem().text(0) == first


def test_a_disabled_command_shows_its_tip_and_does_not_run(qtbot):
    ran = []
    blocked = FXCommand("Blocked thing", lambda: ran.append("ran"),
                        section="Act", enabled=False, tip="Pick a task first")
    _window_, palette = _palette(qtbot, [blocked])

    _type(palette, "blocked")
    QTest.keyClick(palette.field, Qt.Key_Return)

    assert ran == []
    assert palette.isVisible()
    assert palette.hint.text() == "Pick a task first"


def test_escape_closes(qtbot):
    _window_, palette = _palette(qtbot, _commands([]))

    QTest.keyClick(palette.field, Qt.Key_Escape)

    assert not palette.isVisible()


def test_a_click_outside_closes(qtbot):
    window, palette = _palette(qtbot, _commands([]))

    assert QApplication.activePopupWidget() is palette
    # A popup holds the mouse: Qt hands it the click, outside its rect.
    corner = palette.mapFromGlobal(
        window.mapToGlobal(QPoint(20, window.height() - 40))
    )
    assert not palette.rect().contains(corner)
    QTest.mouseClick(palette, Qt.LeftButton, pos=corner)

    qtbot.waitUntil(lambda: not palette.isVisible())


def _below_rows(palette):
    """The height between the list's bottom and the frame's inside."""
    return palette.contentsRect().bottom() - palette.rows.geometry().bottom()


def test_a_row_with_no_tip_leaves_no_hint_line(qtbot):
    _window_, palette = _palette(qtbot, _commands([]))
    _type(palette, "expand")

    assert palette.hint.isHidden()
    assert _below_rows(palette) == palette.layout().contentsMargins().bottom()


def test_a_command_s_tip_shows_under_the_list(qtbot):
    _window_, palette = _palette(qtbot, _commands([]))
    _type(palette, "collapse all")

    layout = palette.layout()
    assert palette.hint.isVisible()
    assert palette.hint.text() == "Close every branch"
    assert _below_rows(palette) == (
        layout.spacing() + palette.hint.height()
        + layout.contentsMargins().bottom()
    )


def test_the_selected_row_is_one_band_across_its_columns(qtbot):
    _window_, palette = _palette(qtbot, _commands([]))
    _type(palette, "collapse all")
    rows = palette.rows
    item = rows.currentItem()
    image = rows.viewport().grab().toImage()
    band = rows.visualItemRect(item)
    fill = image.pixelColor(band.center().x() // 4, band.top())

    # Where one column meets the next, top and bottom edges alike.
    for column in (1, 2):
        seam = rows.header().sectionPosition(column)
        for y in (band.top(), band.bottom()):
            for x in (seam - 1, seam):
                assert image.pixelColor(x, y) == fill, (column, x, y)


def test_go_to_reads_loading_until_the_rows_land(qtbot):
    window = _window(qtbot)
    palette = FXCommandPalette(window, lambda: _commands([]))
    held, picked = [], []

    palette.open_go_to(
        held.append, picked.append,
        loading="Loading shots and tasks",
    )

    assert _labels(palette) == ["Loading shots and tasks"]
    held[0]([("pilot/sh0010/lighting", "sh0010 lighting")])
    assert _labels(palette) == ["sh0010 lighting"]
    QTest.keyClick(palette.field, Qt.Key_Return)
    assert picked == ["pilot/sh0010/lighting"]


def test_a_slow_load_does_not_overwrite_a_newer_one(qtbot):
    window = _window(qtbot)
    palette = FXCommandPalette(window, lambda: _commands([]))
    held = []
    palette.open_go_to(held.append, lambda _row: None)
    palette.open_go_to(held.append, lambda _row: None)

    held[1]([("new", "sh0020 new")])
    held[0]([("old", "sh0010 old")])
    assert _labels(palette) == ["sh0020 new"]

    palette.open_commands()
    held[1]([("new", "sh0020 new")])
    assert "sh0020 new" not in _labels(palette)


def test_a_leading_angle_switches_go_to_to_commands(qtbot):
    window = _window(qtbot)
    palette = FXCommandPalette(window, lambda: _commands([]))
    palette.open_go_to(
        lambda landed: landed([("a", "sh0010 lighting")]),
        lambda _row: None,
    )

    _type(palette, ">keyboard")

    assert _labels(palette) == ["Keyboard shortcuts"]


def _placed(qtbot, position, size=(900, 600)):
    window = QMainWindow()
    fxstyle.register_themed_root(window)
    window.menuBar().addMenu("File")
    window.setCentralWidget(QLabel("body"))
    window.statusBar().showMessage("ready")
    qtbot.addWidget(window)
    window.resize(*size)
    window.show()
    qtbot.waitExposed(window)
    palette = FXCommandPalette(window, lambda: _commands([]))
    palette.open_commands(position=position)
    qtbot.waitUntil(palette.isVisible)
    central = window.centralWidget()
    area = central.geometry()
    area.moveTopLeft(window.mapToGlobal(area.topLeft()))
    return window, palette, palette.frameGeometry(), area


@pytest.mark.parametrize("position", ["top", "center", "bottom"])
def test_the_palette_opens_centred_across_its_window(qtbot, position):
    window, _palette_, frame, area = _placed(qtbot, position)
    middle = window.mapToGlobal(window.rect().center()).x()
    assert abs(frame.center().x() - middle) <= 1


def test_top_opens_under_the_menu_and_bottom_over_the_status_bar(qtbot):
    _w, _p, top, area = _placed(qtbot, "top")
    assert area.top() <= top.top() <= area.top() + 16
    _w, _p, bottom, area = _placed(qtbot, "bottom")
    assert area.bottom() - 16 <= bottom.bottom() <= area.bottom()
    _w, _p, centre, area = _placed(qtbot, "center")
    assert abs(centre.center().y() - area.center().y()) <= 1


@pytest.mark.parametrize("position", ["top", "center", "bottom"])
def test_the_palette_stays_inside_a_small_window(qtbot, position):
    window, _palette_, frame, _area = _placed(qtbot, position, (320, 200))
    inside = window.frameGeometry()
    assert inside.contains(frame.topLeft()) and inside.contains(
        frame.bottomRight()
    ), (inside, frame)


def test_an_unknown_position_is_refused(qtbot):
    window = _window(qtbot)
    palette = FXCommandPalette(window, lambda: [])
    with pytest.raises(ValueError):
        palette.open_commands(position="left")


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_palette_wears_a_popup_frame(qtbot, theme):
    fxstyle.apply_theme(theme)
    _window_, palette = _palette(qtbot, _commands([]))
    image = palette.grab().toImage()
    border = fxstyle.colors().border.lower()
    middle = palette.height() // 2
    assert image.pixelColor(palette.width() // 2, 0).name() == border
    assert image.pixelColor(0, middle).name() == border
    # Rounded at the card radius, a popup's: the corner pixel is not the edge.
    assert image.pixelColor(fxstyle.CARD_RADIUS + 1, 0).name() == border
    assert image.pixelColor(fxstyle.BUTTON_RADIUS, 0).name() != border
    assert image.pixelColor(0, 0).name() != border


def test_the_palette_asks_for_the_platform_s_flyout_corners(qtbot, monkeypatch):
    from fxgui import fxutils

    asked = []
    monkeypatch.setattr(fxutils, "round_window_corners", asked.append)
    _window_, palette = _palette(qtbot, _commands([]))
    assert asked == [palette]


def _ink(palette, row, column):
    from qtpy.QtGui import QPalette
    from qtpy.QtWidgets import QStyleOptionViewItem

    rows = palette.rows
    option = QStyleOptionViewItem()
    index = rows.model().index(row, column)
    rows.itemDelegate().initStyleOption(option, index)
    return option.palette.color(QPalette.Text).name()


def test_open_rows_take_a_theme_switch(qtbot):
    blocked = FXCommand("Blocked", lambda: None, section="Act", enabled=False)
    _window_, palette = _palette(qtbot, [*_commands([]), blocked])
    fxstyle.apply_theme("light")
    colors = fxstyle.colors()

    labels = _labels(palette)
    assert _ink(palette, 0, 1) == colors.text_muted.lower()
    assert _ink(palette, labels.index("Blocked"), 0) == (
        colors.text_disabled.lower()
    )
    assert not hasattr(palette, "_items") and not hasattr(palette, "_shown")


def _text_left(palette, row):
    from qtpy.QtWidgets import QStyle, QStyleOptionViewItem

    rows = palette.rows
    option = QStyleOptionViewItem()
    rows.initViewItemOption(option)
    index = rows.model().index(row, 0)
    option.rect = rows.visualRect(index)
    rows.itemDelegate().initStyleOption(option, index)
    return rows.style().subElementRect(
        QStyle.SE_ItemViewItemText, option, rows).left()


def test_a_command_s_icon_shows_left_of_its_label_in_the_icon_ink(qtbot):
    from qtpy.QtWidgets import QStyle

    from _helpers import inks

    commands = [
        FXCommand("Plain", lambda: None),
        FXCommand("Search", lambda: None, icon="search"),
    ]
    _window_, palette = _palette(qtbot, commands)
    rows = palette.rows
    # Row 1 is not current, so its icon wears the normal ink.
    band = rows.visualItemRect(rows.topLevelItem(1))
    side = rows.style().pixelMetric(QStyle.PM_SmallIconSize)
    image = palette.grab().toImage()
    at = rows.viewport().mapTo(palette, band.topLeft())
    icon = image.copy(at.x(), at.y(), _text_left(palette, 1) - band.left(),
                      band.height())

    assert rows.iconSize().width() == side == 16
    assert fxstyle.colors().icon.lower() in inks(icon)
    assert _text_left(palette, 0) == _text_left(palette, 1) > band.left() + 16


def _hint_gaps(palette):
    """Return the hint's ink gaps to the list above and the frame below."""
    from qtpy.QtGui import QColor

    image = palette.grab().toImage()
    surface = QColor(fxstyle.colors().surface)
    top = palette.rows.geometry().bottom() + 1
    bottom = palette.contentsRect().bottom()
    left, right = palette.hint.geometry().left(), palette.hint.geometry().right()

    def inked(y):
        return any(
            max(abs(c.red() - surface.red()), abs(c.green() - surface.green()),
                abs(c.blue() - surface.blue())) > 60
            for c in (image.pixelColor(x, y) for x in range(left, right + 1))
        )

    rows = [y for y in range(top, bottom + 1) if inked(y)]
    return rows[0] - top, bottom - rows[-1]


def test_every_tip_sits_with_the_same_margins(qtbot):
    long = "<b>Rich</b> and long: " + "a tip that wraps " * 12 + "up"
    commands = [
        FXCommand("Plain", lambda: None, tip="A plain tip"),
        FXCommand("Rich", lambda: None, tip=long),
    ]
    _window_, palette = _palette(qtbot, commands)
    plain = _hint_gaps(palette)
    palette.rows.setCurrentItem(palette.rows.topLevelItem(1))
    QApplication.processEvents()
    rich = _hint_gaps(palette)

    assert palette.hint.height() > palette.fontMetrics().height() * 2
    assert abs(plain[0] - rich[0]) <= 1, (plain, rich)
    assert abs(plain[1] - rich[1]) <= 1, (plain, rich)


def _launch(ran):
    def flavor(name):
        return FXCommand(name, lambda: ran.append(name))

    return FXCommand(
        "Launch", icon="rocket_launch",
        choices=lambda: [
            flavor("Blender"),
            FXCommand("Houdini", choices=lambda: [
                flavor("Houdini FX"), flavor("Houdini Core")]),
        ],
    )


def test_a_command_with_choices_lists_them_in_place(qtbot):
    ran = []
    _window_, palette = _palette(qtbot, [_launch(ran)])

    QTest.keyClick(palette.field, Qt.Key_Return)

    assert palette.isVisible(), "picking a command with choices keeps it open"
    assert _labels(palette) == ["Blender", "Houdini"]
    assert palette.field.text() == ""
    assert "Launch" in palette.field.placeholderText()
    assert ran == []


def test_typing_filters_the_choices_and_enter_runs_one(qtbot):
    ran = []
    _window_, palette = _palette(qtbot, [_launch(ran)])
    QTest.keyClick(palette.field, Qt.Key_Return)

    _type(palette, "houd")
    QTest.keyClick(palette.field, Qt.Key_Return)
    assert _labels(palette) == ["Houdini FX", "Houdini Core"], "a nested step"
    _type(palette, "core")
    QTest.keyClick(palette.field, Qt.Key_Return)

    assert ran == ["Houdini Core"]
    assert not palette.isVisible()


def test_a_command_with_no_choices_says_so(qtbot):
    _window_, palette = _palette(
        qtbot, [FXCommand("Launch", choices=lambda: [])])

    QTest.keyClick(palette.field, Qt.Key_Return)

    assert _labels(palette) == ["Nothing to pick"]


def test_reopening_after_a_choice_step_lists_the_commands_again(qtbot):
    ran = []
    _window_, palette = _palette(qtbot, [_launch(ran), *_commands(ran)])
    QTest.keyClick(palette.field, Qt.Key_Return)
    QTest.keyClick(palette.field, Qt.Key_Escape)

    palette.open_commands()

    assert "Collapse all" in _labels(palette)


def test_a_library_icon_shows_and_a_missing_one_falls_back(qtbot):
    commands = [
        FXCommand("Houdini", icon="brands:houdini_mark"),
        FXCommand("In-house", icon="brands:no_such_tool"),
    ]
    _window_, palette = _palette(qtbot, commands)

    rows = palette.rows
    for index in range(rows.topLevelItemCount()):
        icon = rows.topLevelItem(index).icon(0)
        assert not icon.isNull() and not icon.pixmap(16, 16).isNull()


def _sections(palette):
    rows = palette.rows
    return [rows.topLevelItem(i).text(1) for i in range(rows.topLevelItemCount())]


def test_the_command_run_last_comes_first_next_time(qtbot):
    ran = []
    _window_, palette = _palette(qtbot, _commands(ran))
    told = []
    palette.recent_changed.connect(told.append)

    _type(palette, "keyboard")
    QTest.keyClick(palette.field, Qt.Key_Return)
    palette.open_commands()

    assert _labels(palette)[0] == "Keyboard shortcuts"
    assert _sections(palette)[0] == "recently used"
    assert _sections(palette)[1:] == ["View", "View"], "the rest keep theirs"
    assert told == [["Keyboard shortcuts"]]


def test_recent_rows_lead_the_matches_too(qtbot):
    window = _window(qtbot)
    palette = FXCommandPalette(
        window, lambda: _commands([]), recent=["Expand loaded"])
    palette.open_commands()

    _type(palette, "l")

    assert _labels(palette)[0] == "Expand loaded"


def test_a_key_outlives_a_label_that_changes(qtbot):
    window = _window(qtbot)
    shown = {"label": "Show Log"}
    palette = FXCommandPalette(window, lambda: [
        *_commands([]), FXCommand(shown["label"], lambda: None, key="log")])
    palette.open_commands()
    _type(palette, "show log")
    QTest.keyClick(palette.field, Qt.Key_Return)

    shown["label"] = "Hide Log"
    palette.open_commands()

    assert palette.recent == ["log"]
    assert _labels(palette)[0] == "Hide Log"


def test_a_choice_picked_last_comes_first_among_its_choices(qtbot):
    ran = []
    _window_, palette = _palette(qtbot, [*_commands(ran), _launch(ran)])
    _type(palette, "launch")
    QTest.keyClick(palette.field, Qt.Key_Return)
    _type(palette, "houdini")
    QTest.keyClick(palette.field, Qt.Key_Return)
    _type(palette, "core")
    QTest.keyClick(palette.field, Qt.Key_Return)

    palette.open_commands()
    assert _labels(palette)[0] == "Launch"
    QTest.keyClick(palette.field, Qt.Key_Return)
    assert _labels(palette) == ["Houdini", "Blender"]
    QTest.keyClick(palette.field, Qt.Key_Return)
    assert _labels(palette) == ["Houdini Core", "Houdini FX"]
    assert palette.recent == [
        "Launch/Houdini/Houdini Core", "Launch/Houdini", "Launch"]


def test_go_to_rows_are_not_remembered(qtbot):
    window = _window(qtbot)
    palette = FXCommandPalette(window, lambda: _commands([]))
    palette.open_go_to(
        lambda landed: landed([("a", "sh0010 lighting")]), lambda _row: None)

    QTest.keyClick(palette.field, Qt.Key_Return)

    assert palette.recent == []
