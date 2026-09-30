"""FXSplashScreen crops any image and follows theme switches."""

# Third-party
import pytest
from qtpy.QtCore import QRect
from qtpy.QtGui import QColor, QImage

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXSplashScreen


def _int_rect(*args):
    # PyQt refuses a float coordinate; PySide truncates it quietly.
    assert all(isinstance(value, int) for value in args), args
    return QRect(*args)


@pytest.mark.parametrize("size", [(401, 100), (100, 401)])
def test_an_image_of_any_shape_crops_at_whole_pixels(
    qtbot, tmp_path, monkeypatch, size
):
    from fxgui.fxwidgets import _splash_screen

    path = tmp_path / "image.png"
    image = QImage(*size, QImage.Format_RGB32)
    image.fill(QColor("#336699"))
    image.save(str(path))
    monkeypatch.setattr(_splash_screen, "QRect", _int_rect)

    splash = FXSplashScreen(image_path=str(path))
    qtbot.addWidget(splash)

    assert not splash.pixmap.isNull()


def test_the_splash_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    fxstyle.apply_theme("github_light")

    surface = QColor(fxstyle.colors().surface)
    rgb = f"{surface.red()}, {surface.green()}, {surface.blue()}"
    assert rgb in splash.overlay_frame.styleSheet()
    assert splash.styleSheet() == fxstyle.build_stylesheet()


def test_a_theme_border_reads_the_theme_when_painted(qtbot):
    splash = FXSplashScreen(border_width=2, border_color=None)
    qtbot.addWidget(splash)

    fxstyle.apply_theme("github_light")

    assert splash._border_widget.color().name() == QColor(
        fxstyle.colors().border_light).name()
