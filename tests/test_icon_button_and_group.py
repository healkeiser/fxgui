"""FXIconButton is round; FXJoinedGroup draws its children in one outline."""

import pytest
from qtpy.QtCore import QPoint, QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from fxgui import fxstyle
from fxgui.fxwidgets import FXIconButton, FXJoinedGroup, FXPrimaryButton


def _near(a, b, step: int = 8) -> bool:
    one, two = QColor(a), QColor(b)
    return max(abs(one.red() - two.red()), abs(one.green() - two.green()),
               abs(one.blue() - two.blue())) <= step


def _inks(icon, size: int) -> set:
    image = icon.pixmap(size, size).toImage()
    return {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }


@pytest.fixture
def window(qtbot):
    # A fixture, since pytest-qt holds its widgets only weakly.
    fxstyle.apply_theme("dark")
    widget = QWidget()
    qtbot.addWidget(widget)
    fxstyle.register_themed_root(widget)
    QHBoxLayout(widget).setContentsMargins(10, 10, 10, 10)
    return widget


def _show(qtbot, window, child):
    window.layout().addWidget(child)
    window.show()
    qtbot.waitExposed(window)
    return child


def _pixel(window, widget, x, y) -> str:
    image = window.grab().toImage()
    at = widget.mapTo(window, QPoint(x, y))
    return image.pixelColor(at.x(), at.y()).name()


def _hover(qtbot, window, widget):
    # Off first: the last test may have left the pointer where this is.
    qtbot.mouseMove(window, QPoint(1, 1))
    qtbot.mouseMove(widget, QPoint(widget.width() // 2, widget.height() // 2))
    qtbot.waitUntil(widget.underMouse)
    QApplication.processEvents()


def test_the_icon_button_is_round_and_fills_on_hover(qtbot, window):
    button = _show(
        qtbot, window, FXIconButton("mood", window, tip="Emoji", size=28))
    tokens = fxstyle._token_map("dark")
    assert button.size().width() == button.size().height() == 28
    assert button.iconSize().width() == 16
    _hover(qtbot, window, button)
    assert _near(_pixel(window, button, 14, 3), tokens["@state_hover"])
    assert _near(_pixel(window, button, 1, 1), tokens["@surface"])
    assert _near(_pixel(window, button, 26, 26), tokens["@surface"])


def test_the_icon_button_rests_without_a_fill(qtbot, window):
    button = _show(qtbot, window, FXIconButton("mood", window))
    tokens = fxstyle._token_map("dark")
    assert _near(_pixel(window, button, 14, 3), tokens["@surface"])


def test_the_tip_is_the_house_rich_tooltip(qtbot, window):
    button = FXIconButton("mood", window, tip="Insert an emoji")
    assert "Insert an emoji" in button.toolTip()
    assert button.statusTip() == "Insert an emoji"


def test_checkable_toggles_on_click_and_swaps_icon_and_fill(qtbot, window):
    button = _show(qtbot, window, FXIconButton(
        "visibility_off", window, checkable=True, checked_icon="visibility"))
    tokens = fxstyle._token_map("dark")
    off = button.icon().pixmap(16, 16).toImage()
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert button.isChecked()
    assert button.icon().pixmap(16, 16).toImage() != off
    qtbot.mouseMove(window, QPoint(1, 1))
    qtbot.waitUntil(lambda: not button.underMouse())
    QApplication.processEvents()
    assert _near(_pixel(window, button, 14, 3), tokens["@primary_button"])
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert not button.isChecked()


def test_the_checked_icon_is_drawn_in_the_on_accent_colour(qtbot, window):
    button = FXIconButton("visibility_off", window, checkable=True,
                          checked_icon="visibility")
    button.setChecked(True)
    on = button.icon().pixmap(16, 16).toImage()
    inks = {
        on.pixelColor(x, y).name()
        for x in range(on.width()) for y in range(on.height())
        if on.pixelColor(x, y).alpha() == 255
    }
    assert inks == {fxstyle._token_map("dark")["@icon_on_accent_primary"]}


def _group(qtbot, window, trailing):
    group = FXJoinedGroup(window)
    combo = QComboBox(group)
    combo.addItems(["WIP", "Retake", "Done"])
    group.add_widget(combo)
    button = trailing(group)
    group.add_widget(button)
    # The rest of the form, which holds focus while the group has none.
    elsewhere = QLineEdit(window)
    window.layout().addWidget(elsewhere)
    _show(qtbot, window, group)
    window.layout().addStretch()
    window.activateWindow()
    elsewhere.setFocus()
    qtbot.waitUntil(elsewhere.hasFocus)
    QApplication.processEvents()
    return group, combo, button


def test_the_group_draws_one_outline_and_a_divider(qtbot, window):
    group, combo, button = _group(
        qtbot, window, lambda p: QPushButton("Post", p))
    tokens = fxstyle._token_map("dark")
    middle = combo.width() // 2
    assert _near(_pixel(window, group, combo.x() + middle, 0),
                 tokens["@border_light"])
    # Borderless children: nothing but the one outline at the top.
    assert not _near(_pixel(window, group, combo.x() + middle, 1),
                     tokens["@border_light"], 4)
    assert not _near(_pixel(window, group, combo.x() + middle, 2),
                     tokens["@border_light"], 4)
    divider = _pixel(window, group, button.x(), group.height() // 2)
    assert _near(divider, tokens["@border"], 4), divider
    assert _near(_pixel(window, group, 0, 0), tokens["@surface"])


def test_a_primary_keeps_its_fill_clipped_to_the_outline(qtbot, window):
    group, combo, button = _group(
        qtbot, window, lambda p: FXPrimaryButton("Post", p))
    tokens = fxstyle._token_map("dark")
    mid = group.height() // 2
    fill = tokens["@primary_button"]
    assert _near(_pixel(window, group, button.x() + 4, mid), fill)
    assert _near(_pixel(window, group, group.width() - 6, mid), fill)
    assert not _near(_pixel(window, group, combo.x() + 6, mid), fill, 40)
    # The outer corner lies outside the outline, so shows the window behind.
    assert _near(_pixel(window, group, group.width() - 1, 0),
                 tokens["@surface"])
    # The inner side is square: the fill reaches the top next to the divider.
    assert _near(_pixel(window, group, button.x() + 2, 2), fill)


def test_the_outline_has_the_push_button_corner(qtbot, window):
    group, combo, button = _group(
        qtbot, window, lambda p: FXPrimaryButton("Post", p))
    plain = QPushButton("Cancel", window)
    plain.setFixedHeight(group.height())
    window.layout().insertWidget(0, plain)
    QApplication.processEvents()
    tokens = fxstyle._token_map("dark")
    # 2 px in from the corner is inside a 4 px radius; a pill leaves it out.
    assert _near(_pixel(window, group, group.width() - 3, 2),
                 tokens["@primary_button"])
    image = window.grab().toImage()
    for x in range(5):
        for y in range(5):
            at, ref = (w.mapTo(window, QPoint(x, y)) for w in (group, plain))
            assert _near(image.pixelColor(at), image.pixelColor(ref), 4), (x, y)


def test_keyboard_focus_on_a_child_lights_the_outline(qtbot, window):
    group, combo, _button = _group(
        qtbot, window, lambda p: FXPrimaryButton("Post", p))
    tokens = fxstyle._token_map("dark")
    top = (combo.x() + combo.width() // 2, 0)
    assert not _near(_pixel(window, group, *top), tokens["@accent_primary"])
    qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab)
    qtbot.waitUntil(combo.hasFocus)
    QApplication.processEvents()
    assert _near(_pixel(window, group, *top), tokens["@accent_primary"])
    size = group.size()
    qtbot.keyClick(combo, Qt.Key.Key_Tab)
    qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab)
    qtbot.waitUntil(lambda: not group.isAncestorOf(QApplication.focusWidget()))
    QApplication.processEvents()
    assert not _near(_pixel(window, group, *top), tokens["@accent_primary"])
    assert group.size() == size


def test_building_them_with_a_parent_opens_no_window(qtbot, window):
    before = {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()}
    _group(qtbot, window, lambda p: FXPrimaryButton("Post", p))
    window.layout().addWidget(FXIconButton("mood", window))
    QApplication.processEvents()
    after = {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()}
    assert after - before == {id(window)}


def _places(group_children) -> list:
    return [child.property("fxJoined") for child in group_children]


def test_a_deleted_child_leaves_the_group(qtbot, window):
    from qtpy import shiboken

    group = FXJoinedGroup(window)
    a, b, c = (QPushButton(t, group) for t in "abc")
    for child in (a, b, c):
        group.add_widget(child)
    shiboken.delete(c)
    QApplication.processEvents()
    assert _places([a, b]) == ["first", "last"]
    d = QPushButton("d", group)
    group.add_widget(d)
    assert _places([a, b, d]) == ["first", "middle", "last"]


def test_adding_right_after_a_delete_raises_nothing(qtbot, window):
    from qtpy import shiboken

    group = FXJoinedGroup(window)
    a, b = QPushButton("a", group), QPushButton("b", group)
    group.add_widget(a)
    group.add_widget(b)
    shiboken.delete(b)
    c = QPushButton("c", group)
    group.add_widget(c)
    assert _places([a, c]) == ["first", "last"]


def test_a_hidden_last_child_hands_the_round_end_on(qtbot, window):
    group = FXJoinedGroup(window)
    a, b = QPushButton("a", group), QPushButton("b", group)
    group.add_widget(a)
    group.add_widget(b)
    _show(qtbot, window, group)
    b.hide()
    assert a.property("fxJoined") == "only"
    b.show()
    assert _places([a, b]) == ["first", "last"]


def test_a_hidden_first_child_takes_the_divider_with_it(qtbot, window):
    group = FXJoinedGroup(window)
    a, b, c = (QPushButton(t, group) for t in "abc")
    for child in (a, b, c):
        group.add_widget(child)
    a.hide()
    assert _places([b, c]) == ["first", "last"]
    _show(qtbot, window, group)
    tokens = fxstyle._token_map("dark")
    edge = _pixel(window, group, b.x(), group.height() // 2)
    assert not _near(edge, tokens["@border"], 4), edge


def test_the_icon_button_renders_at_its_own_pixel_ratio(qtbot, window,
                                                        monkeypatch):
    """A second screen can be denser than the primary one."""
    button = FXIconButton("visibility_off", window, checkable=True,
                          checked_icon="visibility")
    for checked in (False, True):
        button.setChecked(checked)
        pixmap = button.icon().pixmap(QSize(16, 16), 2.0)
        assert pixmap.size() == QSize(32, 32), checked


def test_a_hovered_checked_icon_takes_the_hover_ink(
    qtbot, window, monkeypatch
):
    """Hovered, a checked button sits on the hover fill, which is tuned for
    the secondary on-accent ink; Qt draws a hovered tool button's icon in
    Active mode. A theme whose two inks differ tells the pixmaps apart."""
    colors = fxstyle.get_colors()
    split = dict(colors["themes"]["dark"])
    split.update({
        "icon_on_accent_primary": "#ffffff",
        "icon_on_accent_secondary": "#000000",
    })
    patched = dict(colors, themes={**colors["themes"], "split": split})
    monkeypatch.setattr(fxstyle, "get_colors", lambda: patched)
    fxstyle.apply_theme("split")
    button = FXIconButton("visibility_off", window, checkable=True,
                          checked_icon="visibility")
    for checked, token in ((True, "@icon_on_accent_secondary"),
                           (False, "@icon")):
        button.setChecked(checked)
        icon = button.icon()
        image = icon.pixmap(16, 16, icon.Mode.Active).toImage()
        inks = {
            image.pixelColor(x, y).name()
            for x in range(image.width()) for y in range(image.height())
            if image.pixelColor(x, y).alpha() == 255
        }
        assert inks == {fxstyle._token_map("split")[token].lower()}, checked


def test_the_icon_button_is_a_push_button_s_height_by_default(qtbot, window):
    button = _show(qtbot, window, FXIconButton("mood", window))
    assert button.width() == button.height() == fxstyle.control_height(button)


def test_the_icon_button_round_comes_from_the_theme_not_its_own_sheet(
    qtbot, window
):
    button = _show(qtbot, window, FXIconButton("mood", window, size=40))
    tokens = fxstyle._token_map("dark")
    _hover(qtbot, window, button)
    assert button.styleSheet() == ""
    assert _near(_pixel(window, button, 20, 3), tokens["@state_hover"])
    assert _near(_pixel(window, button, 2, 2), tokens["@surface"])


def test_a_deleted_child_leaves_the_group_at_once(qtbot, window):
    from qtpy import shiboken

    group = FXJoinedGroup(window)
    a, b, c = (QPushButton(t, group) for t in "abc")
    for child in (a, b, c):
        group.add_widget(child)
    shiboken.delete(c)
    assert _places([a, b]) == ["first", "last"]
    assert not hasattr(group, "_widgets")
