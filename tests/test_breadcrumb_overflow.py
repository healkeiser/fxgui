"""A path too long for its bar keeps the current segment in view."""

# Third-party
from qtpy.QtCore import QPoint
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

# Internal
from fxgui.fxwidgets import FXBreadcrumb, FXMainWindow
from fxgui.fxwidgets._breadcrumb import _Segment


def _right_edge_in_view(crumb) -> tuple:
    viewport = crumb._scroll_area.viewport()
    shown = [s for s in crumb._container.findChildren(_Segment) if s.isVisible()]
    last = shown[-1]
    return last.mapTo(viewport, QPoint(last.width(), 0)).x(), viewport.width()


def test_the_current_segment_stays_in_a_narrowed_bar(qtbot):
    window = FXMainWindow(title="Path")
    host = QWidget()
    column = QVBoxLayout(host)
    crumb = FXBreadcrumb()
    column.addWidget(crumb)
    column.addStretch()
    window.setCentralWidget(host)
    qtbot.addWidget(window)
    window.resize(900, 300)
    window.show()
    qtbot.waitExposed(window)
    crumb.set_path(["Projects", "Lumi", "sequences", "sq0100",
                    "sh0100_long_shot_name", "lighting"])
    QApplication.processEvents()
    # Narrowed, and a path set while narrow: the end is where the path is.
    window.resize(330, 300)
    QApplication.processEvents()
    right, room = _right_edge_in_view(crumb)
    assert right <= room
    crumb.set_path(["Projects", "Lumi", "sequences", "sq0200",
                    "sh0200_another_long_name", "compositing"])
    QApplication.processEvents()
    right, room = _right_edge_in_view(crumb)
    assert right <= room
