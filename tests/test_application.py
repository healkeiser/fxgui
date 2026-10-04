"""Tests for `fxgui.fxwidgets.FXApplication` inside a host application.

Regression: constructing FXApplication while another QApplication exists
(the situation inside Houdini/Maya/Nuke) raised RuntimeError, making the
library unusable in the DCCs it targets.
"""

# Third-party

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


def _run(code):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "ok" in result.stdout


def test_instance_is_qts_own_and_answers_none_with_no_application():
    _run(
        "import os;"
        "os.environ['QT_QPA_PLATFORM']='offscreen';"
        "from fxgui.fxwidgets import FXApplication;"
        "assert FXApplication.instance() is None, 'built one';"
        "app=FXApplication();"
        "assert FXApplication.instance() is app;"
        "print('ok')"
    )


def test_a_deleted_application_is_not_handed_back():
    _run(
        "import os;"
        "os.environ['QT_QPA_PLATFORM']='offscreen';"
        "import shiboken6;"
        "from qtpy.QtWidgets import QApplication;"
        "from fxgui.fxwidgets import FXApplication;"
        "app=FXApplication();"
        "shiboken6.delete(app);"
        "assert QApplication.instance() is None;"
        "fresh=FXApplication.__new__(FXApplication);"
        "assert fresh is not app, 'handed back a dead one';"
        "print('ok')"
    )


def test_a_second_application_is_themed():
    _run(
        "import os;"
        "os.environ['QT_QPA_PLATFORM']='offscreen';"
        "import shiboken6;"
        "from fxgui.fxwidgets import FXApplication;"
        "shiboken6.delete(FXApplication());"
        "assert FXApplication().styleSheet();"
        "print('ok')"
    )
