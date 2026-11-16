"""The segmented tab bar and a tab's count, as a caller opts in."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLabel, QTabBar, QTabWidget, QVBoxLayout, QWidget

# Internal
from fxgui import _tabs, fxstyle

NAMES = ("All", "Pipeline", "Farm")


def _color(role):
    return QColor(getattr(fxstyle.colors(), role)).name()


def _bar(qtbot, segmented=True, counts=(), theme="dark", closable=False):
    fxstyle.apply_theme(theme)
    host = QWidget()
    fxstyle.register_themed_root(host)
    bar = QTabBar()
    bar.setTabsClosable(closable)
    for name in NAMES:
        bar.addTab(name)
    if segmented:
        fxstyle.mark_as_segmented(bar)
    for index, count in enumerate(counts):
        fxstyle.set_tab_count(bar, index, count)
    layout = QVBoxLayout(host)
    layout.addWidget(bar)
    layout.addStretch()
    host.resize(400, 120)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host, bar


def _painter(bar):
    return bar.findChild(_tabs._Segmented, "", Qt.FindDirectChildrenOnly)


def _count(bar, index):
    room = bar.tabButton(index, QTabBar.RightSide)
    return room.badge if isinstance(room, _tabs._CountRoom) else None


def _pixel(bar, point):
    return bar.grab().toImage().pixelColor(point).name()


# -- The segmented bar ------------------------------------------------------


def test_a_segmented_bar_is_a_36px_track_of_28px_tabs(qtbot):
    _host, bar = _bar(qtbot)
    painter = _painter(bar)

    assert bar.height() == 36
    for index in range(bar.count()):
        assert bar.tabRect(index).height() == 36
        assert painter.chip(index).height() == 28
    # The track's 4 px padding: the first chip's left, the last's right.
    assert painter.chip(0).left() == 4
    assert painter.chip(2).right() == bar.tabRect(2).right() + 1 - 4
    # Side by side: no gap between tabs, unlike the plain bar's 6 px.
    assert bar.tabRect(1).left() == bar.tabRect(0).right() + 1


@pytest.mark.parametrize("theme", ["dark", "github_light"])
def test_the_track_and_chip_wear_the_theme(qtbot, theme):
    _host, bar = _bar(qtbot, theme=theme)
    chip = _painter(bar).chip(0).toRect()
    other = _painter(bar).chip(1).toRect()

    assert _pixel(bar, QPoint(other.left() + 2, other.center().y())) == (
        _color("state_pressed")), "the track"
    assert _pixel(bar, QPoint(chip.left() + 3, chip.center().y())) == (
        _color("surface")), "the chip"
    assert _pixel(bar, QPoint(chip.left(), chip.center().y())) == (
        _color("border")), "the chip's 1 px ring"


def test_the_picked_tab_reads_strong_and_the_rest_muted(qtbot):
    _host, bar = _bar(qtbot)
    image = bar.grab().toImage()

    def inks(index):
        rect = bar.tabRect(index)
        return {image.pixelColor(x, y).name()
                for x in range(rect.left(), rect.right())
                for y in range(rect.top(), rect.bottom())}

    assert _color("text_strong") in inks(0)
    assert _color("text_muted") in inks(1)
    assert _color("text_strong") not in inks(1)


def test_the_chip_jumps_under_reduced_motion(qtbot):
    _host, bar = _bar(qtbot)
    painter = _painter(bar)
    bar.setCurrentIndex(2)
    bar.grab()

    assert painter._shown == painter.chip(2)


def test_the_chip_slides_on_the_spring(qtbot, motion):
    _host, bar = _bar(qtbot)
    painter = _painter(bar)
    bar.grab()
    bar.setCurrentIndex(2)
    qtbot.wait(fxstyle.MOTION_SPRING // 4)
    bar.grab()
    start, end = painter.chip(0), painter.chip(2)

    assert start.left() < painter._shown.left() < end.left(), "on its way"
    qtbot.waitUntil(
        lambda: painter._slide.state() != painter._slide.State.Running,
        timeout=fxstyle.MOTION_SPRING * 3)
    bar.grab()
    assert painter._shown == end


def test_a_tab_widget_can_be_marked_and_unmarked(qtbot):
    fxstyle.apply_theme("dark")
    tabs = QTabWidget()
    fxstyle.register_themed_root(tabs)
    for name in NAMES:
        tabs.addTab(QLabel(name), name)
    qtbot.addWidget(tabs)
    tabs.show()
    qtbot.waitExposed(tabs)
    plain = [tabs.tabBar().tabRect(i) for i in range(tabs.count())]

    fxstyle.mark_as_segmented(tabs)
    assert tabs.tabBar().property(_tabs.SEGMENTED_PROPERTY) is True
    assert tabs.tabBar().tabRect(0).height() == 36

    fxstyle.mark_as_segmented(tabs, False)
    assert [tabs.tabBar().tabRect(i) for i in range(tabs.count())] == plain
    assert len(tabs.tabBar().findChildren(_tabs._Segmented)) == 1


def test_marking_one_bar_leaves_the_plain_bars_alone(qtbot):
    _host, plain = _bar(qtbot, segmented=False)
    before = [plain.tabRect(i) for i in range(plain.count())]
    _other_host, _bar_marked = _bar(qtbot)

    assert [plain.tabRect(i) for i in range(plain.count())] == before
    assert _pixel(plain, plain.tabRect(1).center()) != _color("state_pressed")


# -- Counts -----------------------------------------------------------------


@pytest.mark.parametrize("segmented", [False, True])
def test_a_count_is_a_20px_badge_4px_after_the_label(qtbot, segmented):
    _host, bar = _bar(qtbot, segmented=segmented, counts=(26, 5, 2))
    for index in range(bar.count()):
        badge = _count(bar, index)
        label = _tabs._label_rect(bar, index, badge.room.size())
        tab = bar.tabRect(index)

        assert badge.isVisible()
        assert badge.height() == 20
        assert badge.x() == label.right() + 1 + 4
        assert tab.top() < badge.y() and badge.geometry().bottom() < tab.bottom()
        # Inside its tab, past the label, before the tab's end.
        assert badge.geometry().right() < tab.right()


def test_a_count_is_10px_text_at_the_emphasis_weight(qtbot):
    _host, bar = _bar(qtbot, counts=(26,))
    font = _count(bar, 0).font()

    assert font.pixelSize() == 10
    assert font.weight() == fxstyle._WEIGHTS[
        fxstyle.drawn_weight(fxstyle.EMPHASIS_WEIGHT)]


@pytest.mark.parametrize("theme", ["dark", "github_light"])
def test_a_count_wears_a_border_light_ring(qtbot, theme):
    _host, bar = _bar(qtbot, counts=(26,), theme=theme)
    badge = _count(bar, 0)
    image = badge.grab().toImage()
    middle = badge.height() // 2

    assert image.pixelColor(0, middle).name() == _color("border_light")
    assert image.pixelColor(1, middle).name() == _color("surface")


def test_a_reader_hears_label_and_count(qtbot):
    _host, bar = _bar(qtbot, counts=(26,))
    bar.setTabText(1, "&Pipeline")
    fxstyle.set_tab_count(bar, 1, 5)

    assert bar.accessibleTabName(0) == "All, 26"
    assert bar.accessibleTabName(1) == "Pipeline, 5"


def test_none_removes_the_count(qtbot):
    _host, bar = _bar(qtbot, counts=(26,))
    width = bar.tabRect(0).width()
    fxstyle.set_tab_count(bar, 0, None)
    qtbot.waitUntil(lambda: not bar.findChildren(_tabs._Count))

    assert bar.tabButton(0, QTabBar.RightSide) is None
    assert bar.accessibleTabName(0) == ""
    assert bar.tabRect(0).width() < width


def test_a_new_count_updates_the_badge_in_place(qtbot):
    _host, bar = _bar(qtbot, counts=(5,))
    room = bar.tabButton(0, QTabBar.RightSide)
    fxstyle.set_tab_count(bar, 0, 1200)

    assert bar.tabButton(0, QTabBar.RightSide) is room
    assert room.badge.text() == "1200"
    assert room.width() == room.badge.width() > 24


def test_a_click_on_the_count_picks_its_tab(qtbot):
    _host, bar = _bar(qtbot, counts=(26, 5, 2))
    badge = _count(bar, 2)
    QTest.mouseClick(bar, Qt.LeftButton, Qt.NoModifier,
                     badge.geometry().center())

    assert bar.currentIndex() == 2


def test_a_removed_tab_takes_its_count_along(qtbot):
    _host, bar = _bar(qtbot, counts=(26, 5, 2))
    bar.removeTab(1)
    qtbot.waitUntil(lambda: len(bar.findChildren(_tabs._Count)) == 2)


def test_a_bad_index_raises(qtbot):
    _host, bar = _bar(qtbot)
    with pytest.raises(IndexError):
        fxstyle.set_tab_count(bar, 3, 1)


def test_a_closable_bar_puts_the_count_before_the_label(qtbot):
    _host, bar = _bar(qtbot, segmented=False, closable=True, counts=(26,))

    assert isinstance(bar.tabButton(0, QTabBar.LeftSide), _tabs._CountRoom)
    assert bar.tabButton(0, QTabBar.RightSide).metaObject().className() == (
        "CloseButton")


def test_a_count_follows_a_theme_switch(qtbot):
    _host, bar = _bar(qtbot, counts=(26,))
    fxstyle.apply_theme("github_light")
    qtbot.wait(10)
    badge = _count(bar, 0)
    image = badge.grab().toImage()

    assert image.pixelColor(1, badge.height() // 2).name() == _color("surface")
    assert badge.height() == 20
