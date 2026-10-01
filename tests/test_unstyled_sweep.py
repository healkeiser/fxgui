"""Every standard Qt widget, and every part Qt builds itself, wears a theme fill.

One window of every widget, in every bundled theme: the colour covering most
of each widget, popup and built-in part has to be one of the theme's tokens.
A widget class the sheet should reach is checked by adding it here.
"""

# Built-in
from collections import Counter

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect, Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QKeySequenceEdit,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMdiArea,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizeGrip,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QTableView,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QToolBar,
    QToolBox,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

# Internal
from fxgui import fxstyle


def _theme_inks(theme):
    return {
        value.lower()
        for value in fxstyle._token_map(theme).values()
        if value.startswith("#") and len(value) == 7
    }


def _dominant(image, rect=None):
    """Return the colour covering most of `rect`, sampled every 2 px."""
    rect = rect or image.rect()
    counts = Counter(
        image.pixelColor(x, y).name()
        for x in range(rect.left(), rect.right() + 1, 2)
        for y in range(rect.top(), rect.bottom() + 1, 2)
    )
    return counts.most_common(1)[0][0]


def _plain_widgets():
    """Return {name: widget} for a widget of every standard class."""
    tree = QTreeWidget()
    QTreeWidgetItem(tree, ["row"])
    listing = QListWidget()
    listing.addItems([f"row {index}" for index in range(30)])
    area = QScrollArea()
    held = QWidget()
    held.setMinimumSize(800, 800)
    area.setWidget(held)
    tabs = QTabWidget()
    for index in range(12):
        tabs.addTab(QWidget(), f"A long tab name {index}")
    toolbox = QToolBox()
    toolbox.addItem(QWidget(), "Page")
    splitter = QSplitter()
    splitter.addWidget(QWidget())
    splitter.addWidget(QWidget())
    date = QDateEdit()
    date.setCalendarPopup(True)
    combo = QComboBox()
    combo.addItems([f"item {index}" for index in range(40)])
    return {
        "QPushButton": QPushButton("Push"),
        "QToolButton": QToolButton(),
        "QCheckBox": QCheckBox("Check"),
        "QRadioButton": QRadioButton("Radio"),
        "QLineEdit": QLineEdit(),
        "QTextEdit": QTextEdit(),
        "QPlainTextEdit": QPlainTextEdit(),
        "QComboBox": combo,
        "QFontComboBox": QFontComboBox(),
        "QSpinBox": QSpinBox(),
        "QDoubleSpinBox": QDoubleSpinBox(),
        "QDateEdit": date,
        "QTimeEdit": QTimeEdit(),
        "QDateTimeEdit": QDateTimeEdit(),
        "QKeySequenceEdit": QKeySequenceEdit(),
        "QSlider": QSlider(Qt.Horizontal),
        "QDial": QDial(),
        "QProgressBar": QProgressBar(),
        "QLCDNumber": QLCDNumber(),
        "QLabel": QLabel("Label"),
        "QFrame": QFrame(),
        "QGroupBox": QGroupBox("Group"),
        "QTabWidget": tabs,
        "QToolBox": toolbox,
        "QListWidget": listing,
        "QTreeWidget": tree,
        "QTableWidget": QTableWidget(30, 8),
        "QScrollArea": area,
        "QSplitter": splitter,
        "QCalendarWidget": QCalendarWidget(),
        "QMdiArea": QMdiArea(),
    }


def _window(qtbot, theme):
    fxstyle.apply_theme(theme)
    window = QMainWindow()
    fxstyle.register_themed_root(window)
    qtbot.addWidget(window)
    body = QWidget()
    grid = QGridLayout(body)
    widgets = _plain_widgets()
    for index, widget in enumerate(widgets.values()):
        widget.setMinimumSize(120, 70)
        grid.addWidget(widget, index // 6, index % 6)
    window.setCentralWidget(body)
    toolbar = QToolBar("Tools")
    for index in range(30):
        toolbar.addAction(f"Tool {index}")
    window.addToolBar(toolbar)
    status = QStatusBar()
    status.setSizeGripEnabled(True)
    window.setStatusBar(status)
    dock = QDockWidget("Dock")
    dock.setWidget(QLabel("docked"))
    window.addDockWidget(Qt.LeftDockWidgetArea, dock)
    menu = window.menuBar().addMenu("File")
    menu.addAction("Open")
    window.resize(1000, 760)
    window.show()
    qtbot.waitExposed(window)
    # The window holds focus, so no widget wears its focus look.
    window.setFocus()
    QApplication.processEvents()
    return window, widgets, toolbar, dock, menu


def _parts(window, widgets, toolbar, dock):
    """Return (name, widget, rect) for the parts Qt builds inside widgets."""
    corner = widgets["QTableWidget"].findChild(QAbstractButton)
    parts = [("table corner button", corner, corner.rect())]
    for name in ("QScrollArea", "QTableWidget"):
        area = widgets[name]
        bar = area.verticalScrollBar()
        if bar.isVisible() and area.horizontalScrollBar().isVisible():
            # The square between the two bars, in the area's coordinates.
            spot = QRect(
                bar.mapTo(area, QPoint(0, bar.height())),
                bar.mapTo(area, QPoint(bar.width() - 1, bar.height() + 5)),
            )
            parts.append((f"{name} corner", area, spot))
    for button in widgets["QTabWidget"].tabBar().findChildren(QToolButton):
        if button.isVisible():
            parts.append(("tab scroll button", button, button.rect()))
    for button in toolbar.findChildren(QToolButton):
        if button.metaObject().className() == "QToolBarExtension":
            parts.append(("toolbar extension", button, button.rect()))
    for grip in window.findChildren(QSizeGrip):
        if grip.isVisible():
            parts.append(("size grip", grip, grip.rect()))
    calendar = widgets["QCalendarWidget"].findChild(QTableView)
    header = calendar.visualRect(calendar.model().index(0, 1))
    parts.append(("calendar header", calendar.viewport(), header))
    title = dock.style().pixelMetric(QStyle.PM_TitleBarHeight, None, dock)
    parts.append(("dock title bar", dock, QRect(0, 0, dock.width(), title)))
    return parts


def _popups(qtbot, window, widgets, menu):
    """Open each popup Qt builds, one batch at a time: (name, widget)."""
    combo = widgets["QComboBox"]
    combo.showPopup()
    qtbot.waitUntil(lambda: combo.view().isVisible())
    popup = combo.view().window()
    shown = [("combo popup", popup)]
    for scroller in popup.findChildren(QWidget):
        if scroller.metaObject().className() == "QComboBoxPrivateScroller":
            if scroller.isVisible():
                shown.append(("combo scroll arrow", scroller))
    yield shown
    combo.hidePopup()

    line = widgets["QLineEdit"]
    completer = QCompleter(["alpha", "alpine", "altitude"], line)
    line.setCompleter(completer)
    completer.setCompletionPrefix("al")
    completer.complete()
    qtbot.waitUntil(lambda: completer.popup().isVisible())
    yield [("completer popup", completer.popup())]
    completer.popup().hide()

    date = widgets["QDateEdit"]
    # A click on the arrow opens the calendar.
    QTest.mouseClick(
        date, Qt.LeftButton, Qt.NoModifier,
        QPoint(date.width() - 8, date.height() // 2),
    )
    calendar = date.calendarWidget()
    qtbot.waitUntil(calendar.isVisible)
    yield [("date edit calendar", calendar.window())]
    calendar.window().hide()

    menu.setTearOffEnabled(True)
    menu.popup(window.mapToGlobal(QPoint(20, 20)))
    qtbot.waitExposed(menu)
    yield [("menu with tear-off", menu)]
    menu.close()
    menu.showTearOffMenu(window.mapToGlobal(QPoint(40, 40)))
    QApplication.processEvents()
    torn = [
        widget
        for widget in QApplication.topLevelWidgets()
        if widget.metaObject().className() == "QTornOffMenu"
        and widget.isVisible()
    ]
    assert torn
    yield [("torn-off menu", widget) for widget in torn]
    for widget in torn:
        widget.close()

    box = QMessageBox(QMessageBox.Information, "Note", "A message")
    box.setParent(window, box.windowFlags())
    box.show()
    qtbot.waitExposed(box)
    dialog = QFileDialog(window)
    dialog.setOption(QFileDialog.DontUseNativeDialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    yield [("QMessageBox", box), ("QFileDialog", dialog)]
    box.close()
    dialog.close()


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_every_widget_and_part_wears_a_theme_fill(qtbot, theme):
    window, widgets, toolbar, dock, menu = _window(qtbot, theme)
    inks = _theme_inks(theme)
    image = window.grab().toImage()
    wrong = {}
    for name, widget in widgets.items():
        rect = widget.rect().translated(widget.mapTo(window, QPoint()))
        ink = _dominant(image, rect)
        if ink not in inks:
            wrong[name] = ink
    for name, widget, rect in _parts(window, widgets, toolbar, dock):
        ink = _dominant(image, rect.translated(widget.mapTo(window, QPoint())))
        if ink not in inks:
            wrong[name] = ink
    for shown in _popups(qtbot, window, widgets, menu):
        for name, widget in shown:
            ink = _dominant(widget.grab().toImage())
            if ink not in inks:
                wrong[name] = ink
    assert not wrong, wrong
