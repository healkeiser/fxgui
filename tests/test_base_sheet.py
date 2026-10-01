"""The base sheet carries shape and state; the palette and font the defaults."""

import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor, QFont, QPalette
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QListWidget,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fxgui import fxstyle


@pytest.fixture
def app_root(qtbot, qapp):
    """A window in an application fxgui themes, as FXApplication does."""
    sheet, font, palette = qapp.styleSheet(), qapp.font(), qapp.palette()
    style = qapp.style().name()
    fxstyle.apply_theme("dark")
    fxstyle.set_style(qapp, "Fusion")
    fxstyle.register_themed_root(qapp)
    window = QWidget()
    qtbot.addWidget(window)
    QVBoxLayout(window)
    yield window
    qapp.setStyleSheet(sheet)
    qapp.setFont(font)
    qapp.setPalette(palette)
    qapp.setStyle(style)


@pytest.fixture
def host_root(qtbot):
    """A window themed on its own inside an application fxgui leaves alone."""
    fxstyle.apply_theme("dark")
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    QVBoxLayout(window)
    return window


def _show(qtbot, root):
    root.resize(300, 200)
    root.show()
    qtbot.waitExposed(root)
    QApplication.processEvents()


def _card(root):
    card = QFrame(root)
    card.setObjectName("card")
    card.setStyleSheet("QFrame#card { background: #7a3b8f; }")
    label = QLabel("on the card", card)
    QVBoxLayout(card).addWidget(label)
    root.layout().addWidget(card)
    return label


def _tree(root):
    tree = QTreeWidget(root)
    tree.setHeaderHidden(True)
    item = QTreeWidgetItem(tree, ["row"])
    item.setBackground(0, QColor("#aa3333"))
    root.layout().addWidget(tree)
    return tree, item


def _item_fill(tree, item) -> str:
    rect = tree.visualItemRect(item)
    image = tree.viewport().grab().toImage()
    return image.pixelColor(rect.right() - 4, rect.center().y()).name()


def _label_fill(root, label) -> str:
    image = root.grab().toImage()
    return image.pixelColor(label.mapTo(root, QPoint(label.width() - 2, 1)))


def test_the_base_sheet_sets_no_background_or_font():
    sheet = fxstyle._build_stylesheet("dark")
    start = sheet.index("QWidget\n{")
    rule = sheet[start:sheet.index("}", start)]
    for prop in ("\n    background-color:", "font-size:", "font-family:"):
        assert prop not in rule, prop
    assert "* {\n    font-family" not in sheet


def test_set_font_is_honoured_in_a_themed_app(qtbot, app_root):
    label = QLabel("big", app_root)
    app_root.layout().addWidget(label)
    font = QFont(label.font())
    font.setPixelSize(20)
    font.setFamily("Courier New")
    label.setFont(font)
    _show(qtbot, app_root)
    assert label.font().pixelSize() == 20
    assert label.font().family() == "Courier New"


def test_a_plain_label_takes_the_theme_font_and_ink(qtbot, app_root):
    _show(qtbot, app_root)
    label = QLabel("made late", app_root)
    app_root.layout().addWidget(label)
    QApplication.processEvents()
    assert label.font().pixelSize() == fxstyle.FONT_SIZE
    assert label.font().family() == fxstyle.font().family()
    assert label.palette().color(QPalette.WindowText).name() == QColor(
        fxstyle.colors().text).name()
    fill = app_root.grab().toImage().pixelColor(1, 1).name()
    assert fill == QColor(fxstyle.colors().surface).name()


@pytest.mark.parametrize("where", ["app_root", "host_root"])
def test_a_plain_label_on_a_card_shows_the_card(qtbot, request, where):
    root = request.getfixturevalue(where)
    label = _card(root)
    _show(qtbot, root)
    assert _label_fill(root, label).name() == "#7a3b8f"


@pytest.mark.parametrize("where", ["app_root", "host_root"])
def test_an_item_background_shows(qtbot, request, where):
    root = request.getfixturevalue(where)
    tree, item = _tree(root)
    _show(qtbot, root)
    assert _item_fill(tree, item) == "#aa3333"


@pytest.fixture
def host_font(qapp):
    """The host application's own font, unlike the theme's."""
    font = QFont(qapp.font())
    qapp.setFont(QFont("Courier New", 15))
    yield qapp.font()
    qapp.setFont(font)


def test_a_page_moved_into_a_host_window_takes_the_theme(qtbot, host_font,
                                                         host_root):
    _show(qtbot, host_root)
    page = QScrollArea()
    page.setWidgetResizable(True)
    label = QLabel("moved in")
    page.setWidget(label)
    host_root.layout().addWidget(page)
    QApplication.processEvents()
    assert label.font().pixelSize() == fxstyle.FONT_SIZE
    assert label.font().family() == fxstyle.font().family()
    assert label.font().family() != host_font.family()
    assert label.palette().color(QPalette.WindowText).name() == QColor(
        fxstyle.colors().text).name()
    fill = _label_fill(host_root, label).name()
    assert fill == QColor(fxstyle.colors().surface).name()


def test_a_foreign_app_keeps_its_font_and_palette(qtbot, qapp, host_root):
    font = QFont(qapp.font())
    palette = QPalette(qapp.palette())
    fxstyle.apply_theme("light")
    assert qapp.font() == font
    assert qapp.palette() == palette
    assert qapp.styleSheet() == ""


@pytest.mark.parametrize("where", ["app_root", "host_root"])
def test_a_view_filled_before_it_is_shown_lays_its_rows_out_once_styled(
    qtbot, request, where
):
    root = request.getfixturevalue(where)
    view = QListWidget()
    view.addItems(["one", "two", "three"])
    root.layout().addWidget(view)
    _show(qtbot, root)
    qtbot.wait(20)
    first, second = (view.visualItemRect(view.item(i)) for i in (0, 1))
    assert second.top() == first.bottom() + 1
    assert first.height() == 26


@pytest.mark.parametrize("where", ["app_root", "host_root"])
def test_a_framed_window_keeps_an_unmarked_page_on_the_surface(
    qtbot, request, where
):
    from fxgui.fxwidgets import FXMainWindow

    request.getfixturevalue(where)
    window = FXMainWindow(framed=True)
    qtbot.addWidget(window)
    page, band = QWidget(), QWidget()
    fxstyle.mark_as_frame(band)
    QVBoxLayout(page).addWidget(band)
    band.setMinimumHeight(40)
    window.setCentralWidget(page)
    window.resize(300, 200)
    window.show()
    qtbot.waitExposed(window)
    image = window.grab().toImage()
    corner = page.mapTo(window, QPoint(page.width() - 2, page.height() - 2))
    inside = band.mapTo(window, QPoint(band.width() // 2, band.height() // 2))
    assert image.pixelColor(corner).name() == QColor(
        fxstyle.colors().surface).name()
    assert image.pixelColor(inside).name() == QColor(
        fxstyle.colors().frame).name()
