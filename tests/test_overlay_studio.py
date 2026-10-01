"""An overlay holding one theme and the fonts equals a whole copied file."""

from pathlib import Path

import pytest
import yaml

from fxgui import fxstyle

_OVERLAY = Path(__file__).parent / "data" / "studio_overlay.yaml"


@pytest.fixture
def fresh_colors(monkeypatch):
    """Load colour files from scratch; the originals come back after."""
    monkeypatch.setattr(fxstyle, "_colors", None)
    monkeypatch.setattr(fxstyle, "_color_file", None)


def _full_copy(tmp_path) -> Path:
    """Return fxgui's file with the brand fonts and theme written into it."""
    overlay = yaml.safe_load(_OVERLAY.read_text(encoding="utf-8"))
    text = fxstyle.DEFAULT_COLOR_FILE.read_text(encoding="utf-8")
    fonts = text.index("\nfonts:\n")
    end = text.index("\n\n", fonts + 1)
    block = yaml.safe_dump({"fonts": overlay["fonts"]}, sort_keys=False)
    theme = yaml.safe_dump(overlay["themes"]["lotchi"], sort_keys=False)
    text = (
        text[:fonts + 1] + block + text[end:].rstrip("\n")
        + "\n  lotchi:\n    <<: *dark\n"
        + "".join(f"    {line}\n" for line in theme.splitlines())
    )
    path = tmp_path / "full_copy.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _resolved():
    """Return the lotchi colours and every theme's font roles."""
    fxstyle.apply_theme("lotchi")
    colours = fxstyle.get_theme_colors()
    fonts = {
        theme: fxstyle._font_config(theme)
        for theme in fxstyle.get_available_themes()
    }
    return colours, fonts


def test_the_overlay_resolves_like_the_whole_copy(qapp, tmp_path,
                                                  fresh_colors):
    fxstyle.set_color_file(_full_copy(tmp_path))
    copied = _resolved()
    assert copied[0]["accent_primary"] == "#FF4200"
    assert copied[1]["nord"]["body"] == ["Inter"]

    fxstyle.set_color_file(fxstyle.DEFAULT_COLOR_FILE)
    fxstyle.overlay_color_file(_OVERLAY)
    overlaid = _resolved()

    assert overlaid[0] == copied[0]
    assert overlaid[1] == copied[1]
    assert overlaid[1]["nord"]["body"] == ["Inter"], (
        "the brand faces hold under a theme the artist picks")
