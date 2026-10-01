"""FXFlowLayout wraps its widgets onto new lines instead of widening."""

# Third-party
from qtpy.QtWidgets import QPushButton, QWidget

# Internal
from fxgui.fxwidgets import FXFlowLayout


def _row(qtbot, count=6, spacing=4):
    host = QWidget()
    qtbot.addWidget(host)
    layout = FXFlowLayout(host, spacing=spacing)
    buttons = [QPushButton(f"tag {index}") for index in range(count)]
    for button in buttons:
        button.setFixedSize(60, 20)
        layout.addWidget(button)
    return host, layout, buttons


def test_items_wrap_when_the_line_is_full(qtbot):
    host, layout, buttons = _row(qtbot)
    host.resize(200, 200)
    host.show()
    qtbot.waitExposed(host)

    assert [b.y() for b in buttons[:3]] == [0, 0, 0]
    assert buttons[3].y() == 24 and buttons[3].x() == 0
    assert buttons[1].x() == 64, "one gap between neighbours"


def test_the_height_follows_the_width(qtbot):
    _host, layout, _buttons = _row(qtbot)

    assert layout.hasHeightForWidth()
    assert layout.heightForWidth(400) == 20
    assert layout.heightForWidth(200) == 44
    assert layout.heightForWidth(60) == 6 * 20 + 5 * 4


def test_a_hidden_widget_takes_no_room(qtbot):
    host, layout, buttons = _row(qtbot, count=4)
    buttons[1].hide()

    assert layout.heightForWidth(200) == 20, "three fit on one line"


def test_the_minimum_is_the_widest_item_not_the_whole_row(qtbot):
    _host, layout, buttons = _row(qtbot)
    buttons[2].setFixedSize(90, 20)

    assert layout.minimumSize().width() == 90
    assert layout.sizeHint() == layout.minimumSize()


def test_set_spacing_changes_the_gap(qtbot):
    _host, layout, _buttons = _row(qtbot)
    layout.setSpacing(10)

    assert layout.spacing() == 10
    assert layout.heightForWidth(60) == 6 * 20 + 5 * 10


def test_items_can_be_taken_back_out(qtbot):
    _host, layout, buttons = _row(qtbot, count=2)

    item = layout.takeAt(0)

    assert item.widget() is buttons[0]
    assert layout.count() == 1
    assert layout.itemAt(1) is None
    assert layout.takeAt(5) is None
