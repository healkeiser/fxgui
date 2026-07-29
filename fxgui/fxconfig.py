"""Configuration and settings management for `fxgui`.

This module provides persistent storage for application settings using
QSettings with INI format. Settings are stored in platform-appropriate
locations:
    - Windows: %APPDATA%/fxgui/settings.ini
    - Unix/macOS: ~/.fxgui/settings.ini

Functions:
    get_settings: Get the QSettings instance for fxgui.
    get_config_dir: Get the configuration directory path.
    get_value: Get a setting value.
    set_value: Set a setting value.

Examples:
    Getting and setting values:

    >>> from fxgui import fxconfig
    >>> fxconfig.set_value("theme/current", "dracula")
    >>> theme = fxconfig.get_value("theme/current", "dark")
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### Imports

# Built-in
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Third-party
from qtpy.QtCore import QSettings


###### Public API

__all__ = [
    "get_application_name",
    "get_config_dir",
    "get_settings",
    "get_value",
    "set_application_name",
    "set_value",
    "SETTINGS_FILE",
]


###### Constants

_DEFAULT_APP_NAME = "fxgui"
_APP_NAME = _DEFAULT_APP_NAME


def _get_config_dir() -> Path:
    """Get the platform-appropriate configuration directory.

    Returns:
        Path to the configuration directory:
        - Windows: %APPDATA%/fxgui
        - Unix/macOS: ~/.fxgui
    """
    if sys.platform == "win32":
        # Use APPDATA on Windows
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / _APP_NAME
        # Fallback to user home
        return Path.home() / _APP_NAME
    else:
        # Use hidden directory in home on Unix/macOS
        return Path.home() / f".{_APP_NAME}"


# Configuration directory and settings file
CONFIG_DIR = _get_config_dir()
SETTINGS_FILE = CONFIG_DIR / "settings.ini"


###### Private Helpers

_settings_instance: Optional[QSettings] = None


def _ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


###### Public Functions


def set_application_name(name: str) -> None:
    """Scope fxgui settings (including the persisted theme) to an application.

    By default every tool built on fxgui shares one settings file, so e.g.
    changing the theme in one tool changes it for all of them. Calling this
    early in your application's startup isolates its settings in its own
    file:

    - Windows: ``%APPDATA%/<name>/settings.ini``
    - Unix/macOS: ``~/.<name>/settings.ini``

    Args:
        name: The application name to scope settings under. Must be a
            non-empty, filesystem-safe string.

    Raises:
        ValueError: If the name is empty or contains path separators.

    Examples:
        >>> from fxgui import fxconfig
        >>> fxconfig.set_application_name("my_studio_tool")
    """
    global _APP_NAME, CONFIG_DIR, SETTINGS_FILE, _settings_instance

    if not name or not name.strip():
        raise ValueError("Application name must be a non-empty string.")
    if any(sep in name for sep in ("/", "\\", "..")):
        raise ValueError(
            f"Application name '{name}' must not contain path separators."
        )

    _APP_NAME = name.strip()
    CONFIG_DIR = _get_config_dir()
    SETTINGS_FILE = CONFIG_DIR / "settings.ini"
    _settings_instance = None  # Recreated lazily against the new file


def get_application_name() -> str:
    """Return the application name settings are currently scoped under.

    Returns:
        The current application name ("fxgui" unless changed via
        `set_application_name()`).
    """
    return _APP_NAME


def get_config_dir() -> Path:
    """Get the configuration directory path.

    The directory is created if it doesn't exist.

    Returns:
        Path to the configuration directory.

    Examples:
        >>> config_dir = fxconfig.get_config_dir()
        >>> print(config_dir)  # C:/Users/user/AppData/Roaming/fxgui (Windows)
    """
    _ensure_config_dir()
    return CONFIG_DIR


def get_settings() -> QSettings:
    """Get the QSettings instance for fxgui.

    Settings are stored in an INI file at the platform-appropriate location.
    The instance is cached for reuse.

    Returns:
        QSettings instance configured for fxgui using INI format.

    Examples:
        >>> settings = fxconfig.get_settings()
        >>> settings.setValue("my/key", "my_value")
        >>> settings.sync()
    """
    global _settings_instance

    if _settings_instance is None:
        _ensure_config_dir()
        _settings_instance = QSettings(str(SETTINGS_FILE), QSettings.IniFormat)

    return _settings_instance


def get_value(key: str, default: Any = None) -> Any:
    """Get a setting value.

    Args:
        key: The setting key (e.g., "theme/current").
        default: Default value if the key doesn't exist.

    Returns:
        The setting value, or the default if not found.

    Examples:
        >>> theme = fxconfig.get_value("theme/current", "dark")
    """
    settings = get_settings()
    return settings.value(key, default)


def set_value(key: str, value: Any) -> None:
    """Set a setting value.

    The value is immediately synced to disk.

    Args:
        key: The setting key (e.g., "theme/current").
        value: The value to store.

    Examples:
        >>> fxconfig.set_value("theme/current", "dracula")
    """
    settings = get_settings()
    settings.setValue(key, value)
    settings.sync()
