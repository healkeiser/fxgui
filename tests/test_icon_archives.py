"""Material, Font Awesome and Simple Icons ship as one zip per library."""

from pathlib import Path

import pytest

from fxgui import fxconstants, fxicons


@pytest.mark.parametrize(
    "name, library",
    [("add", "material"), ("lemon", "fontawesome"), ("python", "simple")],
)
def test_an_icon_comes_out_of_its_zip(qapp, name, library):
    path = Path(fxicons.get_icon_path(name, library=library))
    assert not (fxconstants.ICONS_ROOT / library).exists()
    assert path.read_text(encoding="utf-8").lstrip().startswith("<svg")
    assert not fxicons.get_pixmap(name, library=library, dpr=1.0).isNull()


def test_an_icon_another_process_wrote_first_is_used(qapp, monkeypatch):
    import os

    def raced(_part, target):
        # The other process won, and Windows locks its file.
        Path(target).write_text("<svg/>", encoding="utf-8")
        raise PermissionError("held open by another process")

    monkeypatch.setattr(os, "replace", raced)

    path = Path(fxicons._extracted(
        str(fxconstants.ICONS_ROOT / "material.zip"), "svg/add/round.svg"
    ))

    assert path.read_text(encoding="utf-8") == "<svg/>"
    assert not list(path.parent.glob("*.part"))


def test_a_found_icon_is_not_looked_for_again(qapp, monkeypatch):
    import os

    fxicons.get_icon("star")
    found = {
        fxicons.get_icon_path("star"),
        fxicons.get_icon_path("add", library="material"),
    }
    stats = []
    stat = os.stat
    monkeypatch.setattr(
        os, "stat", lambda *args, **kwargs: stats.append(args) or stat(
            *args, **kwargs)
    )

    fxicons.get_icon("star")
    fxicons.get_icon_path("add", library="material")

    # Only the found file is checked, once, in case it was deleted.
    assert sorted(str(args[0]) for args in stats) == sorted(found)


def test_an_icon_missing_from_the_zip_raises():
    with pytest.raises(FileNotFoundError):
        fxicons.get_icon_path("no_such_icon", library="material")
