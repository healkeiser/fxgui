"""Compact controls line up at 24 px; a split button's arrow has a square."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets import FXSplitButton

from _helpers import near, shown


def _row(qtbot, *widgets) -> QWidget:
    window = QWidget()
    fxstyle.register_themed_root(window)
    layout = QHBoxLayout(window)
    for widget in widgets:
        layout.addWidget(widget, 0, Qt.AlignVCenter)
    layout.addStretch()
    shown(qtbot, window, (720, 80))
    return window


def _split(text="", icon=None, style=Qt.ToolButtonTextOnly) -> FXSplitButton:
    button = FXSplitButton()
    button.setToolButtonStyle(style)
    if text:
        button.setText(text)
    if icon:
        fxicons.set_icon(button, icon)
    menu = QMenu(button)
    menu.addAction("Open in Nuke")
    button.setMenu(menu)
    return button


def _status(*choices) -> QComboBox:
    combo = QComboBox()
    combo.addItems(list(choices))
    combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
    return combo


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_every_compact_control_stands_24_px_on_one_line(qtbot, theme):
    fxstyle.apply_theme(theme)
    status, comment = _status("WFA", "Retake"), QPushButton("Comment")
    tool, split = QToolButton(), _split("Send")
    tool.setText("Tool")
    controls = (status, comment, tool, split)
    for control in controls:
        fxstyle.mark_compact(control)
    _window = _row(qtbot, *controls)
    # The split button sets its own hint; the others reach 24 px by sheet.
    assert split.sizeHint().height() == fxstyle.COMPACT_HEIGHT
    for control in controls:
        assert control.height() == fxstyle.COMPACT_HEIGHT, control
        assert control.y() == status.y(), control
        assert control.font().pixelSize() == comment.font().pixelSize()


def test_a_compact_combo_hugs_a_short_choice(qtbot):
    fxstyle.apply_theme("dark")
    combo = _status("WFA")
    fxstyle.mark_compact(combo)
    _window = _row(qtbot, combo)
    text = combo.fontMetrics().horizontalAdvance("WFA")
    # 9 px to the text, 4 to a 16 px chevron, which sits 8 px in.
    assert combo.width() == 9 + text + 4 + 16 + 8


def test_a_combo_sized_to_its_contents_drops_the_floor(qtbot):
    fxstyle.apply_theme("dark")
    hugging, field = _status("WFA"), QComboBox()
    field.addItems(["WFA"])
    _window = _row(qtbot, hugging, field)
    assert hugging.width() < field.width()
    text = hugging.fontMetrics().horizontalAdvance("WFA")
    # 11 px to the text, a 22 px drop-down whose chevron sits 10 px in.
    assert hugging.width() <= 11 + text + 2 + 22 + 10


def _segment(button):
    """Return the divider's x and the chevron's ink span, by pixels."""
    image = button.grab().toImage()
    middle = button.height() // 2
    divider = fxstyle.colors().border_light.lower()
    dividers = [
        x for x in range(button.width() // 2, button.width() - 1)
        if image.pixelColor(x, middle).name() == divider
        and image.pixelColor(x, 4).name() == divider
    ]
    assert len(dividers) == 1, dividers
    # The chevron's own ink, not the round corner's edge beside it.
    chevron = fxstyle.colors().icon
    ink = [
        x for x in range(dividers[0] + 1, button.width() - 1)
        if any(image.pixelColor(x, y).alpha() == 255
               and near(image.pixelColor(x, y), chevron, 24)
               for y in range(middle - 4, middle + 5))
    ]
    return dividers[0], ink


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("make, compact", [
    (lambda: _split("After Effects", "play", Qt.ToolButtonTextBesideIcon),
     False),
    (lambda: _split(icon="play", style=Qt.ToolButtonIconOnly), False),
    (lambda: _split("Publish"), False),
    (lambda: _split("Send"), True),
])
def test_the_arrow_has_a_square_segment_its_chevron_centred(
        qtbot, theme, make, compact):
    fxstyle.apply_theme(theme)
    button = make()
    fxstyle.mark_compact(button, compact)
    _window = _row(qtbot, button, QPushButton("Cancel"))
    divider, ink = _segment(button)
    # The divider and the outer edge bound a square as tall as the button.
    assert button.width() - divider == button.height()
    inside = (divider + 1 + button.width() - 2) / 2
    assert ink and abs((ink[0] + ink[-1]) / 2 - inside) <= 0.5


def test_text_beside_an_icon_keeps_even_sides(qtbot):
    fxstyle.apply_theme("dark")
    button = _split("After Effects", "play", Qt.ToolButtonTextBesideIcon)
    _window = _row(qtbot, button)
    divider, _ink = _segment(button)
    image = button.grab().toImage()
    middle = button.height() // 2
    ground = image.pixelColor(4, middle)
    ink = [
        x for x in range(2, divider)
        if any(image.pixelColor(x, y) != ground
               for y in range(middle - 6, middle + 7))
    ]
    left, right = ink[0], divider - ink[-1]
    assert abs(left - right) <= 2, (left, right)
