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
    assert password.reveal_button.styleSheet() == ""
    assert icon_edit.icon_button.styleSheet() == ""
    sheet = fxstyle.build_stylesheet()
    assert "FXPasswordLineEdit" in sheet
    assert "fx_icon_line_edit_button" in sheet


def test_the_flash_shows_over_a_focused_field(qtbot, qapp):
    from qtpy.QtCore import QPoint, QRect
    from qtpy.QtGui import QColor
    from qtpy.QtWidgets import QVBoxLayout, QWidget

    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    edit = FXValidatedLineEdit(flash_duration=400)
    edit.setValidator(FXLowerCaseValidator())
    QVBoxLayout(window).addWidget(edit)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    edit.setFocus()
    qtbot.waitUntil(edit.hasFocus)
    QTest.keyClicks(edit, "1")
    # Only the hold is the error colour itself; the fades blend it away.
    qtbot.waitUntil(lambda: edit.borderColor.alpha() == 255, timeout=1000)
    area = QRect(edit.mapTo(window, QPoint(0, 0)), edit.size())
    image = window.grab(area).toImage()
    error = QColor(fxstyle.colors().feedback_error_foreground).rgb()
    edge = [image.pixel(x, 0) for x in range(8, image.width() - 8)]
    assert all(pixel == error for pixel in edge)


def test_enter_in_a_dialog_s_password_field_accepts_the_dialog(qtbot):
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import (
        QDialog,
        QDialogButtonBox,
        QLineEdit,
        QVBoxLayout,
    )

    from fxgui.fxwidgets import FXPasswordLineEdit

    dialog = QDialog()
    qtbot.addWidget(dialog)
    column = QVBoxLayout(dialog)
    secret = FXPasswordLineEdit()
    column.addWidget(secret)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    column.addWidget(buttons)
    dialog.show()
    qtbot.waitExposed(dialog)
    secret.line_edit.setText("hunter2")
    # Revealed once with the mouse, then hidden again: the button keeps
    # the focus a click gave it.
    secret.reveal_button.click()
    secret.reveal_button.click()
    secret.reveal_button.setFocus()

    qtbot.keyClick(secret.reveal_button, Qt.Key_Return)

    assert dialog.result() == QDialog.Accepted
    assert secret.line_edit.echoMode() == QLineEdit.Password
