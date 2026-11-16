"""The confirm-delete dialog: the web look, and its typing guard."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QDialog, QMainWindow

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


def test_the_dialog_is_a_themed_root_of_its_own(qtbot):
    dialog = FXConfirmDeleteDialog(
        None, title="t", body="b", confirm_word="w")
    qtbot.addWidget(dialog)
    assert dialog in fxstyle._themed_roots


def test_markup_in_the_word_and_body_reads_as_typed(qtbot):
    dialog = FXConfirmDeleteDialog(
        None, title="t", body="<i>gone</i> & lost", confirm_word="<b>x</b>")
    qtbot.addWidget(dialog)
    labels = {label.text(): label for label in dialog.findChildren(type(dialog.hint))}

    body = labels["<i>gone</i> & lost"]
    assert body.textFormat() == Qt.PlainText
    assert "&lt;b&gt;x&lt;/b&gt;" in dialog.word_label.text()


# The web look (ls-ui's ConfirmModal): no typing unless asked for.


def _plain(qtbot, parented=True, **kwargs):
    parent = None
    if parented:
        parent = QMainWindow()
        _PARENTS.append(parent)
        qtbot.addWidget(parent)
    dialog = FXConfirmDeleteDialog(
        parent, title="Delete SH010?",
        body="Its tasks and comments go with it.", **kwargs)
    if not parented:
        qtbot.addWidget(dialog)
    return dialog


_PARENTS = []


def test_without_a_word_nothing_is_typed_and_delete_is_open(qtbot):
    dialog = _plain(qtbot)

    assert dialog._guard.isHidden()
    assert dialog.delete_button.isEnabled()


def test_a_word_with_typing_turned_off_asks_for_nothing(qtbot):
    dialog = _plain(qtbot, confirm_word="SH010", require_typing=False)
    dialog.field.setText("nope")

    assert dialog._guard.isHidden()
    assert dialog.delete_button.isEnabled()


def test_typing_turned_on_without_a_word_is_refused(qtbot):
    with pytest.raises(ValueError):
        FXConfirmDeleteDialog(None, title="t", require_typing=True)


def test_the_card_is_512_wide_and_carries_the_title(qtbot):
    dialog = _plain(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)

    assert dialog._card.width() == 512
    assert dialog.title_label.text() == "Delete SH010?"
    assert dialog.windowTitle() == "Delete SH010?"
    assert dialog.title_label.font().pixelSize() == 15
    assert dialog.title_label.font().weight() == fxstyle.drawn_weight(
        fxstyle.EMPHASIS_WEIGHT)
    ink = dialog.title_label.palette().color(
        dialog.title_label.foregroundRole())
    assert ink == QColor(fxstyle.colors().text_strong)
    body = dialog.body_label.palette().color(
        dialog.body_label.foregroundRole())
    assert body == QColor(fxstyle.colors().text_muted)


def test_cancel_then_delete_sit_at_the_bottom_right(qtbot):
    dialog = _plain(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)
    card = dialog._card

    cancel = dialog.cancel_button.geometry()
    delete = dialog.delete_button.geometry()
    assert cancel.right() < delete.left()
    assert card.width() - delete.right() - 1 == fxstyle.DIALOG_GUTTER
    assert cancel.height() >= 32 and delete.height() >= 32
    assert dialog.cancel_button.isFlat()
    assert delete.top() > dialog.body_label.geometry().bottom()


def test_the_close_x_is_32_px_in_the_top_right_corner(qtbot):
    dialog = _plain(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)

    x = dialog.close_button.geometry()
    assert x.size().width() == x.size().height() == 32
    assert (x.top(), dialog._card.width() - x.right() - 1) == (12, 12)
    assert not x.intersects(dialog.title_label.geometry().adjusted(
        0, 0, -dialog.title_label.contentsMargins().right(), 0))


def test_the_x_cancels(qtbot):
    dialog = _plain(qtbot)
    dialog.show()

    qtbot.mouseClick(dialog.close_button, Qt.LeftButton)

    assert dialog.result() == QDialog.Rejected
    assert not dialog.isVisible()


def test_focus_starts_on_cancel(qtbot):
    dialog = _plain(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)

    assert dialog.focusWidget() is dialog.cancel_button


def test_focus_starts_in_the_field_when_typing(qtbot):
    dialog = _plain(qtbot, confirm_word="SH010")
    dialog.show()
    qtbot.waitExposed(dialog)

    assert dialog.focusWidget() is dialog.field


def test_escape_cancels(qtbot):
    # Unparented: on PySide6 6.5 a key press, then the parent window's
    # deletion, trips fxstyle's focus marking on a half-deleted widget.
    dialog = _plain(qtbot, parented=False)
    dialog.show()
    qtbot.waitExposed(dialog)

    qtbot.keyClick(dialog, Qt.Key_Escape)

    assert dialog.result() == QDialog.Rejected
    assert not dialog.isVisible()


def test_enter_on_the_first_focus_cancels(qtbot):
    # Unparented: on PySide6 6.5 a key press, then the parent window's
    # deletion, trips fxstyle's focus marking on a half-deleted widget.
    dialog = _plain(qtbot, parented=False)
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))
    dialog.show()
    qtbot.waitExposed(dialog)

    qtbot.keyClick(dialog.cancel_button, Qt.Key_Return)

    assert not accepted
    assert dialog.result() == QDialog.Rejected


def test_delete_is_never_the_default(qtbot):
    dialog = _plain(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)

    assert not dialog.delete_button.isDefault()
    assert not dialog.delete_button.autoDefault()


def test_a_click_on_delete_accepts_without_typing(qtbot):
    dialog = _plain(qtbot)
    dialog.show()

    qtbot.mouseClick(dialog.delete_button, Qt.LeftButton)

    assert dialog.result() == QDialog.Accepted


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_delete_is_the_error_red_with_a_readable_ink(qtbot, theme):
    fxstyle.apply_theme(theme)
    dialog = _plain(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)
    colors = fxstyle.colors()

    shot = dialog.delete_button.grab().toImage()
    fill = QColor(shot.pixel(shot.width() // 2, 3))
    assert fill == QColor(colors.danger_button)
    ink = dialog.delete_button.palette().color(
        dialog.delete_button.foregroundRole())
    assert ink == QColor(colors.text_on_danger)


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_every_theme_s_danger_ink_reads(theme):
    tokens = fxstyle._colour_tokens(theme)

    assert fxstyle.get_contrast_ratio(
        tokens["danger_button"], tokens["text_on_danger"]) >= 4.5
    assert fxstyle.get_contrast_ratio(
        tokens["danger_button_pressed"], tokens["text_on_danger"]) >= 4.5
