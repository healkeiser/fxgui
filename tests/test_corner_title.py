"""A plain FXMainWindow can show its name in the menu bar corner."""

# Third-party
from qtpy.QtCore import QPoint
from qtpy.QtGui import QFontInfo
from qtpy.QtWidgets import QLabel, QMenuBar, QToolButton, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXMainWindow


def _window(qtbot, corner=True, theme="dark"):
    fxstyle.apply_theme(theme)
    window = FXMainWindow(title="probe")
    window.set_banner_text("Probe")
    if corner:
        window.use_corner_title()
    window.body = QLabel("A label")
    window.setCentralWidget(window.body)
    window.resize(640, 360)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(10)
    return window


def test_the_body_sits_under_the_toolbar_and_the_corner_shows(qtbot):
    window = _window(qtbot)
    bar = window.menuBar()
    body_top = window.body.mapTo(window, QPoint(0, 0)).y()

    assert body_top == window.toolbar.geometry().bottom() + 1
    assert bar.cornerWidget() is window.title_corner
    assert window.title_corner.isVisible()
    assert window.title_corner.isAncestorOf(window.banner_label)
    assert window.banner_label.text() == "Probe"
    assert bar.property(fxstyle.FRAME_PROPERTY) is None


def test_a_corner_widget_sits_left_of_the_name_inside_the_bar(qtbot):
    plain = _window(qtbot, corner=False)
    window = _window(qtbot)
    button = QToolButton()
    button.setText("B")

    window.add_corner_widget(button)
    qtbot.wait(10)
    bar = window.menuBar()
    corner = window.title_corner
    name_left = window.banner_label.mapTo(corner, QPoint(0, 0)).x()
    top = button.mapTo(bar, QPoint(0, 0)).y()

    assert button.isVisible() and corner.isAncestorOf(button)
    assert button.geometry().right() < name_left
    assert bar.height() == plain.menuBar().height()
    assert corner.geometry().top() == 0
    assert corner.height() == bar.height()
    assert top >= 0 and top + button.height() <= bar.height()
    assert abs((top + button.height() / 2) - bar.height() / 2) <= 1


def test_a_corner_widget_asks_for_the_corner_itself(qtbot):
    window = _window(qtbot, corner=False)

    window.add_corner_widget(QToolButton())

    assert window.menuBar().cornerWidget() is window.title_corner


def test_a_theme_switch_keeps_the_corner_in_the_menu_bar_face(qtbot):
    window = _window(qtbot)

    fxstyle.apply_theme("github_light")
    qtbot.wait(10)

    bar = window.menuBar()
    label = window.banner_label
    assert label.styleSheet() == ""
    assert QFontInfo(label.font()).pixelSize() == (
        QFontInfo(bar.font()).pixelSize())
    assert window.title_corner.height() == bar.height()


def test_a_new_menu_bar_set_later_gets_the_corner(qtbot, qapp):
    window = _window(qtbot)
    corner = window.title_corner
    bar = QMenuBar()
    bar.addMenu("File")

    window.setMenuBar(bar)
    qapp.processEvents()
    bar.resize(bar.width(), bar.height() + 10)

    assert bar.cornerWidget() is corner
    assert corner.height() == bar.height()
    assert bar.property(fxstyle.FRAME_PROPERTY) is None


def test_a_new_central_widget_keeps_the_corner(qtbot):
    window = _window(qtbot)

    window.setCentralWidget(QWidget())
    qtbot.wait(10)
    with qtbot.captureExceptions() as raised:
        fxstyle.apply_theme("github_light")
        qtbot.wait(10)

    assert not raised, raised
    assert window.menuBar().cornerWidget() is window.title_corner
