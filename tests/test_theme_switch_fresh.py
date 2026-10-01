"""A theme switch paints the gallery exactly as a fresh build in that theme."""

# Built-in
import json
import os
import subprocess
import sys

# Third-party
import pytest
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QApplication, QScrollArea, QTabWidget

# Internal
from fxgui import examples, fxstyle

_LIGHT = ("light", "github_light", "catppuccin_latte", "solarized_light")
_PAIRS = (
    [(light, "dark") for light in _LIGHT]
    + [("dark", light) for light in _LIGHT]
    + [("dark", "dracula")]
)


def _pages(window) -> list:
    app = QApplication.instance()
    tabs = window.findChild(QTabWidget)
    images = []
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        app.processEvents()
        # The window as shown, then the whole page, scrolled-off part too.
        shots = [window.grab()]
        page = tabs.widget(index)
        if isinstance(page, QScrollArea):
            shots.append(page.widget().grab())
        images.append(
            [
                shot.toImage().convertToFormat(QImage.Format_ARGB32)
                for shot in shots
            ]
        )
    return images


def _count(first: QImage, second: QImage) -> int:
    if first.size() != second.size():
        return first.width() * first.height()
    a, b = bytes(first.constBits()), bytes(second.constBits())
    line = first.bytesPerLine()
    count = 0
    for y in range(first.height()):
        row = slice(y * line, (y + 1) * line)
        if a[row] != b[row]:
            count += sum(
                first.pixel(x, y) != second.pixel(x, y)
                for x in range(first.width())
            )
    return count


def differences(before: str, after: str) -> dict:
    """Return the differing pixel count per page, switched against fresh."""
    app = QApplication.instance()
    fxstyle.apply_theme(before)
    pages = []
    # One window at a time: the one shown last is the active window, and
    # an inactive one draws its focus and selection differently.
    for build_in in (before, after):
        window = examples.build()
        window.show()
        app.processEvents()
        if build_in == before:
            _pages(window)
            fxstyle.apply_theme(after)
            app.processEvents()
        tabs = window.findChild(QTabWidget)
        titles = [tabs.tabText(i) for i in range(tabs.count())]
        pages.append(_pages(window))
        window.close()
        window.deleteLater()
        app.processEvents()
    counts = {
        title: sum(map(_count, a, b)) for title, a, b in zip(titles, *pages)
    }
    return {title: count for title, count in counts.items() if count}


@pytest.mark.parametrize("before, after", _PAIRS)
def test_a_switch_inside_a_host_equals_a_fresh_build(qapp, before, after):
    assert differences(before, after) == {}


_APP_MODE = """
import json, os, pathlib, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, {tests!r})
from fxgui import fxconfig
folder = pathlib.Path(tempfile.mkdtemp())
fxconfig.CONFIG_DIR = folder
fxconfig.SETTINGS_FILE = folder / "settings.ini"
from fxgui.fxwidgets import FXApplication
import test_theme_switch_fresh as switch
app = FXApplication()
found = {{}}
for before, after in switch._PAIRS:
    counts = switch.differences(before, after)
    if counts:
        found[before + " -> " + after] = counts
print(json.dumps(found))
"""


def test_a_switch_in_an_fxapplication_equals_a_fresh_build():
    code = _APP_MODE.format(tests=os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {}
