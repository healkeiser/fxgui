"""Constants module for `fxgui` package."""

# Built-in
from pathlib import Path

# Icon paths
PACKAGE_ROOT: Path = Path(__file__).parent
ICONS_ROOT: Path = PACKAGE_ROOT / "icons"

# Specific icon files
FAVICON_LIGHT: Path = ICONS_ROOT / "favicon_light.png"
FAVICON_DARK: Path = ICONS_ROOT / "favicon_dark.png"
