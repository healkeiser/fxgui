"""The docking extra stays optional: fxgui imports without QtAds."""

# Built-in
import subprocess
import sys


def test_importing_fxgui_leaves_qtads_unloaded():
    probe = (
        "import sys, fxgui, fxgui.fxwidgets; "
        "assert 'PySide6QtAds' not in sys.modules"
    )
    done = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True,
        timeout=120, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
