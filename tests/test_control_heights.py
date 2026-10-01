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
from fxgui.fxwidgets import (
    FXBreadcrumb,
    FXFilePathWidget,
    FXJoinedGroup,
    FXPrimaryButton,
    FXSearchBar,
    FXTagInput,
    FXTimelineSlider,
)

# A line edit and a push button come to the same height with the theme's
# font installed; under a test's fontless offscreen platform they differ.
_INPUTS = {
    "QSpinBox": QSpinBox,
    "FXFilePathWidget": FXFilePathWidget,
    "FXSearchBar": FXSearchBar,
    # Its spin boxes set the row.
    "FXTimelineSlider": FXTimelineSlider,
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





def _joined():
    group = FXJoinedGroup()
    group.add_widget(FXPrimaryButton("Post"))
    return group


_BUTTONS = {
    "FXJoinedGroup": _joined,
    "FXBreadcrumb": lambda: FXBreadcrumb(show_navigation=True),
}


@pytest.mark.parametrize("name", sorted(_BUTTONS))
def test_a_button_row_is_as_tall_as_a_push_button(qtbot, name):
    height, button = _heights(qtbot, _BUTTONS[name], lambda: QPushButton("x"))
    assert height == button


def test_a_plain_tool_button_keeps_its_size_with_its_reserved_edge(qtbot):
    """A 16 px icon, 3 px margin, 2 px padding, the 1 px edge, Qt's own 3."""
    from qtpy.QtWidgets import QToolButton

    from fxgui import fxicons

    button = QToolButton()
    fxicons.set_icon(button, "home")
    height, _ = _heights(qtbot, lambda: button, QPushButton)
    assert height == 16 + 2 * (3 + 2 + 1) + 3
