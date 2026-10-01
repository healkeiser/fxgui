"""A host's sheet on the window an FXMainWindow is parented to changes nothing.

Houdini sets its base.qss on its main window, and a Qt child inherits its
parent's sheet for every property its own sheet leaves open.
"""

# Built-in
import re
import sys
from pathlib import Path

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QActionGroup, QColor, QCursor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets import FXMainWindow, FXStatusItem

_SIDEFX = Path("C:/Program Files/Side Effects Software")


def _houdini_sheets():
    """Return Houdini's own sheets: rules from base.qss, and each install's."""
    # The rules of Houdini 21's base.qss that fxgui's sheet leaves open.
    rules = ("QToolButton { width: 17px; height: 17px; margin: 1px; }"
             " QMenu::separator { margin: 4px 0px 4px 0px; }"
             " QMenu::indicator { margin-left: 7px; }"
             " QMenu::indicator:unchecked { border: 1px solid black; }"
             " QMenuBar { border: 1px solid black; padding: 0px 1px; }"
             " QLabel { color: #ff0000; }")
    sheets = [pytest.param(rules, id="rules")]
    for path in sorted(_SIDEFX.glob("Houdini */houdini/config/Styles/base.qss")):
        # Houdini fills its @tokens@ in; any colour stands in for one.
        text = re.sub(r"@(\d+px)@", r"\1", path.read_text(encoding="utf-8"))
        text = re.sub(r"@[^@\s]+@", "128, 128, 128", text)
        sheets.append(pytest.param(text, id=path.parts[-5]))
    if len(sheets) == 1:
        skip = pytest.mark.skip(reason="no Houdini install")
        sheets.append(pytest.param("", id="houdini", marks=skip))
    return sheets


def test_a_machine_without_houdini_skips_its_sheets_by_name(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(sys.modules[__name__], "_SIDEFX", tmp_path)
    marks = [mark for sheet in _houdini_sheets() for mark in sheet.marks]
    assert [mark.kwargs.get("reason") for mark in marks] == ["no Houdini install"]


def _host(qtbot, sheet):
    host = QMainWindow()
    qtbot.addWidget(host)
    host.setStyleSheet(sheet)
    host.show()
    qtbot.waitExposed(host)
    return host


def _shown(qtbot, window, size=(1100, 800)):
    qtbot.addWidget(window)
    window.resize(*size)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(20)
    return window


class _Probe(FXMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent, framed=True, project="Show")
        self.setCentralWidget(QLabel("body"))
        item = FXStatusItem()
        self.statusBar().add_item(item)
        item.show_state("Valentin Beaumont", "cloud_done")


@pytest.mark.parametrize("sheet", _houdini_sheets())
def test_a_host_s_sheet_stays_out_of_a_window_it_owns(qtbot, sheet):
    host = _host(qtbot, sheet)
    free = _shown(qtbot, _Probe())
    held = _shown(qtbot, _Probe(parent=host))

    def looks(window):
        label = window.statusBar().message_label
        label.ensurePolished()
        widgets = [*window.findChildren(QToolButton),
                   *window.findChildren(QMenu), window.menuBar()]
        return [label.palette().color(label.foregroundRole()),
                *[(type(w).__name__, w.sizeHint()) for w in widgets]]

    assert held.parent() is host
    assert looks(held) == looks(free)


def _gallery():
    """Return one of each control a window holds, by name."""
    spin = QSpinBox()
    spin.setValue(25)
    combo = QComboBox()
    combo.addItems(["one", "two"])
    menu_push = QPushButton("Menu")
    menu_push.setMenu(QMenu(menu_push))
    split = QToolButton()
    split.setText("Split")
    split.setMenu(QMenu(split))
    split.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
    check = QCheckBox("Check")
    check.setChecked(True)
    radio = QRadioButton("Radio")
    radio.setChecked(True)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setValue(30)
    upright = QSlider(Qt.Orientation.Vertical)
    upright.setValue(30)
    group = QGroupBox("Group")
    QVBoxLayout(group).addWidget(QLabel("inside"))
    progress = QProgressBar()
    progress.setValue(40)
    tree = QTreeWidget()
    tree.setColumnCount(6)
    tree.setHeaderLabels([f"Column {n}" for n in range(6)])
    items = [QTreeWidgetItem([f"row {n}"] * 6) for n in range(40)]
    tree.addTopLevelItems(items)
    items[0].addChildren([QTreeWidgetItem(["child"]) for _ in range(2)])
    tree.expandAll()
    tree.setSortingEnabled(True)
    tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    table = QTableWidget(20, 6)
    table.setAlternatingRowColors(True)
    listed = QListWidget()
    listed.addItems([f"item {n}" for n in range(30)])
    listed.setAlternatingRowColors(True)
    editable = QComboBox()
    editable.setEditable(True)
    editable.addItems(["typed"])
    # A selected row too: the host styles selection its own way.
    tree.setCurrentItem(items[1])
    table.selectRow(1)
    listed.setCurrentRow(1)
    tabs = QTabWidget()
    tabs.addTab(QLabel("first"), "First")
    tabs.addTab(QLabel("second"), "Second")
    splitter = QSplitter()
    splitter.addWidget(QLabel("left"))
    splitter.addWidget(QLabel("right"))
    return {
        "spin": spin, "double": QDoubleSpinBox(), "combo": combo,
        "edit": QLineEdit("text"), "push": QPushButton("Push"),
        "menu_push": menu_push, "split": split, "check": check,
        "radio": radio, "slider": slider, "progress": progress,
        "tree": tree, "tabs": tabs, "group": group, "upright": upright,
        "text": QPlainTextEdit("line\n" * 60), "splitter": splitter,
        "label": QLabel("Label"), "table": table, "list": listed,
        "editable": editable, "rich": QTextEdit("rich\n" * 60),
    }


def _menu(parent):
    """Return a menu with every kind of entry: icon, ticks, rule, submenu."""
    menu = QMenu(parent)
    menu.addAction(fxicons.get_icon("refresh"), "With an icon")
    ticked = menu.addAction("Ticked")
    ticked.setCheckable(True)
    ticked.setChecked(True)
    menu.addAction("Unticked").setCheckable(True)
    group = QActionGroup(menu)
    for text in ("One of two", "Two of two"):
        choice = menu.addAction(text)
        choice.setCheckable(True)
        group.addAction(choice)
    menu.addSeparator()
    menu.addMenu(QMenu("More", menu))
    return menu


class _Gallery(_Probe):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        body = QWidget()
        grid = QGridLayout(body)
        self.gallery = _gallery()
        for index, widget in enumerate(self.gallery.values()):
            # No focus ring on one window and not the other.
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            grid.addWidget(widget, index // 3, index % 3)
        for name in ("tree", "text", "table", "list", "rich"):
            self.gallery[name].setFixedSize(260, 120)
        self.setCentralWidget(body)
        self.menu = _menu(self)


@pytest.mark.parametrize("sheet", _houdini_sheets())
def test_a_host_s_sheet_changes_no_pixel_of_a_control(qtbot, sheet):
    host = _host(qtbot, sheet)
    free = _shown(qtbot, _Gallery(), (1200, 900))
    held = _shown(qtbot, _Gallery(parent=host), (1200, 900))
    qtbot.wait(50)

    def looks(window):
        window.menu.popup(window.mapToGlobal(QPoint(0, 0)))
        qtbot.waitExposed(window.menu)
        shown = {name: widget.grab().toImage()
                 for name, widget in window.gallery.items()}
        shown.update({"menu": window.menu.grab().toImage(),
                      "menu_bar": window.menuBar().grab().toImage(),
                      "status_bar": window.statusBar().grab().toImage()})
        window.menu.close()
        return shown

    before, after = looks(free), looks(held)

    changed = [name for name in before if before[name] != after[name]]
    assert not changed, f"the host's sheet changed the pixels of {changed}"


def test_a_window_reparented_into_a_host_takes_the_reset(qtbot):
    host = _host(qtbot, _houdini_sheets()[0].values[0])
    free = _shown(qtbot, _Probe())
    moved = _Probe()
    moved.setParent(host, moved.windowFlags())
    _shown(qtbot, moved)

    button = [b for b in moved.findChildren(QToolButton) if b.isVisible()][0]
    twin = [b for b in free.findChildren(QToolButton) if b.isVisible()][0]
    assert button.sizeHint() == twin.sizeHint()
    assert QApplication.instance() is not None


@pytest.mark.parametrize("sheet", _houdini_sheets())
def test_a_table_cell_background_shows_under_a_host_s_sheet(qtbot, sheet):
    host = _host(qtbot, sheet)
    window = _Probe(parent=host)
    table = QTableWidget(2, 1)
    item = QTableWidgetItem("cell")
    item.setBackground(QColor("#aa3333"))
    table.setItem(0, 0, item)
    window.setCentralWidget(table)
    _shown(qtbot, window, (400, 300))

    rect = table.visualItemRect(item)
    image = table.viewport().grab().toImage()
    for x in (rect.center().x(), rect.right()):
        assert image.pixelColor(x, rect.center().y()).name() == "#aa3333"


def _three_rows(build):
    view = build()
    texts = ["own", "selected", "hovered"]
    if isinstance(view, QTableWidget):
        view.setRowCount(3)
        view.setColumnCount(1)
        items = [QTableWidgetItem(text) for text in texts]
        for row, item in enumerate(items):
            view.setItem(row, 0, item)
    elif isinstance(view, QTreeWidget):
        view.setColumnCount(1)
        items = [QTreeWidgetItem([text]) for text in texts]
        view.addTopLevelItems(items)
    else:
        view.addItems(texts)
        items = [view.item(row) for row in range(3)]
    if isinstance(view, QTreeWidget):
        items[0].setBackground(0, QColor("#aa3333"))
    else:
        items[0].setBackground(QColor("#aa3333"))
    return view, items


def _rect(view, item):
    return view.visualItemRect(item)


@pytest.mark.parametrize("build", [QTableWidget, QTreeWidget, QListWidget])
@pytest.mark.parametrize("sheet", _houdini_sheets())
def test_selection_and_hover_wear_the_theme_under_a_host_s_sheet(
    qtbot, sheet, build
):
    host = _host(qtbot, sheet)
    window = _Probe(parent=host)
    view, items = _three_rows(build)
    window.setCentralWidget(view)
    _shown(qtbot, window, (400, 300))
    view.setCurrentItem(items[1])
    QTest.mouseMove(window, QPoint(1, 1))
    hovered = _rect(view, items[2])
    QTest.mouseMove(view.viewport(), hovered.center())
    qtbot.waitUntil(
        lambda: view.indexAt(view.viewport().mapFromGlobal(
            QCursor.pos())) == view.indexFromItem(items[2])
        if hasattr(view, "indexFromItem") else True, timeout=1000)
    qtbot.wait(20)

    image = view.viewport().grab().toImage()

    def fill(item):
        rect = _rect(view, item)
        return image.pixelColor(rect.right() - 2, rect.center().y()).name()

    theme = fxstyle.colors()
    assert fill(items[0]) == "#aa3333", "an unselected cell keeps its own"
    assert fill(items[1]) == QColor(theme.accent_primary).name()
    assert fill(items[2]) == QColor(theme.accent_secondary).name()
    other = QMainWindow()
    qtbot.addWidget(other)
    other.show()
    other.activateWindow()
    qtbot.waitUntil(lambda: not window.isActiveWindow(), timeout=1000)
    image = view.viewport().grab().toImage()
    assert fill(items[1]) == QColor(theme.accent_primary).name(), (
        "an inactive selection wears the theme too")
