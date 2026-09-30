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
    assert splash.styleSheet() == fxstyle.load_stylesheet()


def test_a_theme_border_reads_the_theme_when_painted(qtbot):
    splash = FXSplashScreen(border_width=2, border_color=None)
    qtbot.addWidget(splash)

    fxstyle.apply_theme("github_light")

    assert splash._border_widget.color().name() == QColor(
        fxstyle.colors().border_light).name()


def test_a_fade_in_ends_fully_opaque(qtbot):
    splash = FXSplashScreen(fade_in=True)
    qtbot.addWidget(splash)

    splash.show()

    assert splash.windowOpacity() < 1.0
    qtbot.waitUntil(lambda: splash.windowOpacity() == 1.0, timeout=3000)


def test_the_defaults_say_nothing_made_up(qtbot):
    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    assert splash.info_label.text() == ""
    assert splash.copyright_label.text() == "Project | 0.0.0 | \u00a9 Company"
    splash.set_project_label("Show")
    assert splash.copyright_label.text() == "Show | 0.0.0 | \u00a9 Company"
