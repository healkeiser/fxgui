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


def test_an_icon_missing_from_the_zip_raises():
    with pytest.raises(FileNotFoundError):
        fxicons.get_icon_path("no_such_icon", library="material")
