"""Tests for apply_theme."""

import pytest
from qtpy.QtWidgets import QWidget

from fxgui import fxstyle


def test_new_signature_switches_theme(qtbot):
    fxstyle.apply_theme("light")
    assert fxstyle.get_theme() == "light"
    fxstyle.apply_theme("dark")
    assert fxstyle.get_theme() == "dark"


def test_new_signature_updates_registered_roots(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    fxstyle.apply_theme("light")
    light_sheet = root.styleSheet()
    fxstyle.apply_theme("dark")
    assert root.styleSheet() != light_sheet


def test_unknown_theme_raises(qtbot):
    with pytest.raises(ValueError):
        fxstyle.apply_theme("no_such_theme")


def test_theme_changed_signal_still_fires(qtbot):
    received = []
    # PySide6 6.5 disconnects only the very object it connected.
    note = received.append
    fxstyle.theme_changed.connect(note)
    try:
        fxstyle.apply_theme("light")
    finally:
        fxstyle.theme_changed.disconnect(note)
    assert received == ["light"]

