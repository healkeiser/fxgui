"""Every item view keeps all four frame corners round, scroll bars or not."""

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QListWidget,
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import fxstyle


def _view(kind, rows):
    if kind == "list":
        view = QListWidget()
        view.addItems([f"Row{index} " * (12 if rows > 1 else 1)
                       for index in range(rows)])
        return view
    if kind == "table":
        view = QTableWidget(rows, 6 if rows > 1 else 1)
        return view
    view = QTreeWidget()
    view.setColumnCount(6 if rows > 1 else 1)
    view.setHeaderHidden(kind == "tree")
    for index in range(rows):
        QTreeWidgetItem(view, [f"Row{index}"] * 6)
    return view


# Any well but the sheet's own, as a docked pane's is.
_WELL = "#2b5d34"


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("kind", ["headed tree", "tree", "table", "list"])
@pytest.mark.parametrize("bars", [False, True])
def test_a_views_four_corners_are_round(qtbot, app_root, theme, kind, bars):
    fxstyle.apply_theme(theme)
    view = _view(kind, 40 if bars else 1)
    view.setObjectName("well")
    view.setStyleSheet(f"#well {{ background-color: {_WELL}; }}")
    app_root.layout().addWidget(view)
    app_root.resize(*((160, 140) if bars else (320, 240)))
    app_root.show()
    qtbot.waitExposed(app_root)
    # The windows platform fills a viewport's whole rect; offscreen does not.
    view.viewport().setAutoFillBackground(True)
    qtbot.wait(20)
    window = app_root
    assert view.horizontalScrollBar().isVisible() == bars
    image = window.grab().toImage()
    box = view.geometry()
    # One pixel in from each corner is outside a rounded edge's arc.
    seen = {
        name: QColor(image.pixel(point)).name()
        for name, point in (
            ("top left", box.topLeft() + QPoint(1, 1)),
            ("top right", box.topRight() + QPoint(-1, 1)),
            ("bottom left", box.bottomLeft() + QPoint(1, -1)),
            ("bottom right", box.bottomRight() + QPoint(-1, -1)),
        )
    }
    assert _WELL not in seen.values(), seen
