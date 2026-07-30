"""Tests for the themed-root registry."""

from qtpy.QtWidgets import QWidget

from fxgui import fxstyle


def test_register_themed_root_applies_sheet_immediately(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    assert root.styleSheet() == ""
    fxstyle.register_themed_root(root)
    assert root.styleSheet() != ""
    assert "@" not in root.styleSheet()


def test_reapply_updates_all_roots(qtbot):
    root_a, root_b = QWidget(), QWidget()
    qtbot.addWidget(root_a)
    qtbot.addWidget(root_b)
    fxstyle.register_themed_root(root_a)
    fxstyle.register_themed_root(root_b)

    fragment = "FXPlanRootsProbe { color: @text; }"
    fxstyle.register_widget_style(fragment)

    assert "FXPlanRootsProbe" in root_a.styleSheet()
    assert "FXPlanRootsProbe" in root_b.styleSheet()


def test_dead_roots_drop_out(qtbot):
    root = QWidget()
    fxstyle.register_themed_root(root)
    count_before = len(fxstyle._themed_roots)
    del root
    import gc

    gc.collect()
    assert len(fxstyle._themed_roots) < count_before
    # Must not raise on dead entries either:
    fxstyle._reapply_to_roots()
