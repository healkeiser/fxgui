"""A combo whose popup stays open while several rows are ticked."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtTest import QTest

# Internal
from fxgui.fxwidgets import FXCheckableComboBox


CHOICES = ["render", "cache", "plate"]


def _opened(qtbot):
    combo = FXCheckableComboBox()
    qtbot.addWidget(combo)
    combo.add_items(CHOICES)
    combo.show()
    qtbot.waitExposed(combo)
    combo.showPopup()
    qtbot.waitUntil(combo.view().isVisible)
    return combo


def _click_row(combo, row):
    view = combo.view()
    centre = view.visualRect(combo.model().index(row, 0)).center()
    QTest.mouseClick(view.viewport(), Qt.LeftButton, pos=centre)


def test_a_click_ticks_the_row_and_keeps_the_popup_open(qtbot):
    combo = _opened(qtbot)

    _click_row(combo, 0)
    _click_row(combo, 2)

    assert combo.checked_items() == ["render", "plate"]
    assert combo.view().isVisible()


def test_a_second_click_unticks(qtbot):
    combo = _opened(qtbot)

    _click_row(combo, 1)
    _click_row(combo, 1)

    assert combo.checked_items() == []


def test_space_ticks_the_current_row(qtbot):
    combo = _opened(qtbot)
    combo.view().setCurrentIndex(combo.model().index(1, 0))

    QTest.keyClick(combo.view(), Qt.Key_Space)

    assert combo.checked_items() == ["cache"]
    assert combo.view().isVisible()


def test_ticks_can_be_set_and_say_so(qtbot):
    combo = FXCheckableComboBox()
    qtbot.addWidget(combo)
    combo.add_items(CHOICES)
    seen = []
    combo.checked_changed.connect(seen.append)

    combo.set_checked_items(["plate", "render", "unknown"])

    assert combo.checked_items() == ["render", "plate"]
    assert seen[-1] == ["render", "plate"]


def test_setting_ticks_says_so_once_and_only_on_a_change(qtbot):
    combo = FXCheckableComboBox()
    qtbot.addWidget(combo)
    combo.add_items(CHOICES)
    seen = []
    combo.checked_changed.connect(seen.append)

    combo.set_checked_items(["render", "plate"])
    combo.set_checked_items(["plate", "render"])

    assert seen == [["render", "plate"]]


def test_setting_ticks_repaints_an_open_popup(qtbot):
    combo = _opened(qtbot)
    changed = []
    combo.model().dataChanged.connect(lambda *_: changed.append(True))

    combo.set_checked_items(["cache"])

    assert changed


def test_the_closed_combo_reads_its_ticks(qtbot):
    combo = FXCheckableComboBox()
    qtbot.addWidget(combo)
    combo.add_items(CHOICES)

    combo.set_checked_items(["cache", "plate"])

    assert combo.display_text() == "cache, plate"
