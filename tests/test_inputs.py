"""Input widgets style through the theme and leave the caller's state alone."""

# Third-party
from qtpy.QtCore import QAbstractAnimation
from qtpy.QtTest import QTest

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import (
    FXIconLineEdit,
    FXLowerCaseValidator,
    FXPasswordLineEdit,
    FXValidatedLineEdit,
)


def _validated(qtbot):
    edit = FXValidatedLineEdit(shake_duration=50, flash_duration=50)
    edit.setValidator(FXLowerCaseValidator())
    qtbot.addWidget(edit)
    edit.show()
    qtbot.waitExposed(edit)
    return edit


def _reject(qtbot, edit):
    QTest.keyClicks(edit, "1")
    qtbot.waitUntil(lambda: not edit._is_animating, timeout=1000)


def test_rejections_reuse_one_set_of_animations(qtbot, qapp):
    edit = _validated(qtbot)
    _reject(qtbot, edit)
    first = len(edit.findChildren(QAbstractAnimation))
    for _ in range(3):
        _reject(qtbot, edit)
    assert len(edit.findChildren(QAbstractAnimation)) == first


def test_rejection_keeps_the_callers_margins_and_sheet(qtbot, qapp):
    edit = _validated(qtbot)
    edit.setTextMargins(10, 0, 3, 0)
    sheet = "FXValidatedLineEdit { color: red; }"
    edit.setStyleSheet(sheet)

    QTest.keyClicks(edit, "1")
    assert edit._is_animating
    assert edit.styleSheet() == sheet
    qtbot.waitUntil(lambda: not edit._is_animating, timeout=1000)

    margins = edit.textMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (
        10, 0, 3, 0,
    )
    assert edit.styleSheet() == sheet


def test_icon_and_password_edits_style_through_the_theme(qtbot, qapp):
    password = FXPasswordLineEdit()
    icon_edit = FXIconLineEdit(icon_name="search")
    qtbot.addWidget(password)
    qtbot.addWidget(icon_edit)
    for widget in (password, icon_edit):
        assert not isinstance(widget, fxstyle.FXThemeAware)
    assert password.reveal_button.styleSheet() == ""
    assert icon_edit.icon_button.styleSheet() == ""
    sheet = fxstyle.build_stylesheet()
    assert "FXPasswordLineEdit" in sheet
    assert "fx_icon_line_edit_button" in sheet
