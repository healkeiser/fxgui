"""Button icons are redrawn on a theme switch without the mixin."""

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXIconButton, FXPrimaryButton


def test_button_icons_follow_a_theme_switch(qtbot, qapp):
    primary = FXPrimaryButton("Post", icon="send")
    icon_button = FXIconButton("visibility")
    for button in (primary, icon_button):
        qtbot.addWidget(button)
    keys = [primary.icon().cacheKey(), icon_button.icon().cacheKey()]
    fxstyle.apply_theme("light")
    assert primary.icon().cacheKey() != keys[0]
    assert icon_button.icon().cacheKey() != keys[1]
    assert not isinstance(primary, fxstyle.FXThemeAware)
    assert not isinstance(icon_button, fxstyle.FXThemeAware)
