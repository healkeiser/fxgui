"""A segment click is a navigation: history records it, back returns."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QPushButton

# Internal
from fxgui import fxstyle
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
    assert crumb.path == PATH[:2]

    assert crumb.go_back() is True
    assert crumb.path == PATH
    assert crumb.go_forward() is True
    assert crumb.path == PATH[:2]


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


def test_theme_switch_redraws_the_strip_without_the_mixin(qtbot, qapp):
    crumb = _crumb(qtbot)
    before = crumb._container.grab().toImage()
    fxstyle.apply_theme("light")
    assert crumb._container.grab().toImage() != before
