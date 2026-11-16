"""A page reveals whatever kind of widget it is.

`_Reveal` snapshot a page with `render(pixmap, ...)`; a QGraphicsView's own
`render` takes a painter, so revealing a canvas page raised a TypeError.
"""

# Third-party
import time

import pytest
from qtpy.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
)

# Internal
from fxgui import fxstyle


@pytest.mark.parametrize("kind", [QGraphicsView, QTreeWidget, QTextEdit])
def test_a_page_of_any_kind_is_revealed(qtbot, host_root, motion, kind):
    pages = QStackedWidget()
    pages.addWidget(QLabel("first"))
    page = kind()
    if isinstance(page, QGraphicsView):
        scene = QGraphicsScene(page)
        scene.addText("node")
        page.setScene(scene)
    pages.addWidget(page)
    host_root.layout().addWidget(pages)
    host_root.resize(320, 240)
    host_root.show()
    qtbot.waitExposed(host_root)
    qtbot.waitUntil(lambda: host_root.windowOpacity() >= 1.0)

    pages.setCurrentIndex(1)
    assert page.findChild(fxstyle._Reveal) is not None, "a reveal runs"
    end = time.monotonic() + (fxstyle.PANEL_FADE_MS + 200) / 1000
    while time.monotonic() < end:
        QApplication.processEvents()

    assert page.findChild(fxstyle._Reveal) is None, "the reveal ended"
