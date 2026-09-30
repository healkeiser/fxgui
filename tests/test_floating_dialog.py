"""FXFloatingDialog: opens centred on the cursor, closes like a QDialog."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QLabel, QWidget

# Internal
from fxgui import fxdcc, fxstyle
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
    monkeypatch.setattr(dialog, "exec_", lambda: 0)

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


@pytest.mark.parametrize("package", [None, fxdcc.HOUDINI])
def test_the_body_is_opaque_in_the_theme_surface(qtbot, package):
    dialog = _dialog(qtbot, parent_package=package)
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

    qtbot.waitUntil(lambda: not _compat.is_valid(dialog), timeout=1000)
