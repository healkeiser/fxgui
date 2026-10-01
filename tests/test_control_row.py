"""One row of every control lines up: one height, one centre line.

Text controls are `control_height` tall. On/off marks and slider handles
are smaller and centre on the row's middle; a switch's track is the
indicator size.
"""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStyle,
    QStyleOptionButton,
    QStyleOptionSlider,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import (
    FXBreadcrumb,
    FXFilePathWidget,
    FXIconButton,
    FXJoinedGroup,
    FXPrimaryButton,
    FXSearchBar,
    FXSplitButton,
    FXStatusDot,
    FXTagInput,
    FXToggleSwitch,
)


def _split(parent):
    button = FXSplitButton(parent)
    button.setText("Publish")
    button.setMenu(QMenu(button))
    return button


def _joined(parent):
    group = FXJoinedGroup(parent)
    group.add_widget(FXPrimaryButton("Post"))
    return group


TEXT = {
    "QPushButton": lambda p: QPushButton("Cancel", p),
    "FXPrimaryButton": lambda p: FXPrimaryButton("Post", p),
    "FXIconButton": lambda p: FXIconButton("mood", p),
    "FXSplitButton": _split,
    "FXJoinedGroup": _joined,
    "QLineEdit": QLineEdit,
    "QComboBox": QComboBox,
    "QSpinBox": QSpinBox,
    "FXSearchBar": lambda p: FXSearchBar(parent=p),
    "FXFilePathWidget": lambda p: FXFilePathWidget(parent=p),
    "FXBreadcrumb": lambda p: FXBreadcrumb(p),
    "FXTagInput": lambda p: FXTagInput(p),
}

MARKS = {
    "QCheckBox": lambda p: QCheckBox("Notify", p),
    "QRadioButton": lambda p: QRadioButton("Notify", p),
    "FXToggleSwitch": FXToggleSwitch,
    "QSlider": lambda p: QSlider(Qt.Horizontal, p),
    "FXStatusDot": lambda p: FXStatusDot(p),
}


def _mark_box(widget):
    """Return the rect of what a mark draws, in the widget's coordinates."""
    if isinstance(widget, FXToggleSwitch):
        return widget.track_rect()
    if isinstance(widget, QSlider):
        option = QStyleOptionSlider()
        widget.initStyleOption(option)
        return widget.style().subControlRect(
            QStyle.CC_Slider, option, QStyle.SC_SliderHandle, widget
        )
    if isinstance(widget, (QCheckBox, QRadioButton)):
        option = QStyleOptionButton()
        widget.initStyleOption(option)
        element = (
            QStyle.SE_CheckBoxIndicator
            if isinstance(widget, QCheckBox)
            else QStyle.SE_RadioButtonIndicator
        )
        return widget.style().subElementRect(element, option, widget)
    return widget.rect()


@pytest.fixture
def row(qtbot):
    window = QWidget()
    fxstyle.register_themed_root(window)
    layout = QHBoxLayout(window)
    # Centred, as a toolbar or a form row holds its controls.
    widgets = {}
    for name, make in {**TEXT, **MARKS}.items():
        widget = make(window)
        widgets[name] = widget
        layout.addWidget(widget, 0, Qt.AlignVCenter)
    window.resize(2400, 80)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    window.widgets = widgets
    return window


def test_every_text_control_is_control_height(row):
    probe = row.widgets["QPushButton"]
    if QFontMetrics(probe.font()).height() < 14:
        pytest.skip(
            "no font on this platform: Qt holds a line edit to a 14 px line"
        )
    heights = {name: w.height() for name, w in row.widgets.items()
               if name in TEXT}
    assert set(heights.values()) == {fxstyle.control_height(probe)}, heights


@pytest.mark.parametrize("name", sorted({**TEXT, **MARKS}))
def test_everything_centres_on_one_line(row, name):
    line = row.widgets["QPushButton"].geometry().center().y()
    widget = row.widgets[name]
    box = _mark_box(widget)
    centre = widget.mapTo(row, box.center()).y()
    assert abs(centre - line) <= 1, (name, centre, line)


def test_a_slider_fits_in_the_row(row):
    slider = row.widgets["QSlider"]
    height = fxstyle.control_height(row.widgets["QPushButton"])
    assert fxstyle.INDICATOR_SIZE <= slider.height() <= height
    assert slider.rect().contains(_mark_box(slider))


def test_the_switch_track_is_the_indicator_size(row):
    track = row.widgets["FXToggleSwitch"].track_rect()
    assert track.height() == fxstyle.INDICATOR_SIZE
    assert track.width() == 2 * fxstyle.INDICATOR_SIZE


@pytest.mark.parametrize("name", ["QCheckBox", "QRadioButton"])
def test_a_check_or_radio_mark_is_the_indicator_size(row, name):
    box = _mark_box(row.widgets[name])
    assert box.height() == box.width() == fxstyle.INDICATOR_SIZE
