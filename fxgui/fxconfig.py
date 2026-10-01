"""Configuration and settings management for `fxgui`.

One INI file per application, where `QSettings` puts a user-scope one:
    - Windows: %APPDATA%/<name>/settings.ini
    - Unix/macOS: ~/.config/<name>/settings.ini

Examples:
    >>> from fxgui import fxconfig
    >>> fxconfig.set_value("theme/current", "dracula")
    >>> theme = fxconfig.get_value("theme/current", "dark")
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from typing import Any, Optional

# Third-party
from qtpy.QtCore import QSettings


__all__ = ["get_value", "set_application_name", "set_value"]

_APP_NAME = "fxgui"
_settings_instance: Optional[QSettings] = None


def set_application_name(name: str) -> None:
    """Scope fxgui settings (including the persisted theme) to an application.

    By default every tool built on fxgui shares one settings file, so a theme
    changed in one tool changes it for all. Call this early at startup.

    Args:
        name: The application name, the settings file's folder.

    Raises:
        ValueError: If the name is empty or contains path separators.

    Examples:
        >>> fxconfig.set_application_name("my_studio_tool")
    """
    global _APP_NAME, _settings_instance

    if not name or not name.strip():
        raise ValueError("Application name must be a non-empty string.")
    if any(sep in name for sep in ("/", "\\", "..")):
        raise ValueError(
            f"Application name '{name}' must not contain path separators."
        )
    _APP_NAME = name.strip()
    _settings_instance = None


def _settings() -> QSettings:
    """Return the cached QSettings on this application's INI file."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = QSettings(
            QSettings.IniFormat, QSettings.UserScope, _APP_NAME, "settings"
        )
    return _settings_instance


def get_value(key: str, default: Any = None) -> Any:
    """Get a setting value.

    Args:
        key: The setting key (e.g., "theme/current").
        default: Default value if the key doesn't exist. A bool, int or
            float default also names the type the value is read as.

    Returns:
        The setting value, or the default if not found.

    Examples:
        >>> theme = fxconfig.get_value("theme/current", "dark")
    """
    # An INI file holds strings; a typed default names the type to read.
    if isinstance(default, (bool, int, float)):
        return _settings().value(key, default, type=type(default))
    return _settings().value(key, default)


def set_value(key: str, value: Any) -> None:
    """Set a setting value.

    The value is immediately synced to disk.

    Args:
        key: The setting key (e.g., "theme/current").
        value: The value to store.

    Examples:
        >>> fxconfig.set_value("theme/current", "dracula")
    """
    settings = _settings()
    settings.setValue(key, value)
    settings.sync()
