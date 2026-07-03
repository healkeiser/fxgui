"""Shared pytest configuration for the fxgui test suite.

Forces Qt's offscreen platform so tests run headless (CI, SSH, no display).
Must happen before any Qt binding is imported, hence this lives in conftest.

pytest-qt provides the `qapp` and `qtbot` fixtures used by the tests.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
