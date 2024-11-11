"""Constants module for `fxgui` package."""

# Built-in
from pathlib import Path

# Icon paths
ICONS_ROOT: Path = Path(__file__).parent / "icons"
ICONS_DCC: Path = ICONS_ROOT / "dcc"

# Specific icon files
FAVICON_LIGHT: Path = ICONS_ROOT / "favicon_light.png"
FAVICON_DARK: Path = ICONS_ROOT / "favicon_dark.png"
LOGO_LIGHT: Path = ICONS_ROOT / "fxgui_logo_light.svg"
LOGO_DARK: Path = ICONS_ROOT / "fxgui_logo_dark.svg"
