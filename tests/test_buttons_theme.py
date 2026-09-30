"""Icons name their inks by theme token and take them when drawn."""

import pytest
from qtpy.QtCore import SIGNAL, QSize
from qtpy.QtGui import QIcon

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets import (
    FXCollapsibleWidget,
    FXDropZone,
    FXFilePathWidget,
    FXIconButton,
    FXNotificationBanner,
    FXPrimaryButton,
    FXProgressCard,
    FXRatingWidget,
    FXTagChip,
)


def _inks(icon: QIcon, mode=QIcon.Normal, state=QIcon.Off) -> set:
    image = icon.pixmap(QSize(32, 32), mode, state).toImage()
    return {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }


def _hex(*colours: str) -> set:
    return {colour.lower() for colour in colours}


def _receivers() -> int:
    return fxstyle.theme_manager.receivers(SIGNAL("theme_changed(QString)"))


def test_a_token_ink_is_read_when_the_icon_is_drawn(qapp):
    fxstyle.apply_theme("dark")
    icon = fxicons.get_icon("send", color="text_muted")
    assert _inks(icon) == _hex(fxstyle.colors().text_muted)
    fxstyle.apply_theme("dracula")
    assert _inks(icon) == _hex(fxstyle.colors().text_muted)


def test_each_mode_takes_the_ink_its_token_names(qapp):
    fxstyle.apply_theme("light")
    icon = fxicons.get_icon(
        "send", color="accent_primary",
        inks={"active": "text", "disabled": "border", "selected": "#123456"},
    )
    theme = fxstyle.colors()
    assert _inks(icon) == _hex(theme.accent_primary)
    assert _inks(icon, QIcon.Active) == _hex(theme.text)
    assert _inks(icon, QIcon.Disabled) == _hex(theme.border)
    assert _inks(icon, QIcon.Selected) == _hex("#123456")


def test_an_unknown_ink_key_is_refused(qapp):
    with pytest.raises(ValueError):
        fxicons.get_icon("check", inks={"hovered": "text"})


def test_the_primary_button_icon_follows_a_switch(qtbot, qapp):
    fxstyle.apply_theme("dark")
    button = FXPrimaryButton("Post", icon="send")
    qtbot.addWidget(button)
    assert _inks(button.icon()) == _hex("#ffffff")
    fxstyle.apply_theme("dracula")
    assert _inks(button.icon()) == _hex("#282a36")
    # Focus draws a push button's icon in Active mode, on the same fill.
    assert _inks(button.icon(), QIcon.Active) == _hex("#282a36")


def _drawn(button, mode=QIcon.Normal) -> set:
    """Return the inks Qt draws the button's icon in, for its state."""
    state = QIcon.On if button.isChecked() else QIcon.Off
    return _inks(button.icon(), mode, state)


def test_the_icon_button_icon_follows_a_switch(qtbot, qapp):
    fxstyle.apply_theme("dark")
    button = FXIconButton("visibility", checkable=True)
    qtbot.addWidget(button)
    assert _drawn(button) == _hex(fxstyle.colors().icon)
    assert _drawn(button, QIcon.Active) == _hex(fxstyle.colors().icon)
    button.setChecked(True)
    assert _drawn(button) == _hex("#ffffff")
    fxstyle.apply_theme("dracula")
    theme = fxstyle.colors()
    assert _drawn(button) == _hex(theme.icon_on_accent_primary)
    assert _drawn(button, QIcon.Active) == _hex(theme.icon_on_accent_secondary)
    button.setChecked(False)
    assert _drawn(button) == _hex(theme.icon)


def test_icon_only_widgets_hold_no_theme_connection(qtbot, qapp):
    before = _receivers()
    widgets = [
        FXPrimaryButton("Post", icon="send"),
        FXIconButton("visibility"),
        FXCollapsibleWidget(title="T", icon="settings"),
        FXDropZone(),
        FXFilePathWidget(validate=True),
        FXNotificationBanner(message="hi"),
        FXProgressCard(title="Task", icon="task"),
        FXRatingWidget(),
        FXTagChip("tag"),
    ]
    for widget in widgets:
        qtbot.addWidget(widget)
    assert _receivers() == before


def test_an_icon_label_draws_its_icon_in_the_ink_of_the_moment(qtbot, qapp):
    from fxgui.fxwidgets import FXIconLabel

    fxstyle.apply_theme("dark")
    label = FXIconLabel()
    qtbot.addWidget(label)
    fxicons.set_icon(label, "send", color="accent_primary")
    label.setIconSize(QSize(16, 16))
    assert label.sizeHint() == QSize(16, 16)
    fxstyle.apply_theme("dracula")
    image = label.grab().toImage()
    inks = {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }
    assert _hex(fxstyle.colors().accent_primary) <= inks
    label.setEnabled(False)
    image = label.grab().toImage()
    assert not _hex(fxstyle.colors().accent_primary) & {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
    }


def test_a_message_box_icon_takes_the_feedback_ink_of_the_moment(qapp):
    from qtpy.QtWidgets import QStyle

    style = fxstyle.FXProxyStyle()
    fxstyle.apply_theme("dark")
    icon = style.standardIcon(QStyle.SP_MessageBoxCritical)
    fxstyle.apply_theme("dracula")
    assert _inks(icon) == _hex(fxstyle.colors().feedback_error_foreground)
