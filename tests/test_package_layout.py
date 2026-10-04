"""The package states each path, version and constant once."""

# Built-in
from importlib.metadata import PackageNotFoundError, version

# Internal
import fxgui
from fxgui import fxconstants


def test_one_images_root_holds_the_package_images():
    assert fxconstants.IMAGES_ROOT == fxconstants.PACKAGE_ROOT / "images"
    assert (fxconstants.IMAGES_ROOT / "missing_image.png").exists()
    assert fxconstants.FAVICON_LIGHT.exists()
    assert not hasattr(fxconstants, "FAVICON_DARK")


def test_the_version_is_the_installed_distributions():
    try:
        expected = version("fxgui")
    except PackageNotFoundError:
        expected = "0.0.0.dev"
    assert fxgui.__version__ == expected


def test_the_severity_levels_live_with_the_severities():
    from fxgui.fxwidgets import _severity

    for name, level in (
        ("CRITICAL", 0), ("ERROR", 1), ("WARNING", 2),
        ("SUCCESS", 3), ("INFO", 4), ("DEBUG", 5),
    ):
        assert vars(_severity)[name] == level, name
        assert _severity.severity(level) is _severity.SEVERITIES[level]


def test_importing_fxgui_on_qt5_says_it_needs_qt6():
    import subprocess
    import sys

    code = (
        "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
        "import qtpy; qtpy.QT6 = False; qtpy.QT5 = True\n"
        "try:\n"
        "    import fxgui\n"
        "except ImportError as error:\n"
        "    print(error)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        timeout=120,
    )
    assert "Qt 6" in result.stdout, result.stdout + result.stderr


def test_importing_fxgui_defers_what_only_some_callers_need():
    import subprocess
    import sys

    code = (
        "import os, sys; os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
        "import fxgui\n"
        "print([m for m in ('yaml', 'importlib.metadata', 'markdown')"
        " if m in sys.modules])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        timeout=120,
    )
    assert result.stdout.strip() == "[]", result.stdout + result.stderr
