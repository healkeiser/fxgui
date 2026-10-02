"""Every space between widgets is the one pane gap."""

# Third-party
from qtpy.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Internal
from fxgui import fxdocking, fxstyle
from fxgui.fxwidgets import FXFilteredTree


def test_a_default_layout_under_the_style_spaces_one_pane_gap(app_root):
    for kind in (QVBoxLayout, QHBoxLayout):
        host = QWidget(app_root)
        layout = kind(host)
        layout.addWidget(QLabel("one"))
        layout.addWidget(QLabel("two"))
        assert layout.spacing() == fxstyle.PANE_GAP, kind


def test_a_filtered_trees_bar_stands_one_pane_gap_above_its_tree(
        qtbot, app_root):
    panel = FXFilteredTree()
    app_root.layout().addWidget(panel)
    app_root.resize(300, 200)
    app_root.show()
    qtbot.waitExposed(app_root)
    bar = panel.filter_bar.geometry()
    assert panel.tree.geometry().top() - bar.bottom() - 1 == fxstyle.PANE_GAP


def test_a_dock_area_defaults_to_the_pane_gap():
    assert fxdocking.FXDockArea()._gap == fxstyle.PANE_GAP
