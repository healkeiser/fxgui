"""Qt's HLine and VLine frames draw a flat 1 px rule in the theme's border.

Qt's own line is a two-tone bevel that reads as a groove on a dark panel.
"""

# Third-party
import pytest
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle


def _line(qtbot, shape):
    window = QWidget()
    fxstyle.register_themed_root(window)
    qtbot.addWidget(window)
    box = QVBoxLayout(window) if shape == QFrame.HLine else QHBoxLayout(window)
    line = QFrame()
    line.setFrameShape(shape)
    box.addWidget(line)
    window.resize(200, 200)
    window.show()
    qtbot.waitExposed(window)
    return window, line


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("shape", [QFrame.HLine, QFrame.VLine])
def test_a_line_is_one_flat_pixel_of_the_border(qtbot, shape, theme):
    fxstyle.apply_theme(theme)
    _window, line = _line(qtbot, shape)

    thickness = line.height() if shape == QFrame.HLine else line.width()
    image = line.grab().toImage()
    colours = {
        image.pixelColor(x, y).name()
        for x in range(image.width())
        for y in range(image.height())
    }

    assert thickness == 1
    assert colours == {QColor(fxstyle.colors().border).name()}
