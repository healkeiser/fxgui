"""FXSplashScreen crops any image, follows theme switches, closes on a click."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect, Qt
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

    assert not splash.pixmap().isNull()


def test_the_image_is_qts_own_pixmap(qtbot):
    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    assert callable(splash.pixmap)
    assert splash.pixmap().width() == FXSplashScreen.IDEAL_WIDTH


def test_a_file_that_is_no_image_is_refused(tmp_path):
    path = tmp_path / "broken.png"
    path.write_bytes(b"not an image")

    with pytest.raises(ValueError, match="Invalid image path"):
        FXSplashScreen(image_path=str(path))


def test_the_panel_paints_the_surface_after_a_switch(qtbot):
    fxstyle.apply_theme("dark")
    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    fxstyle.apply_theme("github_light")

    panel = splash.overlay_frame
    image = panel.grab().toImage()
    assert image.pixelColor(panel.width() - 3, panel.height() // 2).name() == (
        QColor(fxstyle.colors().surface).name())
    assert panel.styleSheet() == ""
    assert splash.styleSheet() == (
        fxstyle._host_rules() + fxstyle._build_stylesheet())


def test_the_border_reads_the_theme_by_default(qtbot):
    splash = FXSplashScreen(border_width=2)
    qtbot.addWidget(splash)

    fxstyle.apply_theme("github_light")

    assert splash._border_widget.color().name() == QColor(
        fxstyle.colors().border_light).name()


def test_a_fade_in_ends_fully_opaque(qtbot):
    splash = FXSplashScreen(fade_in=True)
    qtbot.addWidget(splash)

    splash.show()
    assert splash.windowOpacity() < 1.0
    splash._fade.setCurrentTime(splash._fade.duration())

    assert splash.windowOpacity() == 1.0


def test_the_defaults_say_nothing_made_up(qtbot):
    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    assert splash.info_label.text() == ""
    assert splash.copyright_label.text() == ""
    named = FXSplashScreen(project="Show", company="Studio")
    qtbot.addWidget(named)
    assert named.copyright_label.text() == "Show | Studio"


def test_progress_works_without_asking_for_the_bar_first(qtbot):
    splash = FXSplashScreen()
    qtbot.addWidget(splash)
    splash.show()

    splash.set_progress(40, 80)

    assert splash.progress_bar.isVisible()
    assert splash.progress_bar.value() == 40


def test_a_message_shows_in_the_panel(qtbot):
    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    splash.showMessage("Loading shots")

    assert splash.message_label.text() == "Loading shots"


def test_a_click_hides_the_splash(qtbot):
    splash = FXSplashScreen()
    qtbot.addWidget(splash)
    splash.show()
    qtbot.waitExposed(splash)

    qtbot.mouseClick(splash, Qt.LeftButton, pos=QPoint(600, 200))

    assert not splash.isVisible()


def test_the_splash_keeps_one_way_to_set_each_thing():
    for name in (
        "set_pixmap",
        "set_icon",
        "set_title",
        "set_information_text",
        "toggle_progress_bar_visibility",
        "set_project_label",
        "set_version_label",
        "set_company_label",
        "toggle_fade_in",
        "set_overlay_opacity",
        "set_corner_radius",
        "set_border",
        "_apply_rounded_mask",
    ):
        assert not hasattr(FXSplashScreen, name), name
