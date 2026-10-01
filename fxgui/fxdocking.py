"""Dock panes in Qt Advanced Docking System, drawn as cards on the frame.

Needs the `docking` extra (PySide6-QtAds); importing this module imports
it, and nothing else in fxgui does. A window puts an `FXDockArea` where its
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
    QObject,
    QPoint,
    QRect,
    QSize,
    Qt,
    qUncompress,
)
from qtpy.QtGui import QAction, QColor, QIcon, QShortcut
from qtpy.QtWidgets import QSplitter, QVBoxLayout, QWidget

# Internal
from fxgui import _compat, fxicons, fxstyle
from fxgui.fxutils import focus_step, later, rehome

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
    border-radius: @button_radius;
}
#fxDocks ads--CDockAreaTitleBar, #fxDocks ads--CDockAreaTabBar,
#fxDocks ads--CDockAreaTabBar QWidget#qt_scrollarea_viewport,
#fxDocks ads--CDockAreaTabBar QWidget#tabsContainerWidget, #fxDocks ads--CDockWidget,
#fxDocks ads--CDockWidget > QWidget { background: transparent; }
#fxDocks ads--CTitleBarButton::menu-indicator { image: none; width: 0px; }
/* No taller than a tab, so the tab sets the bar's height, buttons or not. */
#fxDocks ads--CTitleBarButton { margin: 0px; padding: 0px; }
#fxDocks ads--CDockAreaWidget QAbstractItemView,
#fxDocks ads--CDockAreaWidget QPlainTextEdit,
#fxDocks ads--CDockAreaWidget QTextEdit { background-color: @well; }
#fxDocks ads--CDockAreaWidget QTreeView::branch,
#fxDocks ads--CDockAreaWidget QTreeView::branch:selected,
#fxDocks ads--CDockAreaWidget QTreeView::branch:!selected:hover {
    background: @well;
}
#fxDocks ads--CDockAreaWidget QComboBox QAbstractItemView {
    background-color: @surface_sunken;
}
"""
)

# A pane scrolls itself; ADS's wrapping scroll area takes a Tab stop.
_NO_SCROLL = ads.CDockWidget.eInsertMode.ForceNoScrollArea

_CENTRAL = "central"

# Each button QtAds draws, by object name, to its icon slot and name.
_BUTTONS = {
    "tabCloseButton": (ads.TabCloseIcon, "close"),
    "dockAreaCloseButton": (ads.DockAreaCloseIcon, "close"),
    "detachGroupButton": (ads.DockAreaUndockIcon, "open_in_new"),
    "tabsMenuButton": (ads.DockAreaMenuIcon, "expand_more"),
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
        # A copy: the provider deletes the icon it is given. A hovered
        # button sits on the neutral hover fill, so Active keeps the ink.
        icons.registerCustomIcon(
            slot, QIcon(fxicons.get_icon(name, inks={"active": "icon"})))
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
        # QtAds paints this one under its cross icons; black, as a shadow is.
        cross.setIconColor(part.ShadowColor, QColor(0, 0, 0, 64))


def _inset(area: "ads.CDockAreaWidget") -> None:
    """Inset `area`'s buttons off its round right corner.

    The tabs start at the pane's edge, as a tab bar's do at its own: a
    tab's margin already clears the corner.
    """
    bar = area.titleBar()
    bar.layout().setContentsMargins(0, 0, fxstyle.BUTTON_RADIUS, 0)


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


def _floor(area: "ads.CDockAreaWidget") -> None:
    """Hold `area` at least as big as the tab in front needs.

    QtAds works its floor out once, as a tab joins; a tab whose content
    grows later, or comes to the front, is squeezed under it.
    """
    held = area.currentDockWidget()
    if held is None or held.widget() is None:
        return
    need = held.widget().minimumSizeHint()
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


class _Floor(QObject):
    """Floor a pane's area again whenever the pane's content re-lays out."""

    def __init__(self, held: "ads.CDockWidget") -> None:
        super().__init__(held)
        self._held = held
        held.widget().installEventFilter(self)

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
    saved = _xml(state)
    return b"<SideBar" not in saved and _pane_names(saved) == _pane_names(
        _xml(built)
    )


def banner_host(widget: QWidget) -> QWidget:
    """Return where a banner about `widget` goes: its app's dock area.

    A floating pane's widget finds the area of the window it floats from.
    Without one, the widget's own window.
    """
    found = widget
    while found is not None:
        if isinstance(found, FXDockArea):
            return found
        found = rehome(_compat.parent_widget(found))
    return widget.window()


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

    def __init__(self, parent: Optional[QWidget] = None, gap: int = 6):
        super().__init__(parent)
        _configure()
        self._gap = gap
        self._sizes: Dict[str, Tuple[int, int]] = {_CENTRAL: (2, 4)}
        self._sides: Dict[str, str] = {}
        self._keep_open = False
        self._placeholder = True
        self._built: Optional[bytes] = None
        self._pending: Optional[bytes] = None
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

    def manager(self) -> "ads.CDockManager":
        """Return the QtAds dock manager under this area."""
        return self._docks

    def set_central(self, widget: QWidget) -> None:
        """Make `widget` the body the panes dock around."""
        held = self._docks.centralWidget()
        old = held.takeWidget()
        held.setWidget(widget, _NO_SCROLL)
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

    def show_dock(self, name: str) -> None:
        """Open the pane `name`, in front of its tabs and its window."""
        held = self._docks.findDockWidget(name)
        if held is None:
            return
        held.toggleView(True)
        held.setAsCurrentTab()
        floating = held.floatingDockContainer()
        if floating is not None:
            floating.raise_()
            floating.activateWindow()

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

    def save_state(self) -> bytes:
        """Return the layout, or the one waiting for the first show."""
        if self._built is None and self._pending is not None:
            return self._pending
        return bytes(self._docks.saveState())

    def restore_state(self, state: bytes) -> bool:
        """Put back the layout `state`; say whether it was taken.

        Refused when `restorable` says no against the panes docked now.
        """
        if not restorable(state, bytes(self._docks.saveState())):
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
        """Return the highest top for a `width` x `height` card at the right.

        One gap in from the right edge, below every pane title bar it would
        cover.
        """
        left = self.width() - width - self._gap
        bars = sorted(
            (
                QRect(bar.mapTo(self, QPoint(0, 0)), bar.size())
                for bar in self._title_bars()
            ),
            key=QRect.top,
        )
        top = self._gap
        for bar in bars:
            if QRect(left, top, width, height).intersects(bar):
                top = bar.bottom() + 1 + self._gap
        return top

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

    def focusNextPrevChild(self, next: bool) -> bool:  # noqa: A002
        """Move Tab to the next widget in the chain that takes focus itself.

        Qt's own walk stops at a widget whose focus proxy sits elsewhere in
        the chain, and jumps there.
        """
        window = self.window()
        start = window.focusWidget()
        if start is None:
            return bool(super().focusNextPrevChild(next))
        widget = start
        while True:
            found = focus_step(widget, next)
            if found is None or found is start:
                return bool(super().focusNextPrevChild(next))
            widget = found
            if (
                widget.focusPolicy() & Qt.TabFocus
                and rehome(widget.focusProxy()) is None
                and widget.isVisibleTo(window)
                and widget.isEnabled()
                and widget.window() is window
            ):
                widget.setFocus(
                    Qt.TabFocusReason if next else Qt.BacktabFocusReason
                )
                return True

    def _restore(self, state: bytes) -> None:
        self._docks.restoreState(QByteArray(state))
        self._hold_open()

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

    def _rethemed(self, _theme: str = "") -> None:
        """Redraw the drop targets and refit the tab bars in the new theme."""
        _recross(self._docks)
        for area in self._docks.findChildren(ads.CDockAreaWidget):
            _inset(area)

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
        window = self.window()
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
