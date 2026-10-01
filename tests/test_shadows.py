"""One shadow rule: a floating card paints the card shadow, a popup none."""

# Third-party
import pytest
from qtpy.QtWidgets import QGraphicsDropShadowEffect, QMenu, QWidget

# Internal
from fxgui.fxwidgets import (
    FXCommandPalette,
    FXNotificationBanner,
    FXProgressCard,
    FXTooltip,
)
from fxgui.fxwidgets._dialogs import FXFloatingDialog

_HOLD = []


def _parent(qtbot):
    parent = QWidget()
    _HOLD.append(parent)
    qtbot.addWidget(parent)
    return parent


_CARDS = {
    "FXNotificationBanner": lambda p: (
        lambda w: (w, w))(FXNotificationBanner(p, message="hi")),
    "FXProgressCard": lambda p: (
        lambda w: (w, w))(FXProgressCard(p, title="Task")),
    "FXTooltip": lambda p: (
        lambda w: (w, w._content_widget))(FXTooltip(p, title="Tip")),
    "FXFloatingDialog": lambda p: (
        lambda w: (w, w._container))(FXFloatingDialog(p)),
}


@pytest.mark.parametrize("name", sorted(_CARDS))
def test_a_floating_card_wears_the_card_shadow(qtbot, name):
    _owner, target = _CARDS[name](_parent(qtbot))
    effect = target.graphicsEffect()
    assert isinstance(effect, QGraphicsDropShadowEffect)
    assert effect.blurRadius() == 20
    assert (effect.xOffset(), effect.yOffset()) == (0, 0)
    assert effect.color().alpha() == 80
    assert effect.color().rgb() & 0xFFFFFF == 0


def test_a_popup_paints_none_the_platform_draws_it(qtbot):
    parent = _parent(qtbot)
    for popup in (FXCommandPalette(parent, lambda: []), QMenu(parent)):
        assert popup.graphicsEffect() is None
