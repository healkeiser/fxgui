"""A thumbnail row with a background shows its card in every theme."""

# Third-party
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate


def _card(qtbot, theme, fill, selected):
    """Return the row's pixels: its edge, its fill and the gap above it."""
    fxstyle.apply_theme(theme)
    root = QWidget()
    tree = QTreeWidget(root)
    QVBoxLayout(root).addWidget(tree)
    tree.setHeaderHidden(True)
    tree.setRootIsDecorated(False)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    FXThumbnailDelegate.apply_transparent_selection(tree)
    item = QTreeWidgetItem(tree, ["sh0010"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    item.setData(0, Qt.BackgroundRole, fill)
    fxstyle.register_themed_root(root)
    root.resize(300, 120)
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)
    item.setSelected(selected)
    rect = tree.visualItemRect(item)
    image = tree.viewport().grab().toImage()

    def at(x, y):
        return image.pixelColor(x, y).name()

    middle = rect.center().y()
    return {
        "edge": at(rect.center().x(), rect.top() + 1),
        "fill": at(rect.right() - 4, middle),
        "gap": at(rect.center().x(), rect.top()),
    }


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
@pytest.mark.parametrize("selected", [False, True])
def test_a_row_shows_its_card_fill_and_outline(qtbot, theme, selected):
    card = _card(qtbot, theme, "surface", selected)
    colors = fxstyle.colors()
    # The card stands on the well with a 1 px gap, selected or not.
    assert card["gap"] == colors.surface_sunken.lower()
    if selected:
        assert card["fill"] == card["edge"] == colors.accent_primary.lower()
    else:
        assert card["fill"] == colors.surface.lower()
        assert card["edge"] == colors.border_light.lower()


def test_a_token_background_follows_a_theme_switch(qtbot):
    _card(qtbot, "dark", "surface", False)
    card = _card(qtbot, "light", "surface", False)
    assert card["fill"] == fxstyle.colors().surface.lower()
