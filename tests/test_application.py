"""Tests for `fxgui.fxwidgets.FXApplication` inside a host application.

Regression: constructing FXApplication while another QApplication exists
(the situation inside Houdini/Maya/Nuke) raised RuntimeError, making the
library unusable in the DCCs it targets.
"""

# Third-party
from qtpy.QtWidgets import QApplication

# Internal
from fxgui.fxwidgets import FXApplication


def test_fxapplication_returns_host_application(qapp):
    """With a foreign QApplication running (pytest-qt's), FXApplication()
    must return it untouched instead of raising RuntimeError."""
    host_stylesheet = qapp.styleSheet()

    app = FXApplication()

    assert app is qapp
    # The host application must not be re-styled
    assert qapp.styleSheet() == host_stylesheet


def test_fxapplication_instance_classmethod(qapp):
    assert FXApplication.instance() is QApplication.instance()


def test_fxapplication_is_themed_root(qtbot):
    """FXApplication's stylesheet follows apply_theme(name) with no
    per-app signal connection."""
    from qtpy.QtWidgets import QApplication

    from fxgui import fxstyle

    app = QApplication.instance()
    fxstyle._themed_roots.add(app)  # simulate FXApplication registration
    try:
        fxstyle.apply_theme("light")
        light_sheet = app.styleSheet()
        fxstyle.apply_theme("dark")
        assert app.styleSheet() != light_sheet
    finally:
        app.setStyleSheet("")  # clean up for other tests


def test_fxapplication_keeps_on_theme_changed_override_point(qapp):
    """`_on_theme_changed` predates the themed-root registry and stays as
    a subclass override point: subclasses that call ``super()`` must not
    hit AttributeError.

    Note:
        Only the method's existence and super()-safety are covered here.
        FXApplication cannot be instantiated under the test suite's
        foreign QApplication, so the ``__init__`` connection itself is not
        exercised; that `theme_changed` connections fire on apply_theme is
        covered by tests/test_fxstyle_colors_api.py.
    """
    assert callable(FXApplication._on_theme_changed)
    # A subclass override calling super() must be a safe no-op.
    assert FXApplication._on_theme_changed(qapp, "dark") is None


def test_fxapplication_constructs_with_no_arguments():
    """`FXApplication()` with no argv must work on every binding.

    PyQt's QApplication requires argv where PySide defaults it, so the
    documented no-argument construction raised TypeError under PyQt5/PyQt6.
    This runs in a subprocess because the in-process QApplication is owned
    by pytest-qt, which makes __init__ short-circuit and hides the bug.
    """
    import subprocess
    import sys

    code = (
        "import os;"
        "os.environ['QT_QPA_PLATFORM']='offscreen';"
        "from fxgui.fxwidgets import FXApplication;"
        "app=FXApplication();"
        "assert app.styleSheet(), 'themed root not styled';"
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"FXApplication() failed:\nstdout={result.stdout}\n"
        f"stderr={result.stderr}"
    )
    assert "ok" in result.stdout
