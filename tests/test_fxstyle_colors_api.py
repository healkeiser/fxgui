"""Tests for the canonical color-read API."""

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
    # PySide6 6.5 disconnects only the very object it connected.
    note = received.append
    fxstyle.theme_changed.connect(note)
    try:
        fxstyle.apply_theme("light")
    finally:
        fxstyle.theme_changed.disconnect(note)
    assert received == ["light"]
