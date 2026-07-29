"""Tests for high-DPI icon rendering in `fxgui.fxicons`.

Regression: SVGs were rasterized at logical size with no devicePixelRatio,
so icons rendered blurry on scaled displays (the norm on 4K monitors).
"""

# Third-party
import pytest

# Internal
from fxgui import fxicons


@pytest.fixture(autouse=True)
def _clean_icon_cache():
    fxicons.clear_icon_cache()
    yield
    fxicons.clear_icon_cache()


def test_pixmap_rendered_at_device_pixel_ratio(qapp, monkeypatch):
    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 2.0)
    pixmap = fxicons.get_pixmap("check", width=48, height=48)
    assert pixmap.devicePixelRatio() == 2.0
    # Physical resolution doubled; logical size unchanged
    assert pixmap.width() == 96
    assert pixmap.height() == 96


def test_dpr_is_part_of_cache_key(qapp, monkeypatch):
    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 1.0)
    pixmap_1x = fxicons.get_pixmap("check", width=48, height=48)

    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 2.0)
    pixmap_2x = fxicons.get_pixmap("check", width=48, height=48)

    # A stale 1x pixmap must not be served for a 2x screen
    assert pixmap_1x.width() != pixmap_2x.width()


def test_dpr_one_keeps_legacy_behavior(qapp, monkeypatch):
    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 1.0)
    pixmap = fxicons.get_pixmap("check", width=48, height=48)
    assert pixmap.width() == 48
    assert pixmap.devicePixelRatio() == 1.0


def test_icon_states_survive_dpr(qapp, monkeypatch):
    """QIcon per-state pixmaps (Disabled/Selected/Active) still differ."""
    from qtpy.QtCore import QSize
    from qtpy.QtGui import QIcon

    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 2.0)
    icon = fxicons.get_icon("check", width=48, height=48)
    size = QSize(48, 48)
    normal = icon.pixmap(size, QIcon.Normal).toImage()
    assert icon.pixmap(size, QIcon.Disabled).toImage() != normal
