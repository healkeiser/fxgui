"""FXMainWindow: Qt's own central widget, menus looked up, bars swappable."""

# Built-in

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QAction
from qtpy.QtWidgets import (
    QDialog,
    QMenuBar,
    QMessageBox,
    QStatusBar,
)

# Internal
from fxgui import _compat, fxstyle
from fxgui.fxwidgets import FXMainWindow

_MENUS = ("main_menu", "window_menu", "theme_menu", "help_menu")


def _window(qtbot, **kwargs):
    window = FXMainWindow(title="probe", **kwargs)
    qtbot.addWidget(window)
    return window


def test_every_window_shows_its_name_in_the_corner(qtbot):
    window = _window(qtbot)

    assert window.menuBar().cornerWidget() is window.title_corner
    assert window.banner_label.text() == "probe"


def test_the_menus_live_on_the_menu_bar(qtbot):
    window = _window(qtbot)
    bar = window.menuBar()

    for name in ("main_menu", "window_menu", "help_menu"):
        assert getattr(window, name).menuAction() in bar.actions(), name
    assert window.theme_menu.menuAction() in window.window_menu.actions()
    assert [action.text() for action in bar.actions()] == [
        "File", "Window", "Help"]


def test_a_new_menu_bar_gets_fxguis_menus_and_the_corner(qtbot, qapp):
    window = _window(qtbot)
    corner = window.title_corner
    bar = QMenuBar()

    window.setMenuBar(bar)
    qapp.processEvents()

    assert bar.cornerWidget() is corner
    for name in ("main_menu", "window_menu", "help_menu"):
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


def test_the_window_holds_no_placeholder_action_and_no_edit_menu(qtbot):
    window = _window(qtbot)

    for name in (
        "check_updates_action",
        "hide_action",
        "hide_others_action",
        "settings_action",
        "home_action",
        "previous_action",
        "next_action",
        "toggle_theme_action",
        "edit_menu",
        "toolbar",
        "theme_action_group",
        "window_icon",
        "window_title",
        "window_size",
        "project",
        "version",
        "company",
    ):
        assert not hasattr(window, name), name
    for name in ("CRITICAL", "ERROR", "WARNING", "SUCCESS", "INFO", "DEBUG"):
        assert not hasattr(FXMainWindow, name), name
    for action in window.findChildren(QAction):
        assert action.isEnabled() or action is window.open_documentation_action


def test_about_reads_the_bar_as_it_is_now(qtbot, monkeypatch):
    window = _window(qtbot, project="Show", version="1.0", company="Studio")
    bar = window.statusBar()
    bar.project_label.setText("Other show")
    bar.version_label.setText("2.0")
    shown = []
    monkeypatch.setattr(
        QMessageBox, "about", lambda *args: shown.append(args[1:]))

    window.about_action.trigger()

    assert shown == [("About", "probe\nOther show\n2.0\nStudio")]
    assert window.findChildren(QDialog) == []


def test_about_on_a_plain_status_bar_names_the_window(qtbot):
    window = _window(qtbot)
    window.setStatusBar(QStatusBar())

    assert window._about_text() == "probe"


def test_unset_project_version_and_company_show_nothing(qtbot):
    window = _window(qtbot)
    bar = window.statusBar()

    for item in (bar.project_label, bar.version_label, bar.company_label):
        assert item.text() == ""
        assert item.isHidden()
    assert window._about_text() == "probe"


def test_always_on_top_is_one_checkable_entry(qtbot):
    window = _window(qtbot)
    action = window.window_on_top_action

    action.trigger()
    assert action.isChecked() and action.text() == "Always on Top"
    assert window.windowFlags() & Qt.WindowStaysOnTopHint
    action.trigger()
    assert not action.isChecked() and action.text() == "Always on Top"
    assert not window.windowFlags() & Qt.WindowStaysOnTopHint


@pytest.mark.parametrize("url, valid", [
    ("https://example.com/docs", True),
    ("example.com", False),
    ("http://[", False),
    (None, False),
])
def test_documentation_is_enabled_only_for_a_url(qtbot, url, valid):
    window = _window(qtbot, documentation=url)

    assert window.open_documentation_action.isEnabled() is valid


def test_documentation_set_later_enables_the_entry(qtbot, monkeypatch):
    from fxgui.fxwidgets import _main_window

    opened = []
    monkeypatch.setattr(_main_window, "open_new_tab", opened.append)
    window = _window(qtbot)

    window.set_documentation("https://example.com/docs")
    window.open_documentation_action.trigger()

    assert window.documentation() == "https://example.com/docs"
    assert opened == ["https://example.com/docs"]
    window.set_documentation(None)
    assert not window.open_documentation_action.isEnabled()


def test_the_theme_actions_follow_a_switch_without_the_mixin(qtbot):
    window = _window(qtbot)

    fxstyle.apply_theme("github_light")

    assert window.theme_actions["github_light"].isChecked()


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


def test_the_theme_actions_switch_the_theme(qtbot):
    fxstyle.apply_theme("dark")
    window = _window(qtbot)

    window.theme_actions["github_light"].trigger()
    assert fxstyle.get_theme() == "github_light"

    themes = fxstyle.get_available_themes()
    assert window.toggle_theme() == fxstyle.get_theme() == themes[
        (themes.index("github_light") + 1) % len(themes)]


def test_center_on_screen_centres_on_the_primary_screen(qtbot):
    from qtpy.QtWidgets import QApplication

    window = _window(qtbot)
    window.resize(300, 200)

    window.center_on_screen()

    centre = QApplication.primaryScreen().availableGeometry().center()
    assert (window.frameGeometry().center() - centre).manhattanLength() <= 2
