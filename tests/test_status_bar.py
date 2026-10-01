"""FXStatusBar paints its accent line from one state and clears its tint."""

# Third-party
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import ERROR
from fxgui.fxwidgets._status_bar import FXStatusBar


_HOSTS = []


def _bar(qtbot, cls=FXStatusBar):
    # qtbot holds widgets weakly; the host must outlive the bar.
    host = QWidget()
    _HOSTS.append(host)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addStretch()
    bar = cls()
    layout.addWidget(bar)
    fxstyle.register_themed_root(host)
    qtbot.addWidget(host)
    host.resize(400, 80)
    host.show()
    qtbot.waitExposed(host)
    return bar


def _pixel(bar, x, y):
    return bar.grab().toImage().pixelColor(x, y).name()


def _hex(name):
    return QColor(getattr(fxstyle.colors(), name)).name()


def test_the_lines_are_painted_not_overlay_frames(qtbot):
    bar = _bar(qtbot)

    frames = [child for child in bar.findChildren(QFrame)
              if not isinstance(child, QLabel)]

    assert frames == []
    assert _pixel(bar, 0, 1) == _hex("accent_primary")
    assert _pixel(bar, bar.width() - 1, 1) == _hex("accent_secondary")
    assert _pixel(bar, bar.width() // 2, 3) == _hex("border")


def test_the_line_follows_a_theme_switch(qtbot):
    fxstyle.apply_theme("dark")
    bar = _bar(qtbot)

    fxstyle.apply_theme("github_light")
    qtbot.wait(10)

    assert _pixel(bar, 0, 1) == _hex("accent_primary")


def test_custom_line_colours_are_painted(qtbot):
    bar = _bar(qtbot)

    bar.set_status_line_colors("#ff0000", "#0000ff")

    assert _pixel(bar, 0, 1) == "#ff0000"
    assert _pixel(bar, bar.width() - 1, 1) == "#0000ff"


def test_a_hidden_line_leaves_the_bar_its_own_ground(qtbot):
    bar = _bar(qtbot)

    bar.hide_status_line()

    assert _pixel(bar, bar.width() // 2, 1) == _hex("surface_sunken")
    assert _pixel(bar, bar.width() // 2, 3) == _hex("surface_sunken")


def test_the_timeout_clears_the_tint(qtbot):
    bar = _bar(qtbot)

    bar.showMessage("boom", ERROR, duration=0.05)
    assert bar.tint()
    qtbot.waitUntil(lambda: bar.tint() is None, timeout=2000)

    assert not bar.message_label.isVisible()
    assert _pixel(bar, bar.width() // 2, bar.height() // 2) == (
        _hex("surface_sunken"))


def test_clear_message_runs_once(qtbot):
    calls = []

    class Counting(FXStatusBar):
        def clearMessage(self):
            calls.append(1)
            super().clearMessage()

    bar = _bar(qtbot, Counting)
    bar.showMessage("hello", duration=30)

    bar.clearMessage()

    assert calls == [1]
    assert bar.tint() is None


def test_the_bar_carries_no_sheet_of_its_own_untinted(qtbot):
    bar = _bar(qtbot)

    assert bar.styleSheet() == ""


def test_a_long_message_does_not_widen_the_window(qtbot):
    bar = _bar(qtbot)
    host = bar.window()
    width = host.width()

    bar.showMessage("a long message " * 20, ERROR, duration=30)
    # A switch lays the bar out again, which grew the window to the text.
    fxstyle.apply_theme("light")
    qtbot.wait(20)

    assert host.width() == width
