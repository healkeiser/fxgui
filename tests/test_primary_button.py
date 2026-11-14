"""FXPrimaryButton: the main action of a form, on the accent, in every theme."""

import pytest
from qtpy.QtCore import QPoint, QRect, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fxgui import fxicons, fxstyle
from fxgui.fxwidgets import FXIconButton, FXPrimaryButton

from _helpers import hover, near, unhover


def _ratio(one: str, two: str) -> float:
    low, high = sorted(
        [fxstyle.get_luminance(one), fxstyle.get_luminance(two)])
    return (high + 0.05) / (low + 0.05)


def _most(image) -> str:
    counts: dict[str, int] = {}
    for x in range(image.width()):
        for y in range(image.height()):
            name = image.pixelColor(x, y).name().lower()
            counts[name] = counts.get(name, 0) + 1
    return max(counts, key=counts.get)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_text_reads_on_the_fill_at_rest_and_hovered(qapp, theme):
    tokens = fxstyle._token_map(theme)
    rest = _ratio(tokens["@text_on_accent_primary"], tokens["@primary_button"])
    hover = _ratio(
        tokens["@text_on_accent_secondary"], tokens["@primary_button_hover"])
    pressed = _ratio(
        tokens["@text_on_accent_primary"], tokens["@primary_button_pressed"])
    assert rest >= 4.5, f"{theme}: {rest:.2f}"
    assert hover >= 4.5, f"{theme}: {hover:.2f}"
    assert pressed >= 4.5, f"{theme}: {pressed:.2f}"


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_icon_reads_on_the_fill_at_rest_and_hovered(qapp, theme):
    """An icon is a non-text component: WCAG asks 3:1."""
    tokens = fxstyle._token_map(theme)
    for fill in ("@primary_button", "@primary_button_hover"):
        ratio = _ratio(tokens["@icon_on_accent_primary"], tokens[fill])
        assert ratio >= 3.0, f"{theme} {fill}: {ratio:.2f}"


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_fill_keeps_the_accent_hue(qapp, theme):
    tokens = fxstyle._token_map(theme)
    accent = QColor(tokens["@accent_primary"])
    fill = QColor(tokens["@primary_button"])
    if accent.hslSaturation() > 40:
        assert abs(accent.hslHue() - fill.hslHue()) <= 8, theme


def _window_with_button(qtbot, theme, **kwargs):
    fxstyle.apply_theme(theme)
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    button = FXPrimaryButton("Post", window, **kwargs)
    QVBoxLayout(window).addWidget(button)
    window.show()
    qtbot.waitExposed(window)
    return window, button


def _grab(window, button) -> str:
    area = QRect(button.mapTo(window, QPoint(0, 0)), button.size())
    return _most(window.grab(area).toImage())


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_button_paints_the_fill_and_the_hover(qtbot, qapp, theme):
    window, button = _window_with_button(qtbot, theme)
    tokens = fxstyle._token_map(theme)
    assert near(_grab(window, button), tokens["@primary_button"], 6)

    hover(qtbot, button)
    assert near(_grab(window, button), tokens["@primary_button_hover"], 6)


def test_a_disabled_button_leaves_the_accent(qtbot, qapp):
    window, button = _window_with_button(qtbot, "dark")
    button.setEnabled(False)
    qapp.processEvents()
    tokens = fxstyle._token_map("dark")
    assert near(_grab(window, button), tokens["@surface_alt"], 6)


def test_a_plain_push_button_is_untouched(qtbot, qapp):
    fxstyle.apply_theme("dark")
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    plain = QPushButton("Cancel", window)
    QVBoxLayout(window).addWidget(plain)
    window.show()
    qtbot.waitExposed(window)
    surface = fxstyle._token_map("dark")["@surface"]
    assert near(_grab(window, plain), surface, 6)


def test_the_icon_is_drawn_in_the_on_accent_colour(qtbot, qapp):
    window, button = _window_with_button(qtbot, "light", icon="send")
    assert not button.icon().isNull()
    image = button.icon().pixmap(16, 16).toImage()
    inks = {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }
    assert inks == {fxstyle._token_map("light")["@icon_on_accent_primary"]}


def test_the_icon_follows_a_theme_switch(qtbot, qapp):
    window, button = _window_with_button(qtbot, "light", icon="send")
    fxstyle.apply_theme("dracula")
    qapp.processEvents()
    image = button.icon().pixmap(16, 16).toImage()
    inks = {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }
    assert inks == {fxstyle._token_map("dracula")["@icon_on_accent_primary"]}


def test_it_takes_the_push_button_shapes(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    assert FXPrimaryButton(parent).parent() is parent
    button = FXPrimaryButton("Post", parent)
    assert button.text() == "Post" and button.parent() is parent
    assert button.property("fxRole") == "primary"
    shown = FXPrimaryButton("Send", parent, icon="send")
    shown.show()
    assert not shown.isWindow()
    assert shown not in QApplication.topLevelWidgets()


def test_every_public_getter_is_exported():
    import inspect

    getters = {
        name for name, value in vars(fxstyle).items()
        if name.startswith("get_") and inspect.isfunction(value)
        and value.__module__ == fxstyle.__name__
    }
    assert getters - set(fxstyle.__all__) == set()


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_rest_hover_and_pressed_fills_differ_visibly(qapp, theme):
    tokens = fxstyle._token_map(theme)
    rest = tokens["@primary_button"]
    hover = tokens["@primary_button_hover"]
    pressed = tokens["@primary_button_pressed"]
    for one, two in ((rest, hover), (pressed, hover), (pressed, rest)):
        # Hue counts too: dracula's purple and pink share a luminance.
        assert _ratio(one, two) >= 1.1 or not near(one, two, 47), (
            f"{theme}: {one} vs {two}")


def _split_theme(monkeypatch):
    """A theme whose two accents carry opposite on-accent inks."""
    colors = fxstyle.get_colors()
    split = dict(colors["themes"]["dark"])
    split.update({
        "accent_primary": "#2f6fdb",
        "accent_secondary": "#9ad0ff",
        "text_on_accent_primary": "#ffffff",
        "text_on_accent_secondary": "#000000",
        "icon_on_accent_primary": "#ffffff",
        "icon_on_accent_secondary": "#000000",
    })
    patched = dict(colors, themes={**colors["themes"], "split": split})
    monkeypatch.setattr(fxstyle, "get_colors", lambda: patched)
    return fxstyle._token_map("split")


def test_each_fill_is_tuned_for_the_text_drawn_on_it(qapp, monkeypatch):
    tokens = _split_theme(monkeypatch)
    white, black = "#ffffff", "#000000"
    assert _ratio(tokens["@primary_button"], white) >= 4.5
    assert _ratio(tokens["@primary_button_hover"], black) >= 4.5
    assert _ratio(tokens["@primary_button_pressed"], white) >= 4.5


def test_a_hovered_press_draws_the_text_its_fill_was_tuned_for(
    qtbot, qapp, monkeypatch
):
    tokens = _split_theme(monkeypatch)
    window, button = _window_with_button(qtbot, "split")
    hover(qtbot, button)
    button.setDown(True)
    qapp.processEvents()
    area = QRect(button.mapTo(window, QPoint(0, 0)), button.size())
    image = window.grab(area).toImage()
    assert near(_most(image), tokens["@primary_button_pressed"], 6)
    inks = [
        image.pixelColor(x, y)
        for x in range(4, image.width() - 4)
        for y in range(4, image.height() - 4)
    ]
    assert any(c.lightness() > 230 for c in inks)
    assert not any(c.lightness() < 25 for c in inks)


def _icon_inks(button) -> set:
    image = button.icon().pixmap(16, 16).toImage()
    return {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }


def test_the_icon_takes_the_ink_of_each_state_fill(qtbot, qapp, monkeypatch):
    colors = fxstyle.get_colors()
    split = dict(colors["themes"]["dark"])
    split.update({
        "icon_on_accent_primary": "#ffffff",
        "icon_on_accent_secondary": "#000000",
    })
    patched = dict(colors, themes={**colors["themes"], "split": split})
    monkeypatch.setattr(fxstyle, "get_colors", lambda: patched)
    window, button = _window_with_button(qtbot, "split", icon="send")
    centre = QPoint(button.width() // 2, button.height() // 2)

    unhover(qtbot, button)
    assert _icon_inks(button) == {"#ffffff"}
    hover(qtbot, button, centre)
    qtbot.waitUntil(lambda: _icon_inks(button) == {"#000000"})
    qtbot.mousePress(button, Qt.MouseButton.LeftButton, pos=centre)
    assert _icon_inks(button) == {"#ffffff"}
    qtbot.mouseRelease(button, Qt.MouseButton.LeftButton, pos=centre)
    assert _icon_inks(button) == {"#000000"}
    unhover(qtbot, button)
    qtbot.waitUntil(lambda: _icon_inks(button) == {"#ffffff"})


def _image(icon):
    return icon.pixmap(16, 16).toImage()


def _themed_window(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    QVBoxLayout(window)
    return window


def _show(qtbot, window):
    window.show()
    qtbot.waitExposed(window)


def test_an_icon_set_after_construction_takes_the_on_accent_ink(qtbot, qapp):
    tokens = fxstyle._token_map("dark")
    window, button = _window_with_button(qtbot, "dark")
    fxicons.set_icon(button, "send")
    assert _icon_inks(button) == {tokens["@icon_on_accent_primary"]}
    hover(qtbot, button)
    assert _icon_inks(button) == {tokens["@icon_on_accent_primary"]}
    unhover(qtbot, button)
    assert _icon_inks(button) == {tokens["@icon_on_accent_primary"]}


def test_set_icon_replaces_the_construction_icon_for_good(qtbot, qapp):
    window, button = _window_with_button(qtbot, "dark", icon="send")
    fxicons.set_icon(button, "save")
    hover(qtbot, button)
    assert _image(button.icon()) == _image(
        fxicons.get_icon("save", color="icon_on_accent_secondary"))
    unhover(qtbot, button)
    assert _image(button.icon()) == _image(
        fxicons.get_icon("save", color="icon_on_accent_primary"))


def test_a_raw_qicon_survives_hover(qtbot, qapp):
    window, button = _window_with_button(qtbot, "dark", icon="send")
    icon = fxicons.get_icon("save", color="#ff0000")
    button.setIcon(icon)
    hover(qtbot, button)
    unhover(qtbot, button)
    assert button.icon().cacheKey() == icon.cacheKey()


def test_a_plain_push_button_with_the_primary_role_takes_the_on_accent_ink(
    qtbot, qapp
):
    tokens = fxstyle._token_map("dark")
    window = _themed_window(qtbot, "dark")
    button = QPushButton("Post", window)
    button.setProperty("fxRole", "primary")
    window.layout().addWidget(button)
    _show(qtbot, window)
    fxicons.set_icon(button, "send")
    assert _icon_inks(button) == {tokens["@icon_on_accent_primary"]}
    fxicons.set_icon(button, "send", color="#ff0000")
    assert _icon_inks(button) == {"#ff0000"}


def test_a_dialog_ranked_button_takes_the_on_accent_ink(qtbot, qapp):
    tokens = fxstyle._token_map("dark")
    window = _themed_window(qtbot, "dark")
    box = QDialogButtonBox(
        QDialogButtonBox.Ok | QDialogButtonBox.Cancel, window)
    window.layout().addWidget(box)
    _show(qtbot, window)
    ok = box.button(QDialogButtonBox.Ok)
    cancel = box.button(QDialogButtonBox.Cancel)
    assert ok.property("fxRole") == "primary"
    fxicons.set_icon(ok, "check")
    assert _icon_inks(ok) == {tokens["@icon_on_accent_primary"]}
    fxicons.set_icon(cancel, "x")
    assert _icon_inks(cancel) == {tokens["@icon"]}


def test_set_icon_on_a_checkable_icon_button_survives_a_toggle(qtbot, qapp):
    window = _themed_window(qtbot, "dark")
    button = FXIconButton("eye-off", window, checkable=True)
    window.layout().addWidget(button)
    _show(qtbot, window)
    fxicons.set_icon(button, "eye")
    button.setChecked(True)
    assert _image(button.icon()) == _image(
        fxicons.get_icon("eye", color="icon_on_accent_primary"))
    button.setChecked(False)
    assert _image(button.icon()) == _image(fxicons.get_icon("eye"))
