"""`import fxgui` refuses a PySide6 older than 6.5, saying which it found."""

# Built-in
import subprocess
import sys

# Third-party
import pytest
import qtpy


@pytest.mark.skipif(not qtpy.PYSIDE6, reason="the floor is PySide6's")
def test_importing_fxgui_on_pyside6_6_4_raises_a_clear_error():
    probe = "import qtpy; qtpy.PYSIDE_VERSION = '6.4.3'; import fxgui"
    done = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True,
        timeout=120, check=False)

    assert done.returncode != 0
    assert "ImportError: fxgui needs PySide6 6.5 or newer" in done.stderr
    assert "6.4.3" in done.stderr
