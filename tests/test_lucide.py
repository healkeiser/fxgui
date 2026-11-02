"""Lucide as the default library: names in Lucide's own spelling."""

# Built-in
import ast
from pathlib import Path
import re
import zipfile

# Third-party
import pytest

# Internal
from fxgui import fxconstants, fxicons

_PACKAGE = Path(fxicons.__file__).parent
# The calls and keywords that take an icon name as a string literal.
_ICON_CALLS = {"get_icon", "get_pixmap", "get_icon_path", "set_icon"}
_ICON_KEYWORDS = {"icon", "icon_name", "checked_icon", "fallback",
                  "home_icon", "filled_icon", "empty_icon", "half_icon"}


def _shipped():
    """Return every icon name in `lucide.zip`."""
    archive = zipfile.ZipFile(fxconstants.ICONS_ROOT / "lucide.zip")
    return {
        name[len("svg/"):-len(".svg")]
        for name in archive.namelist()
        if name.startswith("svg/") and name.endswith(".svg")
    }


def _asked_names():
    """Return (where, name) for each literal icon name fxgui's code asks for.

    A call naming its `library=` is skipped: its names are not Lucide's.
    """
    found = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            keywords = {k.arg: k.value for k in node.keywords}
            if "library" in keywords:
                continue
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            literals = list(node.args[:2]) if name in _ICON_CALLS else []
            literals += [v for k, v in keywords.items() if k in _ICON_KEYWORDS]
            for literal in literals:
                for value in ast.walk(literal):
                    if isinstance(value, ast.Constant) and isinstance(
                            value.value, str):
                        found.append((f"{path.name}:{value.lineno}",
                                      value.value))
    for path in sorted(_PACKAGE.rglob("*.qss")):
        for match in re.finditer(r"~icon\(([\w-]+)", path.read_text()):
            found.append((path.name, match.group(1)))
    return found


def test_lucide_is_the_default_library():
    assert fxicons.default_library() == "lucide"


def test_a_one_word_lucide_name_is_drawn():
    path = fxicons.get_icon_path("stethoscope")
    assert path.endswith("/svg/stethoscope.svg")


def test_a_hyphenated_lucide_name_is_drawn():
    assert fxicons.get_icon_path("circle-check").endswith("/circle-check.svg")


def test_a_material_name_is_not_translated():
    with pytest.raises(FileNotFoundError):
        fxicons.get_icon_path("expand_more")


def test_a_named_library_is_used_as_asked():
    path = fxicons.get_icon_path("expand_more", library="material")
    assert "expand_more" in path


def test_material_as_the_default_takes_material_names(monkeypatch):
    monkeypatch.setattr(fxicons, "_default_library", "lucide")
    fxicons.set_default_library("material")
    assert "expand_more" in fxicons.get_icon_path("expand_more")


def test_an_unknown_library_is_refused():
    with pytest.raises(ValueError):
        fxicons.set_default_library("nope")


def test_an_icon_renders_from_lucide(qapp):
    icon = fxicons.get_icon("x")
    assert not icon.pixmap(16, 16).isNull()


def test_the_scan_finds_the_names_fxgui_asks_for():
    names = {name for _, name in _asked_names()}
    assert {"chevron-down", "x", "circle-check", "house"} <= names


def test_every_name_fxgui_asks_for_ships_in_lucide():
    shipped = _shipped()
    missing = [(where, name) for where, name in _asked_names()
               if name not in shipped]
    assert not missing, missing
