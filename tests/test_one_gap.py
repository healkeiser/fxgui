"""Every space between widgets is the one pane gap."""

# Third-party
import pytest
from qtpy.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFilteredTree


def test_a_default_layout_under_the_style_spaces_one_pane_gap(app_root):
    for kind in (QVBoxLayout, QHBoxLayout):
        host = QWidget(app_root)
        layout = kind(host)
        layout.addWidget(QLabel("one"))
        layout.addWidget(QLabel("two"))
        assert layout.spacing() == fxstyle.PANE_GAP, kind


@pytest.mark.parametrize("styled", [True, False])
def test_a_filtered_trees_bar_stands_one_pane_gap_above_its_tree(
        qtbot, request, styled):
    # Unstyled is a host's own style, as inside a DCC.
    window = request.getfixturevalue("app_root") if styled else QWidget()
    if not styled:
        qtbot.addWidget(window)
        QVBoxLayout(window)
    panel = FXFilteredTree()
    window.layout().addWidget(panel)
    window.resize(300, 200)
    window.show()
    qtbot.waitExposed(window)
    bar = panel.filter_bar.geometry()
    assert panel.tree.geometry().top() - bar.bottom() - 1 == fxstyle.PANE_GAP


def test_a_dock_area_defaults_to_the_pane_gap():
    pytest.importorskip("PySide6QtAds")
    from fxgui import fxdocking

    assert fxdocking.FXDockArea()._gap == fxstyle.PANE_GAP
