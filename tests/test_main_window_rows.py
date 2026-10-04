"""The window's command row, its menu bar corner, a parent, and the frame."""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint, QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets import FXCommandRow, FXMainWindow


def _shown(qtbot, window, size=(800, 400)):
    qtbot.addWidget(window)
    window.setCentralWidget(QLabel("body"))
    window.resize(*size)
    window.show()
    qtbot.waitExposed(window)
    QApplication.processEvents()
    return window


def test_a_window_with_a_parent_stays_its_own_window(qtbot):
    host = QMainWindow()
    qtbot.addWidget(host)
    host.show()

    # The host owns the window; qtbot must close only the host.
    window = FXMainWindow(parent=host)
    window.show()
    qtbot.waitExposed(window)

    assert window.parent() is host
    assert window.isWindow()
    assert window.windowHandle() is not host.windowHandle()


def test_a_window_builds_no_toolbar(qtbot):
    window = _shown(qtbot, FXMainWindow())

    assert window.findChildren(QToolBar) == []


def test_a_command_row_is_fixed_in_place(qtbot):
    window = _shown(qtbot, FXMainWindow())
    row = FXCommandRow()
    window.addToolBar(Qt.TopToolBarArea, row)

    assert not row.isMovable()
    assert not row.isFloatable()
    assert not row.toggleViewAction().isVisible(), (
        "the menu bar's right-click cannot hide it")


@pytest.mark.parametrize("area", [Qt.TopToolBarArea, Qt.LeftToolBarArea])
def test_a_row_is_its_margins_on_every_side(qtbot, area):
    window = _shown(qtbot, FXMainWindow())
    row = FXCommandRow(margins=(2, 5, 7, 11), spacing=0)
    window.addToolBar(area, row)
    first, second = QPushButton("one"), QPushButton("two")
    for button in (first, second):
        button.setFixedSize(30, 30)
        row.addWidget(button)
    QApplication.processEvents()

    assert first.geometry().topLeft() == QPoint(2, 5)
    hint = row.sizeHint()
    across = 2 * 30 if area == Qt.TopToolBarArea else 30
    down = 30 if area == Qt.TopToolBarArea else 2 * 30
    assert (hint.width(), hint.height()) == (2 + across + 7, 5 + down + 11)


def test_a_row_starts_its_controls_at_its_margins(qtbot):
    window = _shown(qtbot, FXMainWindow())
    row = FXCommandRow(margins=(12, 5, 7, 0), spacing=6)
    window.addToolBar(Qt.TopToolBarArea, row)
    first, second = QPushButton("one"), QPushButton("two")
    row.addWidget(first)
    row.addWidget(second)
    QApplication.processEvents()

    assert first.geometry().left() == 12
    assert first.geometry().top() == 5
    assert second.geometry().left() - first.geometry().right() - 1 == 6


def test_a_row_keeps_its_margins_through_a_style_change(qtbot):
    window = _shown(qtbot, FXMainWindow())
    row = FXCommandRow(margins=(12, 5, 7, 0), spacing=6)
    window.addToolBar(Qt.TopToolBarArea, row)
    button = QPushButton("one")
    row.addWidget(button)
    QApplication.processEvents()

    fxstyle.apply_theme("github_light")
    row.setStyleSheet("QToolBar { }")
    QApplication.processEvents()

    assert (button.geometry().left(), button.geometry().top()) == (12, 5)
    assert row.layout().spacing() == 6


def test_a_bare_blank_on_a_framed_row_shows_the_frame(qtbot):
    window = _shown(qtbot, _with_row(FXMainWindow(framed=True)))
    row = FXCommandRow()
    window.addToolBar(Qt.TopToolBarArea, row)
    blank = QWidget()
    blank.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    row.addWidget(blank)
    row.addWidget(QPushButton("Refresh"))
    QApplication.processEvents()

    point = blank.mapTo(window, blank.rect().center())
    seen = QColor(window.grab().toImage().pixel(point)).name()

    assert seen == QColor(fxstyle.colors().frame).name()


def _corner_tools(qtbot, window):
    tools = QToolBar("Tools")
    tools.setIconSize(QSize(17, 17))
    tools.addAction(fxicons.get_icon("refresh"), "Refresh")
    window.add_corner_widget(tools)
    return tools


def test_a_corner_tool_shown_later_is_placed_not_overflowed(qtbot):
    window = FXMainWindow()
    tools = _corner_tools(qtbot, window)
    _shown(qtbot, window)

    later = tools.addAction(fxicons.get_icon("play_arrow"), "Run")
    QApplication.processEvents()
    QApplication.processEvents()

    button = tools.widgetForAction(later)
    assert button is not None and button.isVisible()
    name = window.banner_label.mapTo(window, window.banner_label.rect().topLeft())
    assert button.mapTo(window, button.rect().topRight()).x() < name.x()


def test_add_corner_widget_watches_the_widget_it_adds(qtbot):
    window = FXMainWindow()
    tools = _corner_tools(qtbot, window)
    _shown(qtbot, window)
    hides = []

    class _Spy(QWidget):
        def eventFilter(self, watched, event):
            if watched is window.title_corner and event.type() == QEvent.Hide:
                hides.append(1)
            return False

    spy = _Spy()
    window.title_corner.installEventFilter(spy)
    QApplication.sendEvent(tools, QEvent(QEvent.LayoutRequest))

    assert hides, "a layout request re-places the corner"
    assert window.title_corner.isVisible()


def _with_row(window):
    window.toolbar = FXCommandRow("Toolbar")
    window.addToolBar(Qt.TopToolBarArea, window.toolbar)
    return window


def _icon_button():
    button = QPushButton()
    button.setIcon(fxicons.get_icon("arrow_back"))
    return button


def test_a_framed_window_flattens_icon_only_buttons_on_its_bands(qtbot):
    window = _shown(qtbot, _with_row(FXMainWindow(framed=True)))
    early, worded = _icon_button(), QPushButton("Run")
    window.toolbar.addWidget(early)
    window.toolbar.addWidget(worded)
    holder = QWidget()
    QHBoxLayout(holder).addWidget(later := _icon_button())
    QApplication.processEvents()
    window.toolbar.addWidget(holder)
    on_bar = _icon_button()
    window.statusBar().addPermanentWidget(on_bar)
    QApplication.processEvents()

    assert early.property("fxRole") == "flat"
    assert later.property("fxRole") == "flat", "nested and added after show"
    assert on_bar.property("fxRole") == "flat"
    assert worded.property("fxRole") is None


def test_a_button_given_a_role_keeps_it(qtbot):
    window = _shown(qtbot, _with_row(FXMainWindow(framed=True)))
    primary = _icon_button()
    primary.setProperty("fxRole", "primary")

    window.toolbar.addWidget(primary)
    QApplication.processEvents()

    assert primary.property("fxRole") == "primary"


def test_an_unframed_window_leaves_its_buttons_alone(qtbot):
    window = _shown(qtbot, _with_row(FXMainWindow()))
    button = _icon_button()

    window.toolbar.addWidget(button)
    QApplication.processEvents()

    assert button.property("fxRole") is None


@pytest.mark.parametrize("framed", [False, True])
@pytest.mark.parametrize("theme", ["dark", "github_light"])
def test_corner_tools_show_the_menu_bar_through(qtbot, framed, theme):
    fxstyle.apply_theme(theme)
    window = FXMainWindow(framed=framed)
    tools = _corner_tools(qtbot, window)
    idle = tools.addAction(fxicons.get_icon("play_arrow"), "Run")
    idle.setEnabled(False)
    _shown(qtbot, window)
    bar = window.menuBar()
    image = window.grab().toImage()

    def seen(widget, point):
        return QColor(image.pixel(widget.mapTo(window, point))).name()

    ground = seen(bar, QPoint(bar.width() // 2, 2))
    assert seen(tools, QPoint(0, 1)) == ground, "the toolbar has no fill"
    button = tools.widgetForAction(idle)
    assert seen(button, QPoint(1, button.height() // 2)) == ground, (
        "a disabled tool keeps no fill of its own")
