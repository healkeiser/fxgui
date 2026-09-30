"""FXTooltip lifecycle, click-outside, the manager's item text, item tips."""

# Built-in
import os

# Third-party
from qtpy.QtCore import QEvent, QPoint, QRect, Qt
from qtpy.QtGui import QHelpEvent
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate, FXTooltip, set_tooltip
from fxgui.fxwidgets._tooltip import FXTooltipManager


def _visible_tooltips():
    return [
        w
        for w in QApplication.topLevelWidgets()
        if isinstance(w, FXTooltip) and w.isVisible()
    ]


def _shown(qtbot, widget):
    qtbot.addWidget(widget)
    widget.resize(120, 40)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_a_click_outside_hides_a_shown_tooltip(qtbot):
    anchor = _shown(qtbot, QWidget())
    other = _shown(qtbot, QWidget())
    other.move(600, 600)
    tip = FXTooltip(parent=anchor, description="probe", persistent=True)
    tip.show_at_rect(QRect(10, 10, 20, 20))
    qtbot.waitUntil(tip.isVisible)
    QTest.mouseClick(other, Qt.LeftButton)
    qtbot.waitUntil(lambda: not tip.isVisible(), timeout=1000)
    tip.close()


def test_showing_again_mid_fade_out_stays_shown(qtbot):
    anchor = _shown(qtbot, QWidget())
    tip = FXTooltip(parent=anchor, description="probe", persistent=True)
    tip.show_tooltip()
    tip.hide_tooltip()
    tip.show_tooltip()
    qtbot.wait(400)
    assert tip.isVisible()
    tip.close()


def test_a_one_shot_tooltip_is_deleted_and_clears_the_marker(qtbot):
    anchor = _shown(qtbot, QWidget())
    tip = FXTooltip.show_for_widget(anchor, description="probe", duration=30)
    gone = []
    tip.destroyed.connect(lambda: gone.append(True))
    assert anchor.property("fx_has_explicit_tooltip")
    qtbot.waitUntil(lambda: bool(gone), timeout=2000)
    assert not anchor.property("fx_has_explicit_tooltip")


def test_a_rect_tooltip_is_deleted_when_done(qtbot):
    tip = FXTooltip.show_for_rect(QRect(0, 0, 10, 10), description="x", duration=30)
    gone = []
    tip.destroyed.connect(lambda: gone.append(True))
    qtbot.waitUntil(lambda: bool(gone), timeout=2000)


def test_fxtooltip_is_not_a_theme_aware_mixin(qtbot):
    tip = FXTooltip(description="probe")
    try:
        assert not isinstance(tip, fxstyle.FXThemeAware)
    finally:
        tip.deleteLater()


def _tree_index(qtbot, text, **roles):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    item = QTreeWidgetItem(tree, [text])
    for role, value in roles.items():
        item.setData(0, role, value)
    return tree, tree.model().index(0, 0)


def test_the_item_tooltip_role_wins(qtbot):
    tree, index = _tree_index(qtbot, "Name")
    tree.topLevelItem(0).setData(0, Qt.ToolTipRole, "Custom tip")
    manager = FXTooltipManager()
    assert manager._get_item_view_tooltip(tree, index) == "Custom tip"


def test_item_text_is_escaped(qtbot):
    tree, index = _tree_index(qtbot, "a<b>c")
    tree.topLevelItem(0).setData(
        0, FXThumbnailDelegate.DESCRIPTION_ROLE, "x & y"
    )
    text = FXTooltipManager()._get_item_view_tooltip(tree, index)
    assert "a&lt;b&gt;c" in text
    assert "x &amp; y" in text


def test_hover_events_do_not_touch_the_disk(qtbot, monkeypatch):
    calls = []
    real = os.stat

    def counting_stat(path, *args, **kwargs):
        calls.append(str(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", counting_stat)
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    item = QTreeWidgetItem(tree, ["Shot"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, "C:/nope/x.png")
    tree.show()
    qtbot.waitExposed(tree)
    manager = FXTooltipManager()
    viewport = tree.viewport()
    center = tree.visualItemRect(item).center()
    for _ in range(3):
        event = QHelpEvent(QEvent.ToolTip, center, viewport.mapToGlobal(center))
        manager.eventFilter(viewport, event)
    manager._show_timer.stop()
    assert [c for c in calls if "nope" in c] == []


def test_item_tooltips_share_one_handler_and_build_on_show(qtbot):
    from fxgui.fxwidgets._tooltip import _ItemTooltipHandler

    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    _shown(qtbot, tree)
    tree.resize(200, 120)
    items = [QTreeWidgetItem(tree, [f"Item {i}"]) for i in range(3)]
    before = set(QApplication.topLevelWidgets())
    for item in items:
        set_tooltip(item, description="tip", title=item.text(0), show_delay=0)
    assert len(tree.findChildren(_ItemTooltipHandler)) == 1
    created = [
        w
        for w in QApplication.topLevelWidgets()
        if isinstance(w, FXTooltip) and w not in before
    ]
    assert created == []

    center = tree.visualItemRect(items[1]).center()
    QTest.mouseMove(tree.viewport(), center)
    qtbot.waitUntil(lambda: bool(_visible_tooltips()), timeout=1000)
    assert _visible_tooltips()[0]._title == "Item 1"
    QTest.mouseMove(tree.viewport(), QPoint(190, 115))
    qtbot.waitUntil(lambda: not _visible_tooltips(), timeout=1000)


def test_dropping_a_shown_tooltip_does_not_crash(qtbot):
    # The anchor dies at teardown while the tooltip is still on screen.
    anchor = QWidget()
    qtbot.addWidget(anchor)
    FXTooltip(parent=anchor, description="probe", persistent=True).show_tooltip()
