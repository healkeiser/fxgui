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


def _fonts(theme="dark"):
    """Return each role's resolved family, as the sheet writes it."""
    return {role: fxstyle._qss_family(entries)
            for role, entries in fxstyle._font_config(theme).items()}


###### Fallback to the pre-roles behaviour


def test_shipped_color_file_emits_the_platform_font(qapp):
    # The block this replaced emitted exactly this for `*`.
    default = f'"{fxstyle._platform_default_font()}"'
    assert _fonts()["body"] == default
    assert _fonts()["title"] == default


def test_the_body_family_is_the_root_font_not_a_sheet_rule(qapp):
    default = fxstyle._platform_default_font()
    assert fxstyle.font("dark").family() == default
    assert fxstyle.font("dark").pixelSize() == fxstyle.FONT_SIZE
    assert "@font_body" not in fxstyle._font_stylesheet()


def test_missing_fonts_section_falls_back(qapp, monkeypatch):
    colors = {
        key: value
        for key, value in fxstyle.get_colors().items()
        if key != "fonts"
    }
    monkeypatch.setattr(fxstyle, "_colors", colors)
    default = f'"{fxstyle._platform_default_font()}"'
    fonts = _fonts()
    assert fonts["title"] == default
    assert fonts["body"] == default
    # Mono has no platform equivalent, so its default lives in the module
    # and the log area rule keeps the stack it always had.
    assert fonts["mono"].endswith("monospace")


def test_missing_role_falls_back(qapp, monkeypatch):
    _patch_color_file(monkeypatch, fonts={"body": ["Courier New"]})
    default = f'"{fxstyle._platform_default_font()}"'
    assert _fonts()["title"] == default


@pytest.mark.parametrize("empty", [[], "", None])
def test_empty_role_value_falls_back(qapp, monkeypatch, empty):
    _patch_color_file(monkeypatch, fonts={"title": empty, "body": empty})
    default = f'"{fxstyle._platform_default_font()}"'
    fonts = _fonts()
    assert fonts["title"] == default
    assert fonts["body"] == default


def test_absent_family_is_dropped_not_named(qapp, monkeypatch):
    # Naming a family Qt does not have is the failure to avoid: Qt does
    # not complain, it substitutes whichever family sorts first, so the
    # sheet would claim a face that is not being drawn.
    _patch_color_file(monkeypatch, fonts={"title": ["No Such Family QQQ"]})
    resolved = _fonts()["title"]
    assert "No Such Family QQQ" not in resolved
    assert resolved == f'"{fxstyle._platform_default_font()}"'


def test_generic_keyword_is_terminal_and_unquoted(qapp):
    # A CSS generic ends the stack, so nothing is appended after it.
    assert fxstyle._qss_family(["monospace"]) == "monospace"


def test_a_role_resolves_to_its_first_installed_family_alone(
    qapp, monkeypatch
):
    # Qt on Windows takes about 0.4 s to resolve a first font naming two.
    monkeypatch.setattr(
        fxstyle.QFontDatabase, "families",
        staticmethod(lambda *_: ["Courier New", "Consolas"]))
    stack = ["No Such QQQ", "Consolas", "Courier New", "monospace"]
    assert fxstyle._qss_family(stack) == '"Consolas"'
    _patch_color_file(monkeypatch, fonts={"mono": stack})
    assert fxstyle.font("dark", role="mono").families() == ["Consolas"]


def test_stylesheet_leaves_no_font_token_unresolved(qapp):
    assert "@font_" not in fxstyle._build_stylesheet("dark")


def test_host_rules_resolve_font_tokens(qapp):
    assert "@font_" not in fxstyle._host_rules("dark")


###### Reading roles from the color file


def test_color_file_declares_the_roles(qapp, monkeypatch):
    _patch_color_file(
        monkeypatch, fonts={"title": ["Courier New"], "body": ["Verdana"]}
    )
    available = set(QFontDatabase.families())
    if not {"Courier New", "Verdana"} <= available:
        pytest.skip("system font database is empty on this platform")
    fonts = _fonts()
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


def test_an_unknown_role_falls_back_to_the_body_font(qapp):
    assert fxstyle.font("dark", role="no_such_role") == fxstyle.font("dark")


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
    sheet = fxstyle._build_stylesheet("dark")
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


###### Weight, hinting and a role's QFont


def test_font_takes_a_role(qapp, monkeypatch):
    _patch_color_file(monkeypatch, fonts={"mono": ["No Such QQQ", "monospace"]})
    assert fxstyle.font("dark", role="mono").families() == []
    assert fxstyle.font("dark", role="title").family() == (
        fxstyle._platform_default_font())


def test_a_face_names_its_weight_and_hinting(qapp, monkeypatch):
    _patch_color_file(monkeypatch, fonts={
        "body": {"family": ["Inter"], "weight": 500, "hinting": "none"},
    })
    body = fxstyle.font("dark")
    assert body.weight() == QFont.Medium
    assert body.hintingPreference() == QFont.PreferNoHinting
    assert _fonts()["body"] == (
        f'"{fxstyle._platform_default_font()}"')


def test_a_face_without_weight_keeps_the_default(qapp):
    body = fxstyle.font("dark")
    assert body.weight() == QFont().weight()
    assert body.hintingPreference() == QFont().hintingPreference()


def test_an_unknown_weight_is_refused(qapp, monkeypatch):
    _patch_color_file(monkeypatch, fonts={"body": {"weight": 450}})
    with pytest.raises(ValueError, match="450"):
        fxstyle.font("dark")


def test_the_body_weight_reaches_a_themed_app(qtbot, qapp, monkeypatch):
    font = QFont(qapp.font())
    _patch_color_file(monkeypatch, fonts={"body": {"weight": 500}})
    fxstyle.register_themed_root(qapp)
    try:
        label = QLabel("text")
        qtbot.addWidget(label)
        assert label.font().weight() == QFont.Medium
    finally:
        fxstyle._themed_roots.discard(qapp)
        qapp.setStyleSheet("")
        qapp.setFont(font)


def test_the_body_weight_reaches_a_host_window(qtbot, monkeypatch):
    _patch_color_file(monkeypatch, fonts={"body": {"weight": 500}})
    from qtpy.QtWidgets import QApplication, QScrollArea

    root = QWidget()
    QVBoxLayout(root)
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    root.show()
    qtbot.waitExposed(root)
    page = QScrollArea()
    late = QLabel("moved in after the show")
    page.setWidget(late)
    root.layout().addWidget(page)
    QApplication.processEvents()
    assert late.font().weight() == QFont.Medium
