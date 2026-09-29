"""FXPrimaryButton: the main action of a form, on the accent, in every theme."""

import pytest
from qtpy.QtCore import QPoint, QRect
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from fxgui import fxstyle
from fxgui.fxwidgets import FXPrimaryButton


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


def _near(a: str, b: str, step: int = 6) -> bool:
    one, two = QColor(a), QColor(b)
    return max(abs(one.red() - two.red()), abs(one.green() - two.green()),
               abs(one.blue() - two.blue())) <= step


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
    assert _near(_grab(window, button), tokens["@primary_button"])

    # Off first: the last test left the pointer where this button now is.
    qtbot.mouseMove(window, QPoint(1, 1))
    qtbot.mouseMove(button, QPoint(button.width() // 2, button.height() // 2))
    qtbot.waitUntil(button.underMouse)
    qapp.processEvents()
    assert _near(_grab(window, button), tokens["@primary_button_hover"])


def test_a_disabled_button_leaves_the_accent(qtbot, qapp):
    window, button = _window_with_button(qtbot, "dark")
    button.setEnabled(False)
    qapp.processEvents()
    tokens = fxstyle._token_map("dark")
    assert _near(_grab(window, button), tokens["@surface_alt"])


def test_a_plain_push_button_is_untouched(qtbot, qapp):
    fxstyle.apply_theme("dark")
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    plain = QPushButton("Cancel", window)
    QVBoxLayout(window).addWidget(plain)
    window.show()
    qtbot.waitExposed(window)
    assert _near(_grab(window, plain), fxstyle._token_map("dark")["@surface"])


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
    before = set(map(id, QApplication.topLevelWidgets()))
    FXPrimaryButton("Send", parent, icon="send").show()
    assert set(map(id, QApplication.topLevelWidgets())) == before
