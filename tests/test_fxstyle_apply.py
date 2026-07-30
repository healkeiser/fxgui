"""Tests for apply_theme: new signature, old-signature shim, mixin compat."""

import warnings

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


def test_old_signature_warns_and_registers_root(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    with pytest.warns(DeprecationWarning):
        fxstyle.apply_theme(widget, "light")
    assert fxstyle.get_theme() == "light"
    assert widget.styleSheet() != ""
    # The widget is now a root: further switches keep it updated.
    sheet = widget.styleSheet()
    fxstyle.apply_theme("dark")
    assert widget.styleSheet() != sheet


def test_old_keyword_signature_works(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    with pytest.warns(DeprecationWarning):
        fxstyle.apply_theme(widget, theme="dark")
    assert fxstyle.get_theme() == "dark"


def test_theme_changed_signal_still_fires(qtbot):
    received = []
    fxstyle.theme_manager.theme_changed.connect(received.append)
    try:
        fxstyle.apply_theme("light")
    finally:
        fxstyle.theme_manager.theme_changed.disconnect(received.append)
    assert received == ["light"]


def test_fxthemeaware_mixin_still_notified(qtbot):
    calls = []

    class Probe(fxstyle.FXThemeAware, QWidget):
        def _on_theme_changed(self, _theme_name=None):
            calls.append(fxstyle.get_theme())

    probe = Probe()
    qtbot.addWidget(probe)
    fxstyle.apply_theme("light")
    assert "light" in calls
