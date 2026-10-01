"""Three Qt layout gaps closed: content-sized scroll areas, wrapped label
heights deep in layouts, and one label column across several forms."""

# Third-party
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui.fxwidgets import (
    FXResizedScrollArea,
    align_labels,
    fix_wrapped_heights,
)


FLOOR, CAP = 60, 200


def _scroll(qtbot, rows):
    host = QWidget()
    qtbot.addWidget(host)
    column = QVBoxLayout(host)
    area = FXResizedScrollArea(floor=FLOOR, cap=CAP)
    area.setWidgetResizable(True)
    content = QWidget()
    lines = QVBoxLayout(content)
    for index in range(rows):
        lines.addWidget(QLabel(f"row {index}"))
    area.setWidget(content)
    column.addWidget(area)
    column.addStretch()
    host.resize(300, 600)
    host.show()
    qtbot.waitExposed(host)
    return host, area, content, lines


def test_a_capped_area_asks_for_its_content_between_floor_and_cap(qtbot):
    _host, area, content, _lines = _scroll(qtbot, 4)
    height = area.minimumSizeHint().height()

    assert height == min(max(content.sizeHint().height(), FLOOR), CAP)
    assert FLOOR <= height < CAP


def test_content_reading_no_height_still_gets_the_floor(qtbot, monkeypatch):
    _host, area, content, _lines = _scroll(qtbot, 4)

    monkeypatch.setattr(content, "sizeHint", lambda: QSize(0, 0))

    assert area.minimumSizeHint().height() == FLOOR


def test_content_past_the_cap_scrolls_inside_the_cap(qtbot):
    host, area, content, lines = _scroll(qtbot, 2)
    outside = host.layout()
    before = outside.minimumSize().height()

    for index in range(30):
        lines.addWidget(QLabel(f"more {index}"))
    # The layout outside hears of it: its own minimum grows to the cap.
    qtbot.waitUntil(
        lambda: outside.minimumSize().height() > before, timeout=1000
    )

    assert content.sizeHint().height() > CAP
    assert area.minimumSizeHint().height() == CAP


def test_a_plain_area_keeps_qt_s_own_minimum(qtbot):
    area = FXResizedScrollArea()
    qtbot.addWidget(area)
    content = QWidget()
    QVBoxLayout(content).addWidget(QLabel("one"))
    area.setWidget(content)

    from qtpy.QtWidgets import QScrollArea

    plain = QScrollArea()
    qtbot.addWidget(plain)
    assert area.minimumSizeHint() == plain.minimumSizeHint()


def test_the_area_has_no_resized_signal():
    assert not hasattr(FXResizedScrollArea, "resized")


MESSAGE = (
    "Wood reads C:/me/textures/wood_diffuse.png, which the farm cannot see "
    "from any of its render nodes, so this target would render with nothing "
    "at all on its surface"
)


def test_a_wrapped_label_three_layouts_deep_gets_its_height(qtbot):
    panel = QWidget()
    qtbot.addWidget(panel)
    outer = QVBoxLayout(panel)
    middle = QVBoxLayout()
    inner = QHBoxLayout()
    label = QLabel(MESSAGE)
    label.setWordWrap(True)
    inner.addWidget(label)
    middle.addLayout(inner)
    outer.addLayout(middle)
    panel.setFixedWidth(300)
    panel.show()
    qtbot.waitExposed(panel)

    fix_wrapped_heights(panel)
    lines = label.fontMetrics().lineSpacing()
    at_300 = label.height()
    panel.setFixedWidth(150)
    qtbot.wait(10)
    fix_wrapped_heights(panel)

    assert at_300 >= 2 * lines
    assert label.height() == label.heightForWidth(label.width())
    assert label.height() > at_300


def test_labels_across_forms_share_one_column(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    column = QVBoxLayout(host)
    first, second = QFormLayout(), QFormLayout()
    first.addRow("Frames", QLineEdit())
    second.addRow("Pool and priority", QLineEdit())
    column.addLayout(first)
    column.addLayout(second)

    align_labels(first, second)
    host.show()
    qtbot.waitExposed(host)

    short = first.itemAt(0, QFormLayout.LabelRole).widget()
    wide = second.itemAt(0, QFormLayout.LabelRole).widget()
    assert short.width() == wide.width()
    assert short.alignment() & Qt.AlignRight
