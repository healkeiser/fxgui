"""Every input stands as tall as a line edit, every button as a push button."""

# Third-party
import pytest
from qtpy.QtWidgets import (
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFilePathWidget, FXSearchBar, FXTagInput

# A line edit and a push button come to the same height with the theme's
# font installed; under a test's fontless offscreen platform they differ.
_INPUTS = {
    "QSpinBox": QSpinBox,
    "FXFilePathWidget": FXFilePathWidget,
    "FXSearchBar": FXSearchBar,
    # Its field is the whole widget until a tag is added.
    "FXTagInput": FXTagInput,
    "QDoubleSpinBox": QDoubleSpinBox,
}


def _heights(qtbot, make, reference):
    window = QWidget()
    fxstyle.register_themed_root(window)
    layout = QVBoxLayout(window)
    widget, model = make(), reference()
    layout.addWidget(widget)
    layout.addWidget(model)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return widget.height(), model.height()


@pytest.mark.parametrize("name", sorted(_INPUTS))
def test_an_input_is_as_tall_as_a_line_edit(qtbot, name):
    height, line_edit = _heights(qtbot, _INPUTS[name], QLineEdit)
    assert height == line_edit

