"""The confirm-delete dialog refuses until the word matches exactly."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QDialog

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXConfirmDeleteDialog


def _dialog(qtbot, word="beauty"):
    dialog = FXConfirmDeleteDialog(
        None, title="Delete render/beauty v004",
        body="This cannot be undone.", confirm_word=word,
    )
    fxstyle.register_themed_root(dialog)
    qtbot.addWidget(dialog)
    return dialog


def test_delete_is_shut_until_the_word_matches(qtbot):
    dialog = _dialog(qtbot)

    assert not dialog.delete_button.isEnabled()
    dialog.field.setText("beaut")
    assert not dialog.delete_button.isEnabled()
    dialog.field.setText("beauty")
    assert dialog.delete_button.isEnabled()


def test_the_match_is_exact(qtbot):
    dialog = _dialog(qtbot)

    for near in ("Beauty", " beauty", "beauty ", "beautyy", "BEAUTY"):
        dialog.field.setText(near)
        assert not dialog.delete_button.isEnabled(), near


def test_typing_it_then_breaking_it_shuts_the_button_again(qtbot):
    dialog = _dialog(qtbot)
    dialog.field.setText("beauty")

    dialog.field.setText("beautyx")

    assert not dialog.delete_button.isEnabled()


def test_enter_never_destroys(qtbot):
    dialog = _dialog(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)
    dialog.field.setText("beauty")

    qtbot.keyClick(dialog.field, Qt.Key_Return)

    assert not dialog.delete_button.isDefault()
    assert not dialog.delete_button.autoDefault()
    assert dialog.result() != QDialog.Accepted


def test_a_click_on_an_open_delete_accepts(qtbot):
    dialog = _dialog(qtbot)
    dialog.show()
    dialog.field.setText("beauty")

    qtbot.mouseClick(dialog.delete_button, Qt.LeftButton)

    assert dialog.result() == QDialog.Accepted


def test_clicking_the_word_copies_it(qtbot):
    dialog = _dialog(qtbot, "beauty_lighting_v2")
    QApplication.clipboard().clear()

    qtbot.mouseClick(dialog.word_label, Qt.LeftButton)

    assert QApplication.clipboard().text() == "beauty_lighting_v2"


def test_the_hint_says_when_it_does_not_match(qtbot):
    dialog = _dialog(qtbot)

    assert dialog.hint.text() == ""
    dialog.field.setText("beaut")
    assert "match" in dialog.hint.text().lower()
    dialog.field.setText("beauty")
    assert dialog.hint.text() == ""
    dialog.field.setText("")
    assert dialog.hint.text() == ""


def test_the_hint_wears_the_theme_s_error_ink(qtbot):
    dialog = _dialog(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)
    fxstyle.apply_theme("light")

    ink = dialog.hint.palette().color(dialog.hint.foregroundRole())

    error = fxstyle.colors().feedback_error_foreground
    assert ink == QColor(error)
    assert dialog.hint.styleSheet() == ""
