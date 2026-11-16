"""The splitter handle's lit line and the flat icon button."""

# Built-in
import json
import os
import subprocess
import sys

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint, QRect, Qt
from qtpy.QtGui import QColor, QPixmap
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle

from _helpers import hover, isolated, near

THEMES = fxstyle.get_available_themes()
ORIENTATIONS = [Qt.Horizontal, Qt.Vertical]
GAP = 6


def _color(role):
    return QColor(getattr(fxstyle.colors(), role)).name()


def _splitter(qtbot, orientation, theme="dark", gap=GAP):
    fxstyle.apply_theme(theme)
    host = QWidget()
    fxstyle.register_themed_root(host)
    splitter = QSplitter(orientation)
    splitter.addWidget(QWidget())
    splitter.addWidget(QWidget())
    splitter.setHandleWidth(gap)
    fxstyle.mark_as_frame(splitter)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(splitter)
    host.resize(300, 200)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host, splitter


def _handle_image(host, splitter, ratio=1.0):
    handle = splitter.handle(1)
    pixmap = QPixmap(handle.size() * ratio)
    pixmap.setDevicePixelRatio(ratio)
    handle.render(pixmap)
    return pixmap.toImage()


def _mark(image, frame):
    """Return the bounding box and pixel count of what is not the frame."""
    xs, ys = [], []
    for x in range(image.width()):
        for y in range(image.height()):
            if image.pixelColor(x, y).name() != frame:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None, 0
    return QRect(min(xs), min(ys), max(xs) - min(xs) + 1,
                 max(ys) - min(ys) + 1), len(xs)


@pytest.mark.parametrize("gap", [6, 9])
@pytest.mark.parametrize("orientation", ORIENTATIONS)
def test_a_marked_splitter_keeps_the_handle_width_it_was_given(
    qtbot, orientation, gap
):
    host, splitter = _splitter(qtbot, orientation, gap=gap)
    first = splitter.widget(0).geometry()
    second = splitter.widget(1).geometry()

    if orientation == Qt.Horizontal:
        assert splitter.handle(1).width() == gap
        assert second.left() - first.right() - 1 == gap
    else:
        assert splitter.handle(1).height() == gap
        assert second.top() - first.bottom() - 1 == gap


def _lit(handle):
    """Light `handle` as the pointer does; at once, as motion is off."""
    fxstyle._SplitterMark._light(handle, True)


def _colors(image):
    return {image.pixelColor(x, y).name()
            for x in range(image.width()) for y in range(image.height())}


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("orientation", ORIENTATIONS)
def test_a_marked_handle_is_the_frame_alone_at_rest(qtbot, orientation, theme):
    host, splitter = _splitter(qtbot, orientation, theme)

    assert _colors(_handle_image(host, splitter)) == {_color("frame")}


@pytest.mark.parametrize("theme", ["dark", "github_light"])
@pytest.mark.parametrize("orientation", ORIENTATIONS)
def test_a_lit_handle_draws_a_centred_accent_line(qtbot, orientation, theme):
    host, splitter = _splitter(qtbot, orientation, theme)
    _lit(splitter.handle(1))
    image = _handle_image(host, splitter)
    box, count = _mark(image, _color("frame"))

    assert _colors(image) == {_color("frame"), _color("accent_primary")}
    across = orientation == Qt.Vertical
    length, thick = (box.width(), box.height()) if across else (
        box.height(), box.width())
    side = image.height() if across else image.width()
    # The gap's parity: 1 px in an odd gap, 2 px in an even one.
    assert thick == (1 if side % 2 else 2)
    assert length == (image.width() if across else image.height())
    assert count == length * thick, "one line, drawn once"
    # Centred across the gap: as many pixels on either side.
    near = box.top() if across else box.left()
    far = side - 1 - (box.bottom() if across else box.right())
    assert near == far


_SCREEN_PROBE = r"""
import json, sys
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QSplitter, QVBoxLayout, QWidget
from fxgui import fxstyle
app = QApplication(sys.argv)
fxstyle.apply_theme("dark")
host = QWidget()
fxstyle.register_themed_root(host)
splitter = QSplitter(Qt.Horizontal if sys.argv[1] == "h" else Qt.Vertical)
splitter.addWidget(QWidget())
splitter.addWidget(QWidget())
splitter.setHandleWidth(int(sys.argv[2]))
fxstyle.mark_as_frame(splitter)
QVBoxLayout(host).addWidget(splitter)
host.resize(300, 200)
host.show()
for _ in range(5):
    app.processEvents()
fxstyle._SplitterMark._light(splitter.handle(1), True)
image = splitter.handle(1).grab().toImage()
frame = fxstyle.colors().frame.lower()
ink = [(x, y) for x in range(image.width()) for y in range(image.height())
       if image.pixelColor(x, y).name() != frame]
xs, ys = [p[0] for p in ink], [p[1] for p in ink]
print(json.dumps({"size": [image.width(), image.height()],
                  "box": [min(xs), min(ys), max(xs), max(ys)],
                  "count": len(ink)}))
"""


@pytest.mark.parametrize("gap", [6, 8])
@pytest.mark.parametrize("scale", ["1", "1.25", "1.5", "2"])
@pytest.mark.parametrize("orientation", ["h", "v"])
def test_the_line_is_exact_in_device_pixels_on_a_scaled_screen(
    tmp_path, orientation, scale, gap
):
    """On a real scaled screen, not a pixmap: QT_SCALE_FACTOR in its own
    process, since a process has one scale."""
    env = dict(os.environ, QT_SCALE_FACTOR=scale, QT_QPA_PLATFORM="offscreen",
               APPDATA=str(tmp_path), LOCALAPPDATA=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-c", isolated(_SCREEN_PROBE), orientation, str(gap)],
        env=env, capture_output=True, text=True, timeout=60, check=True)
    probe = json.loads(result.stdout.strip().splitlines()[-1])
    ratio = float(scale)
    width, height = probe["size"]
    left, top, right, bottom = probe["box"]
    across = orientation == "v"
    run, thick = (right - left + 1, bottom - top + 1) if across else (
        bottom - top + 1, right - left + 1)
    side, length = (height, width) if across else (width, height)
    # Whole device pixels, with the gap's parity so it can centre.
    line = max(1, round(ratio))
    line += (side - line) % 2

    assert abs(side - gap * ratio) <= 1, "the handle keeps its width"
    assert thick == line, "whole device pixels"
    assert run == length, "the handle's whole length"
    assert probe["count"] == line * length, "drawn once"
    near, far = (top, height - 1 - bottom) if across else (
        left, width - 1 - right)
    assert near == far, "centred across the gap"


def test_a_handle_added_after_marking_lights(qtbot):
    host, splitter = _splitter(qtbot, Qt.Horizontal)
    splitter.addWidget(QWidget())
    qtbot.wait(10)
    handle = splitter.handle(2)
    _lit(handle)
    pixmap = QPixmap(handle.size())
    handle.render(pixmap)
    box, count = _mark(pixmap.toImage(), _color("frame"))
    thick = 1 if handle.width() % 2 else 2

    assert count == handle.height() * thick


def test_the_pointer_lights_a_handle_and_a_drag_holds_it(qtbot):
    host, splitter = _splitter(qtbot, Qt.Horizontal, gap=8)
    handle = splitter.handle(1)
    hover(qtbot, handle)

    assert handle.property("fxSplitterGlow") == 1.0
    assert handle.cursor().shape() == Qt.SplitHCursor, "the cursor stays"

    QTest.mousePress(handle, Qt.LeftButton, Qt.NoModifier,
                     handle.rect().center())
    QApplication.sendEvent(handle, QEvent(QEvent.Leave))
    assert handle.property("fxSplitterGlow") == 1.0, "held while dragged"

    QTest.mouseRelease(handle, Qt.LeftButton, Qt.NoModifier,
                       QPoint(-20, handle.height() // 2))
    assert handle.property("fxSplitterGlow") == 0.0, "dark, let go off it"
    assert _colors(_handle_image(host, splitter)) == {_color("frame")}


def test_the_line_fades_in_over_the_fast_motion(qtbot, motion):
    host, splitter = _splitter(qtbot, Qt.Horizontal)
    handle = splitter.handle(1)
    _lit(handle)
    qtbot.wait(fxstyle.MOTION_FAST // 3)
    midway = handle.property("fxSplitterGlow")

    assert 0.0 < midway < 1.0
    qtbot.waitUntil(lambda: handle.property("fxSplitterGlow") == 1.0,
                    timeout=fxstyle.MOTION_FAST * 4)


def test_marking_writes_no_file(qtbot, tmp_path, monkeypatch):
    import tempfile

    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp))
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    host, splitter = _splitter(qtbot, Qt.Horizontal)
    _handle_image(host, splitter)

    # The sheet's own tinted icons, and the icons taken out of their zip,
    # are the only files a theme writes.
    written = [
        path for path in temp.rglob("*")
        if path.is_file()
        and path.parent.name != "sheet_icons"
        and (temp / "fxgui" / "icons") not in path.parents
    ]
    assert written == []
    assert "splitter_mark" not in fxstyle._build_stylesheet()


def test_the_lit_line_follows_a_theme_switch(qtbot):
    host, splitter = _splitter(qtbot, Qt.Horizontal)
    _lit(splitter.handle(1))
    fxstyle.apply_theme("github_light")
    qtbot.wait(10)

    assert _colors(_handle_image(host, splitter)) == {
        _color("frame"), _color("accent_primary")}


def test_an_unmarked_splitter_is_untouched(qtbot):
    fxstyle.apply_theme("dark")
    host = QWidget()
    fxstyle.register_themed_root(host)
    splitter = QSplitter(Qt.Horizontal, host)
    splitter.addWidget(QWidget())
    splitter.addWidget(QWidget())
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)

    image = _handle_image(host, splitter)

    assert _color("frame") not in _colors(image)
    assert _color("accent_primary") not in _colors(image)


def test_an_unmarked_splitter_lights_an_8px_handle_under_the_pointer(qtbot):
    fxstyle.apply_theme("dark")
    host = QWidget()
    fxstyle.register_themed_root(host)
    splitter = QSplitter(Qt.Horizontal, host)
    splitter.addWidget(QWidget())
    splitter.addWidget(QWidget())
    splitter.resize(300, 200)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    handle = splitter.handle(1)
    hover(qtbot, handle)
    image = _handle_image(host, splitter)

    assert handle.width() == 8, "the hit area"
    lit = [x for x in range(image.width())
           if image.pixelColor(x, 0).name() == _color("accent_primary")]
    # 2 px in the 8 px gap: 3 pixels on either side.
    assert lit == [3, 4], "a line centred in the gap"


def _flat(qtbot, theme="dark", on_frame=False, enabled=True):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    if on_frame:
        fxstyle.mark_as_frame(window)
    layout = QVBoxLayout(window)
    sink = QPushButton("sink")
    button = QPushButton()
    button.setProperty("fxRole", "flat")
    fxicons.set_icon(button, "arrow-left")
    button.setEnabled(enabled)
    layout.addWidget(sink)
    layout.addWidget(button)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    QApplication.processEvents()
    sink.setFocus(Qt.TabFocusReason)
    QApplication.processEvents()
    return window, button


def _at(window, button, x, y):
    point = button.mapTo(window, QPoint(x, y))
    return window.grab().toImage().pixelColor(point).name()


def _edges(window, button):
    """The button's outermost pixel on each side, at mid-height/width."""
    w, h = button.width(), button.height()
    return {_at(window, button, x, y)
            for x, y in ((0, h // 2), (w - 1, h // 2), (w // 2, 0),
                         (w // 2, h - 1))}


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("on_frame", [False, True])
def test_a_flat_button_has_no_box_at_rest(qtbot, theme, on_frame):
    window, button = _flat(qtbot, theme, on_frame)
    ground = _color("frame" if on_frame else "surface")

    assert _edges(window, button) == {ground}
    assert _at(window, button, 2, 2) == ground


@pytest.mark.parametrize("theme", THEMES)
def test_a_disabled_flat_button_has_no_box(qtbot, theme):
    window, button = _flat(qtbot, theme, on_frame=True, enabled=False)

    assert _edges(window, button) == {_color("frame")}


@pytest.mark.parametrize("theme", THEMES)
def test_a_hovered_flat_button_fills(qtbot, theme):
    window, button = _flat(qtbot, theme, on_frame=True)
    hover(qtbot, button)

    # See-through: the overlay over the frame.
    overlay = QColor(fxstyle.colors().state_hover_overlay)
    expected = fxstyle.mix(_color("frame"), overlay.name(), overlay.alphaF())
    assert near(_at(window, button, fxstyle.BUTTON_RADIUS, 2), expected, 2)


@pytest.mark.parametrize("theme", THEMES)
def test_a_pressed_flat_button_fills(qtbot, qapp, theme):
    window, button = _flat(qtbot, theme, on_frame=True)
    button.setDown(True)
    qapp.processEvents()

    # See-through: the overlay over the frame.
    overlay = QColor(fxstyle.colors().state_pressed_overlay)
    expected = fxstyle.mix(_color("frame"), overlay.name(), overlay.alphaF())
    assert near(_at(window, button, fxstyle.BUTTON_RADIUS, 2), expected, 2)


@pytest.mark.parametrize("theme", THEMES)
def test_a_focused_flat_button_shows_the_accent_ring(qtbot, theme):
    window, button = _flat(qtbot, theme, on_frame=True)
    button.setFocus(Qt.TabFocusReason)
    QApplication.processEvents()

    assert button.hasFocus()
    assert _edges(window, button) == {_color("accent_primary")}


def test_a_marked_splitter_wrapped_in_another_marks_both(qtbot):
    """QtAds wraps a marked splitter in a new one when a pane docks."""
    host, inner = _splitter(qtbot, Qt.Horizontal)
    outer = QSplitter(Qt.Vertical)
    outer.addWidget(inner)
    outer.addWidget(QWidget())
    outer.setHandleWidth(GAP)
    fxstyle.mark_as_frame(outer)
    host.layout().addWidget(outer)
    qtbot.wait(10)

    for splitter in (inner, outer):
        _lit(splitter.handle(1))
        box, _count = _mark(_handle_image(host, splitter), _color("frame"))
        assert box is not None, f"no line on {splitter.orientation()}"


def test_a_theme_switch_survives_a_dropped_handle_wrapper(qtbot):
    """A splitter can hand back a handle whose wrapper PySide dropped."""
    shiboken = pytest.importorskip("shiboken6")
    _host, splitter = _splitter(qtbot, Qt.Horizontal)
    dropped = QWidget()
    shiboken.delete(dropped)
    live = splitter.handle
    splitter.handle = lambda index: dropped if index == 1 else live(index)

    with qtbot.captureExceptions() as raised:
        fxstyle.apply_theme("github_light")
        qtbot.wait(10)

    assert not raised, raised


def test_a_theme_switch_repaints_the_handles_by_itself(qtbot):
    from qtpy.QtCore import QEvent, QObject

    host, splitter = _splitter(qtbot, Qt.Horizontal)
    qtbot.wait(10)

    class Paints(QObject):
        count = 0

        def eventFilter(self, watched, event):
            if event.type() == QEvent.Paint:
                Paints.count += 1
            return False

    counter = Paints(splitter)
    splitter.handle(1).installEventFilter(counter)
    fxstyle.apply_theme("github_light")
    qtbot.waitUntil(lambda: Paints.count > 0)
