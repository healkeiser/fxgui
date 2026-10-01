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

    - Points user-scope INI settings at a temp directory so tests never
      touch the user's real ``%APPDATA%/fxgui/settings.ini`` (apply_theme
      persists the theme).
    - Starts every test on the dark theme with the pointer off every
      window, and resets fxstyle's caches afterwards, so no test leaks a
      theme or a hover into the next.
    """
    import tempfile

    from fxgui import fxconfig, fxstyle

    # Anything written to the temp folder lands in this test's own.
    temp = tmp_path / "tmp"
    temp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    from qtpy.QtCore import QSettings

    # Every user-scope INI file, fxconfig's included, lands in this test's
    # own folder; the previous test's QSettings is dropped first.
    QSettings.setPath(
        QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings")
    )
    monkeypatch.setattr(fxconfig, "_APP_NAME", "fxgui")
    monkeypatch.setattr(fxconfig, "_settings_instance", None)
    # Widget modules register their fragments at import; keep those.
    fragments = dict(fxstyle._widget_fragments)
    # Every test starts on the dark theme, with the pointer off every window.
    fxstyle._theme = fxstyle._DEFAULT_THEME
    fxstyle._invalidate_theme_namespace()
    from qtpy.QtWidgets import QApplication

    if QApplication.instance() is not None:
        from qtpy.QtGui import QCursor

        QCursor.setPos(-1000, -1000)

    yield

    # A popup left open grabs the mouse from every later test.
    app = QApplication.instance()
    if app is not None:
        for widget in app.topLevelWidgets():
            if widget.isVisible():
                widget.close()
        # A deleteLater() pending from this test runs now, not in the next.
        from qtpy.QtCore import QEvent

        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    fxstyle._colors = None
    fxstyle._color_file = None
    fxstyle._theme = None
    fxstyle._default_theme = fxstyle._DEFAULT_THEME
    fxstyle._theme_namespace = None
    fxstyle._standard_icon_map = None
    fxstyle._widget_fragments.clear()
    fxstyle._widget_fragments.update(fragments)
    fxstyle._themed_roots = type(fxstyle._themed_roots)()
