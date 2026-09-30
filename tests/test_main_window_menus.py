"""FXMainWindow: Qt's own central widget, menus looked up, bars swappable."""

# Third-party
import pytest
from qtpy.QtWidgets import QLabel, QMenuBar, QStatusBar, QWidget

# Internal
from fxgui import _compat, fxstyle
from fxgui.fxwidgets import FXMainWindow, FXStatusBar

_MENUS = ("main_menu", "edit_menu", "window_menu", "theme_menu", "help_menu")


def _window(qtbot, **kwargs):
    window = FXMainWindow(title="probe", **kwargs)
    qtbot.addWidget(window)
    return window


def test_the_central_widget_is_the_one_set(qtbot):
    window = _window(qtbot)
    body = QLabel("Body")

    window.setCentralWidget(body)

    assert window.centralWidget() is body


def test_there_is_no_banner_band(qtbot):
    window = _window(qtbot)

    assert not hasattr(window, "banner")
    assert not hasattr(window, "hide_banner")
    assert not hasattr(window, "show_banner")


def test_every_window_shows_its_name_in_the_corner(qtbot):
    window = _window(qtbot)

    assert window.menuBar().cornerWidget() is window.title_corner
    assert window.banner_label.text() == "probe"
    window.use_corner_title()
    assert window.menuBar().cornerWidget() is window.title_corner


def test_the_menus_live_on_the_menu_bar(qtbot):
    window = _window(qtbot)
    bar = window.menuBar()

    for name in ("main_menu", "edit_menu", "window_menu", "help_menu"):
        assert getattr(window, name).menuAction() in bar.actions(), name
    assert window.theme_menu.menuAction() in window.window_menu.actions()
    assert window.menu_bar is bar


def test_a_new_menu_bar_gets_fxguis_menus_and_the_corner(qtbot, qapp):
    window = _window(qtbot)
    corner = window.title_corner
    bar = QMenuBar()

    window.setMenuBar(bar)
    qapp.processEvents()

    assert bar.cornerWidget() is corner
    for name in ("main_menu", "edit_menu", "window_menu", "help_menu"):
        menu = getattr(window, name)
        assert _compat.is_valid(menu), name
        assert menu.menuAction() in bar.actions(), name
    assert window.theme_menu.actions()


def test_no_menu_bar_keeps_the_corner_for_the_next_one(qtbot, qapp):
    window = _window(qtbot)
    corner = window.title_corner

    window.setMenuBar(None)
    qapp.processEvents()

    assert _compat.is_valid(corner)
    for name in _MENUS:
        assert getattr(window, name) is None, name

    bar = QMenuBar()
    window.setMenuBar(bar)
    assert bar.cornerWidget() is corner
    assert window.main_menu.menuAction() in bar.actions()


def test_status_bar_falls_back_to_qts_own(qtbot):
    window = _window(qtbot)

    window.setStatusBar(None)

    assert isinstance(window.statusBar(), QStatusBar)


def test_the_helpers_refuse_a_plain_status_bar_clearly(qtbot):
    window = _window(qtbot)
    window.setStatusBar(QStatusBar())

    window.hide_status_line()  # Nothing to hide: not an error.
    for call in (
        lambda: window.set_project_label("P"),
        lambda: window.set_version_label("1"),
        lambda: window.set_company_label("C"),
        lambda: window.show_status_line(),
        lambda: window.set_status_line_colors("#000000", "#ffffff"),
    ):
        with pytest.raises(TypeError, match="FXStatusBar"):
            call()


def test_the_helpers_still_drive_an_fxstatusbar(qtbot):
    window = _window(qtbot)

    window.set_project_label("Show")

    assert isinstance(window.statusBar(), FXStatusBar)
    assert window.statusBar().project_label.text() == "Show"


def test_the_theme_actions_follow_a_switch_without_the_mixin(qtbot):
    window = _window(qtbot)

    fxstyle.apply_theme("github_light")

    assert not isinstance(window, fxstyle.FXThemeAware)
    assert window.theme_actions["github_light"].isChecked()


def test_the_dead_helpers_are_gone():
    for name in (
        "_move_window",
        "_refresh_dialog_button_icons",
        "_add_shadows",
        "_live_menu_bar",
        "_create_banner",
    ):
        assert not hasattr(FXMainWindow, name), name
    assert "closeEvent" not in FXMainWindow.__dict__


def test_a_subclass_hook_without_the_theme_name_still_runs(qtbot):
    seen = []

    class Window(FXMainWindow):
        def _on_theme_changed(self):
            seen.append(1)
            super()._on_theme_changed()

    window = Window()
    qtbot.addWidget(window)

    fxstyle.apply_theme("github_light")

    assert seen == [1]


def test_a_replaced_central_widget_is_deleted_by_qt(qtbot):
    window = _window(qtbot)
    first = QWidget()
    window.setCentralWidget(first)

    window.setCentralWidget(QWidget())
    qtbot.wait(10)

    assert not _compat.is_valid(first)
