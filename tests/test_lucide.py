"""Lucide as the default library: Material names drawn as their Lucide twins."""

# Third-party
import pytest

# Internal
from fxgui import fxicons


@pytest.fixture
def lucide(monkeypatch):
    """Make Lucide the default library for one test."""
    monkeypatch.setattr(fxicons, "_default_library", "material")
    fxicons.set_default_library("lucide")
    yield
    monkeypatch.setattr(fxicons, "_default_library", "material")


def test_a_material_name_draws_its_lucide_twin(lucide):
    path = fxicons.get_icon_path("expand_more")
    assert path.endswith("/svg/chevron-down.svg")


def test_a_name_lucide_lacks_keeps_its_material_icon(lucide):
    assert "join_full" not in fxicons._names("lucide")
    path = fxicons.get_icon_path("join_full")
    assert "/material/" in path or "material-" in path


def test_a_name_in_lucide_spelling_is_drawn_as_it_is(lucide):
    assert fxicons.get_icon_path("circle-check").endswith("/circle-check.svg")


def test_a_named_library_is_not_translated(lucide):
    path = fxicons.get_icon_path("expand_more", library="material")
    assert "expand_more" in path


def test_every_twin_ships_in_the_zip():
    import zipfile

    from fxgui import fxconstants

    shipped = {
        name[len("svg/"):-len(".svg")]
        for name in zipfile.ZipFile(
            fxconstants.ICONS_ROOT / "lucide.zip").namelist()
        if name.startswith("svg/")
    }
    missing = set(fxicons._names("lucide").values()) - shipped
    assert not missing, sorted(missing)


def test_an_unknown_library_is_refused():
    with pytest.raises(ValueError):
        fxicons.set_default_library("nope")


def test_an_icon_renders_from_lucide(qapp, lucide):
    icon = fxicons.get_icon("close")
    assert not icon.pixmap(16, 16).isNull()
