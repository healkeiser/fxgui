"""Shared pytest configuration for the fxgui test suite.

Forces Qt's offscreen platform so tests run headless (CI, SSH, no display).
Must happen before any Qt binding is imported, hence this lives in conftest.

pytest-qt provides the `qapp` and `qtbot` fixtures used by the tests.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_fxgui_state(tmp_path, monkeypatch):
    """Isolate persistent and cached fxgui state per test.

    - Redirects fxconfig's settings file to a temp directory so tests never
      touch the user's real ``%APPDATA%/fxgui/settings.ini`` (apply_theme
      persists the theme).
    - Resets fxstyle's module-level theme caches afterwards so theme changes
      made by one test cannot leak into the next.
    """
    from fxgui import fxconfig, fxstyle

    monkeypatch.setattr(fxconfig, "CONFIG_DIR", tmp_path / "fxgui")
    monkeypatch.setattr(
        fxconfig, "SETTINGS_FILE", tmp_path / "fxgui" / "settings.ini"
    )
    monkeypatch.setattr(fxconfig, "_settings_instance", None)

    yield

    fxstyle._theme = None
    fxstyle._default_theme = fxstyle._DEFAULT_THEME
    fxstyle._theme_namespace = None
    fxstyle._standard_icon_map = None
    fxstyle._widget_fragments.clear()
    fxstyle._themed_roots = type(fxstyle._themed_roots)()
