"""Tests for the font roles in fxstyle.

fxgui ships no typefaces of its own, so these cover the mechanism: the
`fonts:` mapping is read from the color file, every way of leaving a role
unset falls back to the font the module emitted before roles existed, and
a consumer can register its own files and name them.

The offscreen platform has an empty *system* font database on Windows, so
tests needing two real families skip rather than assert on nothing.
"""

# Third-party
import pytest
from qtpy.QtGui import QFont, QFontDatabase
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle


def _patch_color_file(monkeypatch, **sections):
    """Replace the cached color config, keeping the themes intact."""
    colors = fxstyle.get_colors()
    monkeypatch.setattr(fxstyle, "_colors", {**colors, **sections})


###### Fallback to the pre-roles behaviour


def test_shipped_color_file_emits_the_platform_font(qapp):
    # The block this replaced emitted exactly this for `*`.
    default = f'"{fxstyle._platform_default_font()}"'
    assert fxstyle.get_fonts("dark")["body"] == default
    assert fxstyle.get_fonts("dark")["title"] == default


def test_font_block_is_unchanged_for_the_universal_selector(qapp):
    default = fxstyle._platform_default_font()
    sheet = fxstyle.build_stylesheet("dark")
    assert f'* {{\n    font-family: "{default}";\n}}\n' in sheet


def test_missing_fonts_section_falls_back(qapp, monkeypatch):
    colors = {
        key: value
        for key, value in fxstyle.get_colors().items()
        if key != "fonts"
    }
    monkeypatch.setattr(fxstyle, "_colors", colors)
    default = f'"{fxstyle._platform_default_font()}"'
    fonts = fxstyle.get_fonts("dark")
    assert fonts["title"] == default
    assert fonts["body"] == default
    # Mono has no platform equivalent, so its default lives in the module
    # and the log area rule keeps the stack it always had.
    assert fonts["mono"].endswith("monospace")


def test_missing_role_falls_back(qapp, monkeypatch):
    _patch_color_file(monkeypatch, fonts={"body": ["Courier New"]})
    default = f'"{fxstyle._platform_default_font()}"'
    assert fxstyle.get_fonts("dark")["title"] == default


@pytest.mark.parametrize("empty", [[], "", None])
def test_empty_role_value_falls_back(qapp, monkeypatch, empty):
    _patch_color_file(monkeypatch, fonts={"title": empty, "body": empty})
    default = f'"{fxstyle._platform_default_font()}"'
    fonts = fxstyle.get_fonts("dark")
    assert fonts["title"] == default
    assert fonts["body"] == default


def test_absent_family_is_dropped_not_named(qapp, monkeypatch):
    # Naming a family Qt does not have is the failure to avoid: Qt does
    # not complain, it substitutes whichever family sorts first, so the
    # sheet would claim a face that is not being drawn.
    _patch_color_file(monkeypatch, fonts={"title": ["No Such Family QQQ"]})
    resolved = fxstyle.get_fonts("dark")["title"]
    assert "No Such Family QQQ" not in resolved
    assert resolved == f'"{fxstyle._platform_default_font()}"'


def test_generic_keyword_is_terminal_and_unquoted(qapp):
    # A CSS generic ends the stack, so nothing is appended after it.
    assert fxstyle._resolve_font_stack(["monospace"]) == "monospace"


def test_stylesheet_leaves_no_font_token_unresolved(qapp):
    assert "@font_" not in fxstyle.build_stylesheet("dark")


def test_load_stylesheet_also_resolves_font_tokens(qapp):
    # The legacy entry point prepended the font block *after* the token
    # pass, which would now ship a literal @font_body to Qt.
    assert "@font_" not in fxstyle.load_stylesheet(theme="dark")


###### Reading roles from the color file


def test_color_file_declares_the_roles(qapp, monkeypatch):
    _patch_color_file(
        monkeypatch, fonts={"title": ["Courier New"], "body": ["Verdana"]}
    )
    available = set(QFontDatabase.families())
    if not {"Courier New", "Verdana"} <= available:
        pytest.skip("system font database is empty on this platform")
    fonts = fxstyle.get_fonts("dark")
    assert fonts["title"].startswith('"Courier New"')
    assert fonts["body"].startswith('"Verdana"')


def test_theme_may_override_a_single_role(qapp, monkeypatch):
    colors = fxstyle.get_colors()
    themes = dict(colors["themes"])
    themes["_typographic"] = {
        **themes["dark"],
        "fonts": {"title": ["Courier New"]},
    }
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "themes": themes})

    config = fxstyle._font_config("_typographic")
    assert config["title"] == ["Courier New"]
    # Roles the theme stays silent about keep the file-level values.
    assert config["mono"] == colors["fonts"]["mono"]


def test_get_font_family_falls_back_to_body_for_unknown_role(qapp):
    fonts = fxstyle.get_fonts("dark")
    assert fxstyle.get_font_family("no_such_role", "dark") == fonts["body"]


###### Registering a consumer's own files


def test_register_fonts_reports_a_file_that_did_not_load(qapp, tmp_path):
    missing = tmp_path / "not_a_font.ttf"
    missing.write_bytes(b"this is not a font")
    result = fxstyle.register_fonts(missing)
    assert result[str(missing)] == []


def test_register_fonts_accepts_several_paths(qapp, tmp_path):
    paths = []
    for name in ("a.ttf", "b.ttf"):
        path = tmp_path / name
        path.write_bytes(b"nope")
        paths.append(path)
    result = fxstyle.register_fonts(paths)
    assert set(result) == {str(path) for path in paths}
    assert all(families == [] for families in result.values())


def test_register_fonts_leaves_roots_alone_when_nothing_loaded(
    qapp, tmp_path, monkeypatch
):
    # Restyling every root is wasted work if no family became available.
    calls = []
    monkeypatch.setattr(
        fxstyle, "_reapply_to_roots", lambda: calls.append(True)
    )
    path = tmp_path / "bad.ttf"
    path.write_bytes(b"nope")
    fxstyle.register_fonts(path)
    assert calls == []


###### The title selector


def _themed_pair(qtbot, sheet_fonts=None):
    """Return (root, body_label, title_label) under a themed root."""
    root = QWidget()
    layout = QVBoxLayout(root)
    body = QLabel("Handgloves body")
    title = QLabel("Handgloves title")
    for label in (body, title):
        label.setFixedSize(240, 30)
        layout.addWidget(label)
    fxstyle.mark_as_title(title)
    fxstyle.register_themed_root(root)
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)
    return root, body, title


def test_title_property_is_set_by_the_helper(qtbot):
    _root, body, title = _themed_pair(qtbot)
    assert title.property(fxstyle.TITLE_PROPERTY) is True
    assert body.property(fxstyle.TITLE_PROPERTY) is None


def test_unmarking_clears_the_property(qtbot):
    _root, _body, title = _themed_pair(qtbot)
    fxstyle.mark_as_title(title, False)
    assert title.property(fxstyle.TITLE_PROPERTY) is False


def test_title_selector_is_in_the_stylesheet(qapp):
    sheet = fxstyle.build_stylesheet("dark")
    assert f'[{fxstyle.TITLE_PROPERTY}="true"]' in sheet


def test_default_roles_make_marking_a_title_a_visual_no_op(qtbot):
    # fxgui's own file leaves `title` empty, so the mechanism must be
    # inert until a consumer names a family.
    _root, body, title = _themed_pair(qtbot)
    assert title.fontInfo().family() == body.fontInfo().family()


def test_title_selector_reaches_the_widget_when_roles_differ(
    qtbot, monkeypatch
):
    available = set(QFontDatabase.families())
    candidates = [
        name for name in ("Courier New", "Verdana") if name in available
    ]
    if len(candidates) < 2:
        pytest.skip("needs two system families; font database is empty")

    _patch_color_file(
        monkeypatch,
        fonts={"title": [candidates[0]], "body": [candidates[1]]},
    )
    _root, body, title = _themed_pair(qtbot)
    assert title.fontInfo().family() == candidates[0]
    assert body.fontInfo().family() == candidates[1]


def test_marking_a_title_keeps_its_size_and_weight(qtbot, monkeypatch):
    available = set(QFontDatabase.families())
    if "Courier New" not in available:
        pytest.skip("needs a system family; font database is empty")
    _patch_color_file(monkeypatch, fonts={"title": ["Courier New"]})

    root = QWidget()
    layout = QVBoxLayout(root)
    label = QLabel("Handgloves")
    label.setStyleSheet("font-size: 18pt;")
    font = QFont()
    font.setBold(True)
    label.setFont(font)
    layout.addWidget(label)
    fxstyle.register_themed_root(root)
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)

    before = (label.fontInfo().pixelSize(), label.fontInfo().weight())
    fxstyle.mark_as_title(label)
    after = (label.fontInfo().pixelSize(), label.fontInfo().weight())

    assert label.fontInfo().family() == "Courier New"
    assert after == before
