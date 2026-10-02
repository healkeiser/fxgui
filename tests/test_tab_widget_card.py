"""A tab widget is one pane card around its tabs and its page."""

# Third-party
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QLabel, QTabWidget

# Internal
from fxgui import fxstyle


def _shown(qtbot, app_root, document_mode=False):
    tabs = QTabWidget()
    tabs.setDocumentMode(document_mode)
    tabs.addTab(QLabel("page"), "One")
    tabs.addTab(QLabel("other"), "Two")
    app_root.layout().addWidget(tabs)
    app_root.resize(300, 200)
    app_root.show()
    qtbot.waitExposed(app_root)
    return tabs


def test_the_card_edge_runs_beside_the_tabs(qtbot, app_root):
    tabs = _shown(qtbot, app_root)
    shot = tabs.grab().toImage()
    edge = QColor(str(fxstyle.colors().pane_border)).name()
    beside_tabs = tabs.tabBar().geometry().center().y()

    assert shot.pixelColor(0, beside_tabs).name() == edge


def test_the_page_stands_one_gap_inside_the_card(qtbot, app_root):
    tabs = _shown(qtbot, app_root)
    page = tabs.currentWidget().mapTo(tabs, tabs.currentWidget().rect().topLeft())

    assert page.x() == fxstyle.PANE_GAP


def test_a_document_mode_tab_widget_draws_no_card(qtbot, app_root):
    tabs = _shown(qtbot, app_root, document_mode=True)
    shot = tabs.grab().toImage()
    edge = QColor(str(fxstyle.colors().pane_border)).name()
    beside_tabs = tabs.tabBar().geometry().center().y()

    assert shot.pixelColor(0, beside_tabs).name() != edge
