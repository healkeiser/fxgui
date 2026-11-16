"""A cover paints the colour that is really under it, in both theming modes.

Under an application sheet (FXApplication) every widget holds the app's
opaque palette though it paints nothing; inside a host, a scroll area's
palette is an empty brush that reads black. A cover, a fade or a row fill
must show the card, the frame or the pane the person sees there.
"""

# Built-in
import time

# Third-party
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import (
    FXBreadcrumb,
    FXProgressCard,
    FXSkeleton,
    FXThumbnailDelegate,
)
from fxgui.fxwidgets._breadcrumb import _Strip


def _on(root, kind, content):
    """Put `content` on a card or in a frame band in `root`; return root."""
    if kind == "card":
        box = FXProgressCard(title="Card")
        box.layout().addWidget(content)
    else:
        box = QWidget()
        fxstyle.mark_as_frame(box)
        QVBoxLayout(box).addWidget(content)
    root.layout().addWidget(box)
    return root


def _shown(qtbot, root):
    root.resize(420, 380)
    root.show()
    qtbot.waitExposed(root)
    for _ in range(3):
        QApplication.processEvents()
    return root


def _at(root, widget, point):
    return root.grab().toImage().pixelColor(widget.mapTo(root, point))


@pytest.mark.parametrize("kind", ["card", "frame"])
def test_the_ground_is_what_is_painted_under_an_app_sheet(
    qtbot, app_root, kind
):
    body = QWidget()
    body.setMinimumSize(120, 120)
    inner = QWidget(body)
    inner.setGeometry(10, 10, 40, 40)
    _shown(qtbot, _on(app_root, kind, body))

    drawn = _at(app_root, inner, QPoint(20, 20))
    assert fxstyle._ground(inner) == drawn
    assert drawn != QColor(fxstyle.colors().surface), "a ground of its own"


@pytest.mark.parametrize("kind", ["card", "frame"])
def test_a_skeleton_covers_a_body_in_its_card_s_colour_under_an_app_sheet(
    qtbot, app_root, kind
):
    body = QWidget()
    QVBoxLayout(body).addWidget(QLabel("OLD CONTENT " * 3))
    body.setMinimumSize(240, 160)
    _shown(qtbot, _on(app_root, kind, body))
    corner = body.rect().bottomRight() - QPoint(3, 3)
    ground = _at(app_root, body, corner)

    skeleton = FXSkeleton.cover(body, "lines")
    skeleton._animation.stop()
    QApplication.processEvents()

    assert _at(app_root, body, corner) == ground


def test_a_skeleton_over_a_scroll_area_fills_its_ground_not_black(
    qtbot, host_root
):
    area = QScrollArea()
    page = QWidget()
    QVBoxLayout(page).addWidget(QLabel("OLD CONTENT " * 3))
    area.setWidget(page)
    area.setWidgetResizable(True)
    host_root.layout().addWidget(area)
    _shown(qtbot, host_root)
    corner = area.viewport().rect().bottomRight() - QPoint(3, 3)
    ground = _at(host_root, area.viewport(), corner)

    skeleton = FXSkeleton.cover(area, "rows")
    skeleton._animation.stop()
    QApplication.processEvents()

    assert _at(host_root, area.viewport(), corner) == ground


def _reveal_frames(qtbot, root, pages, kind):
    """Bring `pages`' second page up on a `kind`; return its ground and
    every colour its corner shows while it fades in."""
    _shown(qtbot, _on(root, kind, pages))
    # A page shown with its window rides the window's fade, not a reveal.
    qtbot.waitUntil(lambda: root.windowOpacity() >= 1.0)
    first, second = pages.widget(0), pages.widget(1)
    ground = _at(root, first, QPoint(4, 4)).name()

    pages.setCurrentIndex(1)
    assert second.findChild(fxstyle._Reveal) is not None, "a reveal runs"
    spot = second.rect().bottomRight() - QPoint(6, 6)
    seen = set()
    end = time.monotonic() + (fxstyle.PANEL_FADE_MS + 150) / 1000
    while time.monotonic() < end:
        seen.add(_at(root, second, spot).name())
        QApplication.processEvents()
    assert second.findChild(fxstyle._Reveal) is None, "the reveal ended"
    return ground, seen


@pytest.mark.parametrize("mode", ["host_root", "app_root"])
@pytest.mark.parametrize("kind", ["card", "frame"])
def test_a_stacked_page_fades_in_on_its_card_every_frame(
    qtbot, request, motion, mode, kind
):
    root = request.getfixturevalue(mode)
    pages = QStackedWidget()
    pages.setMinimumSize(240, 160)
    second = QWidget()
    QVBoxLayout(second).addWidget(QLabel("PAGE TWO"))
    pages.addWidget(QWidget())
    pages.addWidget(second)

    ground, seen = _reveal_frames(qtbot, root, pages, kind)

    assert ground != fxstyle.colors().surface.lower(), "a ground of its own"
    assert seen == {ground}


@pytest.mark.parametrize("kind", ["card", "frame"])
def test_a_tab_page_fades_in_on_its_card_in_a_host(
    qtbot, host_root, motion, kind
):
    tabs = QTabWidget()
    tabs.setMinimumSize(240, 160)
    second = QWidget()
    QVBoxLayout(second).addWidget(QLabel("PAGE TWO"))
    tabs.addTab(QWidget(), "one")
    tabs.addTab(second, "two")

    ground, seen = _reveal_frames(qtbot, host_root, tabs, kind)

    assert ground != fxstyle.colors().surface.lower(), "a ground of its own"
    assert seen == {ground}


def _tree_on_card(qtbot, root):
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    delegate = FXThumbnailDelegate(tree)
    delegate.show_thumbnail = False
    tree.setItemDelegate(delegate)
    for name in ("one", "two"):
        QTreeWidgetItem(tree, [name])
    fxstyle.mark_as_thin_scroll(tree)
    _shown(qtbot, _on(root, "card", tree))
    return tree, delegate


def _row_spot(tree, row):
    rect = tree.visualItemRect(tree.topLevelItem(row))
    return QPoint(rect.right() - 4, rect.center().y())


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_rows_on_a_see_through_view_paint_the_card_under_it(
    qtbot, host_root, theme
):
    fxstyle.apply_theme(theme)
    tree, delegate = _tree_on_card(qtbot, host_root)
    viewport = tree.viewport()
    card = _at(host_root, viewport, QPoint(4, viewport.height() - 4))

    assert _at(host_root, viewport, _row_spot(tree, 1)) == card
    # Half way through a hover's fade, the hover mixes from the card.
    delegate._hover_amount = lambda option, index: (
        0.5 if index.row() == 0 else 0.0)
    viewport.update()
    QApplication.processEvents()
    half = fxstyle.mix(card, fxstyle.colors().state_hover, 0.5)
    assert _at(host_root, viewport, _row_spot(tree, 0)).name() == half


def test_the_breadcrumb_strip_paints_the_card_it_sits_on(qtbot, host_root):
    crumb = FXBreadcrumb()
    crumb.set_path(["Project", "Shot", "Task"])
    _shown(qtbot, _on(host_root, "card", crumb))
    strip = crumb.findChild(_Strip)
    card = _at(host_root, crumb, QPoint(crumb.width() // 2, crumb.height() + 3))

    assert card != QColor(fxstyle.colors().surface), "a card of its own"
    assert _at(host_root, strip, strip.rect().bottomRight()
               - QPoint(3, 2)) == card
