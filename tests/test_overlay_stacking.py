"""A loading line and a skeleton stay over what their view gains later."""

# Third-party
from qtpy.QtWidgets import (
    QApplication,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui.fxwidgets import FXMainWindow, FXSkeleton, FXTopProgress


def _shown(qtbot, body):
    window = FXMainWindow(title="Loading")
    window.setCentralWidget(body)
    qtbot.addWidget(window)
    window.resize(500, 300)
    window.show()
    qtbot.waitExposed(window)
    return window


def _settle():
    for _ in range(3):
        QApplication.processEvents()


def _on_top(parent) -> QWidget:
    """The visible child painted last, over its siblings."""
    return [
        child for child in parent.children()
        if isinstance(child, QWidget) and child.isVisible()
    ][-1]


def _pane():
    pane = QWidget()
    column = QVBoxLayout(pane)
    for n in range(4):
        column.addWidget(QLabel(f"row {n}"))
    return pane


def test_a_skeleton_covering_later_leaves_the_loading_line_on_top(qtbot):
    pane = _pane()
    _window = _shown(qtbot, pane)
    line = FXTopProgress(pane)
    line.set_value(0.5)
    FXSkeleton.cover(pane, "lines")
    _settle()
    assert _on_top(pane) is line


def test_a_loading_line_shown_on_a_covered_pane_stays_on_top(qtbot):
    pane = _pane()
    _window = _shown(qtbot, pane)
    FXSkeleton.cover(pane, "lines")
    line = FXTopProgress(pane)
    line.set_value(0.5)
    _settle()
    assert _on_top(pane) is line


def test_an_index_widget_added_under_a_skeleton_stays_covered(qtbot):
    tree = QTreeWidget()
    _window = _shown(qtbot, tree)
    skeleton = FXSkeleton.cover(tree)
    for n in range(4):
        QTreeWidgetItem(tree, [f"sh00{n}0"])
    tree.setItemWidget(tree.topLevelItem(1), 0, QLabel("OLD"))
    _settle()
    assert _on_top(tree.viewport()) is skeleton
