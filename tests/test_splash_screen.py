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


def test_a_show_costs_what_a_widget_show_costs(qtbot):
    # Qt 6.7+ waits up to 1 s in the Show event for a window it maps after.
    import time

    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    start = time.perf_counter()
    splash.show()
    elapsed = time.perf_counter() - start

    assert splash.isVisible()
    assert elapsed < 0.5, elapsed


def _mark_inks(splash):
    image = splash.icon_label.pixmap().toImage()
    return {
        image.pixelColor(x, y).name()
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }


def test_the_default_mark_wears_the_icon_ink_of_every_theme(qtbot):
    splash = FXSplashScreen()
    qtbot.addWidget(splash)

    for theme in ("light", "dark"):
        fxstyle.apply_theme(theme)
        assert _mark_inks(splash) == {QColor(fxstyle.colors().icon).name()}
