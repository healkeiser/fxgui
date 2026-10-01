"""Input widgets style through the theme and leave the caller's state alone."""

# Third-party
import pytest
from qtpy.QtCore import QAbstractAnimation, Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLineEdit, QPushButton, QToolButton

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


def _animating(edit):
    group = edit._flash_group
    return group is not None and group.state() == QAbstractAnimation.Running


def _reject(qtbot, edit):
    QTest.keyClicks(edit, "1")
    qtbot.waitUntil(lambda: not _animating(edit))


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
    assert _animating(edit)
    assert edit.styleSheet() == sheet
    qtbot.waitUntil(lambda: not _animating(edit))

    margins = edit.textMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (
        10, 0, 3, 0,
    )
    assert edit.styleSheet() == sheet


def test_a_finished_flash_leaves_no_border(qtbot, qapp):
    edit = _validated(qtbot)
    _reject(qtbot, edit)
    assert edit.borderColor.alpha() == 0


def _shown(qtbot, edit):
    qtbot.addWidget(edit)
    edit.resize(200, edit.sizeHint().height())
    edit.show()
    qtbot.waitExposed(edit)
    return edit


@pytest.mark.parametrize("position", ["left", "right"])
def test_the_icon_is_a_line_edit_action_on_its_side(qtbot, qapp, position):
    edit = _shown(qtbot, FXIconLineEdit(icon_name="search",
                                        icon_position=position))
    assert len(edit.actions()) == 1
    assert edit.findChildren(QPushButton) == []
    (button,) = [b for b in edit.findChildren(QToolButton) if b.isVisible()]
    on_left = button.geometry().center().x() < edit.width() // 2
    assert on_left == (position == "left")


def test_a_bad_icon_position_is_refused(qtbot, qapp):
    with pytest.raises(ValueError):
        FXIconLineEdit(icon_name="search", icon_position="top")


def test_the_parent_comes_first(qtbot, qapp):
    from qtpy.QtWidgets import QWidget

    holder = QWidget()
    qtbot.addWidget(holder)
    assert FXIconLineEdit(holder, "search").parent() is holder
    assert FXPasswordLineEdit(holder).parent() is holder


def test_the_password_field_is_the_line_edit(qtbot, qapp):
    secret = _shown(qtbot, FXPasswordLineEdit())
    assert isinstance(secret, QLineEdit)
    assert secret.echoMode() == QLineEdit.Password
    (reveal,) = secret.actions()
    reveal.trigger()
    assert secret.echoMode() == QLineEdit.Normal
    reveal.trigger()
    assert secret.echoMode() == QLineEdit.Password


def test_the_reveal_takes_no_tab_stop(qtbot, qapp):
    secret = _shown(qtbot, FXPasswordLineEdit())
    for button in secret.findChildren(QToolButton):
        assert button.focusPolicy() == Qt.NoFocus


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
    qtbot.waitUntil(lambda: edit.borderColor.alpha() == 255)
    area = QRect(edit.mapTo(window, QPoint(0, 0)), edit.size())
    image = window.grab(area).toImage()
    error = QColor(fxstyle.colors().feedback_error_foreground).rgb()
    edge = [image.pixel(x, 0) for x in range(8, image.width() - 8)]
    assert all(pixel == error for pixel in edge)


def test_enter_in_a_dialog_s_password_field_accepts_the_dialog(qtbot):
    from qtpy.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

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
    secret.setText("hunter2")
    # Revealed once with the mouse, then hidden again.
    (reveal,) = [b for b in secret.findChildren(QToolButton) if b.isVisible()]
    QTest.mouseClick(reveal, Qt.LeftButton)
    QTest.mouseClick(reveal, Qt.LeftButton)

    qtbot.keyClick(dialog.focusWidget() or secret, Qt.Key_Return)

    assert dialog.result() == QDialog.Accepted
    assert secret.echoMode() == QLineEdit.Password
