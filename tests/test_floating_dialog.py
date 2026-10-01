"""FXFloatingDialog: opens centred on the cursor, closes like a QDialog."""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QLabel, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import _dialogs
from fxgui.fxwidgets._dialogs import FXFloatingDialog


class _Cursor:
    @staticmethod
    def pos():
        return QPoint(500, 400)


_PARENTS = []


def _dialog(qtbot, **kwargs):
    # qtbot holds widgets weakly; the parent must outlive the dialog.
    parent = QWidget()
    _PARENTS.append(parent)
    qtbot.addWidget(parent)
    return FXFloatingDialog(parent, **kwargs)


def test_it_opens_centred_on_the_cursor_at_its_final_size(qtbot, monkeypatch):
    dialog = _dialog(qtbot, title="Probe")
    dialog.main_layout.addWidget(QLabel("A longer line of text\n" * 6))
    monkeypatch.setattr(_dialogs, "QCursor", _Cursor)
    monkeypatch.setattr(dialog, "exec", lambda: 0)

    dialog.show_under_cursor()

    centre = dialog.frameGeometry().center()
    assert abs(centre.x() - 500) <= 1 and abs(centre.y() - 400) <= 1


def test_close_runs_qdialogs_own_close(qtbot):
    dialog = _dialog(qtbot)
    dialog.show()

    with qtbot.waitSignal(dialog.finished, timeout=1000):
        dialog.close()

    assert "closeEvent" not in FXFloatingDialog.__dict__


def test_layout_is_qts_method(qtbot):
    dialog = _dialog(qtbot)

    assert callable(dialog.layout)
    assert dialog.layout() is not None


def test_the_body_is_opaque_in_the_theme_surface(qtbot):
    dialog = _dialog(qtbot)
    dialog.resize(240, 160)
    dialog.show()
    qtbot.waitExposed(dialog)
    body = dialog.main_widget
    point = body.mapTo(dialog, QPoint(body.width() // 2, body.height() // 2))

    colour = dialog.grab().toImage().pixelColor(point)

    assert colour.alpha() == 255
    assert colour.name() == QColor(fxstyle.colors().surface).name()


def test_the_default_icon_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    dialog = _dialog(qtbot)
    qtbot.wait(10)
    before = dialog._icon_label.pixmap().toImage()
    assert not before.isNull()

    fxstyle.apply_theme("github_light")

    assert dialog._icon_label.pixmap().toImage() != before


def test_a_given_icon_survives_a_theme_switch(qtbot):
    from fxgui import fxicons

    icon = fxicons.get_icon("settings", color="#ff0000").pixmap(32, 32)
    dialog = _dialog(qtbot, icon=icon)
    before = dialog._icon_label.pixmap().toImage()

    fxstyle.apply_theme("github_light")

    assert dialog._icon_label.pixmap().toImage() == before


def test_the_close_button_rejects_and_deletes_the_dialog(qtbot):
    from fxgui import _compat

    dialog = _dialog(qtbot)
    dialog.show()

    with qtbot.waitSignal(dialog.rejected, timeout=1000):
        dialog.button_close.click()
    # PySide6 6.5 runs a deleteLater only once control is back in the loop
    # it was posted from; delivering it here proves one was posted.
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    assert not _compat.is_valid(dialog)


def test_the_dialog_keeps_no_dead_state_and_no_host_look(qtbot):
    dialog = _dialog(qtbot, popup=False)

    for name in ("dialog_icon", "dialog_title", "parent_package"):
        assert not hasattr(dialog, name), name
    assert "houdini" not in fxstyle._build_stylesheet()


def _shown(qtbot, theme):
    fxstyle.apply_theme(theme)
    dialog = _dialog(qtbot, title="Publish")
    dialog.main_layout.addWidget(QLabel("Three files will be written."))
    dialog.resize(280, 180)
    dialog.show()
    qtbot.waitExposed(dialog)
    return dialog


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_frame_wears_the_border_at_the_card_radius(qtbot, theme):
    dialog = _shown(qtbot, theme)
    frame = dialog._container
    image = frame.grab().toImage()
    border = QColor(fxstyle.colors().border).name()
    radius = fxstyle.CARD_RADIUS
    middle = frame.height() // 2
    assert image.pixelColor(0, middle).name() == border
    assert image.pixelColor(frame.width() - 1, middle).name() == border
    assert image.pixelColor(frame.width() // 2, frame.height() - 1).name() == (
        border
    )
    # Rounded at the radius: just past it the edge is straight.
    assert image.pixelColor(radius + 1, frame.height() - 1).name() == border
    assert image.pixelColor(0, frame.height() - 1).name() != border


def test_the_title_is_a_section_title(qtbot):
    dialog = _shown(qtbot, "dark")
    label = dialog.title_label
    assert label.property(fxstyle.TITLE_PROPERTY) == "section"
    assert label.font().pixelSize() == 15


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_buttons_are_the_theme_s_push_buttons(qtbot, theme):
    dialog = _shown(qtbot, theme)
    button = dialog.button_close
    assert button.height() == fxstyle.control_height(button)
    qtbot.mouseMove(dialog, QPoint(1, 1))
    qtbot.mouseMove(button, button.rect().center())
    qtbot.wait(20)
    image = button.grab().toImage()
    colors = fxstyle.colors()
    assert image.pixelColor(4, button.height() // 2).name() == (
        QColor(colors.state_hover).name()
    )
    # Hover is a fill only: the edge stays the button's own.
    assert image.pixelColor(button.width() // 2, 0).name() == (
        QColor(colors.border_light).name()
    )


def test_title_body_and_buttons_share_one_left_edge(qtbot):
    dialog = _shown(qtbot, "dark")
    title = dialog.title_layout.contentsMargins().left()
    body = dialog.main_layout.contentsMargins().left()
    buttons = dialog.button_box.contentsMargins().left()
    assert title == body == buttons
