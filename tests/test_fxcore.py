"""Tests for `fxgui.fxcore.FXSortFilterProxyModel` filtering and match color."""

# Third-party
from qtpy.QtCore import QModelIndex, QStringListModel, Qt
from qtpy.QtGui import QColor, QStandardItem, QStandardItemModel

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
    colors = dict(vars(fxstyle.colors()))
    poor = FXSortFilterProxyModel._match_color(0.0)
    good = FXSortFilterProxyModel._match_color(1.0)

    assert poor == QColor(colors["text_disabled"])
    assert good == QColor(colors["accent_primary"])
    assert poor != QColor(255, 0, 0)
    assert good != QColor(0, 255, 0)


def _count_calls(monkeypatch, module, name):
    calls = []
    original = getattr(module, name)

    def counting(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, name, counting)
    return calls


def _number_proxy():
    model = QStandardItemModel()
    for value in (5, 15, None):
        item = QStandardItem()
        item.setData(value, Qt.DisplayRole)
        model.appendRow(item)
    proxy = FXSortFilterProxyModel(ratio=0.5)
    proxy.setSourceModel(model)
    proxy._test_model = model
    return proxy, model


def test_filtering_survives_non_text_data(qapp):
    proxy, model = _number_proxy()
    proxy._filter_text = "5"
    proxy._matcher.set_seq2("5")

    assert proxy.filterAcceptsRow(0, QModelIndex())
    assert isinstance(
        proxy.lessThan(model.index(0, 0), model.index(1, 0)), bool
    )
    proxy.set_filter_text("5")
    assert proxy.index(0, 0).data(Qt.ForegroundRole) is not None


def test_sorting_reads_each_row_once(qapp, monkeypatch):
    from fxgui import fxcore

    words = ["item%03d_%s" % (i, "xyz"[i % 3]) for i in range(200)]
    proxy = _proxy_with(words)
    reads = _count_calls(monkeypatch, fxcore, "_text")

    proxy.set_filter_text("item")

    assert proxy.rowCount() == 200
    assert len(reads) <= 200


def test_the_filter_reads_the_key_column(qapp):
    model = QStandardItemModel()
    for name, tag in (("alpha", "zzz"), ("beta", "comp"), ("gamma", "qqq")):
        model.appendRow([QStandardItem(name), QStandardItem(tag)])
    proxy = FXSortFilterProxyModel(ratio=0.9)
    proxy.setSourceModel(model)
    proxy._test_model = model

    proxy.setFilterKeyColumn(1)
    proxy.set_filter_text("comp")

    assert _visible(proxy) == ["beta"]


def test_rows_rank_by_their_own_score_after_a_removal(qapp):
    proxy = _proxy_with(["abcx", "abzz", "abcd"], ratio=0.1)
    proxy.set_filter_text("abcd")
    model = proxy._test_model

    model.removeRows(0, 1)
    model.setData(model.index(0, 0), "abzz")

    assert _visible(proxy) == ["abcd", "abzz"]


def test_match_colour_reads_the_cache(qapp, monkeypatch):
    fxstyle.colors()
    depth = _count_calls(monkeypatch, fxstyle, "_depth_colors")

    for ratio in (0.0, 0.5, 1.0):
        FXSortFilterProxyModel._match_color(ratio)

    assert depth == []
