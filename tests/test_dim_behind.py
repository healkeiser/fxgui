"""fxutils.dim_behind: a modal dialog veils its window, and only then."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QDialog, QMainWindow, QWidget

# Internal
from fxgui import fxstyle, fxutils
from fxgui.fxwidgets import FXConfirmDeleteDialog, FXFloatingDialog

_HELD = []


def _window(qtbot):
    window = QMainWindow()
    window.setCentralWidget(QWidget())
    fxstyle.register_themed_root(window)
    _HELD.append(window)
    qtbot.addWidget(window)
    window.resize(400, 300)
    window.show()
    qtbot.waitExposed(window)
    return window


def _scrims(window):
    return [
        child for child in window.children()
        if isinstance(child, fxutils._Scrim)
    ]


def _dialog(window):
    dialog = QDialog(window)
    fxutils.dim_behind(dialog)
    return dialog


def test_an_open_dialog_veils_the_whole_window(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)

    dialog.open()

    (scrim,) = _scrims(window)
    assert scrim.isVisible()
    assert scrim.geometry() == window.rect()
    assert scrim.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert scrim.focusPolicy() == Qt.NoFocus
    # The veil is the window's, never over the dialog.
    assert not scrim.isAncestorOf(dialog) and scrim.window() is window


def test_the_veil_follows_the_window_s_size(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)
    dialog.open()

    window.resize(520, 380)

    (scrim,) = _scrims(window)
    assert scrim.geometry() == window.rect()


def test_closing_the_dialog_lifts_the_veil_at_once(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)
    dialog.open()

    dialog.reject()

    assert _scrims(window) == []


def test_a_dialog_opened_again_veils_once(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)
    fxutils.dim_behind(dialog)

    dialog.open()
    dialog.reject()
    dialog.open()

    assert len(_scrims(window)) == 1


def test_a_dialog_from_a_child_veils_the_child_s_window(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window.centralWidget())

    dialog.open()

    assert len(_scrims(window)) == 1


def test_a_modeless_dialog_dims_nothing(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)

    dialog.show()

    assert _scrims(window) == []


def test_a_dialog_with_no_parent_dims_nothing(qtbot):
    dialog = QDialog()
    qtbot.addWidget(dialog)
    fxutils.dim_behind(dialog)

    dialog.open()

    assert dialog.isVisible()


def test_a_deleted_dialog_takes_its_veil(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)
    dialog.open()
    (scrim,) = _scrims(window)

    dialog.deleteLater()
    qtbot.waitUntil(lambda: _scrims(window) == [])


@pytest.mark.parametrize(
    ("theme", "veil"),
    [("dark", "#99000000"), ("light", "#bff3f3f5")],
)
def test_the_veil_is_the_theme_s(qtbot, theme, veil):
    fxstyle.apply_theme(theme)
    assert fxstyle.colors().modal_scrim == veil
    window = _window(qtbot)
    ground = window.grab().toImage().pixelColor(QPoint(200, 150))
    dialog = _dialog(window)

    dialog.open()

    seen = window.grab().toImage().pixelColor(QPoint(200, 150))
    tint = QColor(veil)
    alpha = tint.alphaF()
    for part in ("red", "green", "blue"):
        expected = getattr(tint, part)() * alpha + getattr(
            ground, part)() * (1 - alpha)
        assert abs(getattr(seen, part)() - expected) <= 2, part


def test_a_theme_switch_repaints_the_veil(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)
    dialog.open()

    fxstyle.apply_theme("light")

    seen = window.grab().toImage().pixelColor(QPoint(200, 150))
    assert seen.lightness() > 128


def test_reduced_motion_veils_at_once(qtbot):
    window = _window(qtbot)
    dialog = _dialog(window)

    dialog.open()

    (scrim,) = _scrims(window)
    assert scrim._level == 1.0


def test_motion_fades_the_veil_in(qtbot, motion):
    window = _window(qtbot)
    dialog = _dialog(window)

    dialog.open()

    (scrim,) = _scrims(window)
    assert scrim._level < 1.0
    assert scrim._fade.duration() == fxstyle.MOTION_BASE
    qtbot.waitUntil(lambda: scrim._level == 1.0, timeout=2000)


def test_the_confirm_dialog_dims_its_window(qtbot):
    window = _window(qtbot)
    dialog = FXConfirmDeleteDialog(window, title="Delete SH010?")

    dialog.open()
    assert len(_scrims(window)) == 1
    dialog.reject()
    assert _scrims(window) == []


def test_a_modal_floating_dialog_dims_and_a_popup_does_not(qtbot):
    window = _window(qtbot)
    modal = FXFloatingDialog(window, title="Modal")
    modal.open()
    assert len(_scrims(window)) == 1
    modal.reject()

    popup = FXFloatingDialog(window, title="Popup", popup=True)
    popup.open()
    assert _scrims(window) == []
    popup.close()
