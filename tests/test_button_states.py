"""Every button state shows, on any ground: one convention for all."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle

from _helpers import hover, pixel, unhover

THEMES = fxstyle.get_available_themes()
STATES = ("state_hover", "state_pressed", "state_checked_hover")

# A raised card, as a media player's controls sit on: a ground an opaque
# fill can match.
fxstyle.register_widget_style(
    "QFrame#fxTestTooltipCard { background-color: @tooltip; border: none; }")


def _name(color):
    return QColor(color).name()


def _button(kind):
    if kind == "tool":
        button = QToolButton()
    else:
        button = QPushButton("Apply" if kind == "push" else "")
        if kind == "setFlat":
            button.setFlat(True)
        elif kind == "fxRole":
            button.setProperty("fxRole", "flat")
    button.setCheckable(True)
    if kind != "push":
        fxicons.set_icon(button, "arrow-left")
    return button


def _shown(qtbot, theme, button, card):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    holder = QFrame(window)
    if card:
        holder.setObjectName("fxTestTooltipCard")
    QVBoxLayout(window).addWidget(holder)
    QVBoxLayout(holder).addWidget(button)
    qtbot.addWidget(window)
    window.resize(200, 120)
    window.show()
    qtbot.waitExposed(window)
    window.setFocus()
    QApplication.processEvents()
    return window


def _fill(window, button):
    # A tool button has a 2 px margin: read inside it, clear of the icon.
    point = (QPoint(3, button.height() // 2)
             if isinstance(button, QToolButton)
             else QPoint(fxstyle.BUTTON_RADIUS, 2))
    return pixel(window, button, point)


def _states(qtbot, qapp, window, button):
    """Return the fill at rest, hovered, pressed, checked, checked+hovered."""
    rest = _fill(window, button)
    hover(qtbot, button)
    hovered = _fill(window, button)
    button.setDown(True)
    qapp.processEvents()
    pressed = _fill(window, button)
    button.setDown(False)
    button.setChecked(True)
    qapp.processEvents()
    checked_hovered = _fill(window, button)
    unhover(qtbot, button)
    checked = _fill(window, button)
    return rest, hovered, pressed, checked, checked_hovered


@pytest.mark.parametrize("kind", ["setFlat", "fxRole", "tool"])
@pytest.mark.parametrize("theme", THEMES)
def test_every_state_of_a_flat_button_shows_on_a_tooltip_card(
        qtbot, qapp, theme, kind):
    button = _button(kind)
    window = _shown(qtbot, theme, button, card=True)
    rest, hovered, pressed, checked, checked_hovered = _states(
        qtbot, qapp, window, button)
    ground = _name(fxstyle.colors().tooltip)

    assert rest == ground
    for fill in (hovered, pressed, checked, checked_hovered):
        assert fxstyle._visibly_differ(fill, ground), fill
    assert fxstyle._visibly_differ(pressed, hovered)
    assert fxstyle._visibly_differ(checked_hovered, checked)
    assert checked == pressed


@pytest.mark.parametrize("theme", THEMES)
def test_a_push_button_wears_one_fill_per_state(qtbot, qapp, theme):
    button = _button("push")
    window = _shown(qtbot, theme, button, card=False)
    _, hovered, pressed, checked, checked_hovered = _states(
        qtbot, qapp, window, button)
    colors = fxstyle.colors()

    assert hovered == _name(colors.state_hover)
    assert pressed == _name(colors.state_pressed)
    assert checked == _name(colors.state_pressed)
    assert checked_hovered == _name(colors.state_checked_hover)


@pytest.mark.parametrize("theme", THEMES)
def test_each_overlay_is_the_text_see_through_as_far_as_its_fill(theme):
    colors = fxstyle._colour_tokens(theme)
    surface = colors["surface"]

    for state in STATES:
        overlay = QColor(colors[f"{state}_overlay"])
        assert overlay.isValid()
        assert overlay.name() == _name(colors["text"])
        assert 0 < overlay.alpha() <= 128
        if overlay.alpha() < 128:
            blend = fxstyle.mix(surface, colors["text"], overlay.alphaF())
            assert fxstyle.get_contrast_ratio(blend, surface) >= (
                fxstyle.get_contrast_ratio(colors[state], surface))


@pytest.mark.parametrize("theme", THEMES)
def test_a_checked_hover_fill_stands_past_the_pressed_fill(theme):
    colors = fxstyle._colour_tokens(theme)
    checked_hover = colors["state_checked_hover"]

    assert fxstyle.get_contrast_ratio(
        checked_hover, colors["state_pressed"]) >= fxstyle.state_contrast(
            theme)
    assert fxstyle.get_contrast_ratio(colors["text"], checked_hover) >= 4.5


# A brand theme as a studio writes one: its own faint opaque fills, held
# at no floor of fxgui's, and a raised card one step off the window.
_BRAND = """
themes:
  brand_dark:
    surface: "#101113"
    surface_alt: "#0B0C0D"
    surface_sunken: "#0B0C0D"
    tooltip: "#191A1D"
    frame: "#0B0C0D"
    well: "#101113"
    text: "#D6D9DD"
    text_muted: "#A2A7B0"
    state_hover: "#151618"
    state_pressed: "#191A1D"
    state_contrast: 1.0
  brand_light:
    surface: "#FFFFFF"
    surface_alt: "#F7F7F8"
    surface_sunken: "#F7F7F8"
    tooltip: "#F3F3F5"
    frame: "#F7F7F8"
    well: "#FFFFFF"
    text: "#2C2D33"
    text_muted: "#54555B"
    state_hover: "#F9F9FA"
    state_pressed: "#F3F3F5"
    state_contrast: 1.0
"""


@pytest.mark.parametrize("theme", ["brand_dark", "brand_light"])
def test_a_flat_button_shows_on_a_brand_s_card_at_fxgui_s_floor(
    qapp, tmp_path, theme
):
    path = tmp_path / "brand.yaml"
    path.write_text(_BRAND, encoding="utf-8")
    fxstyle.overlay_color_file(str(path))
    fxstyle.apply_theme(theme, save=False)
    colors = fxstyle.colors()

    # The brand's opaque fills stay exactly as stated: they are its rows'.
    stated = fxstyle.get_colors()["themes"][theme]
    assert _name(colors.state_hover) == _name(stated["state_hover"])
    assert _name(colors.state_pressed) == _name(stated["state_pressed"])
    for ground in (colors.surface, colors.tooltip):
        reached = []
        for state in STATES:
            fill = QColor(getattr(colors, f"{state}_overlay"))
            painted = fxstyle.mix(ground, fill.name(), fill.alphaF())
            reached.append(fxstyle.get_contrast_ratio(painted, ground))
        # A 24 px icon cannot carry a faint fill: hover holds 1.2:1, and
        # pressed and checked+hover each stand further off.
        assert reached[0] >= fxstyle.STATE_MIN_CONTRAST, (ground, reached)
        assert reached[0] < reached[1] < reached[2], (ground, reached)
