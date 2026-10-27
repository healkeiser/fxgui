"""A delegate row is flat and runs edge to edge, its indentation included."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate
from fxgui.fxwidgets._delegates import _hover_on

from _helpers import hover, near, themed_window

# Any well but the sheet's own `surface_sunken`, as a docked pane's is.
_WELL = "#2b5d34"


def _rule_on(
    ground: str, alpha: float = FXThumbnailDelegate._RULE_ALPHA
) -> QColor:
    """Return the hairline's `border` at `alpha`, laid over `ground`."""
    under, ink = QColor(ground), QColor(fxstyle.colors().border)
    return QColor(*(
        round(a * alpha + b * (1 - alpha))
        for a, b in zip(ink.getRgb()[:3], under.getRgb()[:3])
    ))


def _well_view(qtbot, theme, band, nested=False):
    view = QTreeWidget()
    view.setObjectName("well")
    view.setHeaderHidden(True)
    view.setRootIsDecorated(nested)
    view.setItemDelegate(FXThumbnailDelegate())
    FXThumbnailDelegate.apply_transparent_selection(view)
    rows = [QTreeWidgetItem(view, [f"Row{index}"]) for index in range(3)]
    if nested:
        rows.append(QTreeWidgetItem(rows[0], ["Child"]))
        view.expandAll()
    if band:
        for row in rows:
            row.setData(0, Qt.BackgroundRole, "surface")
    view.setStyleSheet(f"#well {{ background-color: {_WELL}; }}")
    window = themed_window(qtbot, theme, view)
    return window, view, rows


def _at(image, view, point):
    viewport = view.viewport()
    return QColor(image.pixel(viewport.mapTo(view.window(), point))).name()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("band", [True, False])
@pytest.mark.parametrize("state", ["rest", "hover", "selected"])
def test_a_rows_top_corners_wear_its_own_fill(qtbot, theme, band, state):
    window, view, rows = _well_view(qtbot, theme, band)
    item = rows[1]
    if state == "selected":
        item.setSelected(True)
    elif state == "hover":
        hover(qtbot, view.viewport(), view.visualItemRect(item).center())
    image = window.grab().toImage()
    colors = fxstyle.colors()
    ground = colors.surface if band else _WELL
    fill = {
        "rest": ground,
        "hover": _hover_on(QColor(ground) if band else None),
        "selected": colors.selection,
    }[state]
    rect = view.visualItemRect(item)
    corners = {_at(image, view, point)
               for point in (rect.topLeft(), rect.topRight())}
    assert corners == {QColor(fill).name()}


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_frame_s_round_corner_shows_over_a_banded_first_row(qtbot, theme):
    """The first row's band stops at the frame's arc, not at a square."""
    window, view, rows = _well_view(qtbot, theme, band=False)
    band = "#ff0000"
    rows[0].setData(0, Qt.BackgroundRole, band)
    view.viewport().update()
    qtbot.wait(50)
    image = window.grab().toImage()
    rect = view.visualItemRect(rows[0])
    assert _at(image, view, rect.topLeft()) != band
    inside = rect.topLeft() + QPoint(fxstyle.BUTTON_RADIUS, 2)
    assert _at(image, view, inside) == band


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_hairline_runs_under_every_row(qtbot, theme):
    window, view, rows = _well_view(qtbot, theme, band=False)
    image = window.grab().toImage()
    rule = _rule_on(_WELL)
    for item in rows:
        rect = view.visualItemRect(item)
        bottom = {
            _at(image, view, rect.bottomLeft() + QPoint(x, 0))
            for x in range(rect.width())
        }
        assert all(near(ink, rule, 1) for ink in bottom), bottom
        # Mid-top: the view's first corner is rounded over the row.
        top = QPoint(rect.center().x(), rect.top())
        assert _at(image, view, top) in (_WELL, rule.name())


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_nested_row_runs_under_its_indentation(qtbot, theme):
    window, view, rows = _well_view(qtbot, theme, band=False, nested=True)
    child = rows[-1]
    child.setSelected(True)
    image = window.grab().toImage()
    rect = view.visualItemRect(child)
    assert rect.left() > 2, "the child is indented"
    selection = QColor(fxstyle.colors().selection).name()
    middle = rect.center().y()
    # From the view's own edge, not from the indented cell.
    assert _at(image, view, QPoint(1, middle)) == selection
    assert near(
        QColor(_at(image, view, QPoint(1, rect.bottom()))),
        _rule_on(selection, FXThumbnailDelegate._NESTED_RULE_ALPHA),
        1,
    )


def _band_fill(qtbot, theme, fill):
    """Return the fill at a banded row's middle, in a themed root."""
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
    rect = tree.visualItemRect(item)
    image = tree.viewport().grab().toImage()
    return image.pixelColor(rect.right() - 4, rect.center().y()).name()


def test_a_token_background_follows_a_theme_switch(qtbot):
    _band_fill(qtbot, "dark", "surface")
    fill = _band_fill(qtbot, "light", "surface")
    assert fill == fxstyle.colors().surface.lower()


@pytest.mark.parametrize("size", ["small", "normal"])
def test_a_one_line_row_sets_its_count_left_of_its_dot(qtbot, size):
    """The count and the status dot share the line, never a pixel."""
    fxstyle.apply_row_size(size)
    try:
        window, view, rows = _well_view(qtbot, "dark", band=False)
        delegate = view.itemDelegate()
        row = rows[0]
        row.setData(0, FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE, "#00ff00")
        for index in range(12):
            QTreeWidgetItem(row, [f"Child{index}"])
        view.viewport().update()
        qtbot.wait(50)
        image = window.grab().toImage()
        rect = view.visualItemRect(row)
        _label_x, dot_x = delegate._indicator_left(
            rect, 0, delegate._DOT_SIZE)
        ink = QColor(fxstyle.colors().text_muted)
        dot = [
            QColor(_at(image, view, QPoint(x, y)))
            for x in range(dot_x, dot_x + delegate._DOT_SIZE)
            for y in range(rect.top(), rect.bottom())
        ]
        assert not any(near(pixel, ink, 30) for pixel in dot)
    finally:
        fxstyle.apply_row_size("normal")
