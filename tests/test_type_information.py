"""fxgui ships its type information (PEP 561), and a type checker reads it."""

# Built-in
import os
import re
import subprocess
import sys
from pathlib import Path

# Third-party
import pytest

# Internal
import fxgui

ROOT = Path(fxgui.__file__).resolve().parent.parent


def _mypy(tmp_path: Path, source: str) -> str:
    """Return mypy's report on `source`, with fxgui seen as installed."""
    pytest.importorskip("mypy")
    consumer = tmp_path / "consumer.py"
    consumer.write_text(source)
    # On PYTHONPATH fxgui counts as installed, so mypy reads it only through
    # py.typed; run elsewhere, or mypy reads fxgui/ as plain source.
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    result = subprocess.run(
        [
            sys.executable, "-m", "mypy", "--no-incremental",
            "--python-executable", sys.executable, str(consumer),
        ],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    return result.stdout + result.stderr


def test_the_package_carries_the_py_typed_marker():
    assert (ROOT / "fxgui" / "py.typed").is_file()


def test_a_type_checker_sees_fxguis_own_types(tmp_path):
    report = _mypy(
        tmp_path,
        "from fxgui import fxstyle\n"
        "from fxgui.fxwidgets import FXMainWindow\n"
        "reveal_type(fxstyle.get_theme())\n"
        "reveal_type(FXMainWindow)\n",
    )
    assert "import-untyped" not in report, report
    assert 'Revealed type is "Any"' not in report, report
    assert report.count("Revealed type is") == 2, report


def test_a_misspelled_fxgui_attribute_is_a_type_error(tmp_path):
    report = _mypy(
        tmp_path,
        "import fxgui\n"
        "reveal_type(fxgui.__version__)\n"
        "fxgui.no_such_name\n",
    )
    assert re.search(r'Revealed type is "(builtins\.)?str"', report), report
    assert 'has no attribute "no_such_name"' in report, report
