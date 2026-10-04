"""A segment click is a navigation: history records it, back returns."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QPushButton

# Internal
from fxgui.fxwidgets import FXBreadcrumb


PATH = ["Projects", "MyShow", "Assets", "Hero"]


def _crumb(qtbot):
    crumb = FXBreadcrumb(show_navigation=True)
    qtbot.addWidget(crumb)
    crumb.resize(500, 32)
    crumb.set_path(PATH)
    crumb.show()
    qtbot.waitExposed(crumb)
    return crumb


def _buttons(crumb):
    layout = crumb._layout
    return [
        layout.itemAt(index).widget()
        for index in range(layout.count())
        if isinstance(layout.itemAt(index).widget(), QPushButton)
    ]


def test_a_segment_click_can_be_undone_with_back(qtbot, qapp):
    crumb = _crumb(qtbot)
    QTest.mouseClick(_buttons(crumb)[1], Qt.LeftButton)
    assert crumb.path() == PATH[:2]

    assert crumb.go_back() is True
    assert crumb.path() == PATH
    assert crumb.go_forward() is True
    assert crumb.path() == PATH[:2]


def test_double_click_on_a_segment_opens_the_editor(qtbot, qapp):
    crumb = _crumb(qtbot)
    segment = _buttons(crumb)[1]
    assert "mouseDoubleClickEvent" not in vars(segment)
    QTest.mouseDClick(segment, Qt.LeftButton)
    assert crumb.is_editing()
    # QTest drops the release on the now hidden segment; without one the
    # button stays down for every later test.
    QTest.mouseRelease(crumb, Qt.LeftButton)
    assert QApplication.mouseButtons() == Qt.NoButton


def test_a_home_click_says_home_once(qtbot, qapp):
    crumb = _crumb(qtbot)
    homes, segments = [], []
    crumb.home_clicked.connect(lambda: homes.append(True))
    crumb.segment_clicked.connect(lambda *args: segments.append(args))

    QTest.mouseClick(_buttons(crumb)[0], Qt.LeftButton)

    assert homes == [True]
    assert segments == []
    assert crumb.path() == PATH[:1]


def test_a_home_click_goes_to_the_home_path(qtbot, qapp):
    crumb = _crumb(qtbot)
    crumb.set_home_path(["Projects", "MyShow"])

    QTest.mouseClick(_buttons(crumb)[0], Qt.LeftButton)

    assert crumb.path() == ["Projects", "MyShow"]
    assert crumb.home_path() == ["Projects", "MyShow"]


def test_back_and_forward_hand_out_a_copy(qtbot, qapp):
    crumb = _crumb(qtbot)
    crumb.set_path(PATH[:2])
    seen = []
    crumb.navigated_back.connect(seen.append)
    crumb.navigated_forward.connect(seen.append)

    crumb.go_back()
    seen[-1].append("x")
    crumb.go_forward()
    seen[-1].append("x")

    assert crumb.path() == PATH[:2]
    crumb.go_back()
    assert crumb.path() == PATH
