"""Tests for the theming core: token resolution, colour cache, colour files."""

# Third-party
import pytest
from qtpy.QtCore import QModelIndex, Qt
from qtpy.QtGui import QColor, QImage, QPixmap, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxcore import FXSortFilterProxyModel


@pytest.fixture
def own_colors(monkeypatch):
    """Restore the loaded colour file after a test swaps it."""
    monkeypatch.setattr(fxstyle, "_colors", None)
    monkeypatch.setattr(fxstyle, "_color_file", None)
    yield


def _count_calls(monkeypatch, module, name):
    calls = []
    original = getattr(module, name)

    def counting(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, name, counting)
    return calls


def _yaml(tmp_path, text):
    path = tmp_path / "colors.yaml"
    path.write_text(text, encoding="utf-8")
    return path


# load_stylesheet


def test_load_stylesheet_leaves_the_current_theme_alone(qapp, monkeypatch):
    fxstyle.save_theme("dark")
    fxstyle._theme = "light"

    sheet = fxstyle.load_stylesheet()

    assert fxstyle.get_theme() == "light"
    assert fxstyle.get_colors()["themes"]["light"]["surface"] in sheet


# get_theme_colors / colors()


def test_theme_colors_are_the_resolved_token_map(qapp):
    colors = fxstyle.get_theme_colors()
    tokens = fxstyle._token_map(fxstyle.get_theme())

    assert colors == {
        key[1:]: value for key, value in tokens.items() if key[0] == "@"
    }
    assert "text_on_accent_primary" in colors
    assert "icon_on_accent_secondary" in colors


def test_theme_colors_load_the_saved_theme(qapp):
    fxstyle.save_theme("light")
    fxstyle._theme = None

    light = fxstyle.get_colors()["themes"]["light"]["surface"]
    assert fxstyle.get_theme_colors()["surface"] == light


def test_theme_colors_and_namespace_share_one_cache(qapp, monkeypatch):
    fxstyle.get_theme_colors()
    depth = _count_calls(monkeypatch, fxstyle, "_depth_colors")

    for _ in range(5):
        fxstyle.get_theme_colors()
        fxstyle.colors()

    assert depth == []
    assert fxstyle.colors().surface == fxstyle.get_theme_colors()["surface"]


def test_a_colour_file_without_dark_fills_from_the_default(
    qapp, tmp_path, own_colors
):
    path = _yaml(tmp_path, "themes:\n  studio:\n    surface: '#101010'\n")
    fxstyle.set_color_file(path)
    fxstyle._theme = "studio"

    colors = fxstyle.get_theme_colors()

    default_dark = fxstyle._builtin_theme()
    assert colors["surface"] == "#101010"
    assert colors["text"] == default_dark["text"]


# resolve / replace_colors


def test_resolve_knows_every_token_family(qapp):
    qss = (
        "a { r: @radiuspx; b: @button_radius; f: @font_body; "
        "e: @feedback_error_foreground; p: @primary_button; }"
    )
    out = fxstyle.resolve(qss)

    assert "@" not in out
    assert f"r: {fxstyle.BUTTON_RADIUS}px;" in out
    assert f"b: {fxstyle.BUTTON_RADIUS}px;" in out


def test_replace_colors_without_a_dict_resolves_like_the_sheet(qapp):
    qss = "a { b: @button_radius; e: @feedback_error_background; }"
    assert fxstyle.replace_colors(qss) == fxstyle.resolve(qss)


def test_replace_colors_with_theme_colors_resolves_radius(qapp):
    out = fxstyle.replace_colors(
        "a { r: @radiuspx; }", fxstyle.get_theme_colors()
    )
    assert out == f"a {{ r: {fxstyle.BUTTON_RADIUS}px; }}"


# overlay_color_file / set_color_file


def test_overlay_sets_a_few_keys_and_keeps_the_rest(
    qapp, tmp_path, own_colors
):
    fxstyle._theme = "dark"
    default_text = fxstyle.get_theme_colors()["text"]
    path = _yaml(
        tmp_path,
        "themes:\n"
        "  dark:\n    accent_primary: '#ff0000'\n"
        "  studio:\n    surface: '#101010'\n"
        "fonts:\n  title: [Arial]\n",
    )

    fxstyle.overlay_color_file(path)

    colors = fxstyle.get_theme_colors()
    assert colors["accent_primary"] == "#ff0000"
    assert colors["text"] == default_text
    assert {"dark", "light", "dracula", "studio"} <= set(
        fxstyle.get_available_themes()
    )
    assert fxstyle.get_colors()["fonts"]["mono"]
    assert fxstyle.get_colors()["fonts"]["title"] == ["Arial"]


@pytest.mark.parametrize("change", ["overlay", "replace"])
def test_a_colour_file_change_reaches_roots_and_signal(
    qtbot, tmp_path, own_colors, change
):
    fxstyle._theme = "dark"
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    received = []
    fxstyle.theme_changed.connect(received.append)
    path = _yaml(tmp_path, "themes:\n  dark:\n    surface: '#123456'\n")

    try:
        if change == "overlay":
            fxstyle.overlay_color_file(path)
        else:
            fxstyle.set_color_file(path)
    finally:
        fxstyle.theme_changed.disconnect(received.append)

    assert "#123456" in root.styleSheet()
    assert received == ["dark"]


# dead code


def test_dead_style_hooks_are_gone(qapp):
    assert not hasattr(fxstyle.FXProxyStyle, "set_icon_color")
    assert not hasattr(fxstyle.FXProxyStyle(), "icon_color")
    assert not hasattr(fxstyle, "_FORCE_UPDATE_WALK")


def test_dead_utils_are_gone():
    for name in ("deprecated", "set_formatted_tooltip"):
        assert not hasattr(fxutils, name), name
        assert name not in fxutils.__all__


# fxicons


def test_get_icon_reads_the_colour_cache(qapp, monkeypatch):
    fxstyle.colors()
    depth = _count_calls(monkeypatch, fxstyle, "_depth_colors")
    for name in ("add", "close", "save"):
        fxicons.get_icon(name)

    assert depth == []


def test_an_opaque_pixmap_recolours(qapp):
    pixmap = QPixmap(8, 8)
    pixmap.fill(QColor("#ff0000"))

    out = fxicons._tint(pixmap, "#00ff00")

    assert out.toImage().pixelColor(4, 4) == QColor("#00ff00")
    assert not hasattr(fxicons, "has_transparency")


def _png_library(monkeypatch, tmp_path):
    folder = tmp_path / "studio"
    folder.mkdir()
    image = QImage(8, 8, QImage.Format_ARGB32)
    image.fill(QColor("#ff0000"))
    image.save(str(folder / "square.png"))
    monkeypatch.setattr(
        fxicons, "_libraries_info", dict(fxicons._libraries_info)
    )
    fxicons.add_library(
        "studio",
        pattern="{root}/{library}/{icon_name}.{extension}",
        defaults={
            "extension": "png",
            "style": None,
            "color": "#00ff00",
            "width": 8,
            "height": 8,
        },
        root=str(tmp_path),
    )


def test_an_opaque_png_icon_recolours(qapp, monkeypatch, tmp_path):
    _png_library(monkeypatch, tmp_path)

    pixmap = fxicons.get_pixmap("square", library="studio", dpr=1.0)

    assert pixmap.toImage().pixelColor(4, 4) == QColor("#00ff00")


# fxcore


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


def test_match_colour_reads_the_cache(qapp, monkeypatch):
    fxstyle.colors()
    depth = _count_calls(monkeypatch, fxstyle, "_depth_colors")

    for ratio in (0.0, 0.5, 1.0):
        FXSortFilterProxyModel._match_color(ratio)

    assert depth == []


# FXWidget


def test_fx_widget_is_gone():
    from fxgui import fxwidgets

    assert not hasattr(fxwidgets, "FXWidget")
