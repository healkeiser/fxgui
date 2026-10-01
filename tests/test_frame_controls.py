"""The splitter mark and the flat icon button, as a caller opts in."""

# Built-in
import json
import os
import subprocess
import sys

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect, Qt
from qtpy.QtGui import QColor, QPixmap
from qtpy.QtWidgets import (
    QApplication,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle

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


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("orientation", ORIENTATIONS)
def test_the_mark_is_five_dots_centred_in_the_gap(qtbot, orientation, theme):
    host, splitter = _splitter(qtbot, orientation, theme)
    image = _handle_image(host, splitter)
    box, count = _mark(image, _color("frame"))

    assert box is not None, "no mark drawn"
    assert count == 5 * 2 * 2, "five 2 px dots, drawn once"
    assert {image.pixelColor(x, y).name()
            for x in range(box.left(), box.right() + 1)
            for y in range(box.top(), box.bottom() + 1)} == {
        _color("splitter_mark"), _color("frame")}
    across = orientation == Qt.Vertical
    length = box.width() if across else box.height()
    assert length == 18
    # Centred both ways: equal room on each side of the mark.
    assert box.left() == image.width() - 1 - box.right()
    assert abs(box.top() - (image.height() - 1 - box.bottom())) <= 1


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
splitter.setHandleWidth(6)
fxstyle.mark_as_frame(splitter)
QVBoxLayout(host).addWidget(splitter)
host.resize(300, 200)
host.show()
for _ in range(5):
    app.processEvents()
image = splitter.handle(1).grab().toImage()
frame = fxstyle.colors().frame.lower()
ink = [(x, y) for x in range(image.width()) for y in range(image.height())
       if image.pixelColor(x, y).name() != frame]
xs, ys = [p[0] for p in ink], [p[1] for p in ink]
print(json.dumps({"size": [image.width(), image.height()],
                  "box": [min(xs), min(ys), max(xs), max(ys)],
                  "count": len(ink)}))
"""


@pytest.mark.parametrize("scale", ["1", "1.5", "2"])
@pytest.mark.parametrize("orientation", ["h", "v"])
def test_the_mark_is_exact_in_device_pixels_on_a_scaled_screen(
    tmp_path, orientation, scale
):
    """On a real scaled screen, not a pixmap: QT_SCALE_FACTOR in its own
    process, since a process has one scale."""
    env = dict(os.environ, QT_SCALE_FACTOR=scale, QT_QPA_PLATFORM="offscreen",
               APPDATA=str(tmp_path), LOCALAPPDATA=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-c", _SCREEN_PROBE, orientation],
        env=env, capture_output=True, text=True, timeout=60, check=True)
    probe = json.loads(result.stdout.strip().splitlines()[-1])
    ratio = float(scale)
    dot = round(2 * ratio)
    width, height = probe["size"]
    left, top, right, bottom = probe["box"]
    across = orientation == "v"
    run, thick = (right - left + 1, bottom - top + 1) if across else (
        bottom - top + 1, right - left + 1)
    side = height if across else width

    assert side == round(6 * ratio), "the handle keeps its width"
    assert probe["count"] == 5 * dot * dot, "five whole dots, drawn once"
    assert thick == dot
    assert run == 9 * dot
    near, far = (top, height - 1 - bottom) if across else (
        left, width - 1 - right)
    assert abs(near - far) <= 1, "centred across the gap"


def test_a_handle_added_after_marking_gets_the_mark(qtbot):
    host, splitter = _splitter(qtbot, Qt.Horizontal)
    splitter.addWidget(QWidget())
    qtbot.wait(10)
    handle = splitter.handle(2)
    pixmap = QPixmap(handle.size())
    handle.render(pixmap)
    box, count = _mark(pixmap.toImage(), _color("frame"))

    assert count == 5 * 2 * 2


def test_marking_writes_no_file(qtbot, tmp_path, monkeypatch):
    import tempfile

    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp))
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    host, splitter = _splitter(qtbot, Qt.Horizontal)
    _handle_image(host, splitter)

    # The sheet's own tinted icons are the only files a theme writes.
    written = [
        path for path in temp.rglob("*")
        if path.is_file() and path.parent.name != "sheet_icons"
    ]
    assert written == []
    assert "splitter_mark" not in fxstyle._build_stylesheet()


def test_the_mark_follows_a_theme_switch(qtbot):
    host, splitter = _splitter(qtbot, Qt.Horizontal)
    fxstyle.apply_theme("github_light")
    qtbot.wait(10)
    image = _handle_image(host, splitter)
    colors = {image.pixelColor(x, y).name()
              for x in range(image.width()) for y in range(image.height())}

    assert colors == {_color("frame"), _color("splitter_mark")}


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
    colors = {image.pixelColor(x, y).name()
              for x in range(image.width()) for y in range(image.height())}

    assert _color("frame") not in colors


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
    fxicons.set_icon(button, "arrow_back")
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
    # From off the button: the cursor stays where the last test left it.
    qtbot.mouseMove(window, QPoint(1, 1))
    qtbot.mouseMove(button, button.rect().center())
    qtbot.wait(20)

    assert _at(window, button, 2, 2) == _color("state_hover")


@pytest.mark.parametrize("theme", THEMES)
def test_a_pressed_flat_button_fills(qtbot, qapp, theme):
    window, button = _flat(qtbot, theme, on_frame=True)
    button.setDown(True)
    qapp.processEvents()

    assert _at(window, button, 2, 2) == _color("state_pressed")


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
        box, _count = _mark(_handle_image(host, splitter), _color("frame"))
        assert box is not None, f"no mark on {splitter.orientation()}"


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
