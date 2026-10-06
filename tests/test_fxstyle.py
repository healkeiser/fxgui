"""The theme engine: tokens, the sheet, the colour cache, roots and files."""

# Built-in
import gc
import inspect
from pathlib import Path

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QLabel, QTreeWidget, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle


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


def _received():
    """Connect a list to theme_changed; return it and its disconnect."""
    received = []
    # PySide6 6.5 disconnects only the very object it connected.
    note = received.append
    fxstyle.theme_changed.connect(note)
    return received, lambda: fxstyle.theme_changed.disconnect(note)


# -- Tokens -------------------------------------------------------------


def test_token_replacement_takes_the_longest_key_first():
    tokens = {"@border": "#111111", "@border_light": "#222222"}
    out = fxstyle._substitute("a { x: @border; y: @border_light; }", tokens)
    assert "#222222" in out
    assert "#111111_light" not in out
    assert "@" not in out


def test_every_token_family_resolves(qapp):
    sheet = fxstyle._build_stylesheet("dark")
    assert sheet
    assert "@" not in sheet
    assert "~icons" not in sheet

    qss = (
        "a { b: @button_radius; c: @card_radius; f: @font_body; "
        "e: @feedback_error_foreground; p: @primary_button; s: @shadow; }"
    )
    out = fxstyle.resolve(qss)
    assert "@" not in out
    assert f"b: {fxstyle.BUTTON_RADIUS}px;" in out
    assert f"c: {fxstyle.CARD_RADIUS}px;" in out


def test_resolve_icons_path(qapp):
    dark = fxstyle.resolve("url(~icons/close.svg)", "dark")
    light = fxstyle.resolve("url(~icons/close.svg)", "light")
    assert "~icons" not in dark
    assert "/stylesheet_dark_close_18.png" in dark
    assert "/stylesheet_light_close_18.png" in light


def test_token_map_flattens_feedback_colors(qapp):
    tokens = fxstyle._token_map("dark")
    assert tokens["@feedback_error_foreground"].startswith("#")
    assert tokens["@feedback_error_background"].startswith("#")


def test_a_partial_or_unknown_theme_fills_from_dark(qapp, monkeypatch):
    assert fxstyle._token_map("no_such_theme") == fxstyle._token_map("dark")

    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    themes["_partial"] = {"surface": "#123456"}
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})
    tokens = fxstyle._token_map("_partial")
    assert tokens["@surface"] == "#123456"
    assert tokens["@text"] == fxstyle._token_map("dark")["@text"]


def test_a_colour_file_without_dark_fills_from_the_default(qapp, tmp_path):
    path = _yaml(tmp_path, "themes:\n  studio:\n    surface: '#101010'\n")
    fxstyle.set_color_file(path)
    fxstyle._theme = "studio"

    colors = dict(vars(fxstyle.colors()))

    default_dark = fxstyle._builtin_theme()
    assert colors["surface"] == "#101010"
    assert colors["accent_primary"] == default_dark["accent_primary"]


def test_token_map_computes_on_accent_when_theme_omits_them(qapp, monkeypatch):
    # Only when dark itself omits the on-accent keys does the computed
    # fallback run (the baseline merge fills them in for any other theme).
    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    themes["dark"] = {
        key: value
        for key, value in themes["dark"].items()
        if not key.startswith(("text_on_accent", "icon_on_accent"))
    }
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})
    tokens = fxstyle._token_map("dark")
    expected = fxstyle._pole_from(themes["dark"]["accent_primary"])
    assert tokens["@text_on_accent_primary"] == expected
    assert tokens["@icon_on_accent_primary"] == expected


_TEXT_GROUNDS = ("surface", "surface_sunken", "surface_alt", "well", "frame",
                 "tooltip", "state_hover")


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_every_text_ink_reads_on_every_surface_it_sits_on(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    ratio = fxstyle.get_contrast_ratio
    for ground in _TEXT_GROUNDS:
        assert ratio(colors["text"], colors[ground]) >= 4.5, ground
        assert ratio(colors["text_muted"], colors[ground]) >= 4.5, ground
    # A pressed or checked fill carries text, never muted text.
    assert ratio(colors["text"], colors["state_pressed"]) >= 4.5


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_pressed_fill_stands_off_the_hover_fill(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    assert fxstyle.get_contrast_ratio(
        colors["state_pressed"], colors["state_hover"]
    ) >= fxstyle.STATE_MIN_CONTRAST


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_muted_text_stays_a_visible_step_from_text(qapp, theme):
    colors = fxstyle._colour_tokens(theme)
    assert fxstyle.get_contrast_ratio(
        colors["text"], colors["text_muted"]
    ) >= fxstyle.MUTED_STEP


# -- The sheet ----------------------------------------------------------


def test_build_stylesheet_defaults_to_current_theme(qapp):
    assert fxstyle._build_stylesheet() == fxstyle._build_stylesheet(
        fxstyle.get_theme()
    )


def test_building_another_themes_sheet_leaves_the_current_one(qapp):
    fxstyle._theme = "light"

    sheet = fxstyle._build_stylesheet("dark")

    assert fxstyle.get_theme() == "light"
    assert fxstyle.get_colors()["themes"]["dark"]["surface"] in sheet


def test_register_widget_style_appends_one_resolved_fragment(qapp):
    fragment = "FXPlanTestWidget { background: @surface; }"
    fxstyle.register_widget_style(fragment)
    fxstyle.register_widget_style(fragment)
    sheet = fxstyle._build_stylesheet("dark")
    assert sheet.count("FXPlanTestWidget") == 1
    assert "@surface" not in sheet


def test_the_proxy_style_answers_qts_standard_icons_with_themed_ones(qapp):
    from qtpy.QtWidgets import QStyle

    style = fxstyle.FXProxyStyle()
    icon = style.standardIcon(QStyle.SP_MessageBoxCritical)
    assert icon is fxstyle._standard_icons()[QStyle.SP_MessageBoxCritical]
    assert not icon.pixmap(16, 16).isNull()


# -- colors() -----------------------------------------------------------


def test_colors_is_one_cached_strict_namespace(qapp, monkeypatch):
    first = fxstyle.colors()
    assert first is fxstyle.colors()
    assert first.surface.startswith("#")
    depth = _count_calls(monkeypatch, fxstyle, "_depth_colors")
    for _ in range(5):
        dict(vars(fxstyle.colors()))
    assert depth == []

    with pytest.raises(AttributeError, match="Unknown theme color role"):
        _ = first.this_role_does_not_exist


def test_theme_colors_are_the_resolved_token_map(qapp):
    colors = dict(vars(fxstyle.colors()))
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
    assert fxstyle.colors().surface == light


# -- apply_theme --------------------------------------------------------


def test_apply_theme_switches_and_signals(qtbot):
    received, disconnect = _received()
    try:
        fxstyle.apply_theme("light")
    finally:
        disconnect()
    assert received == ["light"]
    assert fxstyle.get_theme() == "light"
    assert fxstyle.colors().surface == "#f0f0f0"

    fxstyle.apply_theme("dark")
    assert fxstyle.colors().surface == "#302f2f"


def test_apply_theme_takes_a_known_theme_name_only(qtbot):
    assert list(inspect.signature(fxstyle.apply_theme).parameters) == [
        "theme"]
    with pytest.raises(ValueError):
        fxstyle.apply_theme("no_such_theme")


# -- Themed roots -------------------------------------------------------


def test_register_themed_root_applies_sheet_immediately(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    assert root.styleSheet() == ""
    fxstyle.register_themed_root(root)
    assert root.styleSheet() != ""
    assert "@" not in root.styleSheet()


def test_every_root_follows_a_fragment_and_a_switch(qtbot):
    root_a, root_b = QWidget(), QWidget()
    qtbot.addWidget(root_a)
    qtbot.addWidget(root_b)
    fxstyle.register_themed_root(root_a)
    fxstyle.register_themed_root(root_b)

    fxstyle.register_widget_style("FXPlanRootsProbe { color: @text; }")
    assert "FXPlanRootsProbe" in root_a.styleSheet()
    assert "FXPlanRootsProbe" in root_b.styleSheet()

    dark_sheet = root_a.styleSheet()
    fxstyle.apply_theme("light")
    assert root_a.styleSheet() != dark_sheet
    assert root_b.styleSheet() == root_a.styleSheet()


def test_dead_roots_drop_out(qtbot):
    root = QWidget()
    fxstyle.register_themed_root(root)
    count_before = len(fxstyle._themed_roots)
    del root
    gc.collect()
    assert len(fxstyle._themed_roots) < count_before
    # Must not raise on dead entries either:
    fxstyle._reapply_to_roots()


def test_a_root_switched_before_its_first_show_wears_the_new_theme(qtbot):
    from fxgui.fxwidgets import FXKeycap

    fxstyle.apply_theme("dark")
    root = QWidget()
    qtbot.addWidget(root)
    layout = QVBoxLayout(root)
    layout.addWidget(FXKeycap("Ctrl+S"))
    layout.addWidget(QLabel("child"))
    fxstyle.register_themed_root(root)
    fxstyle.apply_theme("light")
    root.resize(120, 80)
    root.show()
    qtbot.waitExposed(root)
    image = root.grab().toImage()
    assert image.pixelColor(1, 1).name() == fxstyle.colors().surface.lower()


def test_a_view_in_a_host_window_draws_no_focus_rect(qtbot):
    """PySide6 6.5 drew the host style's focus rect over a current cell."""
    root = QWidget()
    qtbot.addWidget(root)
    tree, combo = QTreeWidget(), QComboBox()
    combo.addItems(["a", "b"])
    layout = QVBoxLayout(root)
    layout.addWidget(tree)
    layout.addWidget(combo)
    fxstyle.register_themed_root(root)
    root.show()
    qtbot.waitExposed(root)
    combo.showPopup()
    qtbot.waitUntil(combo.view().isVisible)

    own = Qt.FindDirectChildrenOnly
    assert len(tree.findChildren(fxstyle.FXProxyStyle, "", own)) == 1
    # A header draws no cell; a popup's list keeps its menu rows.
    assert tree.header().findChild(fxstyle.FXProxyStyle) is None
    assert combo.view().findChild(fxstyle.FXProxyStyle) is None
    combo.hidePopup()


# -- Colour files -------------------------------------------------------


def test_overlay_sets_a_few_keys_and_keeps_the_rest(qapp, tmp_path):
    fxstyle._theme = "dark"
    default_text = fxstyle.colors().text
    path = _yaml(
        tmp_path,
        "themes:\n"
        "  dark:\n    accent_primary: '#ff0000'\n"
        "  studio:\n    surface: '#101010'\n"
        "fonts:\n  title: [Arial]\n",
    )

    fxstyle.overlay_color_file(path)

    colors = dict(vars(fxstyle.colors()))
    assert colors["accent_primary"] == "#ff0000"
    assert colors["text"] == default_text
    assert {"dark", "light", "dracula", "studio"} <= set(
        fxstyle.get_available_themes()
    )
    assert fxstyle.get_colors()["fonts"]["mono"]
    assert fxstyle.get_colors()["fonts"]["title"] == ["Arial"]


@pytest.mark.parametrize("change", ["overlay", "replace"])
def test_a_colour_file_change_reaches_roots_and_signal(
    qtbot, tmp_path, change
):
    fxstyle._theme = "dark"
    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    path = _yaml(tmp_path, "themes:\n  dark:\n    surface: '#123456'\n")

    received, disconnect = _received()
    try:
        if change == "overlay":
            fxstyle.overlay_color_file(path)
        else:
            fxstyle.set_color_file(path)
    finally:
        disconnect()

    assert "#123456" in root.styleSheet()
    assert received == ["dark"]


def test_a_sheet_icon_cut_off_mid_write_is_written_whole_next_time(
    qapp, monkeypatch, tmp_path
):
    import tempfile

    from qtpy.QtGui import QImage, QPixmap

    from fxgui import fxicons

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    svg = fxicons.get_icon_path("check")
    monkeypatch.setattr(QPixmap, "save", lambda *args: False)
    with pytest.raises(OSError):
        fxstyle._sheet_icon(svg, "check_123456", 16, "#123456")
    monkeypatch.undo()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    url = fxstyle._sheet_icon(svg, "check_123456", 16, "#123456")

    image = QImage(url[len("url("):-1])
    assert not image.isNull()
    solid = max(
        (image.pixelColor(x, y) for x in range(16) for y in range(16)),
        key=lambda color: color.alpha(),
    )
    assert solid.alpha() > 128 and solid.name() == "#123456"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_every_sheet_image_is_a_png_qt_reads_without_the_svg_plugin(
    qapp, theme
):
    import re

    from qtpy.QtGui import QImageReader

    # PNG is built into QtGui; SVG needs the qsvg plugin Cinema 4D lacks.
    urls = re.findall(r"url\(([^)]*)\)", fxstyle._build_stylesheet(theme))
    assert urls
    for url in urls:
        assert url.endswith(".png"), url
        reader = QImageReader(url)
        assert reader.format() == b"png" and not reader.read().isNull(), url
        assert Path(url[: -len(".png")] + "@2x.png").is_file(), url


def test_a_checked_box_draws_its_indicator(qtbot):
    from qtpy.QtWidgets import QCheckBox

    fxstyle.apply_theme("dark")
    box = QCheckBox()
    box.setChecked(True)
    qtbot.addWidget(box)
    fxstyle.register_themed_root(box)
    box.resize(60, 24)
    box.show()
    qtbot.waitExposed(box)

    image = box.grab().toImage()
    background = image.pixelColor(image.width() - 1, 0)
    size = fxstyle.INDICATOR_SIZE
    top = (image.height() - size) // 2
    inked = [
        (x, y)
        for x in range(size + 4)
        for y in range(top, top + size)
        if image.pixelColor(x, y) != background
    ]
    assert len(inked) > size * size // 4
