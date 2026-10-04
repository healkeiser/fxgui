"""An icon renders at the screen's device pixel ratio, its logical size kept."""

# Third-party
import pytest
from qtpy.QtGui import QPixmapCache

# Internal
from fxgui import fxicons


@pytest.fixture(autouse=True)
def _clean_icon_cache():
    QPixmapCache.clear()
    yield
    QPixmapCache.clear()


@pytest.mark.parametrize("dpr", [1.0, 2.0])
def test_pixmap_rendered_at_device_pixel_ratio(qapp, monkeypatch, dpr):
    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: dpr)
    pixmap = fxicons.get_pixmap("check", width=48, height=48)
    assert pixmap.devicePixelRatio() == dpr
    assert pixmap.width() == pixmap.height() == 48 * dpr


def test_dpr_is_part_of_cache_key(qapp, monkeypatch):
    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 1.0)
    pixmap_1x = fxicons.get_pixmap("check", width=48, height=48)

    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 2.0)
    pixmap_2x = fxicons.get_pixmap("check", width=48, height=48)

    # A stale 1x pixmap must not be served for a 2x screen
    assert pixmap_1x.width() != pixmap_2x.width()


def test_icon_states_survive_dpr(qapp, monkeypatch):
    """QIcon per-state pixmaps (Disabled/Selected/Active) still differ."""
    from qtpy.QtCore import QSize
    from qtpy.QtGui import QIcon

    monkeypatch.setattr(fxicons, "_screen_dpr", lambda: 2.0)
    icon = fxicons.get_icon("check", width=48, height=48)
    size = QSize(48, 48)
    normal = icon.pixmap(size, QIcon.Normal).toImage()
    assert icon.pixmap(size, QIcon.Disabled).toImage() != normal


def test_a_pixmap_asked_at_a_ratio_has_that_ratio(qapp):
    """Qt before 6.8 hands the engine a device size, later ones a logical."""
    from qtpy.QtCore import QSize

    pixmap = fxicons.get_icon("check").pixmap(QSize(16, 16), 2.0)
    assert pixmap.size() == QSize(32, 32)
    assert pixmap.devicePixelRatio() == 2.0
