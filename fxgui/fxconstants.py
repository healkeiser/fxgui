"""Paths inside the `fxgui` package, stated once for every module."""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from pathlib import Path


PACKAGE_ROOT: Path = Path(__file__).parent
ICONS_ROOT: Path = PACKAGE_ROOT / "icons"
IMAGES_ROOT: Path = PACKAGE_ROOT / "images"
FAVICON_LIGHT: Path = ICONS_ROOT / "favicon_light.png"
