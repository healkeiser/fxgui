"""A theme switch paints the gallery exactly as a fresh build in that theme.

One pair each way: every bug this caught was one mechanism, not one theme.
"""

# Built-in
import json
import os
import subprocess
import sys

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint
from qtpy.QtGui import QHelpEvent, QImage
from qtpy.QtWidgets import (
    QApplication,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolTip,
)

# Internal
from fxgui import examples, fxstyle, fxwidgets

_PAIRS = (("light", "dark"), ("dark", "light"))


def _image(widget) -> QImage:
    return widget.grab().toImage().convertToFormat(QImage.Format_ARGB32)


def _pages(window) -> list:
    """Return each whole page, scrolled-off part too, then the window."""
    app = QApplication.instance()
    tabs = window.findChild(QTabWidget)
    images = []
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        app.processEvents()
        page = tabs.widget(index)
        images.append(
            _image(page.widget() if isinstance(page, QScrollArea) else page)
        )
    # The chrome round the pages, the status bar and its message.
    images.append(_image(window))
    return images


def _tooltip(window) -> list:
    """Return the native rich tooltip of the gallery's `apply_tip` button."""
    app = QApplication.instance()
    button = next(
        button
        for button in window.findChildren(QPushButton)
        if button.text() == "Native rich tooltip"
    )
    point = QPoint(2, 2)
    app.sendEvent(
        button, QHelpEvent(QEvent.ToolTip, point, button.mapToGlobal(point))
    )
    app.processEvents()
    label = next(
        widget
        for widget in app.topLevelWidgets()
        if widget.inherits("QTipLabel") and widget.isVisible()
    )
    image = _image(label)
    QToolTip.hideText()
    app.processEvents()
    return image


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
        # A running spinner's angle is the time it has run: hold it still.
        for spinner in window.findChildren(fxwidgets.FXLoadingSpinner):
            spinner.stop()
            spinner._angle = 0
        window.resize(720, 540)
        window.show()
        # A message shown across the switch keeps its words and recolours.
        window.statusBar().showMessage(
            "Render queued", fxwidgets.WARNING, duration=600, time=False
        )
        app.processEvents()
        if build_in == before:
            _pages(window)
            fxstyle.apply_theme(after)
            app.processEvents()
        tabs = window.findChild(QTabWidget)
        titles = [tabs.tabText(i) for i in range(tabs.count())]
        titles += ["Window", "Tooltip"]
        pages.append(_pages(window) + [_tooltip(window)])
        window.close()
        window.deleteLater()
        # Outside an event loop a deleteLater waits forever, and every
        # later switch restyles the windows left behind.
        app.sendPostedEvents(None, QEvent.DeferredDelete)
    counts = {title: _count(a, b) for title, a, b in zip(titles, *pages)}
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
print(json.dumps(switch.differences(*switch._PAIRS[0])))
"""


def test_a_switch_in_an_fxapplication_equals_a_fresh_build():
    code = _APP_MODE.format(tests=os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {}
