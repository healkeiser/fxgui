"""Dock panes in Qt Advanced Docking System, drawn as cards on the frame.

Needs PySide6-QtAds, installed beside the PySide6 it was built for;
importing this module imports it, and nothing else in fxgui does. A window puts an `FXDockArea` where its
body goes and docks its panes on it.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

__all__ = ["FXDockArea", "banner_host", "restorable"]

# Built-in
import re
from typing import Dict, List, Optional, Set, Tuple

# Third-party
import PySide6QtAds as ads
from qtpy.QtCore import (
    QByteArray,
    QEvent,
    QMargins,
    QObject,
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    qUncompress,
)
from qtpy.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPen, QShortcut
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import _compat, fxicons, fxstyle
from fxgui.fxutils import focus_step, later, rehome, repolish

_AREAS = {
    "left": ads.LeftDockWidgetArea,
    "right": ads.RightDockWidgetArea,
    "bottom": ads.BottomDockWidgetArea,
    "top": ads.TopDockWidgetArea,
}

# Panes are cards on the frame; lists and logs are wells set into them.
# Under the manager's id: the base sheet's QFrame[frameShape] rules outrank
# a bare class selector.
fxstyle.register_widget_style(
    """
#fxDocks, #fxDocks ads--CDockContainerWidget, #fxDocks ads--CDockSplitter,
#fxDocks ads--CFloatingDockContainer { background: @frame; }
#fxDocks ads--CDockAreaWidget {
    background: @surface; border: 1px solid @pane_border;
    border-radius: @card_radius;
}
#fxDocks ads--CDockAreaTitleBar, #fxDocks ads--CDockAreaTabBar,
#fxDocks ads--CDockAreaTabBar QWidget#qt_scrollarea_viewport,
#fxDocks ads--CDockAreaTabBar QWidget#tabsContainerWidget, #fxDocks ads--CDockWidget,
#fxDocks ads--CDockWidget > QWidget { background: transparent; }
#fxDocks ads--CTitleBarButton::menu-indicator { image: none; width: 0px; }
/* A tab pill's height: the tab sets the bar's, buttons or not. */
#fxDocks ads--CTitleBarButton { margin: @pane_gap 0px; padding: 0px; }
#fxDocks ads--CDockAreaWidget QAbstractItemView,
#fxDocks ads--CDockAreaWidget QPlainTextEdit,
#fxDocks ads--CDockAreaWidget QTextEdit { background-color: @well; }
/* A header is an item view too, but sits on the pane above its well. */
#fxDocks ads--CDockAreaWidget QHeaderView { background-color: @surface; }
#fxDocks ads--CDockAreaWidget QTreeView::branch,
#fxDocks ads--CDockAreaWidget QTreeView::branch:selected,
#fxDocks ads--CDockAreaWidget QTreeView::branch:!selected:hover {
    background: @well;
}
/* A tree whose delegate owns its rows fills its own indentation. */
#fxDocks ads--CDockAreaWidget QTreeView[fxOwnsRow="true"]::branch,
#fxDocks ads--CDockAreaWidget QTreeView[fxOwnsRow="true"]::branch:selected,
#fxDocks ads--CDockAreaWidget QTreeView[fxOwnsRow="true"]::branch:!selected:hover {
    background: transparent;
}
#fxDocks ads--CDockAreaWidget QComboBox QAbstractItemView {
    background-color: @surface_sunken;
}
/* A pane alone in its area wears its tab as a plain title, not a pill. */
#fxDocks ads--CDockWidgetTab[fxSole="true"],
#fxDocks ads--CDockWidgetTab[fxSole="true"]:hover {
    background: transparent;
}
#fxDocks ads--CDockWidgetTab[fxSole="true"] QLabel {
    color: @text;
}
"""
)

# A pane scrolls itself; ADS's wrapping scroll area takes a Tab stop.
_NO_SCROLL = ads.CDockWidget.eInsertMode.ForceNoScrollArea

_CENTRAL = "central"

# Set on a pane whose content was deleted: QtAds still hands out the
# dangling pointer, and reading it crashes.
_EMPTY = "fxEmpty"

# Each button QtAds draws, by object name, to its icon slot and name.
_BUTTONS = {
    "tabCloseButton": (ads.TabCloseIcon, "x"),
    "dockAreaCloseButton": (ads.DockAreaCloseIcon, "x"),
    "detachGroupButton": (ads.DockAreaUndockIcon, "external-link"),
    "tabsMenuButton": (ads.DockAreaMenuIcon, "chevron-down"),
}

_configured = False

def _configure() -> None:
    """Set the process-wide flags, which apply to managers made after."""
    global _configured
    if _configured:
        return
    _configured = True
    flag = ads.CDockManager.eConfigFlag
    for name in (
        "OpaqueSplitterResize",
        "DockAreaHasCloseButton",
        "DockAreaHasUndockButton",
        "DockAreaHasTabsMenuButton",
        "DockAreaDynamicTabsMenuButtonVisibility",
        "EqualSplitOnInsertion",
        # A tab keeps its whole title; a crowded bar scrolls instead.
        "DisableTabTextEliding",
        # A kept-open pane shows no close button at all.
        "DockAreaHideDisabledButtons",
    ):
        ads.CDockManager.setConfigFlag(getattr(flag, name), True)
    # The area's own close button covers it; the theme boxes a tab's.
    ads.CDockManager.setConfigFlag(flag.ActiveTabHasCloseButton, False)
    icons = ads.CDockManager.iconProvider()
    for slot, name in _BUTTONS.values():
        # A copy: the provider deletes the icon it is given.
        icons.registerCustomIcon(slot, QIcon(fxicons.get_icon(name)))
    # No auto-hide: its pin read as "keep here" and made the pane vanish.
    hide = ads.CDockManager.eAutoHideFlag
    for name in ("AutoHideFeatureEnabled", "DockAreaHasAutoHideButton"):
        ads.CDockManager.setAutoHideConfigFlag(getattr(hide, name), False)


def _recross(docks: "ads.CDockManager") -> None:
    """Give the drop targets a dragged pane shows the theme in force.

    QtAds rebuilds them on their next show once a color is set;
    `updateOverlayIcons` crashes on a cross never shown.
    """
    colors = fxstyle.colors()
    accent = QColor(colors.accent_primary)
    overlay = QColor(accent)
    overlay.setAlpha(64)
    part = ads.CDockOverlayCross.eIconColor
    for cross in docks.findChildren(ads.CDockOverlayCross):
        cross.setIconColor(part.FrameColor, accent)
        cross.setIconColor(
            part.WindowBackgroundColor, QColor(colors.surface_alt))
        cross.setIconColor(part.OverlayColor, overlay)
        cross.setIconColor(part.ArrowColor, QColor(colors.text))
        # QtAds paints this one under its cross icons.
        cross.setIconColor(part.ShadowColor, QColor(colors.shadow))


def _inset(area: "ads.CDockAreaWidget") -> None:
    """Inset `area`'s buttons off its round right corner, and its tabs."""
    bar = area.titleBar()
    bar.layout().setContentsMargins(0, 0, fxstyle.BUTTON_RADIUS, 0)
    # With a tab's half-gap side margin, the first pill sits one gap in, as
    # it sits one gap down: the sheet's QTabBar::tab:first.
    lead = fxstyle.PANE_GAP - fxstyle.PANE_GAP // 2
    bar.tabBar().widget().layout().setContentsMargins(lead, 0, 0, 0)
    # The tabs set the bar's height; a button takes it, its margin inside.
    for button in bar.findChildren(ads.CTitleBarButton):
        policy = button.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Ignored)
        button.setSizePolicy(policy)
        _Square.keep(button)


class _Square(QObject):
    """Keep a title bar button as wide as the bar makes it tall.

    Its height is the tab strip's, its width QtAds' icon's: square, it
    lights a square, as a flat tool button beside it does.
    """

    @classmethod
    def keep(cls, button: QWidget) -> None:
        if getattr(button, "_fx_square", None) is None:
            button._fx_square = cls(button)

    def __init__(self, button: QWidget):
        super().__init__(button)
        button.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Resize and _compat.is_valid(watched):
            side = watched.height()
            if side > 0 and watched.minimumWidth() != side:
                watched.setFixedWidth(side)
        return False


def _bare(tab: "ads.CDockWidgetTab") -> None:
    """Drop the gaps QtAds lays around a tab's title.

    They scale with the font, so only the sheet's padding is left, and a tab
    is its text plus that padding, as a QTabBar tab is.
    """
    layout = tab.layout()
    layout.setContentsMargins(0, 0, 0, 0)
    for index in range(layout.count()):
        spacer = layout.itemAt(index).spacerItem()
        if spacer is not None:
            spacer.changeSize(0, 0)
    layout.invalidate()
    _TabKeys.keep(tab)


class _TabKeys(QObject):
    """Let Left and Right walk a pane's tabs, as a QTabBar's.

    An arrow makes the next open tab current, the focus going with it.
    A tab stays out of Qt's own focus chain: `FXDockArea`'s Tab walk
    stops on a pane's current tab right before its content.
    """

    @classmethod
    def keep(cls, tab: "ads.CDockWidgetTab") -> None:
        if getattr(tab, "_fx_keys", None) is None:
            tab._fx_keys = cls(tab)

    def __init__(self, tab: "ads.CDockWidgetTab"):
        super().__init__(tab)
        self._tab = tab
        tab.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.KeyPress or event.key() not in (
            Qt.Key_Left, Qt.Key_Right
        ):
            return False
        area = self._tab.dockAreaWidget()
        if area is None:
            return False
        bar = area.titleBar().tabBar()
        step = 1 if event.key() == Qt.Key_Right else -1
        index = bar.currentIndex() + step
        while 0 <= index < bar.count() and not bar.isTabOpen(index):
            index += step
        if 0 <= index < bar.count():
            area.setCurrentIndex(index)
            bar.tab(index).setFocus(Qt.TabFocusReason)
        return True


def _area_of(widget: Optional[QWidget]) -> Optional["ads.CDockAreaWidget"]:
    """Return the dock area holding `widget` (a tab or a pane's content)."""
    while widget is not None:
        if isinstance(widget, (ads.CDockWidget, ads.CDockWidgetTab)):
            return widget.dockAreaWidget()
        widget = widget.parentWidget()
    return None


def _strip_tab(
    area: Optional["ads.CDockAreaWidget"],
) -> Optional["ads.CDockWidgetTab"]:
    """Return `area`'s current tab when its strip has tabs to walk."""
    if area is None:
        return None
    bar = area.titleBar().tabBar()
    if sum(bool(bar.isTabOpen(index)) for index in range(bar.count())) < 2:
        return None
    tab = bar.currentTab()
    return tab if tab is not None and tab.isVisible() else None


def _content(held: "ads.CDockWidget") -> Optional[QWidget]:
    """Return `held`'s content, or None once it was deleted."""
    return None if held.property(_EMPTY) else held.widget()


def _open(held: "ads.CDockWidget") -> None:
    """Grow a pane just opened from nothing, its content sliding in."""
    if not fxstyle.motion():
        return
    later(0, held, lambda: _grow(held))


def _grow(held: "ads.CDockWidget") -> None:
    """Widen `held`'s area in its splitter from nothing to the size it took.

    Its neighbour gives the room back as it goes; the content fades in.
    """
    area = held.dockAreaWidget()
    splitter = _compat.parent_widget(area) if area is not None else None
    body = _content(held)
    if body is None or not isinstance(splitter, QSplitter):
        return
    if splitter.count() < 2:
        return
    index = splitter.indexOf(area)
    final = splitter.sizes()
    if index < 0 or final[index] <= 0:
        return
    beside = index - 1 if index > 0 else index + 1
    start = list(final)
    start[beside] += start[index]
    start[index] = 0
    fxstyle._Reveal.over(body, moving=False)
    floor = area.minimumSize()
    area.setMinimumSize(0, 0)

    def still_here() -> bool:
        # A drag or a restore may move the area, or drop the splitter.
        return (
            _compat.is_valid(splitter)
            and _compat.is_valid(area)
            and splitter.indexOf(area) == index
            and splitter.count() == len(final)
        )

    def size(progress: float) -> None:
        if still_here():
            splitter.setSizes([
                round(begin + (end - begin) * progress)
                for begin, end in zip(start, final)
            ])

    def done() -> None:
        if still_here():
            splitter.setSizes(final)
        # Unless `_floor` has set a newer one meanwhile.
        if _compat.is_valid(area) and area.minimumSize().isNull():
            area.setMinimumSize(floor)

    grow = QVariantAnimation(area)
    grow.setDuration(fxstyle.PANEL_OPEN_MS)
    grow.setStartValue(0.0)
    grow.setEndValue(1.0)
    grow.setEasingCurve(fxstyle.ease_spring())
    grow.valueChanged.connect(size)
    grow.finished.connect(done)
    size(0.0)
    grow.start(QVariantAnimation.DeleteWhenStopped)


def _floor(area: "ads.CDockAreaWidget") -> None:
    """Hold `area` at least as big as the tab in front needs.

    QtAds works its floor out once, as a tab joins; a tab whose content
    grows later, or comes to the front, is squeezed under it.
    """
    # A tab change the window's teardown fires, after PySide let go of it.
    if not _compat.is_valid(area):
        return
    held = area.currentDockWidget()
    body = _content(held) if held is not None else None
    if body is None:
        return
    pad = held.layout().contentsMargins()
    # As Qt's layouts do: a minimum the content set beats its hint.
    need = body.minimumSizeHint().expandedTo(body.minimumSize()) + QSize(
        pad.left() + pad.right(), pad.top() + pad.bottom())
    # From the border and the bar, never live sizes: a size caught
    # mid-layout moves the floor, which lays out again.
    edge = area.contentsMargins()
    bar = area.titleBar()
    floor = need + QSize(
        edge.left() + edge.right(),
        edge.top()
        + edge.bottom()
        + (bar.sizeHint().height() if bar.isVisible() else 0),
    )
    if area.minimumSize() != floor:
        area.setMinimumSize(floor)


def _flush_view(widget: QWidget) -> bool:
    """Whether `widget` is a flush row view, one that runs to the border."""
    return isinstance(widget, QAbstractItemView) and bool(
        widget.property(fxstyle.FLUSH_PROPERTY))


class _PaneEdges(QObject):
    """Let a pane's flush row views run to its border; pad the rest.

    The pane's body stands `PANE_GAP` off the pane's sides and bottom
    through its own contents margins, so a form, a filter bar or buttons
    keep the gap a pill keeps off its strip. A flush item view
    (`fxstyle.mark_flush`), and each container between it and the body,
    takes back the gap on every side it touches: its rows, header, column
    rules and summary row reach the pane's border. A container so widened
    gives the gap to its own other children. A text view (a log) keeps the
    gap: its text is read, not scanned in rows. An `FXFilteredTree` in a
    pane flushes its tree.
    """

    def __init__(self, held: QWidget, body: QWidget):
        super().__init__(body)
        self._held = held
        self._body = body
        self._chain: List[QWidget] = []
        # Containers padded for a flush view, with their own margins.
        self._padded: Dict[QWidget, QMargins] = {}
        self._busy = False
        self._queued = False
        body._fx_pane_edges = self
        body.installEventFilter(self)
        held.installEventFilter(self)
        self.rescan()

    def rescan(self) -> None:
        """Find the flush views and the containers that lead to them."""
        gap = fxstyle.PANE_GAP
        body = self._body
        for filtered in [body, *body.findChildren(QWidget)]:
            tree = getattr(filtered, "tree", None)
            if hasattr(filtered, "filter_bar") and isinstance(
                tree, QAbstractItemView
            ) and not tree.property(fxstyle.FLUSH_PROPERTY):
                fxstyle.mark_flush(tree)
        # A view added anywhere in the body later, or one taken out, scans
        # it again: it may be flush, or the chain may lead nowhere now.
        for holder in [body, *body.findChildren(QWidget)]:
            if holder.layout() is not None:
                holder.installEventFilter(self)
        # Undo the last scan's padding: a view unmarked or marked again
        # since must not keep the gap a former state gave it.
        self._held.layout().setContentsMargins(0, 0, 0, 0)
        for padded, margins in self._padded.items():
            if _compat.is_valid(padded):
                padded.setContentsMargins(margins)
        self._padded = {}
        if _flush_view(body):
            body.setContentsMargins(0, 0, 0, 0)
            self._chain = []
            return
        if isinstance(body, QAbstractScrollArea):
            # A text view paints its whole box: the pane holds it off the
            # border, as before, so its text keeps the gap.
            self._held.layout().setContentsMargins(gap, 0, gap, gap)
            self._chain = []
            return
        body.setContentsMargins(gap, 0, gap, gap)
        chain: List[QWidget] = []
        for view in body.findChildren(QAbstractItemView):
            if not _flush_view(view):
                continue
            link = view
            while link is not None and link is not body:
                parent = link.parentWidget()
                # Only through laid-out containers: a splitter or a scroll
                # area places its children itself.
                if parent is None or parent.layout() is None:
                    break
                if link not in chain:
                    chain.append(link)
                    link.installEventFilter(self)
                if parent is not body and parent not in chain:
                    self._padded.setdefault(parent, parent.contentsMargins())
                    parent.setContentsMargins(gap, 0, gap, gap)
                link = parent
        self._chain = chain
        # Outermost first: fitting a link fits the links inside it.
        for link in chain:
            if link.parentWidget() not in chain:
                self._fit(link)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        kind = event.type()
        if watched is self._held:
            if kind in (QEvent.Show, QEvent.ParentChange):
                area = self._held.dockAreaWidget() if _compat.is_valid(
                    self._held) else None
                if area is not None:
                    _PaneCorners.cover(area)
            return False
        if kind in (QEvent.ChildAdded, QEvent.ChildRemoved):
            # Once the new child is laid out, and marked as it will be.
            if not self._queued:
                self._queued = True
                later(0, self, self._rescan_queued)
            return False
        if self._busy:
            return False
        if kind == QEvent.Show and watched is self._body:
            self.rescan()
            return False
        if kind not in (QEvent.Move, QEvent.Resize, QEvent.LayoutRequest):
            return False
        # A link deleted since the last scan, before the queued one.
        if not all(_compat.is_valid(link) for link in self._chain):
            self._chain = [
                link for link in self._chain if _compat.is_valid(link)]
        if kind in (QEvent.Move, QEvent.Resize) and watched in self._chain:
            self._fit(watched)
        elif kind in (QEvent.Resize, QEvent.LayoutRequest):
            for link in self._chain:
                if link.parentWidget() is watched:
                    self._fit(link)
        return False

    def _rescan_queued(self) -> None:
        self._queued = False
        if _compat.is_valid(self._body):
            self.rescan()

    def _fit(self, link: QWidget) -> None:
        """Stretch `link` over the gap on each side it touches."""
        parent = link.parentWidget()
        if parent is None or not _compat.is_valid(link):
            return
        inner = parent.contentsRect()
        whole = parent.rect()
        shape = link.geometry()
        fitted = QRect(shape)
        if shape.left() <= inner.left():
            fitted.setLeft(whole.left())
        if shape.right() >= inner.right():
            fitted.setRight(whole.right())
        if shape.bottom() >= inner.bottom():
            fitted.setBottom(whole.bottom())
        if fitted != shape:
            self._busy = True
            try:
                link.setGeometry(fitted)
            finally:
                self._busy = False
        # Its layout has just put the links inside it back: fit them in
        # turn, so a view any number of containers deep reaches the border.
        for inner in self._chain:
            if inner.parentWidget() is link:
                self._fit(inner)


class _PaneCorners(QWidget):
    """Redraw a pane's bottom arcs over a row that runs to its border.

    The sheet rounds the pane, but a flush view's rows, scroll bar or
    summary row paint the square corner over it. This transparent child
    covers the pane; at each bottom corner it paints the ground outside the
    arc, then the arc.
    """

    @classmethod
    def cover(cls, area: QWidget) -> None:
        """Give `area` its corners once."""
        if area.findChild(cls, "", Qt.FindDirectChildrenOnly) is None:
            cls(area)

    def __init__(self, area: QWidget):
        super().__init__(area)
        self._area = area
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        area.installEventFilter(self)
        self._follow()
        self.show()

    def _follow(self) -> None:
        # QtAds deletes an emptied area while its events still arrive.
        if not (_compat.is_valid(self) and _compat.is_valid(self._area)):
            return
        self.setGeometry(self._area.rect())
        self.raise_()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (
            QEvent.Resize, QEvent.Show, QEvent.ChildAdded, QEvent.LayoutRequest
        ):
            self._follow()
        return False

    def paintEvent(self, event) -> None:
        area = self._area
        if not _compat.is_valid(area):
            return
        outer = QRectF(self.rect())
        radius = fxstyle.CARD_RADIUS
        clip = QPainterPath()
        for x in (outer.left(), outer.right() - radius):
            clip.addRect(QRectF(x, outer.bottom() - radius, radius + 1, radius + 1))
        shape = QPainterPath()
        shape.addRoundedRect(outer, radius, radius)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipPath(clip)
        painter.fillPath(
            clip.subtracted(shape), fxstyle._ground(area.parentWidget()))
        edge = QPainterPath()
        edge.addRoundedRect(outer.adjusted(0.5, 0.5, -0.5, -0.5),
                            radius - 0.5, radius - 0.5)
        painter.setPen(QPen(QColor(fxstyle.colors().pane_border), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(edge)
        painter.end()


class _Floor(QObject):
    """Floor a pane's area again whenever the pane's content re-lays out.

    Marks the pane empty once its content is deleted; the pane stays.
    """

    def __init__(self, held: "ads.CDockWidget") -> None:
        super().__init__(held)
        self._held = held
        body = held.widget()
        body.installEventFilter(self)
        body.destroyed.connect(self._emptied)

    def _emptied(self) -> None:
        # Also sent as the pane itself goes, its wrapper already invalid.
        if _compat.is_valid(self._held):
            self._held.setProperty(_EMPTY, True)
            # QtAds keeps its own pointer to the content: drop it too.
            self._held.takeWidget()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Re-floor on a layout pass or a show of the pane's content."""
        if event.type() in (QEvent.LayoutRequest, QEvent.Show):
            area = self._held.dockAreaWidget()
            if area is not None:
                _floor(area)
        return False


def _xml(state: bytes) -> bytes:
    """Return a saved layout's XML, empty for a broken one."""
    return bytes(qUncompress(QByteArray(state))) or bytes(state)


def _pane_names(xml: bytes) -> Set[bytes]:
    """Return the pane names a layout's XML holds."""
    return set(re.findall(rb'<Widget Name="([^"]*)"', xml))


def restorable(state: bytes, built: bytes) -> bool:
    """Say whether the saved layout `state` may replace the layout `built`.

    Not when it names other panes, which would close the ones it misses,
    nor when it tucks one in a side bar, which reopens it hidden.
    """
    return _restorable(state, built, set())


def _restorable(state: bytes, built: bytes, ignore: Set[bytes]) -> bool:
    """Say what `restorable` says, the panes named in `ignore` left out."""
    saved = _xml(state)
    return b"<SideBar" not in saved and _pane_names(saved) - ignore == (
        _pane_names(_xml(built)) - ignore
    )


def _app_window(widget: QWidget) -> QWidget:
    """Return `widget`'s app window: its nearest main window, or its window.

    A main window embedded in a host is not a window, so `window()` is the
    host's.
    """
    found = widget
    while not found.isWindow() and not isinstance(found, QMainWindow):
        found = found.parentWidget()
    return found


def banner_host(widget: QWidget) -> QWidget:
    """Return where a banner about `widget` goes: its app's dock area.

    A floating pane's widget finds the area of the window it floats from.
    Without one, the dock area in the widget's app window, else that window.
    """
    found = widget
    while found is not None:
        if isinstance(found, FXDockArea):
            return found
        found = rehome(_compat.parent_widget(found))
    window = _app_window(widget)
    return window.findChild(FXDockArea) or window


class FXDockArea(QWidget):
    """Dock named panes around a body, one gap apart, in QtAds.

    A pane's layout saves and restores as bytes. A layout restored before
    the first show waits for it, since the split is sized then.

    Args:
        parent: The parent widget.
        gap: Pixels between panes, and from the panes to the edges.

    Examples:
        >>> docks = FXDockArea()
        >>> window.setCentralWidget(docks)
        >>> docks.set_central(viewer)
        >>> log_toggle = docks.add_dock("log", "Log", log, "bottom")
    """

    def __init__(self, parent: Optional[QWidget] = None, gap: int = fxstyle.FRAME_GAP):
        super().__init__(parent)
        _configure()
        self._gap = gap
        self._sizes: Dict[str, Tuple[int, int]] = {_CENTRAL: (2, 4)}
        self._sides: Dict[str, str] = {}
        self._keep_open = False
        self._placeholder = True
        self._built: Optional[bytes] = None
        # Set once the first show has laid the panes out; a layout being
        # restored meanwhile brings panes up with it, unanimated.
        self._ready = False
        self._restoring = False
        self._pending: Optional[bytes] = None
        self._restored = False
        # The stop a Tab walk turned off to a pane's tab for, and its way.
        self._detour: Optional[Tuple[QWidget, QWidget, bool]] = None
        self._sweep_queued = False
        self._docks = ads.CDockManager(self)
        self._docks.setObjectName("fxDocks")
        # Its own sheet paints tabs light; the theme's registered rules win.
        self._docks.setStyleSheet("")
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self._docks)
        fxstyle.mark_as_frame(self)
        _recross(self._docks)
        self._docks.dockAreaCreated.connect(self._area_created)
        self._docks.floatingWidgetCreated.connect(self._key_the_float)
        self._keep_gaps()
        fxstyle.theme_changed.connect(self._rethemed)
        # The centre must be the first dock added, before any pane.
        held = ads.CDockWidget(self._docks, "")
        held.setObjectName(_CENTRAL)
        held.setWidget(QWidget(), _NO_SCROLL)
        held.setFeature(ads.CDockWidget.DockWidgetFeature.NoTab, True)
        for feature in (
            "DockWidgetClosable",
            "DockWidgetMovable",
            "DockWidgetFloatable",
            "DockWidgetPinnable",
        ):
            held.setFeature(
                getattr(ads.CDockWidget.DockWidgetFeature, feature), False
            )
        self._docks.setCentralWidget(held)
        # Out of the size hints until a body arrives: a window seated before
        # its first show (a tray panel) would otherwise stand its height.
        held.dockAreaWidget().setVisible(False)

    def manager(self) -> "ads.CDockManager":
        """Return the QtAds dock manager under this area."""
        return self._docks

    def set_central(self, widget: QWidget) -> None:
        """Make `widget` the body the panes dock around."""
        held = self._docks.centralWidget()
        old = held.takeWidget()
        held.setWidget(widget, _NO_SCROLL)
        # A view that is the whole pane needs no frame inside the pane's.
        if isinstance(widget, QAbstractScrollArea):
            fxstyle.mark_flush(widget)
        held.dockAreaWidget().setVisible(True)
        self._placeholder = False
        if old is not None:
            old.deleteLater()

    def add_dock(
        self,
        name: str,
        title: str,
        widget: QWidget,
        area: str,
        *,
        beside: str = "",
        size: Tuple[int, int] = (1, 1),
        tab_with: str = "",
    ) -> QAction:
        """Dock `widget` as the pane `name` on `area`; return its toggle.

        `area` is "left", "right", "bottom" or "top": of the window, or of
        the pane `beside`. Without `beside`, a second pane on one side tabs
        with the first; `tab_with` tabs it behind that pane wherever it
        sits. `size` weighs the pane across and down at the first show.

        Raises:
            ValueError: `area` is unknown, or no pane is named `beside`
                or `tab_with`.
        """
        if area not in _AREAS:
            raise ValueError(f"no dock area {area!r}; one of {list(_AREAS)}")
        for other in (beside, tab_with):
            if other and self._docks.findDockWidget(other) is None:
                raise ValueError(f"no pane named {other!r} to dock {name!r} by")
        held = ads.CDockWidget(self._docks, title)
        held.setObjectName(name)
        held.setWidget(widget, _NO_SCROLL)
        # A view that is the whole pane needs no frame inside the pane's.
        if isinstance(widget, QAbstractScrollArea):
            fxstyle.mark_flush(widget)
        _PaneEdges(held, widget)
        # A pane picked by its tab rises in; one a person opens grows
        # open. `triggered`, not `viewToggled`: a window building or
        # restoring its layout toggles every pane, and none may grow.
        held.visibilityChanged.connect(
            lambda shown, held=held: shown and self._reveal(held)
        )
        held.toggleViewAction().triggered.connect(
            lambda checked, held=held: checked and _open(held)
        )
        # The content's gap to the pane's edges is the body's own (see
        # _PaneEdges), so a flush view can run to the border.
        held.layout().setContentsMargins(0, 0, 0, 0)
        _bare(held.tabWidget())
        # Its content's floor, not QtAds' 60 px: a narrower pane clips.
        held.setMinimumSizeHintMode(
            ads.CDockWidget.eMinimumSizeHintMode.MinimumSizeHintFromContent
        )
        _Floor(held)
        self._sizes[name] = tuple(size)
        if tab_with:
            joined = self._docks.findDockWidget(tab_with)
            self._docks.addDockWidgetTabToArea(held, joined.dockAreaWidget())
            joined.setAsCurrentTab()
        elif beside:
            target = self._docks.findDockWidget(beside).dockAreaWidget()
            self._docks.addDockWidget(_AREAS[area], held, target)
        else:
            tabbed = [
                other
                for other in self._docks.dockWidgetsMap().values()
                if self._sides.get(other.objectName()) == area
                and not other.isClosed()
            ]
            self._sides[name] = area
            if tabbed:
                self._docks.addDockWidgetTabToArea(
                    held, tabbed[0].dockAreaWidget()
                )
            else:
                self._docks.addDockWidget(_AREAS[area], held)
        return held.toggleViewAction()

    def _settled(self) -> bool:
        """Whether the window shows, and its panes have come up with it."""
        return (
            self._ready
            and not self._restoring
            and self.window().windowOpacity() >= 1.0
        )

    def _reveal(self, held: "ads.CDockWidget") -> None:
        """Fade `held` in, unless its window is still coming up."""
        body = _content(held)
        if body is not None and self._settled():
            fxstyle._Reveal.over(body)

    def show_dock(self, name: str, activate: bool = True) -> None:
        """Open the pane `name`, in front of its tabs and its window.

        A closed pane grows open once its window has settled.

        Args:
            name: The pane's name.
            activate: Raise and focus a floating pane's window. False
                makes the pane its tabs' current one and leaves the
                windows' order and focus alone.
        """
        held = self._docks.findDockWidget(name)
        if held is None:
            return
        opening = held.isClosed() and self._settled()
        held.toggleView(True)
        if opening:
            _open(held)
        held.setAsCurrentTab()
        floating = held.floatingDockContainer()
        if activate and floating is not None:
            floating.raise_()
            floating.activateWindow()

    def hide_dock(self, name: str) -> None:
        """Close the pane `name`, as its toggle does; nothing if unknown.

        Before the first show, the layout Reset goes back to keeps it closed.
        """
        held = self._docks.findDockWidget(name)
        if held is not None:
            held.toggleView(False)

    def is_dock_open(self, name: str) -> bool:
        """Return whether the pane `name` is open; False if unknown."""
        held = self._docks.findDockWidget(name)
        return held is not None and not held.isClosed()

    def set_dock_title(self, name: str, title: str) -> None:
        """Rename the pane `name`'s tab."""
        held = self._docks.findDockWidget(name)
        if held is not None:
            held.setWindowTitle(title)

    def set_dock_tip(self, name: str, tip: str) -> None:
        """Give the pane `name`'s tab the tooltip `tip`."""
        held = self._docks.findDockWidget(name)
        if held is not None:
            held.tabWidget().setToolTip(tip)

    def keep_panes_open(self) -> None:
        """Open every pane for good, and after every layout restore.

        For a window with no menu to reopen a closed pane from.
        """
        self._keep_open = True
        self._hold_open()

    def fix_panes(self) -> None:
        """Fix every pane docked now where it is: none moves, floats or closes.

        For a window with nowhere to put a pane, such as a tray panel. A pane
        still opens and shuts through its toggle.
        """
        held_by = ads.CDockWidget.DockWidgetFeature
        for held in self._panes():
            for feature in (
                held_by.DockWidgetClosable,
                held_by.DockWidgetMovable,
                held_by.DockWidgetFloatable,
                held_by.DockWidgetPinnable,
            ):
                held.setFeature(feature, False)

    def save_state(self) -> bytes:
        """Return the layout, or the one waiting for the first show."""
        if self._built is None and self._pending is not None:
            return self._pending
        return bytes(self._docks.saveState())

    def restore_state(self, state: bytes) -> bool:
        """Put back the layout `state`; say whether it was taken.

        Refused when `restorable` says no against the panes docked now.
        """
        # An unfilled centre is docked until the first show drops it, so a
        # layout saved on either side of that show may name it or not.
        ignore = {_CENTRAL.encode()} if self._placeholder else set()
        if not _restorable(state, bytes(self._docks.saveState()), ignore):
            return False
        if self._built is None:
            self._pending = bytes(state)
        else:
            self._restore(state)
        return True

    def reset_layout(self) -> None:
        """Put every pane back where the first show placed it."""
        if self._built is not None:
            self._restore(self._built)

    def clear_top(self, width: int, height: int) -> int:
        """Return the top for a `width` x `height` card at the top right.

        One gap in from the right edge, and one gap under the topmost pane
        title bar in that corner. A taller card covers the title bars below
        it rather than moving down past them, which lands it mid-window.
        """
        left = self.width() - width - self._gap
        column = QRect(left, 0, width, max(self.height(), height, 1))
        corner = [
            box
            for box in (
                QRect(bar.mapTo(self, QPoint(0, 0)), bar.size())
                for bar in self._title_bars()
            )
            if box.intersects(column)
        ]
        if not corner:
            return self._gap
        return min(corner, key=QRect.top).bottom() + 1 + self._gap

    def showEvent(self, event) -> None:
        """Size the split at the first show, then apply a waiting layout."""
        super().showEvent(event)
        if self._built is not None:
            return
        # Insetted as each area was made, before a host window's sheet
        # reached its buttons.
        for area in self._docks.findChildren(ads.CDockAreaWidget):
            _inset(area)
        self._settle()
        self._built = bytes(self._docks.saveState())
        if self._pending is not None:
            self._restore(self._pending)
            self._pending = None
        self._hold_open()
        # A window that grows to fit does so after its children's show.
        settled = self.size()
        later(0, self, lambda: self._resettle(settled))

    def _resettle(self, settled: QSize) -> None:
        """Split again at the shown size, if the show changed it."""
        self._ready = True
        if self.size() == settled:
            return
        # A layout restored since the show stays; only the reset target moves.
        kept = bytes(self._docks.saveState()) if self._restored else None
        self._split(self._docks.rootSplitter(), self.width(), self.height())
        self._built = bytes(self._docks.saveState())
        if kept is not None:
            self._restore(kept)

    def focusNextPrevChild(self, next: bool) -> bool:  # noqa: A002
        """Move Tab to the next widget in the chain that takes focus itself.

        Qt's own walk stops at a widget whose focus proxy sits elsewhere in
        the chain, and jumps there.
        """
        window = self.window()
        start = window.focusWidget()
        if start is None:
            return bool(super().focusNextPrevChild(next))
        reason = Qt.TabFocusReason if next else Qt.BacktabFocusReason
        if isinstance(start, ads.CDockWidgetTab):
            found = self._from_tab(start, next)
            if found is None:
                return bool(super().focusNextPrevChild(next))
            found.setFocus(reason)
            return True
        found = self._next_stop(start, next)
        if found is None:
            return bool(super().focusNextPrevChild(next))
        # A pane's tab strip is one stop, right before its content: on
        # the way in forward, on the way out backward.
        here = _area_of(start)
        tab = _strip_tab(_area_of(found) if next else here)
        if tab is not None and _area_of(found) is not here:
            self._detour = (tab, found, next)
            tab.setFocus(reason)
            return True
        found.setFocus(reason)
        return True

    def _stops(self, widget: QWidget) -> bool:
        """Whether Tab may stop on `widget`."""
        window = self.window()
        return bool(
            widget.focusPolicy() & Qt.TabFocus
            and rehome(widget.focusProxy()) is None
            and widget.isVisibleTo(window)
            and widget.isEnabled()
            and widget.window() is window
        )

    def _next_stop(
        self, start: QWidget, forward: bool, skip=None
    ) -> Optional[QWidget]:
        """Return the stop after `start` in the chain, or None.

        Qt's own walk stops at a widget whose focus proxy sits elsewhere
        in the chain, and jumps there. `skip` passes a dock area's widgets.
        """
        widget = start
        while True:
            widget = focus_step(widget, forward)
            if widget is None or widget is start:
                return None
            if self._stops(widget) and (
                skip is None or _area_of(widget) is not skip
            ):
                return widget

    def _from_tab(
        self, tab: "ads.CDockWidgetTab", forward: bool
    ) -> Optional[QWidget]:
        """Return the stop after a pane's tab: its content, or before it."""
        detour, self._detour = self._detour, None
        area = tab.dockAreaWidget()
        if detour is not None:
            was, found, way = detour
            if (
                was is tab and way == forward
                and _compat.is_valid(found) and self._stops(found)
                and (_area_of(found) is area) == forward
            ):
                return found
        content = tab.dockWidget().widget()
        if content is None:
            return None
        first = content if self._stops(content) else self._next_stop(
            content, True)
        if first is None or _area_of(first) is not area:
            return None
        if forward:
            return first
        return self._next_stop(first, False, skip=area)

    def _restore(self, state: bytes) -> None:
        self._restored = True
        self._restoring = True
        try:
            self._docks.restoreState(QByteArray(state))
            self._hold_open()
        finally:
            self._restoring = False

    def _panes(self) -> List["ads.CDockWidget"]:
        return [
            held
            for name, held in self._docks.dockWidgetsMap().items()
            if name != _CENTRAL
        ]

    def _hold_open(self) -> None:
        """Take away every way to close a pane, once `keep_panes_open` ran."""
        if not self._keep_open:
            return
        closable = ads.CDockWidget.DockWidgetFeature.DockWidgetClosable
        for held in self._panes():
            held.setFeature(closable, False)
            toggle = held.toggleViewAction()
            toggle.setVisible(False)
            # Hidden, a Qt 6 action still triggers.
            toggle.setEnabled(False)
            if held.isClosed():
                held.toggleView(True)
            area = held.dockAreaWidget()
            if area is not None:
                # Asked again: a first show brings back a disabled button.
                area.titleBar().button(ads.TitleBarButtonClose).setVisible(
                    True
                )

    def _title_bars(self) -> List[QWidget]:
        """Return every pane title bar shown in this area's own window."""
        return [
            bar
            for bar in self._docks.findChildren(ads.CDockAreaTitleBar)
            if bar.isVisible() and bar.window() is self.window()
        ]

    def _area_created(self, area: "ads.CDockAreaWidget") -> None:
        _inset(area)
        area.currentChanged.connect(lambda _index: _floor(area))
        bar = area.titleBar().tabBar()
        for signal in (bar.tabOpened, bar.tabClosed, bar.tabInserted):
            signal.connect(self._resweep)

    def _rethemed(self, _theme: str = "") -> None:
        """Redraw the drop targets in the new theme."""
        _recross(self._docks)

    def _sweep(self) -> None:
        """Give every splitter and container the one gap."""
        gap = self._gap
        docks = self._docks
        for container in [docks, *docks.findChildren(ads.CDockContainerWidget)]:
            container.layout().setContentsMargins(gap, gap, gap, gap)
        for splitter in docks.findChildren(ads.CDockSplitter):
            if splitter.property(fxstyle.FRAME_PROPERTY) is not True:
                splitter.setHandleWidth(gap)
                fxstyle.mark_as_frame(splitter)
        for area in docks.findChildren(ads.CDockAreaWidget):
            sole = area.openDockWidgetsCount() == 1
            for held in area.dockWidgets():
                tab = held.tabWidget()
                if tab.property("fxSole") is not sole:
                    tab.setProperty("fxSole", sole)
                    repolish(tab)
                    for label in tab.findChildren(QLabel):
                        repolish(label)

    def _keep_gaps(self) -> None:
        """Sweep now, and after every change QtAds makes to its tree.

        Signals, not an event filter: a Python filter on QtAds' own widgets
        crashed natively.
        """
        self._sweep()
        docks = self._docks
        for signal in (
            docks.dockAreasAdded,
            docks.dockAreasRemoved,
            docks.dockAreaCreated,
            docks.floatingWidgetCreated,
            docks.stateRestored,
            docks.dockWidgetAdded,
        ):
            signal.connect(self._resweep)
        docks.floatingWidgetCreated.connect(self._follow)

    def _resweep(self, *_args) -> None:
        """Sweep once after the burst of signals one change sends."""
        if not self._sweep_queued:
            self._sweep_queued = True
            later(0, self, self._queued_sweep)

    def _queued_sweep(self) -> None:
        self._sweep_queued = False
        self._sweep()

    def _follow(self, floating: "ads.CFloatingDockContainer") -> None:
        """Sweep again as a floating window's own tree changes."""
        container = floating.dockContainer()
        container.dockAreasAdded.connect(self._resweep)
        container.dockAreasRemoved.connect(self._resweep)

    def _key_the_float(self, floating: QWidget) -> None:
        """Answer the window's own keys inside `floating`, a pane's window.

        A floating pane is a window of its own, where a window key is dead.
        A widget's own key stays its own.
        """
        window = _app_window(self)
        own = [
            action
            for action in window.actions()
            if action.shortcutContext() != Qt.WidgetShortcut
        ]
        wide = [
            action
            for action in window.findChildren(QAction)
            if action.shortcutContext() == Qt.WindowShortcut
        ]
        floating.addActions(
            [
                action
                for action in dict.fromkeys([*own, *wide])
                if action.shortcuts()
            ]
        )
        for shortcut in window.findChildren(
            QShortcut, options=Qt.FindDirectChildrenOnly
        ):
            # Already live everywhere: a copy makes the key ambiguous.
            if shortcut.context() == Qt.ApplicationShortcut:
                continue
            copy = QShortcut(shortcut.key(), floating)
            copy.setContext(shortcut.context())
            copy.activated.connect(shortcut.activated)

    def _settle(self) -> None:
        """Drop an unfilled centre, then split every side by pane sizes."""
        middle = self._docks.centralWidget()
        if middle is not None and self._placeholder:
            # Removed, never deleted: QtAds names the centre in every saved
            # layout, so a deleted one crashes the next save.
            self._docks.removeDockWidget(middle)
            # Parented, or Python frees the orphan as this call returns.
            middle.setParent(self._docks)
            middle.hide()
        self._split(self._docks.rootSplitter(), self.width(), self.height())

    def _split(self, splitter: QSplitter, width: int, height: int) -> None:
        """Size `splitter`'s children by weight, then theirs within them."""
        across = splitter.orientation() == Qt.Horizontal
        children = [splitter.widget(i) for i in range(splitter.count())]
        weights = [self._weight(child, 0 if across else 1) for child in children]
        if not weights:
            return
        total = width if across else height
        sizes = [total * weight // sum(weights) for weight in weights]
        for index, weight in enumerate(weights):
            splitter.setStretchFactor(index, weight)
        splitter.setSizes(sizes)
        for child, size in zip(children, sizes):
            if isinstance(child, QSplitter):
                self._split(
                    child,
                    size if across else width,
                    height if across else size,
                )

    def _weight(self, child: QWidget, axis: int) -> int:
        """Return a splitter child's weight on `axis`: its largest pane's."""
        while isinstance(child, QSplitter):
            child = child.widget(0)
        panes = child.dockWidgets() if hasattr(child, "dockWidgets") else []
        sizes = [self._sizes.get(pane.objectName()) for pane in panes]
        return max((size[axis] for size in sizes if size), default=1)
