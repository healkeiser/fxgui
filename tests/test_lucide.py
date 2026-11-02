"""Lucide as the default library: names in Lucide's own spelling."""

# Built-in
import ast
from pathlib import Path
import zipfile

# Third-party
import pytest

# Internal
from fxgui import fxconstants, fxicons, fxstyle

_PACKAGE = Path(fxicons.__file__).parent
# The calls taking an icon name positionally, and that argument's index.
_ICON_CALLS = {"get_icon": 0, "get_pixmap": 0, "get_icon_path": 0,
               "set_icon": 1, "_mark": 0, "_fold_button": 0}
# Keywords, and parameters whose default is an icon name.
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


def _literals(node):
    """Return every non-empty string constant inside `node`."""
    return [value for value in ast.walk(node)
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
            and value.value]


def _defaults(function):
    """Return the defaults of `function`'s parameters named in _ICON_KEYWORDS."""
    args = function.args
    positional = args.posonlyargs + args.args
    pairs = list(zip(positional[len(positional) - len(args.defaults):],
                     args.defaults))
    pairs += [(a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults) if d]
    return [default for arg, default in pairs if arg.arg in _ICON_KEYWORDS]


def _call_names(call):
    """Return the arguments of `call` that hold a Lucide icon name.

    A call naming its `library=` keeps only `fallback=`, which is always
    looked up in the default library.
    """
    keywords = {k.arg: k.value for k in call.keywords}
    if "library" in keywords:
        return [keywords["fallback"]] if "fallback" in keywords else []
    name = getattr(call.func, "attr", getattr(call.func, "id", ""))
    index = _ICON_CALLS.get(name)
    found = [call.args[index]] if index is not None and len(call.args) > index else []
    return found + [v for k, v in keywords.items() if k in _ICON_KEYWORDS]


def _asked_names():
    """Return (where, name) for each literal icon name fxgui's code asks for."""
    found = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                holders = _call_names(node)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                holders = _defaults(node)
            else:
                continue
            for holder in holders:
                found += [(f"{path.name}:{value.lineno}", value.value)
                          for value in _literals(holder)]
    for path in sorted(_PACKAGE.rglob("*.qss")):
        for match in fxstyle._SHEET_ICON.finditer(path.read_text()):
            found.append((path.name, match.group(1)))
    return found


def test_a_name_with_no_library_resolves_in_lucide():
    assert fxicons.get_icon_path("x") == fxicons.get_icon_path(
        "x", library="lucide")


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


def test_an_icon_renders_from_lucide(qapp):
    icon = fxicons.get_icon("x")
    assert not icon.pixmap(16, 16).isNull()


def test_the_scan_finds_the_names_fxgui_asks_for():
    asked = _asked_names()
    names = {name for _, name in asked}
    assert {"chevron-down", "x", "circle-check", "house", "star-half",
            "layout-grid", "minus", "chevrons-up-down"} <= names
    sheet = {name for where, name in asked if where.endswith(".qss")}
    assert {"chevron-down", "check"} <= sheet


def test_every_name_fxgui_asks_for_ships_in_lucide():
    shipped = _shipped()
    missing = [(where, name) for where, name in _asked_names()
               if name not in shipped]
    assert not missing, missing
