"""Tests for the canonical color-read API."""

from qtpy.QtWidgets import QWidget

from fxgui import fxstyle


def test_colors_returns_namespace(qtbot):
    fxstyle.apply_theme("dark")
    colors = fxstyle.colors()
    assert colors.surface.startswith("#")
    assert colors.text.startswith("#")


def test_colors_tracks_theme_switches(qtbot):
    fxstyle.apply_theme("dark")
    dark_surface = fxstyle.colors().surface
    fxstyle.apply_theme("light")
    assert fxstyle.colors().surface != dark_surface


def test_module_level_theme_changed_signal(qtbot):
    received = []
    fxstyle.theme_changed.connect(received.append)
    try:
        fxstyle.apply_theme("light")
    finally:
        fxstyle.theme_changed.disconnect(received.append)
    assert received == ["light"]
