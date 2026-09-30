"""A shown FXTooltip leaves with its anchor, hidden or deleted."""

# Built-in
import gc

# Third-party
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget

# Internal
from fxgui.fxwidgets import FXTooltip


def _window(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    button = QPushButton("anchor", window)
    QVBoxLayout(window).addWidget(button)
    window.resize(200, 80)
    window.show()
    qtbot.waitExposed(window)
    return window, button


def _shown_on(qtbot, anchor):
    tip = FXTooltip(parent=anchor, description="probe", persistent=True)
    tip.show_tooltip()
    qtbot.waitUntil(tip.isVisible)
    return tip


def test_closing_the_anchor_window_hides_its_tooltip(qtbot):
    window, _button = _window(qtbot)
    tip = _shown_on(qtbot, window)
    window.close()
    qtbot.waitUntil(lambda: not tip.isVisible(), timeout=1000)


def test_closing_the_window_hides_a_child_anchor_s_tooltip(qtbot):
    window, button = _window(qtbot)
    tip = _shown_on(qtbot, button)
    window.close()
    qtbot.waitUntil(lambda: not tip.isVisible(), timeout=1000)


def test_hiding_the_anchor_hides_its_tooltip(qtbot):
    _window_, button = _window(qtbot)
    tip = _shown_on(qtbot, button)
    button.hide()
    qtbot.waitUntil(lambda: not tip.isVisible(), timeout=1000)


def test_deleting_a_shown_anchor_does_not_crash(qtbot):
    window, button = _window(qtbot)
    tip = _shown_on(qtbot, button)
    gone = []
    tip.destroyed.connect(lambda: gone.append(True))
    window.deleteLater()
    qtbot.waitUntil(lambda: bool(gone), timeout=1000)


def test_a_hover_tooltip_still_shows_after_its_anchor_comes_back(qtbot):
    _window_, button = _window(qtbot)
    tip = _shown_on(qtbot, button)
    button.hide()
    qtbot.waitUntil(lambda: not tip.isVisible(), timeout=1000)
    button.show()
    tip.show_tooltip()
    qtbot.waitUntil(tip.isVisible)
    tip.close()


def test_dropping_a_hidden_tooltip_that_last_holds_its_anchor(qtbot):
    # The tooltip's teardown frees the anchor, whose destroyed signal then
    # reached the half-freed tooltip: an access violation.
    tip = FXTooltip(parent=QWidget(), description="probe", persistent=True)
    del tip
    gc.collect()
