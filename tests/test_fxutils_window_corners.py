"""Asking the compositor for the chrome it draws around its own flyouts.

The answer under the offscreen platform the suite runs on is always no:
there is no compositor behind it and the window handle it hands out
belongs to nothing. So what is testable everywhere is the half that has
to hold on every machine -- that a refusal is an answer rather than an
exception, and that a platform which cannot be asked is not asked at all.
"""

# Built-in
import ctypes
import sys

# Third-party
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import fxutils


def test_asking_for_the_flyout_chrome_answers_rather_than_raises(qtbot):
    """A panel that cannot have rounded corners is still a panel.

    Whatever this platform says, it says it as a value: a consumer asks
    on every show, so an exception here would be a window that cannot
    open rather than one with square corners.

    Asked twice, because it is asked once per show: the second answer has
    to be the first, or one of the two is wrong.
    """
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()

    answer = fxutils.round_window_corners(widget)

    assert isinstance(answer, bool)
    assert fxutils.round_window_corners(widget) == answer, (
        "and asking twice agrees"
    )


def test_a_platform_with_no_compositor_is_never_asked(qtbot, monkeypatch):
    """Off Windows the library is not there to load, so nothing tries.

    Read as what was loaded rather than as what came back, because the
    answer is `False` either way: this pins that the platform is checked
    before `dwmapi` is reached for at all, which is what keeps this from
    raising on a machine with no such library to fail to load.
    """
    reached = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        ctypes, "WinDLL", lambda *args, **kwargs: reached.append("dwmapi")
    )
    widget = QWidget()
    qtbot.addWidget(widget)

    assert fxutils.round_window_corners(widget) is False
    assert reached == [], "nothing was loaded to ask with"


def test_a_window_with_no_handle_yet_is_not_asked(qtbot, monkeypatch):
    """`winId` creating a handle is the point: a widget with none is one
    the request has nothing to name."""
    reached = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes, "WinDLL", lambda *args, **kwargs: reached.append("dwmapi")
    )

    class _Handleless(QWidget):
        def winId(self):
            return 0

    widget = _Handleless()
    qtbot.addWidget(widget)

    assert fxutils.round_window_corners(widget) is False
    assert reached == []


def test_a_compositor_that_declines_is_not_an_error(qtbot, monkeypatch):
    """The failure code path, which is the one an older Windows build
    takes. `ctypes.HRESULT` would raise on it; the raw `c_long` does not,
    and a build with no window rounding is not an error here, it is the
    other answer."""

    class _Declining:
        class DwmSetWindowAttribute:
            argtypes = None
            restype = None

            def __call__(self, *args):
                # E_INVALIDARG, what a build without the attribute says.
                return -2147024809

        DwmSetWindowAttribute = DwmSetWindowAttribute()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *args, **kwargs: _Declining())
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()

    assert fxutils.round_window_corners(widget) is False


def test_a_compositor_that_accepts_says_so(qtbot, monkeypatch):
    """`S_OK` is zero, and zero is the only success."""
    asked = {}

    class _Accepting:
        class DwmSetWindowAttribute:
            argtypes = None
            restype = None

            def __call__(self, handle, attribute, value, size):
                # `.value`, not `int()`: these arrive as the ctypes
                # objects the declaration above them asked for, and a
                # ctypes scalar has no `__int__`.
                asked["attribute"] = attribute.value
                asked["size"] = size.value
                return 0

        DwmSetWindowAttribute = DwmSetWindowAttribute()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *args, **kwargs: _Accepting())
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()

    assert fxutils.round_window_corners(widget) is True
    assert asked["attribute"] == 33, "DWMWA_WINDOW_CORNER_PREFERENCE"
    assert asked["size"] == ctypes.sizeof(ctypes.c_int()), (
        "the size in bytes of the value, not of the pointer"
    )


def test_a_library_that_will_not_load_is_an_answer_too(qtbot, monkeypatch):
    """`dwmapi` missing, or the symbol absent from it."""

    def _refuse(*args, **kwargs):
        raise OSError("no dwmapi here")

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "WinDLL", _refuse)
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()

    assert fxutils.round_window_corners(widget) is False


def test_it_is_exported(qtbot):
    assert "round_window_corners" in fxutils.__all__
