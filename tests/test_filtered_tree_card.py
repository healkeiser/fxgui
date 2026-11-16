"""An FXFilteredTree reads as one card: a rule under its bar, its actions in."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, QRect
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXFilteredTree, FXSummaryRow

from _helpers import near, pixel, themed_window


def _filtered(qtbot, theme="dark", flush=False, summary=False, button=None):
    actions = None
    if button is not None:
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(button)
    filtered = FXFilteredTree(actions=actions)
    tree = filtered.tree
    tree.setHeaderLabels(["Shot", "Status"])
    for row in range(3):
        QTreeWidgetItem(tree, [f"sh{row:03d}0", "WIP"])
    if flush:
        fxstyle.mark_flush(tree)
    if summary:
        FXSummaryRow(tree).set_texts(["3 shots", ""])
    window = themed_window(qtbot, theme, filtered, size=(360, 320))
    return filtered, window


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_flush_trees_header_has_a_rule_under_the_bar(qtbot, theme):
    filtered, window = _filtered(qtbot, theme, flush=True)
    tree, border = filtered.tree, fxstyle.colors().border
    for x in (0, tree.width() // 2, tree.width() - 1):
        assert near(pixel(window, tree, x, 0), border, 2), x
    assert not near(pixel(window, tree, tree.width() // 2, 1), border, 2)
    # Its frame back, the card's edge is the rule: no second one.
    fxstyle.mark_flush(tree, False)
    assert not near(pixel(window, tree, tree.width() // 2, 1), border, 2)
    assert near(pixel(window, tree, tree.width() // 2, 0), border, 2)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("summary", [True, False])
def test_the_actions_are_the_cards_footer(qtbot, theme, summary):
    button = QPushButton("Open")
    filtered, window = _filtered(
        qtbot, theme, summary=summary, button=button)
    tree = filtered.tree
    footer = tree.findChild(QFrame, "fxTreeActions")
    frame = tree.frameWidth()
    inside = tree.rect().adjusted(frame, frame, -frame, -frame)
    placed = QRect(button.mapTo(tree, QPoint(0, 0)), button.size())
    assert inside.contains(placed)
    # Under the summary band, or the rows, down to the card's bottom edge.
    above = tree.findChild(FXSummaryRow) if summary else tree.viewport()
    assert footer.geometry().top() == above.geometry().bottom() + 1
    assert footer.geometry().bottom() == inside.bottom()
    colors = fxstyle.colors()
    middle = button.geometry().center().y()
    assert near(pixel(window, footer, 4, middle), colors.surface_sunken, 2)
    assert near(pixel(window, footer, 4, 0), colors.border, 2)
    # The card's edge runs under the footer.
    assert near(
        pixel(window, tree, placed.center().x(), tree.height() - 1),
        colors.border, 2)
