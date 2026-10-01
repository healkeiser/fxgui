"""A split button stands and hovers as the push buttons beside it."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QMenu, QPushButton, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXPrimaryButton, FXSplitButton


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_split_button_is_as_tall_as_a_push_button(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    row = QHBoxLayout(window)
    split = FXSplitButton()
    split.setText("Publish")
    split.setMenu(QMenu(split))
    plain, primary = QPushButton("Cancel"), FXPrimaryButton("Post")
    for widget in (plain, primary, split):
        row.addWidget(widget)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    heights = {w.sizeHint().height() for w in (plain, primary, split)}
    assert heights == {fxstyle.control_height(plain)}
    assert split.height() == plain.height()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_hovered_split_button_hovers_as_a_push_button(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = QWidget()
    fxstyle.register_themed_root(window)
    row = QHBoxLayout(window)
    split = FXSplitButton()
    split.setText("Publish")
    split.setMenu(QMenu(split))
    row.addWidget(split)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    split.setAttribute(Qt.WA_UnderMouse, True)
    image = split.grab().toImage()
    colors = fxstyle.colors()
    middle = split.height() // 2
    assert image.pixelColor(3, middle).name() == colors.state_hover.lower()
    # Hover is a fill only: the edge stays the button's own.
    assert image.pixelColor(split.width() // 2, 0).name() == (
        colors.border_light.lower()
    )
    # The arrow's part takes the same fill, not a second accent.
    assert image.pixelColor(split.width() - 3, 3).name() == (
        colors.state_hover.lower()
    )
