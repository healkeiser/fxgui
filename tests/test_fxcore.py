"""Tests for `fxgui.fxcore.FXSortFilterProxyModel` filtering and match color."""

# Third-party
from qtpy.QtCore import QStringListModel
from qtpy.QtGui import QColor

# Internal
from fxgui import fxstyle
from fxgui.fxcore import FXSortFilterProxyModel


def _proxy_with(items, ratio=0.5):
    model = QStringListModel(items)
    proxy = FXSortFilterProxyModel(ratio=ratio)
    proxy.setSourceModel(model)
    # Keep the source model alive alongside the proxy
    proxy._test_model = model
    return proxy


def _visible(proxy):
    return [proxy.index(row, 0).data() for row in range(proxy.rowCount())]


def test_substring_filter(qapp):
    proxy = _proxy_with(["apple", "banana", "cherry"])
    proxy.set_filter_text("app")
    texts = _visible(proxy)
    assert "apple" in texts
    assert "cherry" not in texts


def test_fuzzy_filter_tolerates_typos(qapp):
    proxy = _proxy_with(["banana", "zzzzzz"])
    proxy.set_filter_text("banna")  # Typo: not a substring of "banana"
    texts = _visible(proxy)
    assert "banana" in texts
    assert "zzzzzz" not in texts


def test_empty_filter_shows_everything(qapp):
    proxy = _proxy_with(["a", "b", "c"])
    proxy.set_filter_text("")
    assert proxy.rowCount() == 3


def test_matcher_is_per_instance(qapp):
    """A class-level matcher was shared mutable state across every proxy."""
    proxy_a = _proxy_with(["x"])
    proxy_b = _proxy_with(["y"])
    assert proxy_a._matcher is not proxy_b._matcher


def test_match_color_is_theme_aware_not_red_green(qapp):
    """Match quality color: theme disabled-text to accent interpolation, not
    the colorblind-hostile pure red/green gradient."""
    colors = fxstyle.get_theme_colors()
    poor = FXSortFilterProxyModel._match_color(0.0)
    good = FXSortFilterProxyModel._match_color(1.0)

    assert poor == QColor(colors["text_disabled"])
    assert good == QColor(colors["accent_primary"])
    assert poor != QColor(255, 0, 0)
    assert good != QColor(0, 255, 0)
