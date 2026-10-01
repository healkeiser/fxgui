"""Tests for `later`, `rehome` and `focus_step` in `fxgui.fxutils`."""

# Built-in
import ast
import gc
from pathlib import Path

# Third-party
from qtpy.QtCore import QEvent, QObject
from qtpy.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QWidget,
)

# Internal
from fxgui import fxutils

_PACKAGE = Path(fxutils.__file__).resolve().parent


def test_later_runs_the_call_once(qtbot):
    owner = QObject()
    ran = []

    fxutils.later(0, owner, lambda: ran.append(1))
    qtbot.waitUntil(lambda: ran == [1])
    qtbot.wait(30)

    assert ran == [1]


def test_later_skips_the_call_when_the_owner_died(qtbot):
    owner = QObject()
    ran = []

    fxutils.later(10, owner, lambda: ran.append(1))
    owner.deleteLater()
    qtbot.wait(60)

    assert ran == []


def _context_single_shots(source: str) -> list:
    """Return the line of every `singleShot` call given three arguments."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "singleShot"
        and len(node.args) + len(node.keywords) >= 3
    ]


def test_the_check_sees_a_context_single_shot():
    assert _context_single_shots(
        "QTimer.singleShot(0, owner, run)\nQTimer.singleShot(0, run)\n"
    ) == [1]


def test_no_single_shot_takes_a_context_object():
    # Houdini 21's PySide6 6.5 has no singleShot(ms, context, callable).
    found = [
        f"{path.relative_to(_PACKAGE)}:{line}"
        for path in sorted(_PACKAGE.rglob("*.py"))
        for line in _context_single_shots(path.read_text(encoding="utf-8"))
    ]

    assert found == [], "use fxgui.fxutils.later instead"


def test_a_focus_step_leaves_no_wrapper_owned_by_a_widget_that_dies(qtbot):
    from shiboken6 import Shiboken

    window = QMainWindow()
    qtbot.addWidget(window)
    bar = window.menuBar()
    body = QWidget()
    window.setCentralWidget(body)
    passing = QPushButton(body)

    reached = fxutils.focus_step(passing)
    passing.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    assert reached is window, "the chain comes round to the window"
    assert Shiboken.isValid(bar), "the window's menu bar keeps its wrapper"
    assert Shiboken.ownedByPython(window)


def test_rehome_returns_none_for_none():
    assert fxutils.rehome(None) is None



def test_rehome_never_files_a_wrapper_under_one_about_to_go(qtbot):
    from shiboken6 import Shiboken

    area = QScrollArea()
    qtbot.addWidget(area)
    # Its parent is a container Qt made, which no Python name holds.
    bar = fxutils.rehome(area.horizontalScrollBar())
    gc.collect()

    assert Shiboken.isValid(bar)


def test_the_helpers_are_public_in_fxutils():
    for name in ("later", "rehome", "focus_step"):
        assert name in fxutils.__all__, name
