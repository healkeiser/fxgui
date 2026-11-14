"""`fxutils.set_tab_order` chains widgets into a declared tab order."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget

from fxgui import fxutils


def _shown(qtbot, *widgets):
    window = QWidget()
    qtbot.addWidget(window)
    layout = QVBoxLayout(window)
    for widget in widgets:
        layout.addWidget(widget)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitActive(window)
    return window


def test_tab_follows_the_declared_order(qtbot):
    # Laid out a, b, c; any rotation of that is the order Tab already has.
    a, b, c = QLineEdit("a"), QLineEdit("b"), QLineEdit("c")
    window = _shown(qtbot, a, b, c)
    fxutils.set_tab_order([c, b, a])

    c.setFocus()
    qtbot.waitUntil(lambda: QApplication.focusWidget() is c)
    window.focusNextChild()
    assert QApplication.focusWidget() is b
    window.focusNextChild()
    assert QApplication.focusWidget() is a
    window.focusPreviousChild()
    assert QApplication.focusWidget() is b


def test_a_proxied_widget_chains_through_its_proxy(qtbot):
    compound = QWidget()
    compound.setFocusPolicy(Qt.NoFocus)
    inner = QLineEdit("inner", compound)
    QVBoxLayout(compound).addWidget(inner)
    compound.setFocusProxy(inner)
    first, last = QLineEdit("first"), QLineEdit("last")
    _window = _shown(qtbot, first, last, compound)  # held: it owns the edits
    fxutils.set_tab_order([first, compound, last])

    assert first.nextInFocusChain() is inner
    assert inner.nextInFocusChain() is last
