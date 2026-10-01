"""The command palette filters as you type, runs on Enter, and gets out of the way."""

# Third-party
from qtpy.QtCore import QPoint, Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QMainWindow

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
    palette.open_commands(window.mapToGlobal(QPoint(450, 20)))
    qtbot.waitUntil(palette.isVisible, timeout=1000)
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
    QTest.qWait(50)

    assert not palette.isVisible()


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
        window.mapToGlobal(QPoint(450, 20)), held.append, picked.append,
        loading="Loading shots and tasks",
    )

    assert _labels(palette) == ["Loading shots and tasks"]
    held[0]([("pilot/sh0010/lighting", "sh0010 lighting")])
    assert _labels(palette) == ["sh0010 lighting"]
    QTest.keyClick(palette.field, Qt.Key_Return)
    assert picked == ["pilot/sh0010/lighting"]


def test_a_leading_angle_switches_go_to_to_commands(qtbot):
    window = _window(qtbot)
    palette = FXCommandPalette(window, lambda: _commands([]))
    palette.open_go_to(
        window.mapToGlobal(QPoint(450, 20)),
        lambda landed: landed([("a", "sh0010 lighting")]),
        lambda _row: None,
    )

    _type(palette, ">keyboard")

    assert _labels(palette) == ["Keyboard shortcuts"]
