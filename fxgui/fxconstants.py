"""Constants and path definitions for the `fxgui` package.

This module provides centralized access to package-level constants,
file paths, and directory locations used throughout the fxgui framework.

Constants:
    PACKAGE_ROOT: Path to the fxgui package directory.
    ICONS_ROOT: Path to the icons directory.
    FAVICON_LIGHT: Path to the light theme favicon.
    FAVICON_DARK: Path to the dark theme favicon.

Examples:
    Accessing icon paths:

    >>> from fxgui.fxconstants import ICONS_ROOT
    >>> material_icons = ICONS_ROOT / "material"
    >>> custom_icon = ICONS_ROOT / "custom" / "my_icon.svg"
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from pathlib import Path


# Package paths
PACKAGE_ROOT: Path = Path(__file__).parent
"""Path to the fxgui package root directory."""

ICONS_ROOT: Path = PACKAGE_ROOT / "icons"
"""Path to the icons directory containing all icon libraries."""

# Favicon paths
FAVICON_LIGHT: Path = ICONS_ROOT / "favicon_light.png"
"""Path to the light-themed favicon image."""

FAVICON_DARK: Path = ICONS_ROOT / "favicon_dark.png"
"""Path to the dark-themed favicon image."""
